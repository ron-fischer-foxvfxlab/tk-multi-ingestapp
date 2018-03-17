# following line is for standalone testing and allows completion while typing
#from PySide import QtCore, QtGui
import sgtk
from sgtk.platform.qt import QtCore, QtGui
from movie_metadata import extract_timing
from timecode import TC, Interval, Base

logger = sgtk.platform.get_logger(__name__)
def loggie(*a):
    for i in a: print i,
    print

#logger = loggie

"""
File States:
interval matched - interval darkGray
file ingesting - name darkYellow
file ingested - name darkBlue
version exists - name darkGray
camera linked - camera darkGray
movie uploading - name progress
movie uploaded - row darkGreen
"""

class VideoFilesModel(QtGui.QFileSystemModel):
    """
    Add cached timecode range and camera columns.
    """

    NAME_COLUMN = 0
    INTERVAL_COLUMN = 4
    CAMERA_COLUMN = 5

    def __init__(self, *args, **kwargs):
        super(VideoFilesModel, self).__init__(*args, **kwargs)
        self._initCaches()

    def _initCaches(self):
        self._intervalCache = dict()
        self._cameraCache = dict()
        self._versionExists = dict()
        self._movieUploaded = dict()
        self._linkedIntervals = dict()
        self._linkedCameras = dict()

    def modelReset(self, *args, **kwargs):
        super(VideoFilesModel, self).modelReset(*args, **kwargs)
        self._initCaches()

    def columnCount(self, *args, **kwargs):
        assert super(VideoFilesModel, self).columnCount() + 2 == 6
        return 6

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if role == QtCore.Qt.BackgroundRole and self.movieUploaded(index):
            return QtGui.QBrush(QtCore.Qt.darkGreen)

        column = index.column()

        if column == self.NAME_COLUMN:
            if role == QtCore.Qt.BackgroundRole:
                if self.versionExists(index):
                    return QtGui.QBrush(QtCore.Qt.darkGray)
        elif index.column() == self.INTERVAL_COLUMN:
            if role == QtCore.Qt.DisplayRole:
                return unicode(self.interval(index))
            elif role == QtCore.Qt.BackgroundRole:
                if self.intervalLinked(index):
                    return QtGui.QBrush(QtCore.Qt.darkGray)
        elif index.column() == self.CAMERA_COLUMN:
            if role == QtCore.Qt.DisplayRole:
                return unicode(self.camera(index))
            elif role == QtCore.Qt.BackgroundRole:
                if self.cameraLinked(index):
                    return QtGui.QBrush(QtCore.Qt.darkGray)

        return super(VideoFilesModel, self).data(index, role=role)

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        if section == self.INTERVAL_COLUMN and role == QtCore.Qt.DisplayRole and orientation == QtCore.Qt.Horizontal:
            return u"Time Range"
        elif section == self.CAMERA_COLUMN and role == QtCore.Qt.DisplayRole and orientation == QtCore.Qt.Horizontal:
            return u"Camera"
        else:
            return super(VideoFilesModel, self).headerData(section, orientation, role=role)

    def interval(self, index):
        """Get the timecode interval for this row."""
        # NOTE: rows move around! that's why we key the cache by path and not the "index"
        # ideally this might be a threaded task with update msgs

        path = self.filePath(index)
        interval = self._intervalCache.get(path)
        if interval:
            return interval

        try:
            tcIn, tcOut, tcRate, fps = extract_timing(path)
            base = Base(tcRate, float(tcRate) / fps)
            interval = Interval(TC(tcIn, base=base), endtc=TC(tcOut, base=base))
        except Exception, e:
            logger.error("Error retrieving timecode range from %s" % path)
            interval = "Invalid"

        self._intervalCache[path] = interval
        return interval

    def camera(self, index):
        path = self.filePath(index)
        cameraName = self._cameraCache.get(path)
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
            logger.error("Error retrieving camera letter index %s" % fileName)
            cameraName = "Invalid"

        self._cameraCache[path] = cameraName
        return cameraName

    def intervalLinked(self, index):
        path = self.filePath(index)
        return self._linkedIntervals.get(path)

    def setIntervalLinked(self, index):
        path = self.filePath(index)
        self._linkedIntervals[path] = True
        cellIndex = index.sibling(index.row(), self.INTERVAL_COLUMN)
        self.dataChanged.emit(cellIndex, cellIndex)

    def cameraLinked(self, index):
        path = self.filePath(index)
        return self._linkedCameras.get(path)

    def setCameraLinked(self, index):
        path = self.filePath(index)
        self._linkedCameras[path] = True
        cellIndex = index.sibling(index.row(), self.CAMERA_COLUMN)
        self.dataChanged.emit(cellIndex, cellIndex)

    def versionExists(self, index):
        path = self.filePath(index)
        return self._versionExists.get(path)

    def setVersionExists(self, index):
        path = self.filePath(index)
        self._versionExists[path] = True
        cellIndex = index.sibling(index.row(), self.NAME_COLUMN)
        self.dataChanged.emit(cellIndex, cellIndex)

    def movieUploaded(self, index):
        path = self.filePath(index)
        return self._movieUploaded.get(path)

    def setMovieUploaded(self, index):
        path = self.filePath(index)
        self._movieUploaded[path] = True
        self.dataChanged.emit(index, index.sibling(index.row(), self.CAMERA_COLUMN))

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
