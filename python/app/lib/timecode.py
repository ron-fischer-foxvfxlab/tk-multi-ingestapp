"""Time, duration, intervals, frame counts and code strings.
   Note: realtime seconds' and 'frametime seconds' are not equivalent.
   Realtime seconds are the 'wall clock time' of a duration,
   whereas 'frametime seconds' occur when the number of counts
   per second is passed.
"""

# -----

class Base(object):
    """A base for time rep, like base for number rep.
       Number of frames per second, e.g. 24 fps
       and number of realtime seconds per frame, as float."""
    
    def __init__(self, framesPerSecond, realtimeScale):
        """Initialize a timebase from counts per second and realtime per count."""
        if not isinstance(framesPerSecond, int):
            raise TypeError(framesPerSecond)
        if framesPerSecond <= 0:
            raise ValueError(framesPerSecond)
        if not isinstance(realtimeScale, float):
            raise TypeError(realtimeScale)
        if realtimeScale <= 0.0:
            raise ValueError(realtimeScale)
        self.FramesPerSecond = framesPerSecond
        self.RealtimeScale = realtimeScale

    def __eq__(self, other):
        """Equality operation for Bases."""
        if not isinstance(other, Base):
            raise TypeError(other)
        return self.FramesPerSecond == other.FramesPerSecond and \
               abs(self.RealtimeScale - other.RealtimeScale) < 0.0001

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        """Return evaluable string to reproduce this Base instance.
           Assumes namespace of module."""
        if self.RealtimeScale == RTS_WHOLE:
            s = 'RTS_WHOLE'
        elif self.RealtimeScale == RTS_VIDEO:
            s = 'RTS_VIDEO'
        else:
            s = str(self.RealtimeScale)
        
        return "TB(%r, %s)" % (self.FramesPerSecond, s)

    def timecodeToFrame(self, timecode):
        """Given timecode as basestring, e.g. '-00:00:00:01', return int frame number."""
        if not isinstance(timecode, basestring):
            raise TypeError(timecode)

        if len(timecode) < 11:
            raise ValueError(timecode)

        arity = 1
        if timecode[0] == '-':
            arity = -1
            timecode = timecode[1:]

        segs = timecode.split(':')
        if len(segs) != 4:
            raise ValueError(timecode)

        h, m, s, f = ( int(x) for x in segs )
        
        for value, limit in [(m, 60), (s, 60), (f, self.FramesPerSecond)]:
            if value >= limit:
                raise ValueError('Bad value %r in timecode string %r' % (value, timecode))
        
        frame = h * 60 * 60 * self.FramesPerSecond
        frame += m * 60 * self.FramesPerSecond
        frame += s * self.FramesPerSecond
        frame += f

        return frame * arity

    def frameToRealtimeSeconds(self, frame):
        """Given a frame number return float wall clock seconds."""
        return ( frame / self.FramesPerSecond ) * self.RealtimeScale

    def frameToCounts(self, frame):
        """Given a frame number, return tuple of arity, hours, minutes, seconds and frames."""

        if frame < 0:
            a = '-'
            frame = abs(frame)
        else:
            a = ''
        
        h = frame / ( 60 * 60 * self.FramesPerSecond )
        frame = frame % ( 60 * 60 * self.FramesPerSecond )

        m = frame / (  60 * self.FramesPerSecond )
        frame = frame % (  60 * self.FramesPerSecond )

        s = frame / self.FramesPerSecond
        
        f = frame % self.FramesPerSecond

        return a, h, m, s, f

    def fpsToScale(self, fps):
        """Given a playback speed in fps return ratio to this base's natural speed."""
        return fps / float(self.FramesPerSecond)

def TB(fps, rpf):
    """Abbreviation for Timebase definition, eqv to Base(fps, rpf)."""
    return Base(fps, rpf)

# ----

# Note: these should be configured for facility, shows or depts only as needed

RTS_WHOLE = 1.0
"""Realtime speed is whole number, e.g. frame rate is 1:1 with wallclock time."""

RTS_VIDEO = 1.001001001001001
"""Realtime speed is video fraction, e.g. frame rate is NOT 1:1 with wallclock time."""

TB_24     = TB(24, RTS_WHOLE)
"""Timebase for 24fps film."""

TB_23976  = TB(24, RTS_VIDEO)
"""Timebase for 23.976 video (progressive video frames)."""

