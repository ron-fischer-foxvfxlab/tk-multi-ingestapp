# following line is for standalone testing and allows completion while typing
from PySide import QtCore, QtGui
#from sgtk.platform.qt import QtCore, QtGui
from movie_metadata import extract_timing
from timecode import TC, Interval, Base

class VideoFilesModel(QtGui.QFileSystemModel):
    """
    Add cached timecode range and camera columns.
    """

    INTERVAL_COLUMN = 4
    CAMERA_COLUMN = 5

    def __init__(self, *args, **kwargs):
        super(VideoFilesModel, self).__init__(*args, **kwargs)
        self._initCaches()

    def _initCaches(self):
        self._intervalCache = dict()
        self._cameraCache = dict()

    def modelReset(self, *args, **kwargs):
        super(VideoFilesModel, self).modelReset(*args, **kwargs)
        self._initCaches()

    def columnCount(self, *args, **kwargs):
        assert super(VideoFilesModel, self).columnCount() + 2 == 6
        return 6

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if index.column() == self.INTERVAL_COLUMN and role == QtCore.Qt.DisplayRole:
            return self.interval(index, role=role)
        elif index.column() == self.CAMERA_COLUMN and role == QtCore.Qt.DisplayRole:
            return self.camera(index, role=role)
        else:
            return super(VideoFilesModel, self).data(index, role=role)

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        if section == self.INTERVAL_COLUMN and role == QtCore.Qt.DisplayRole and orientation == QtCore.Qt.Horizontal:
            return u"Time Range"
        elif section == self.CAMERA_COLUMN and role == QtCore.Qt.DisplayRole and orientation == QtCore.Qt.Horizontal:
            return u"Camera"
        else:
            return super(VideoFilesModel, self).headerData(section, orientation, role=role)

    def interval(self, index, role=QtCore.Qt.DisplayRole):
        """Get the timecode interval for this row."""
        # ideally this should be a threaded task with update msgs

        interval = self._intervalCache.get(index.row())
        if interval:
            return interval

        path = self.filePath(index)
        try:
            tcIn, tcOut, tcRate, fps = extract_timing(path)
            base = Base(tcRate, float(tcRate) / fps)
            interval = Interval(TC(tcIn, base=base), endtc=TC(tcOut, base=base))
        except Exception, e:
            print "Error retrieving timecode range from file", path, e
            interval = "Invalid"

        self._intervalCache[index.row()] = interval
        return interval

    def camera(self, index, role=QtCore.Qt.DisplayRole):
        cameraName = self._cameraCache.get(index.row())
        if cameraName:
            return cameraName

        fileName = self.fileName(index.sibling(index.row(), 0))
        if not fileName:
            return None
        try:
            takeName = fileName.split('#')[0]
            tupe = takeName.split('_')
            cameraName = tupe[3]
        except IndexError, e:
            print "Error retrieving camera letter index", index, "file", fileName, e
            cameraName = "Invalid"

        self._cameraCache[index.row()] = cameraName
        return cameraName

if __name__ == '__main__':
    """Test retrieving TC ranges from video files"""

    TEST_PATH = "P:/vptest2/io/shoot_days/incoming/20180223_AlamedaStage02/qtake/raw"

    app = QtGui.QApplication([])
    fileView = QtGui.QListView()

    fsm = VideoFilesModel()
    fsm.setRootPath(TEST_PATH)

    fileView.setModel(fsm)
    fileView.setRootIndex(fsm.index(TEST_PATH))

    def dirLoaded(path):
        print "dirLoaded", path

        # headers
        for column in range(fsm.columnCount()):
            header = fsm.headerData(column, QtCore.Qt.Horizontal)
            print header,
        print

        # rows
        rootIndex = fsm.index(path)
        row = 0
        while True:
            for column in range(fsm.columnCount()):
                index = rootIndex.child(row, column)
                if not index.isValid():
                    print
                    return
                data = index.data()
                print data,
            print
            row += 1

    fsm.directoryLoaded.connect(dirLoaded)

    fileView.show()

    fsm.setRootPath(TEST_PATH)
    fileView.setRootIndex(fsm.index(TEST_PATH))

    app.exec_()
