import sgtk
from sgtk.platform.qt import QtCore
import os.path

logger = sgtk.platform.get_logger(__name__)

import traceback

def logerrors_decorate(func):
    def func_wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception:
            logger.error("Error calling %s(%s, %s):\n%s" % (
                func.__name__, args, kwargs, traceback.format_exc()))
    return func_wrapper

def q2e(q):
    return q and {'type': q['type'], 'id' : q['id']}

class TakeMediaProcessor(QtCore.QObject):

    # These are the fields in the MocapTakes (under a ShootDay) used to match the video file
    REQUIRED_MOCAPTAKE_FIELDS = ['sg_slate', 'sg_take_number']

    signalIntervalMatched = QtCore.Signal(object, object)
    signalFileIngesting = QtCore.Signal(object)
    signalFileIngested = QtCore.Signal(object)
    signalVersionExists = QtCore.Signal(object, object)
    signalCameraLinked = QtCore.Signal(object, object)
    signalMovieUploading = QtCore.Signal(object, object)
    signalMovieUploaded = QtCore.Signal(object, object)

    def __init__(self, takesModel, app):
        super(TakeMediaProcessor, self).__init__()
        self.takesModel = takesModel
        self.app = app

    @logerrors_decorate
    def processFile(self, filePath, fileName, fileInterval, fileCamera):
        # File processing must be idempotent,
        # e.g. it can be started, stopped, restarted and re-run
        # without duplicating.
        # IOW: Any step in this process should be able to fail and be re-run later.

        logger.info("===== processing file %s %s %s" % (fileName, fileCamera, fileInterval))

        # find corresponding mocap take
        sgMocapTake = self.takesModel.findCoveringTakeSGData(fileInterval)
        if not sgMocapTake:
            logger.warning("no match (skipped)")
            return
        else:
            logger.info("matched to %s with %d%% coverage" % (sgMocapTake['code'], (sgMocapTake['fvl_match_coverage'] * 100)))

        self.signalIntervalMatched.emit(filePath, sgMocapTake)

        # 1) Is there already a file at the templated target path?

        # - evaluate template to get version path
        ignore, fileExtension = os.path.splitext(fileName)
        versionPath = self.evalTemplate(
            'take_vidref_version_path',
            Slate=sgMocapTake['sg_slate']['name'],
            MocapTake=sgMocapTake['code'],
            MocapTakeNumber=sgMocapTake['sg_take_number'],
            Camera=fileCamera,
            file_type=fileExtension[1:]
        )

        project = self.app.context.project

        self.signalFileIngesting.emit(filePath)

        if not os.path.isfile(versionPath):
            logger.info("ingesting file")

            # - ensure folders exist (so we can copy there!)
            logger.info("ensuring directory exists")
            versionFolder = os.path.dirname(versionPath)
            self.app.ensure_folder_exists(versionFolder)

            INGEST_POLICY_KEY = 'file_ingest_policy'
            ingestPolicy = self.app.get_setting(INGEST_POLICY_KEY)
            if ingestPolicy == 'copy':
                # - copy file to target folder
                logger.info("copying to %s" % (versionFolder))
                sgtk.util.filesystem.copy_file(filePath, versionFolder, permissions=0440)

                # - rename to template name
                versionName = os.path.basename(versionPath)
                os.chdir(versionFolder)
                logger.info("renaming %s to %s" % (fileName, versionName))
                os.rename(fileName, versionName)

                # -  set read-only and not public
                logger.info("setting 0440 read-only")
                os.chmod(versionName, 0440)
            elif ingestPolicy == 'symlink':
                # - link file in target folder
                logger.info("linking %s to %s" % (versionPath, filePath))

                # build a relative path from versionPath to filePath
                relativePath = os.path.relpath(filePath, versionFolder)

                if os.name == 'nt':
                    self.winSymlink(relativePath, versionPath)
                else:
                    os.symlink(relativePath, versionPath)
            else:
                logger.error("Bad value '%s' for configuration key %s" % (ingestPolicy, INGEST_POLICY_KEY))

        self.signalFileIngested.emit(filePath)

        # 2) Does a Version with that path linked to the mocaptake exist?

        sgVersion = self.findTakeVersion(project, sgMocapTake, versionPath)
        if not sgVersion:
            logger.info("creating Version for %s camera %s" % (sgMocapTake['code'], fileCamera))

            # - create Version linked to mocap take and path
            versionName = self.evalTemplate(
                "take_vidref_version_name",
                MocapTake = sgMocapTake['code'],
                Camera = fileCamera
            )

            sgVersion = self.createTakeVersion(project, sgMocapTake, versionName, versionPath, fileInterval)
        else:
            versionName = sgVersion['code']
            logger.info("version already exists for %s" % versionName)

        self.signalVersionExists.emit(filePath, sgVersion)

        # 3) Is the Camera linked to the Version?

        sgCamera = self.findCamera(project, fileCamera)
        if not sgCamera:
            logger.warn("Camera %s not found: camera linking skipped for %s" % (fileCamera, versionName))
        else:
            if not self.versionHasCamera(sgVersion, sgCamera):
                logger.info("setting Version %s to Camera %s" % (versionName, fileCamera))
                self.setVersionCamera(sgVersion, sgCamera)
            else:
                logger.info("Version already has Camera %s" % fileCamera)

        self.signalCameraLinked.emit(filePath, sgVersion)

        # 4) Is movie uploaded?

        self.signalMovieUploading.emit(filePath, sgVersion)

        if not sgVersion['sg_uploaded_movie']:
            # - upload file from target folder into Version (see below snippet)
            logger.info("uploading %s to Version" % versionName)
            self.uploadMovie(sgVersion['id'], versionPath)
        else:
            logger.info("Version %s already has uploaded movie" % versionName)

        self.signalMovieUploaded.emit(filePath, sgVersion)

    def evalTemplate(self, name, validate=True, **kwargs):
        template = self.app.get_template(name)
        ctx = self.app.context.as_template_fields(template, validate=validate)
        ctx.update(kwargs)
        return template.apply_fields(ctx)

    def winSymlink(self, relativePath, versionPath):
        # requires
        # - Windows >= Vista
        # - user has CreateSymbolicLink priv
        # - user has remote to remote link evaluation priv
        import win32file
        linkFiles = 0
        linkDirectories = 1
        win32file.CreateSymbolicLink(versionPath, relativePath, linkFiles)

    def findTakeVersion(self, sgProject, sgMocapTake, versionPath):
        return self.app.shotgun.find_one(
            "Version",
            filters=[['project', 'is', sgProject],
                     ['entity', 'is', q2e(sgMocapTake)],
                     ['sg_path_to_movie', 'is', versionPath]],
            fields=['code', 'sg_camera', 'sg_uploaded_movie'])

    def createTakeVersion(self, sgProject, sgMocapTake, versionName, versionPath, interval):
        # Note: Version timecode fields are strings, MocapTakes fields are type timecode
        data = {'project': sgProject,
                'entity': q2e(sgMocapTake),
                'code': versionName,
                'sg_timecode_start': unicode(interval.Start),
                'sg_timecode_end': unicode(interval.EndTC),
                'sg_path_to_movie' : versionPath,
                'sg_camera' : None,
                'sg_uploaded_movie' : None,
                }

        # if we can, we should add this version to the Ingest task for the MocapTake now
        #task_id = self.getTaskID(sgProject, sgMocapTake, 'ingest')
        #if task_id:
        #    data.update({'sg_task': {'type': 'Task', 'id': task_id}})

        entry = self.app.shotgun.create('Version', data)

        return entry

    def uploadMovie(self, version_id, path):
        return self.app.shotgun.upload('Version', version_id, path, field_name='sg_uploaded_movie')

    def findCamera(self, sgProject, cameraName):
        return self.app.shotgun.find_one(
            "Camera",
            filters=[['project', 'is', sgProject],
                     ['code', 'is', cameraName]])

    def versionHasCamera(self, sgVersion, sgCamera):
        return sgCamera == q2e(sgVersion['sg_camera'])

    def setVersionCamera(self, sgVersion, sgCamera):
        self.app.shotgun.update(
            "Version", sgVersion['id'],
            {"sg_camera" : sgCamera},
        )

    def getTaskID(self, sgProject, sgEntity, taskName='ingest'):
        """
        Built for ingest purposes... can be used for other task names
        Get the Task id for the specified entity based on project and task name.
        :param sgProject: (sg_data) Project dict
        :param sgEntity: (sg_data) entity
        :param task_name: (string) task name
        :return: (int) Task id or None
        """
        sgEntity = self.app.shotgun.find_one(
            sgEntity['type'],
            fields=['tasks'],
            filters=[['project', 'is', sgProject],
            ['id', 'is', sgEntity['id']]])
        if not sgEntity or not sgEntity.has_key('tasks'):
            return None
        task_id = None
        for task in sgEntity['tasks']:
            if task['name'].lower() == taskName.lower():
                task_id = task['id']
        return task_id
