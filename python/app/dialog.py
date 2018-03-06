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

# Import the shotgun_model module from the shotgun utils framework.
shotgun_model = sgtk.platform.import_framework("tk-framework-shotgunutils",
                                               "shotgun_model")
# Set up alias
ShotgunModel = shotgun_model.ShotgunModel

from .delegate_list_item import ListItemDelegate

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
    def slotScanFiles(self, *args):
        # via the self._app handle we can for example access:
        # - The engine, via self._app.engine
        # - A Shotgun API instance, via self._app.shotgun
        # - A tk API instance, via self._app.tk
        #self._app = sgtk.platform.current_bundle()

        self._shotgunModel = shotgun_model.SimpleShotgunModel(self)
        self.ui.takeView.setModel(self._shotgunModel)
        self._shotgunModel.load_data(entity_type="MocapTake")
        # setup a delegate
        #self._delegate = ListItemDelegate(self.ui.view)
        # hook up delegate renderer with view
        #self.ui.view.setItemDelegate(self._delegate)
        # FILTER TO SHOOTDAY

        # ingest directory model
        path = self.ui.dirLineEdit.text()
        self._filesystemModel = QtGui.QFileSystemModel()
        self._filesystemModel.setRootPath(path)
        self.ui.fileView.setModel(self._filesystemModel)
        self.ui.fileView.setRootIndex(self._filesystemModel.index(path))

    @logerrors_decorate
    def slotIngestFiles(self, *args):
        pass

    @logerrors_decorate
    def slotDirectoryBrowser(self, *args):
        dirname = QtGui.QFileDialog.getExistingDirectory(
            parent=self,
            caption="Locate shoot day directory",
            dir=self.get_ingest_dir(),
            options=QtGui.QFileDialog.Option.ShowDirsOnly)
        self.signalDirectorySelected.emit(dirname)

    def get_ingest_dir(self):
        self._app = sgtk.platform.current_bundle()

        template = self._app.get_template("take_vidref_area_ingest")
        ctx = self._app.context.as_template_fields(template, validate=True)
        path = template.apply_fields(ctx)

        return path

    def default_load(self):
        path = self.get_ingest_dir()
        self.ui.dirLineEdit.setText(path)
        self.slotScanFiles()
