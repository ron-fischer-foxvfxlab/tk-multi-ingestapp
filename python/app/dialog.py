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
    app_instance.engine.show_dialog("Ingest Turnover...", app_instance, AppDialog)

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
        self.signalDirectorySelected.connect(self.ui.lineEdit.setText)
        self.ui.lineEdit.returnPressed.connect(self.ui.actionScanTurnoverFiles.trigger)
        self.ui.scanButton.clicked.connect(self.ui.actionScanTurnoverFiles.trigger)
        self.ui.actionScanTurnoverFiles.triggered.connect(self.slotScanForTurnoverFiles)
        QtCore.QMetaObject.connectSlotsByName(self)

    @logerrors_decorate
    def slotScanForTurnoverFiles(self, *args):
        # most of the useful accessors are available through the Application class instance
        # it is often handy to keep a reference to this. You can get it via the following method:
        self._app = sgtk.platform.current_bundle()

        model = QtGui.QFileSystemModel()
        model.setRootPath("")

        # via the self._app handle we can for example access:
        # - The engine, via self._app.engine
        # - A Shotgun API instance, via self._app.shotgun
        # - A tk API instance, via self._app.tk

        # setup our data backend
        self._model = shotgun_model.SimpleShotgunModel(self)

        # tell the view to pull data from the model
        self.ui.view.setModel(self._model)

        # load all assets from Shotgun
        self._model.load_data(entity_type="Asset")

        # setup a delegate
        self._delegate = ListItemDelegate(self.ui.view)

        # hook up delegate renderer with view
        self.ui.view.setItemDelegate(self._delegate)

    @logerrors_decorate
    def slotDirectoryBrowser(self, *args):
        dirname = QtGui.QFileDialog.getExistingDirectory(
            parent=self,
            caption="Locate turnover directory",
            dir="P:\\COTW\\Turnovers",
            options=QtGui.QFileDialog.Option.ShowDirsOnly)
        self.signalDirectorySelected.emit(dirname)