TB_30     = TB(30, RTS_WHOLE)
"""Timebase for 30fps, not a video rate."""

TB_2997   = TB(30, RTS_VIDEO)
"""Timebase for 29.97 video (non-interlaced video frames)."""

TB_60     = TB(60, RTS_WHOLE)
"""Timebase for 60fps, not a video rate."""

TB_5994   = TB(60, RTS_VIDEO)
"""Timebase for 59.94 video (interlaced video frames)."""

TB_120    = TB(120, RTS_WHOLE)
"""Timebase for 120fps, not a video rate."""

# Need either no defaulting or something configurable.

TB_DEFAULT = TB_24
"""Default timebase.  All code should support alternate timebases, e.g. through keyword arguments."""

# -----

class Time(object):
    """Encoded time.  Can be set from a base plus either timecode string (h:m:s:f) or a frame int.  No subframes yet."""
    
    def __init__(self, **kwargs):
        """Initialize a Time instance.
           Arguments same as read method."""
        self.read(**kwargs)

    def read(self, time=None, timecode=None, frame=None, base=None):
        """Set time from:
        - another time
        or an optional base with either:
        - timecode basestring
        - frame int
        Time defaults to zero and base defaults to TB_DEFAULT."""

        if time is not None:
            if not (timecode is None and frame is None and base is None):
                raise ValueError('Keyword argument time must be given alone')
            if not isinstance(time, Time):
                raise TypeError(time)
            self._frame = time._frame
            self.Base = time.Base
            return

        elif timecode is not None:
            if frame is not None:
                raise ValueError('Keyword argument timecode can only be given with base')
            self.Base = base or TB_DEFAULT
            self._frame = self.Base.timecodeToFrame(timecode)
            return

        elif frame is not None:
            if not isinstance(frame, int):
                raise TypeError(frame)
            self.Base = base or TB_DEFAULT
            self._frame = frame
            return

        else:
            self._frame = 0
            self.Base = base or TB_DEFAULT

    def timecode(self):
        """Return time as string in timecode format for current base."""
        return "%s%02d:%02d:%02d:%02d" % self.Base.frameToCounts(self._frame)

    def frame(self):
        """Return time as integer frame count in current base."""
        return self._frame

    def realtimeSeconds(self):
        """Return time as float seconds of realtime in current base."""
        return self.Base.frameToRealtimeSeconds(self._frame)

    def __repr__(self):
        """Return evaluable string to reproduce this Time instance.
           Assumes namespace of module."""
        return "TC(%r, base=%r)" % (self.timecode(), self.Base)

    def __nonzero__(self):
        """Operator non zero.  Is not at frame or TC zero."""
        return self._frame != 0

    def __cmp__(self, other):
        """Comparison (ordering) operator time to interval.
           Bases must match.
           If other is Time, returns <0 if before other, 0 if equal or >0 if after.
           If other is Interval, returns <0 if before, 0 if IN, of >0 if after."""
        if isinstance(other, Time):
            if self.Base != other.Base:
                raise ValueError('Mismatched time Bases %r != %r' % (self.Base, other.Base))
            return self._frame - other._frame
        elif isinstance(other, Interval):
            if self.Base != other.Start.Base:
                raise ValueError('Mismatched time Bases %r != %r' % (self.Base, other.Base))
            if self in other:
                return 0
            elif self < other.Start:
                return -1
            elif self > other.Stop:
                return 1
        else:
            raise TypeError('Cannot compare Time to %r' % other)

    def __str__(self):
        """Convert to string.  Equivalent to method timecode()"""
        return self.timecode()

    def __int__(self):
        """Convert to int.  Equivalent to method frame()"""
        return self.frame()

    def __pos__(self):
        return self

    def __neg__(self):
        """Return new time instance which is negative of self."""
        return Time(frame=-self._frame, base=self.Base)

    def __add__(self, other):
        """Add this time to other and return new time.
           Bases must match."""
        if not isinstance(other, Time):
            raise TypeError('Cannot add Time to %r' % other)
        if self.Base != other.Base:
            raise ValueError('Mismatched time Bases %r != %r' % (self.Base, other.Base))
        return Time(frame=self._frame + other._frame, base=self.Base)

    def __iadd__(self, other):
        """Increment this time by other time.
           Bases must match."""
        if not isinstance(other, Time):
            raise TypeError('Cannot iadd Time to %r' % other)
        if self.Base != other.Base:
            raise ValueError('Mismatched time Bases %r != %r' % (self.Base, other.Base))
        self._frame += other._frame
        return self

    def __sub__(self, other):
        """Subtract other time from self and return new Time.
           Bases must match."""
        if not isinstance(other, Time):
            raise TypeError('Cannot sub %r from Time' % other)
        if self.Base != other.Base:
            raise ValueError('Mismatched time Bases %r != %r' % (self.Base, other.Base))
        return Time(frame=self._frame - other._frame, base=self.Base)

    def __isub__(self, other):
        """Decrement this time by other time.
           Bases must match."""
        if not isinstance(other, Time):
            raise TypeError('Cannot isub %r from Time' % other)
        if self.Base != other.Base:
            raise ValueError('Mismatched time Bases %r != %r' % (self.Base, other.Base))
        self._frame -= other._frame
        return self

    def __mul__(self, other):
        """Multiply this time by a float."""
        if not isinstance(other, float):
            raise TypeError('Cannot multiply Time by %r' % other)
        return Time(frame=int(round(self._frame * other)), base=self.Base)

