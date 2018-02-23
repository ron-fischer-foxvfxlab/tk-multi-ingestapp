# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'dialog.ui'
#
#      by: pyside-uic 0.2.15 running on PySide 1.2.4
#
# WARNING! All changes made in this file will be lost!

from tank.platform.qt import QtCore, QtGui

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(608, 517)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(Dialog.sizePolicy().hasHeightForWidth())
        Dialog.setSizePolicy(sizePolicy)
        self.verticalLayout_2 = QtGui.QVBoxLayout(Dialog)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.scanDir = QtGui.QWidget(Dialog)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.scanDir.sizePolicy().hasHeightForWidth())
        self.scanDir.setSizePolicy(sizePolicy)
        self.scanDir.setObjectName("scanDir")
        self.horizontalLayout = QtGui.QHBoxLayout(self.scanDir)
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.label = QtGui.QLabel(self.scanDir)
        self.label.setObjectName("label")
        self.horizontalLayout.addWidget(self.label)
        self.lineEdit = QtGui.QLineEdit(self.scanDir)
        self.lineEdit.setObjectName("lineEdit")
        self.horizontalLayout.addWidget(self.lineEdit)
        self.dirButton = QtGui.QPushButton(self.scanDir)
        self.dirButton.setObjectName("dirButton")
        self.horizontalLayout.addWidget(self.dirButton)
        self.verticalLayout_2.addWidget(self.scanDir)
        self.scanButton = QtGui.QPushButton(Dialog)
        self.scanButton.setObjectName("scanButton")
        self.verticalLayout_2.addWidget(self.scanButton)
        self.view = QtGui.QListView(Dialog)
        self.view.setObjectName("view")
        self.verticalLayout_2.addWidget(self.view)
        self.actionScanTurnoverFiles = QtGui.QAction(Dialog)
        self.actionScanTurnoverFiles.setObjectName("actionScanTurnoverFiles")

        self.retranslateUi(Dialog)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        Dialog.setWindowTitle(QtGui.QApplication.translate("Dialog", "Ingest Turnover Files...", None, QtGui.QApplication.UnicodeUTF8))
        self.label.setText(QtGui.QApplication.translate("Dialog", "Turnover folder", None, QtGui.QApplication.UnicodeUTF8))
        self.dirButton.setText(QtGui.QApplication.translate("Dialog", "...", None, QtGui.QApplication.UnicodeUTF8))
        self.scanButton.setText(QtGui.QApplication.translate("Dialog", "Scan", None, QtGui.QApplication.UnicodeUTF8))
        self.actionScanTurnoverFiles.setText(QtGui.QApplication.translate("Dialog", "ScanTurnoverFiles", None, QtGui.QApplication.UnicodeUTF8))

from . import resources_rc
