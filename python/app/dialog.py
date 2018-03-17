# Copyright (c) 2013 Shotgun Software Inc.
# 
# CONFIDENTIAL AND PROPRIETARY
# 
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit 
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your 
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights 
# not expressly granted therein are reserved by Shotgun Software Inc.

import sgtk
import os
import sys
import threading

# by importing QT from sgtk rather than directly, we ensure that
# the code will be compatible with both PySide and PyQt.
from sgtk.platform.qt import QtCore, QtGui
from .ui.dialog import Ui_Dialog
from .lib.filesystem_model import VideoFilesModel
from .lib.shootday_model import ShootDayModel
from .lib.link_versions import TakeMediaProcessor

shotgun_data = sgtk.platform.import_framework("tk-framework-shotgunutils",
                                              "shotgun_data")
task_manager = sgtk.platform.import_framework("tk-framework-shotgunutils",
                                              "task_manager")
shotgun_globals = sgtk.platform.import_framework("tk-framework-shotgunutils",
                                                 "shotgun_globals")

import traceback
logger = sgtk.platform.get_logger(__name__)

def logerrors_decorate(func):
    def func_wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception:
            logger.error("Error calling %s(%s, %s):\n%s" % (
                func.__name__, args, kwargs, traceback.format_exc()))
    return func_wrapper

def show_dialog(app_instance):
    """
    Shows the main dialog window.
    """
    # in order to handle UIs seamlessly, each toolkit engine has methods for launching
    # different types of windows. By using these methods, your windows will be correctly
    # decorated and handled in a consistent fashion by the system.

    # we pass the dialog class to this method and leave the actual construction
    # to be carried out by toolkit.
    dialog = app_instance.engine.show_dialog("Ingest Shoot Day files...", app_instance, AppDialog)
    dialog.default_load()