def TC(timecode, base=None):
    """Timecode string in base."""
    return Time(timecode=timecode, base=base)

def FR(frame, base=None):
    """Frame integer in base."""
    return Time(frame=frame, base=base)

class Interval(object):
    """Contiguous interval from a start to an end time.
       Retrieve start time with Start member.
       Retrieve end frame or timecode with EndTC or EndFR.
       Note: end frames are inclusive, while end timecode is exclusive.
       Warning: Do not set the .EndTC or .EndFR values directly."""
    
    # Consider: discontiguous interval rep with math
    
    def __init__(self, start, endtc=None, endfr=None):
        """start is always included in the range.
           endfr means set end from frame, endtc means as TC.
           endfr is INCLUSIVE (no zero length ranges).
           endtc is EXCLUSIVE (last value not part of range).
           Frame range 1 - 2 is frames 1 and 2.
           TC range 00:00:00:01 - 00:00:00:02 is one frame 00:00:00:01.
        """
        if not isinstance(start, Time):
            raise TypeError(start)
        
        if isinstance(endtc, Time):
            if endfr is not None:
                raise TypeError('Interval endtc %r and endfr %r keyword arguments are exclusive' % (endtc, endfr))
            if start.Base != endtc.Base:
                raise ValueError('Mismatched time Bases on start %r and endtc %r' % (start.Base, endtc.Base))
        elif isinstance(endfr, Time):
            if start.Base != endfr.Base:
                raise ValueError('Mismatched time Bases on start %r and endfr %r' % (start.Base, endfr.Base))
        else:
            raise TypeError('Interval requires either endtc or endfr keyword argument')
        
        self.Start = start
        if isinstance(endtc, Time):
            self.EndTC = endtc
            self.EndFR = endtc - FR(1, endtc.Base)
        if isinstance(endfr, Time):
            if endfr < start:
                raise ValueError("Negative frame interval")
            self.EndFR = endfr
            self.EndTC = endfr + FR(1, endfr.Base)

    def duration(self):
        """Return interval's duration as a time value."""
        return Time(frame=len(self), base=self.Start.Base)

    def asFR(self):
        """Return string representing interval in frames.  Note that end frame is inclusive."""
        return "%d - %d" % (self.Start.frame(), self.EndFR.frame())

    def asTC(self):
        """Return string representing interval as timecode.  Note that end timecode is exclusive."""
        return "%s - %s" % (self.Start, self.EndTC)

    def __repr__(self):
        """Return an evaluable string representing this instance."""
        return "Interval(FR(%d), endfr=FR(%d))" % (self.Start.frame(), self.EndFR.frame())

    def __str__(self):
        """Equivalent to asTC()"""
        return self.asTC()

    def __nonzero__(self):
        """Is this interval non-zero?"""
        return self.EndTC._frame > self.Start._frame

    def __len__(self):
        """Return length in frames as int."""
        return self.EndTC._frame - self.Start._frame

    def __iter__(self):
        """Return iterator over each Time (frame) in Interval."""
        return ( Time(frame=f, base=self.Start.Base)
                 for f in range(self.Start._frame, self.EndTC._frame) )

    def __contains__(self, item):
        """Does this interval contain the given time or interval?"""
        if isinstance(item, Time):
            if item.Base != self.Start.Base:
                raise ValueError('Mismatched time Bases %r != %r' % (item.Base, self.Start.Base))
            return self.Start._frame <= item._frame < self.EndTC._frame
        if not isinstance(item, Interval):
            raise TypeError(item)
        return item.Start >= self.Start and item.EndTC <= self.EndTC

    def merge(self, item):
        """Returns a single, new interval encompassing both."""
        return Interval(min((self.Start, item.Start)), endtc=max((self.EndTC, item.EndTC)))

    #def union(self, item):
    #    """Join two intervals.  Returns a tuple of one or two intervals."""
    #    assert isinstance(item, Interval)
    #    return ()

    #def intersect(self, item):
    #    """Intersect two intervals.  Returns a tuples of zero or one intervals."""
    #    assert isinstance(item, Interval)
    #    return ()

