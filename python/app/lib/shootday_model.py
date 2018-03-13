import sgtk
# following line gives completion while typing (remove before flight)
#from PySide import QtCore, QtGui
from sgtk.platform.qt import QtCore, QtGui
from timecode import Time, Interval, TB_23976

shotgun_model = sgtk.platform.import_framework("tk-framework-shotgunutils",
                                               "shotgun_model")

shotgun_project_timebase = TB_23976

def msec_to_timecode(value, base):
    milliseconds = float(value)
    frame = milliseconds / base.fpsToScale(1000.0)
    tc = Time(frame=int(frame + 0.5), base=base)
    return tc

def _intersect(a, b):
    if a.Start in b:
        if b.EndTC in a:
            return Interval(a.Start, endtc=b.EndTC)
        else:
            return a
    elif b.Start in a:
        if a.EndTC in b:
            return b
        else:
            return Interval(b.Start, a.EndTC)
    else:
        return None

class ShootDayModel(shotgun_model.SimpleShotgunModel):
    """
    Add timecode range column.
    """

    SG_TCINTERVAL_ROLE = QtCore.Qt.UserRole + 11

    INTERVAL_COLUMN = 1

    def load_data(self, date, select=True):
        filters = [
            ["sg_shoot_day", "is", {'type':'ShootDay', 'id': date.entity.get('id')}],
        ]
        if select:
            filters.append(["sg_select", "is", True])

        super(ShootDayModel, self).load_data(
            "MocapTake",
            filters=filters,
            fields=["code", "sg_slate","sg_timecode_in", "sg_timecode_out"],
            columns=["sg_timecode_interval"])

    def _before_data_processing(self, data):
        for record in data:
            tcIn = msec_to_timecode(record['sg_timecode_in'], shotgun_project_timebase)
            tcOut = msec_to_timecode(record['sg_timecode_out'], shotgun_project_timebase)
            interval = Interval(tcIn, endtc=tcOut)
            record['sg_timecode_interval'] = interval
        return data

    def headerData(self, section,  orientation, role=QtCore.Qt.DisplayRole):
        if section == self.INTERVAL_COLUMN and role == QtCore.Qt.DisplayRole and orientation == QtCore.Qt.Horizontal:
            return u"Time Range"
        else:
            return super(ShootDayModel, self).headerData(section,  orientation, role=role)

    def interval(self, index):
        return None

    COVERAGE_MIN = 0.6

    def findCoveringTake(self, fileInterval, requiredCoverage=COVERAGE_MIN):
        fileDurationRTSecs = fileInterval.duration().realtimeSeconds()
        for takeID in self.entity_ids:
            takeItem = self.item_from_entity(self.get_entity_type(), takeID)
            takeInterval = takeItem.get_sg_data()['sg_timecode_interval']
            intersection = _intersect(fileInterval, takeInterval)
            if intersection:
                coverage = intersection.duration().realtimeSeconds() / fileDurationRTSecs
                if coverage > requiredCoverage:
                    return takeItem
        return None