class AppDialog(QtGui.QWidget):
    """
    Main application dialog window
    """

    signalDirectorySelected = QtCore.Signal(str)
    
    def __init__(self):
        """
        Constructor
        """
        # first, call the base class and let it do its thing.
        QtGui.QWidget.__init__(self)

        self.ingestTaskID = None

        # create a background task manager
        self._task_manager = task_manager.BackgroundTaskManager(self,
                                                                start_processing=False,
                                                                max_threads=8)
        shotgun_globals.register_bg_task_manager(self._task_manager)
        self._task_manager.task_completed.connect(self.slotTaskCompleted)

        # now load in the UI that was created in the UI designer
        self.ui = Ui_Dialog() 
        self.ui.setupUi(self)

        # Qt Designer is funky about connections so do them here
        self.ui.dirButton.clicked.connect(self.slotDirectoryBrowser)
        self.signalDirectorySelected.connect(self.ui.dirLineEdit.setText)
        self.ui.dirLineEdit.returnPressed.connect(self.ui.actionScanFiles.trigger)
        self.ui.actionScanFiles.triggered.connect(self.slotScanFiles)

        self.ui.ingestButton.clicked.connect(self.ui.actionIngestFiles.trigger)
        self.ui.actionIngestFiles.triggered.connect(self.slotIngestFiles)

        QtCore.QMetaObject.connectSlotsByName(self)

    @logerrors_decorate
    def slotScanTakes(self, *args):
        date = self.get_ingest_shootday()

        self._shotgunModel = ShootDayModel(parent=self, bg_task_manager=self._task_manager)
        self.ui.takeView.setModel(self._shotgunModel)
        self._shotgunModel.load_data(date, additionalFields=TakeMediaProcessor.REQUIRED_MOCAPTAKE_FIELDS)

        self.ui.takeView.setColumnWidth(0, 150) # take name
        self.ui.takeView.setColumnWidth(1, 150) # time range

    @logerrors_decorate
    def slotScanFiles(self, *args):
        path = self.ui.dirLineEdit.text()
        self._filesystemModel = VideoFilesModel(self)
        self._filesystemModel.setRootPath(path)
        self.ui.fileView.setModel(self._filesystemModel)
        self.ui.fileView.setRootIndex(self._filesystemModel.index(path))

        self.ui.fileView.hideColumn(1)
        self.ui.fileView.hideColumn(2)
        self.ui.fileView.hideColumn(3)

        self.ui.fileView.setColumnWidth(0, 200)
        self.ui.fileView.setColumnWidth(4, 150) # time range
        self.ui.fileView.setColumnWidth(5, 50) # camera name (letter)

    @logerrors_decorate
    def slotDirectoryBrowser(self, *args):
        dirname = QtGui.QFileDialog.getExistingDirectory(
            parent=self,
            caption="Locate shoot day directory",
            dir=self.get_ingest_dir(),
            options=QtGui.QFileDialog.Option.ShowDirsOnly)
        self.signalDirectorySelected.emit(dirname)

    # via the self._app handle we can for example access:
    # - The engine, via self._app.engine
    # - A Shotgun API instance, via self._app.shotgun
    # - A tk API instance, via self._app.sgtk
    #self._app = sgtk.platform.current_bundle()

    def get_ingest_shootday(self):
        self._app = sgtk.platform.current_bundle()
        return self._app.context

    def get_ingest_dir(self):
        self._app = sgtk.platform.current_bundle()

        template = self._app.get_template("take_vidref_ingest_folder")
        ctx = self._app.context.as_template_fields(template, validate=True)
        path = template.apply_fields(ctx)

        return path

    def default_load(self):
        date = self.get_ingest_shootday()
        self.ui.dateLineEdit.setText(date.entity.get('name'))
        self.slotScanTakes()

        path = self.get_ingest_dir()
        self.ui.dirLineEdit.setText(path)
        self.slotScanFiles()

    INGESTFILES_TASKGROUP = "IngestFiles"

    def slotIngestFiles(self, *args):
        self.ui.ingestButton.setEnabled(False)
        self.ingestTaskID = self._task_manager.add_task(
            self._processFiles, group=self.INGESTFILES_TASKGROUP, task_args=(self._shotgunModel, self._app, self._filesystemModel))

    @logerrors_decorate
    def _processFiles(self, sgModel, sgApp, fsModel):
        rootPath = fsModel.rootPath()
        rootIndex = fsModel.index(rootPath)
        tmp = TakeMediaProcessor(sgModel, sgApp)
        tmp.signalIntervalMatched.connect(self.slotIntervalMatched)
        tmp.signalVersionExists.connect(self.slotVersionExists)
        tmp.signalCameraLinked.connect(self.slotCameraLinked)
        tmp.signalMovieUploaded.connect(self.slotMovieUploaded)

        logger.info("vvvvvvvvvv Start processing files in %s" % rootPath)

        row = 0
        while True:
            fileIndex = rootIndex.child(row, 0)
            if not fileIndex.isValid():
                return
            filePath = fsModel.filePath(fileIndex)
            fileName = fsModel.fileName(fileIndex)
            fileInterval = fsModel.interval(fileIndex)
            fileCamera = fsModel.camera(fileIndex)
            tmp.processFile(filePath, fileName, fileInterval, fileCamera)
            row += 1

        logger.info("^^^^^^^^^^ Done processing files in %s" % rootPath)

    # TODO These should just be connected to the file model, poss. through path interpretation
    def slotIntervalMatched(self, filePath, sgMocapTake):
        index = self._filesystemModel.index(filePath)
        self._filesystemModel.setIntervalLinked(index)

    slotFileIngesting = None
    slotFileIngested = None

    def slotVersionExists(self, filePath, sgVersion):
        index = self._filesystemModel.index(filePath)
        self._filesystemModel.setVersionExists(index)

    def slotCameraLinked(self, filePath, sgVersion):
        index = self._filesystemModel.index(filePath)
        self._filesystemModel.setCameraLinked(index)

    slotMovieUploading = None

    def slotMovieUploaded(self, filePath, sgVersion):
        index = self._filesystemModel.index(filePath)
        self._filesystemModel.setMovieUploaded(index)

    def slotTaskCompleted(self, uid, group, result):
        logger.info("task completed uid %s group %s" % (uid, group))
        if uid == self.ingestTaskID:
            self.ui.ingestButton.setEnabled(True)
            self.ingestTaskID = None

    def closeEvent(self, event):
        shotgun_globals.unregister_bg_task_manager(self._task_manager)
        self._task_manager.shut_down()
        event.accept()