# ----

class Speed(object):
    """Virtual base class for speed variation (use its derivations).
       Speed is a map from one Interval to another.
       There are linear (e.g. 2.0x) and curve mappings (TimeWarp)."""

    def __getitem__(self, time):
        """This API allows us to support timewarp in future."""
        assert False

class LinearSpeed(Speed):
    """The origin of a linear speed map is start of clip.
       Output is unclipped (no loops)."""

    def __init__(self, interval, scale=1.0):
        """A linear map over interval from interval.Start to infinity."""
        if not isinstance(interval, Interval):
            raise TypeError(interval)
        if not isinstance(scale, float):
            raise TypeError(scale)
        self.Interval = interval
        self._scale = scale

    def __getitem__(self, time):
        """Given a time, produce linearly scaled time from start of interval."""
        if not isinstance(time, Time):
            raise TypeError(time)
        delta = time - self.Interval.Start
        delta *= self._scale
        return self.Interval.Start + delta

    def __float__(self):
        """Return realtime multiplier as a float."""
        return self._scale

# Eventually: class Timewarp(Speed)

# ----

import unittest

class TestTimecode(unittest.TestCase):

    def testBases(self):
        self.assert_(isinstance(RTS_WHOLE, float))
        self.assert_(isinstance(RTS_VIDEO, float))

        self.assert_(isinstance(TB_24, Base))
        self.assert_(isinstance(TB_23976, Base))
        self.assert_(isinstance(TB_30, Base))
        self.assert_(isinstance(TB_2997, Base))
        self.assert_(isinstance(TB_60, Base))
        self.assert_(isinstance(TB_5994, Base))
        self.assert_(isinstance(TB_120, Base))

        self.assert_(isinstance(TB_DEFAULT, Base))
        self.assertEqual(TB_DEFAULT, TB_24)

        self.assert_(Base(24, 1.0))
        self.assertRaises(TypeError, Base, None, 1.0)
        self.assertRaises(TypeError, Base, 24, None)
        self.assertRaises(ValueError, Base, 0, 1.0)
        self.assertRaises(ValueError, Base, -1, 1.0)
        self.assertRaises(ValueError, Base, 24, 0.0)
        self.assertRaises(ValueError, Base, 24, -1.0)

        self.assertRaises(TypeError, Base.__eq__, TB_24, 1)
        self.assertNotEqual(TB_24, TB_23976)
        self.assertEqual(TB_24, TB_24)
        self.assertEqual(TB_23976, TB_23976)
        self.assertEqual(Base(24, RTS_VIDEO), Base(24, RTS_VIDEO))

        self.assertEqual(repr(TB_24), 'TB(24, RTS_WHOLE)')
        self.assertEqual(repr(TB_23976), 'TB(24, RTS_VIDEO)')

        self.assertRaises(TypeError, Base.timecodeToFrame, TB_24, 67)

        self.assertEqual(TB_24.frameToRealtimeSeconds(24), 1.0)
        self.assertEqual(TB_24.frameToRealtimeSeconds(0), 0.0)
        self.assertRaises(TypeError, Base.frameToRealtimeSeconds, TB_24, 'bad')

        self.assertEqual(TB_24.frameToCounts(25), ('', 0, 0, 1, 1))
        self.assertEqual(TB_24.frameToCounts(0), ('', 0, 0, 0, 0))
        self.assertEqual(TB_24.frameToCounts(-25), ('-', 0, 0, 1, 1))
        self.assertRaises(TypeError, Base.frameToCounts, TB_24, 'bad')

        self.assertEqual(TB_24.fpsToScale(24), 1.0)
        self.assertEqual(TB_24.fpsToScale(12), 0.5)
        self.assertEqual(TB_24.fpsToScale(0), 0.0)
        self.assertEqual(TB_24.fpsToScale(-12), -0.5)
        self.assertRaises(TypeError, Base.fpsToScale, TB_24, 'bad')

        self.assert_(isinstance(TB(1, 1.0), Base))

        # tests across bases
        self.assertRaises(ValueError, Time.__cmp__, Time(base=TB_24), Time(base=TB_120))

        # accept 1001/1000 instead of repeating float
        self.assert_(TB_23976 == Base(24, 1.001))
        self.assert_(TB_2997 == Base(30, 1.001))
        self.assert_(TB_5994 == Base(60, 1.001))

    def variantTestBase(self, strtype):
        self.assertEqual(TB_24.timecodeToFrame(strtype('00:00:00:00')), 0)
        self.assertEqual(TB_24.timecodeToFrame(strtype('00:00:00:01')), 1)
        self.assertEqual(TB_24.timecodeToFrame(strtype('-00:00:00:00')), 0)
        self.assertEqual(TB_24.timecodeToFrame(strtype('-00:00:00:01')), -1)
        self.assertEqual(TB_24.timecodeToFrame(strtype('00:00:00:23')), 23)
        self.assertEqual(TB_24.timecodeToFrame(strtype('-00:00:00:23')), -23)
        self.assertEqual(TB_24.timecodeToFrame(strtype('00:00:01:00')), 24)
        self.assertEqual(TB_24.timecodeToFrame(strtype('-00:00:01:00')), -24)
        self.assertRaises(ValueError, Base.timecodeToFrame, TB_24, strtype('00:00'))
        self.assertRaises(ValueError, Base.timecodeToFrame, TB_24, strtype('00:00:00:24'))
        self.assertRaises(ValueError, Base.timecodeToFrame, TB_24, strtype('00:00:60:01'))

    def variantTestTime(self, strtype, base):
        print "Time Codes"

        self.assert_(isinstance(Time(base=base), Time))
        
        self.assertEqual(Time(base=base).frame(), 0)
        self.assertEqual(Time(base=base).Base, base or TB_DEFAULT)
        
        # illegal initialization variants
        self.assertRaises(ValueError, Time, time=Time(base=base), timecode='00:00:00:00')
        self.assertRaises(ValueError, Time, time=Time(base=base), frame=5)
        self.assertRaises(ValueError, Time, time=Time(base=base), base=TB_DEFAULT)
        self.assertRaises(ValueError, Time, timecode=strtype('00:00:00:00'), frame=4, base=base)
        
        # initialized with another time
        self.assert_(isinstance(Time(time=Time(base=base)), Time))
        self.assertRaises(TypeError, Time, time='bad')

        # initialized with a code basestring
        self.assert_(isinstance(Time(timecode=strtype('00:00:00:00')), Time))
        self.assertRaises(TypeError, Time, timecode=45, base=base)
        
        # initialized with a frame int
        self.assert_(isinstance(Time(frame=4), Time))
        self.assertRaises(TypeError, Time, frame='bad', base=base)
        
        tzero = TC(strtype("00:00:00:00"), base=base)
        self.assert_(tzero.frame() == 0)
        self.assert_(tzero.timecode() == strtype("00:00:00:00"))
        
        tone = TC(strtype("00:00:00:01"), base=base)
        self.assert_(tone.frame() == 1)
        self.assert_(tone.timecode() == strtype("00:00:00:01"))
        
        ttwo = TC(strtype("00:00:00:02"), base=base)
        assert ttwo.frame() == 2
        assert ttwo.timecode() == strtype("00:00:00:02")

        print "Time Frames"

        zero = FR(0, base=base)
        assert zero.frame() == 0
        
        one = FR(1, base=base)
        assert one.frame() == 1
        
        two = FR(2, base=base)
        assert two.frame() == 2

        three = FR(3, base=base)
        assert three.frame() == 3

        onesec = TC(strtype("00:00:01:00"), base=base)
        assert onesec.frame() == (base or TB_DEFAULT).FramesPerSecond

        print "Time Realtime"

        assert 0.0 == zero.realtimeSeconds()
        assert ( 1.0 * (base or TB_DEFAULT).RealtimeScale ) == onesec.realtimeSeconds()

        print "Time Limits"
        
        lowLimit = TC(strtype("-999:59:59:00"), base=base)
        print 'lowLimit', lowLimit, int(lowLimit)
        assert lowLimit.frame() < 0
        assert lowLimit < zero
        assert lowLimit.timecode() == strtype("-999:59:59:00")

        upLimit = TC(strtype("999:59:59:00"), base=base)
        print 'upLimit', upLimit, int(upLimit)
        assert upLimit.frame() > 0
        assert upLimit > zero
        assert upLimit.timecode() == strtype("999:59:59:00")

        print "Time Counting"

        for frame in range(-60, 61):
            f = FR(frame, base=base)
            t = TC(f.timecode(), base=base)
            assert f == t

        print "Time Comparisons"

        assert zero == zero
        assert one == one
        assert two == two

        assert tzero == zero
        assert tone == one
        assert ttwo == two

        assert not ( zero > one )
        assert one > zero
        assert two > zero
        assert zero < one
        assert zero <= one
        assert two <= two
        
        print "Time Math"

        assert zero + one == one
        assert one + one == two
        assert two - one == one
        assert two - two == zero

        print "Intervals"

        self.assert_(isinstance(Interval(zero, endtc=one), Interval))
        self.assertEqual(Interval(zero, endtc=one).Start, zero)
        self.assertEqual(Interval(zero, endtc=one).EndTC, one)
        self.assertEqual(Interval(zero, endtc=one).EndFR, zero)

        self.assert_(isinstance(Interval(zero, endfr=zero), Interval))
        self.assertEqual(Interval(zero, endfr=one).Start, zero)
        self.assertEqual(Interval(zero, endfr=one).EndTC, two)
        self.assertEqual(Interval(zero, endfr=one).EndFR, one)
        
        self.assertRaises(TypeError, Interval, None)
        self.assertRaises(TypeError, Interval, None, endtc=one)
        self.assertRaises(TypeError, Interval, None, endfr=one)

        iZeroZero = Interval(zero, endtc=zero)
        assert iZeroZero.duration() == zero
        # Interval(zero, endfr=zero) would be negative, value error
        
        iZeroOne = Interval(zero, endtc=one)
        assert iZeroOne.duration() == one
        assert Interval(zero, endfr=one).duration() == two

        iOneTwo = Interval(one, endtc=two)
        assert iOneTwo.duration() == one
        assert Interval(one, endfr=two).duration() == two
        
        iZeroTwo = Interval(zero, endtc=two)
        assert iZeroTwo.duration() == two
        assert Interval(zero, endfr=two).duration() == three
        
        for t in iZeroTwo:
            print t

        print "Time / Interval comparisons"
        assert zero < iOneTwo

        print "Time / Interval Contains"
        
        assert zero in iZeroOne
        assert one not in iZeroOne
        assert two not in iZeroOne
        assert zero not in iOneTwo

        print "Interval / Interval Contains"

        assert iZeroZero not in iOneTwo
        assert iOneTwo in iZeroTwo

        # union & intersect test

        print "Speed"
        
        self.assert_(isinstance(LinearSpeed(Interval(Time(base=base), endtc=Time(base=base)), 1.0), Speed))

        s1 = LinearSpeed(iZeroTwo, 2.0)
        assert s1[one] == two

    def testVariants(self):
        for strtype in [lambda value: value, lambda value: unicode(value)]:
            self.variantTestBase(strtype)
            for base in [ None, 
                         TB_24, TB_23976,
                         TB_30, TB_2997,
                         TB_60, TB_5994,
                         TB_120 ]:
                self.variantTestTime(strtype, base)

            print "Rollover"
    
            t23 = FR(23, base=TB_24)
            assert t23.timecode() == strtype("00:00:00:23")
    
            t24 = FR(24, base=TB_24)
            assert t24.timecode() == strtype("00:00:01:00")
    
            assert ( t23 + FR(1, base=TB_24) ) == t24
    
            t1min = TC(strtype("00:01:00:00"), base=TB_24)
            assert t1min.frame() == ( 60 * 24 )

    def testIntervals(self):
        print "Interval / Interval bases"
        self.assertRaises(ValueError, Interval, Time(base=TB_120), endtc=Time(base=TB_24))
        self.assertRaises(ValueError, Interval, Time(base=TB_120), endfr=Time(base=TB_24))

if __name__ == "__main__":
    unittest.main()
