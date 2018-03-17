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

def timecode_to_msec(tc):
    return tc.realtimeSeconds() * 1000.0

class ShootDayModel(shotgun_model.SimpleShotgunModel):
    """
    Add timecode range column.
    """

    INTERVAL_COLUMN = 1

    def __init__(self, *args, **kwargs):
        super(ShootDayModel, self).__init__(*args, **kwargs)

    def load_data(self, date, select=True, additionalFields=[]):
        filters = [
            ['sg_shoot_day', 'is', {'type':'ShootDay', 'id': date.entity.get('id')}],
        ]
        if select:
            filters.append(["sg_select", "is", True])

        super(ShootDayModel, self).load_data(
            'MocapTake',
            filters=filters,
            fields=['code', 'sg_timecode_in', 'sg_timecode_out'] + additionalFields,
            columns=['sg_timecode_interval'])
        self._refresh_data()

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

    COVERAGE_MIN = 0.6

    def findCoveringTakeSGData(self, fileInterval, requiredCoverage=COVERAGE_MIN):
        fileDurationRTSecs = fileInterval.duration().realtimeSeconds()
        for takeID in self.entity_ids:
            takeItem = self.item_from_entity(self.get_entity_type(), takeID)
            takeInterval = takeItem.get_sg_data()['sg_timecode_interval']
            intersection = fileInterval.intersect(takeInterval)
            if intersection:
                coverage = intersection.duration().realtimeSeconds() / fileDurationRTSecs
                if coverage > requiredCoverage:
                    data = takeItem.get_sg_data()
                    data['fvl_match_coverage'] = coverage
                    return data
        return None
