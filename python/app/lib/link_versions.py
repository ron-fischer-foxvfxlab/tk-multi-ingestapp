class TakeMediaProcessor(object):
    def __init__(self, takesModel, bundle):
        self.takesModel = takesModel
        self.sg = bundle.shotgun

    def getOrCreateVersions(self, filesModel):
        rootPath = filesModel.rootPath()
        rootIndex = filesModel.index(rootPath)

        print "Processing files in", rootPath, "..."

        row = 0
        while True:
            fileIndex = rootIndex.child(row, 0)
            if not fileIndex.isValid():
                return
            self.processFile(fileIndex)
            row += 1

    def processFile(self, fileIndex):
        fileModel = fileIndex.model()
        fileName = fileModel.fileName(fileIndex)

        # find corresponding mocap take
        fileInterval = fileModel.interval(fileIndex)
        fileCamera = fileModel.camera(fileIndex)
        mocapTake = self.takesModel.findCoveringTake(fileInterval)
        if not mocapTake:
            print "no match", fileName, fileInterval, "(skipped)"
            return

        print "matched", fileName, fileInterval, "to", mocapTake, "camera", fileCamera

        # get mocap take's slate
        #self.sg.find("MocapSlate", )

        # IF the acquisition folder exists
        # ...and the file is already copied
        # ...if there's already a matching Version we're done
        # ELSE
        # if needed: make the acquisition folders for the slate
        # copy the file to the slate acquisition directory
        # change the copied file to read-only
        # make a Version
        # upload the movie to the version
        # link the version to the mocap take and camera

    def uploadMovie(self, version_id, path):
        result = self.sg.upload('Version', version_id, path, field_name='sg_uploaded_movie')
        self.sg.close()
        return result
