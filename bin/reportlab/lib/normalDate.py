#!/usr/bin/env python
# normalDate.py - version 1.0 - 20000717
#hacked by Robin Becker 10/Apr/2001
#major changes include
#   using Types instead of type(0) etc
#   BusinessDate class
#   __radd__, __rsub__ methods
#   formatMS stuff

# derived from an original version created
# by Jeff Bauer of Rubicon Research and used
# with his kind permission
__version__=''' $Id: normalDate.py 2742 2005-12-12 11:58:08Z oualid $ '''



_bigBangScalar = -4345732  # based on (-9999, 1, 1) BC/BCE minimum
_bigCrunchScalar = 2958463  # based on (9999,12,31) AD/CE maximum
_daysInMonthNormal = [31,28,31,30,31,30,31,31,30,31,30,31]
_daysInMonthLeapYear = [31,29,31,30,31,30,31,31,30,31,30,31]
_dayOfWeekName = ['Monday', 'Tuesday', 'Wednesday', 'Thursday',
                  'Friday', 'Saturday', 'Sunday']
_monthName = ['January', 'February', 'March', 'April', 'May', 'June',
              'July','August','September','October','November','December']

from types import IntType, StringType, ListType, TupleType
import string, re, time, datetime
if hasattr(time,'struct_time'):
    _DateSeqTypes = (ListType,TupleType,time.struct_time)
else:
    _DateSeqTypes = (ListType,TupleType)

_fmtPat = re.compile('\\{(m{1,5}|yyyy|yy|d{1,4})\\}',re.MULTILINE|re.IGNORECASE)
_iso_re = re.compile(r'(\d\d\d\d|\d\d)-(\d\d)-(\d\d)')

def getStdMonthNames():
    return map(string.lower,_monthName)

def getStdShortMonthNames():
    return map(lambda x: x[:3],getStdMonthNames())

def getStdDayNames():
    return map(string.lower,_dayOfWeekName)

def getStdShortDayNames():
    return map(lambda x: x[:3],getStdDayNames())

def isLeapYear(year):
    """determine if specified year is leap year, returns Python boolean"""
    if year < 1600:
        if year % 4:
            return 0
        else:
            return 1
    elif year % 4 != 0:
        return 0
    elif year % 100 != 0:
        return 1
    elif year % 400 != 0:
        return 0
    else:
        return 1

class NormalDateException(Exception):
    """Exception class for NormalDate"""
    pass

class NormalDate:
    """
    NormalDate is a specialized class to handle dates without
    all the excess baggage (time zones, daylight savings, leap
    seconds, etc.) of other date structures.  The minimalist
    strategy greatly simplifies its implementation and use.

    Internally, NormalDate is stored as an integer with values
    in a discontinuous range of -99990101 to 99991231.  The
    integer value is used principally for storage and to simplify
    the user interface.  Internal calculations are performed by
    a scalar based on Jan 1, 1900.

    Valid NormalDate ranges include (-9999,1,1) B.C.E. through
    (9999,12,31) C.E./A.D.

    1.0 - No changes, except the version number.  After 3 years of use
            by various parties I think we can consider it stable.
    0.8 - added Prof. Stephen Walton's suggestion for a range method
            - module author resisted the temptation to use lambda <0.5 wink>
    0.7 - added Dan Winkler's suggestions for __add__, __sub__ methods
    0.6 - modifications suggested by Kevin Digweed to fix:
            - dayOfWeek, dayOfWeekAbbrev, clone methods
            - permit NormalDate to be a better behaved superclass
    0.5 - minor tweaking
    0.4 - added methods __cmp__, __hash__
        - added Epoch variable, scoped to the module
        - added setDay, setMonth, setYear methods
    0.3 - minor touch-ups
    0.2 - fixed bug for certain B.C.E leap years
        - added Jim Fulton's suggestions for short alias class name =ND
          and __getstate__, __setstate__ methods

    Special thanks:  Roedy Green
    """
    def __init__(self, normalDate=None):
        """
        Accept 1 of 4 values to initialize a NormalDate:
            1. None - creates a NormalDate for the current day
            2. integer in yyyymmdd format
            3. string in yyyymmdd format
            4. tuple in (yyyy, mm, dd) - localtime/gmtime can also be used
        """
        if normalDate is None:
            self.setNormalDate(time.localtime(time.time()))
        else:
            self.setNormalDate(normalDate)

    def add(self, days):
        """add days to date; use negative integers to subtract"""
        if not type(days) is IntType:
            raise NormalDateException( \
                'add method parameter must be integer type')
        self.normalize(self.scalar() + days)

    def __add__(self, days):
        """add integer to normalDate and return a new, calculated value"""
        if not type(days) is IntType:
            raise NormalDateException( \
                '__add__ parameter must be integer type')
        cloned = self.clone()
        cloned.add(days)
        return cloned

    def __radd__(self,days):
        '''for completeness'''
        return self.__add__(days)

    def clone(self):
        """return a cloned instance of this normalDate"""
        return self.__class__(self.normalDate)

    def __cmp__(self, target):
        if target is None:
            return 1
        elif not hasattr(target, 'normalDate'):
            return 1
        else:
            return cmp(self.normalDate, target.normalDate)

    def day(self):
        """return the day as integer 1-31"""
        return int(repr(self.normalDate)[-2:])

    def dayOfWeek(self):
        """return integer representing day of week, Mon=0, Tue=1, etc."""
        return apply(dayOfWeek, self.toTuple())

    def dayOfWeekAbbrev(self):
        """return day of week abbreviation for current date: Mon, Tue, etc."""
        return _dayOfWeekName[self.dayOfWeek()][:3]

    def dayOfWeekName(self):
        """return day of week name for current date: Monday, Tuesday, etc."""
        return _dayOfWeekName[self.dayOfWeek()]

    def dayOfYear(self):
        """day of year"""
        if self.isLeapYear():
            daysByMonth = _daysInMonthLeapYear
        else:
            daysByMonth = _daysInMonthNormal
        priorMonthDays = 0
        for m in xrange(self.month() - 1):
            priorMonthDays = priorMonthDays + daysByMonth[m]
        return self.day() + priorMonthDays

    def daysBetweenDates(self, normalDate):
        """
        return value may be negative, since calculation is
        self.scalar() - arg
        """
        if type(normalDate) is _NDType:
            return self.scalar() - normalDate.scalar()
        else:
            return self.scalar() - NormalDate(normalDate).scalar()

    def equals(self, target):
        if type(target) is _NDType:
            if target is None:
                return self.normalDate is None
            else:
                return self.normalDate == target.normalDate
        else:
            return 0

    def endOfMonth(self):
        """returns (cloned) last day of month"""
        return self.__class__(self.__repr__()[-8:-2]+str(self.lastDayOfMonth()))

    def firstDayOfMonth(self):
        """returns (cloned) first day of month"""
        return self.__class__(self.__repr__()[-8:-2]+"01")

    def formatUS(self):
        """return date as string in common US format: MM/DD/YY"""
        d = self.__repr__()
        return "%s/%s/%s" % (d[-4:-2], d[-2:], d[-6:-4])

    def formatUSCentury(self):
        """return date as string in 4-digit year US format: MM/DD/YYYY"""
        d = self.__repr__()
        return "%s/%s/%s" % (d[-4:-2], d[-2:], d[-8:-4])

    def _fmtM(self):
        return str(self.month())

    def _fmtMM(self):
        return '%02d' % self.month()

    def _fmtMMM(self):
        return self.monthAbbrev()

    def _fmtMMMM(self):
        return self.monthName()

    def _fmtMMMMM(self):
        return self.monthName()[0]

    def _fmtD(self):
        return str(self.day())

    def _fmtDD(self):
        return '%02d' % self.day()

    def _fmtDDD(self):
        return self.dayOfWeekAbbrev()

    def _fmtDDDD(self):
        return self.dayOfWeekName()

    def _fmtYY(self):
        return '%02d' % (self.year()%100)

    def _fmtYYYY(self):
        return str(self.year())

    def formatMS(self,fmt):
        '''format like MS date using the notation
        {YY}    --> 2 digit year
        {YYYY}  --> 4 digit year
        {M}     --> month as digit
        {MM}    --> 2 digit month
        {MMM}   --> abbreviated month name
        {MMMM}  --> monthname
        {MMMMM} --> first character of monthname
        {D}     --> day of month as digit
        {DD}    --> 2 digit day of month
        {DDD}   --> abrreviated weekday name
        {DDDD}  --> weekday name
        '''
        r = fmt[:]
        f = 0
        while 1:
            m = _fmtPat.search(r,f)
            if m:
                y = getattr(self,'_fmt'+string.upper(m.group()[1:-1]))()
                i, j = m.span()
                r = (r[0:i] + y) + r[j:]
                f = i + len(y)
            else:
                return r

    def __getstate__(self):
        """minimize persistent storage requirements"""
        return self.normalDate

    def __hash__(self):
        return hash(self.normalDate)

    def __int__(self):
        return self.normalDate

    def isLeapYear(self):
        """
        determine if specified year is leap year, returning true (1) or
        false (0)
        """
        return isLeapYear(self.year())

    def _isValidNormalDate(self, normalDate):
        """checks for date validity in [-]yyyymmdd format"""
        if type(normalDate) is not IntType:
            return 0
        if len(repr(normalDate)) > 9:
            return 0
        if normalDate < 0:
            dateStr = "%09d" % normalDate
        else:
            dateStr = "%08d" % normalDate
        if len(dateStr) < 8:
            return 0
        elif len(dateStr) == 9:
            if (dateStr[0] != '-' and dateStr[0] != '+'):
                return 0
        year = int(dateStr[:-4])
        if year < -9999 or year > 9999 or year == 0:
            return 0    # note: zero (0) is not a valid year
        month = int(dateStr[-4:-2])
        if month < 1 or month > 12:
            return 0
        if isLeapYear(year):
            maxDay = _daysInMonthLeapYear[month - 1]
        else:
            maxDay = _daysInMonthNormal[month - 1]
        day = int(dateStr[-2:])
        if day < 1 or day > maxDay:
            return 0
        if year == 1582 and month == 10 and day > 4 and day < 15:
            return 0  # special case of 10 days dropped: Oct 5-14, 1582
        return 1

    def lastDayOfMonth(self):
        """returns last day of the month as integer 28-31"""
        if self.isLeapYear():
            return _daysInMonthLeapYear[self.month() - 1]
        else:
            return _daysInMonthNormal[self.month() - 1]

    def localeFormat(self):
        """override this method to use your preferred locale format"""
        return self.formatUS()

    def month(self):
        """returns month as integer 1-12"""
        return int(repr(self.normalDate)[-4:-2])

    def monthAbbrev(self):
        """returns month as a 3-character abbreviation, i.e. Jan, Feb, etc."""
        return _monthName[self.month() - 1][:3]

    def monthName(self):
        """returns month name, i.e. January, February, etc."""
        return _monthName[self.month() - 1]

    def normalize(self, scalar):
        """convert scalar to normalDate"""
        if scalar < _bigBangScalar:
            msg = "normalize(%d): scalar below minimum" % \
                  _bigBangScalar
            raise NormalDateException(msg)
        if scalar > _bigCrunchScalar:
            msg = "normalize(%d): scalar exceeds maximum" % \
                  _bigCrunchScalar
            raise NormalDateException(msg)
        from math import floor
        if scalar >= -115860:
            year = 1600 + int(floor((scalar + 109573) / 365.2425))
        elif scalar >= -693597:
            year = 4 + int(floor((scalar + 692502) / 365.2425))
        else:
            year = -4 + int(floor((scalar + 695058) / 365.2425))
        days = scalar - firstDayOfYear(year) + 1
        if days <= 0:
            year = year - 1
            days = scalar - firstDayOfYear(year) + 1
        daysInYear = 365
        if isLeapYear(year):
            daysInYear = daysInYear + 1
        if days > daysInYear:
            year = year + 1
            days = scalar - firstDayOfYear(year) + 1
        # add 10 days if between Oct 15, 1582 and Dec 31, 1582
        if (scalar >= -115860 and scalar <= -115783):
            days = days + 10
        if isLeapYear(year):
            daysByMonth = _daysInMonthLeapYear
        else:
            daysByMonth = _daysInMonthNormal
        dc = 0; month = 12
        for m in xrange(len(daysByMonth)):
            dc = dc + daysByMonth[m]
            if dc >= days:
                month = m + 1
                break
        # add up the days in prior months
        priorMonthDays = 0
        for m in xrange(month - 1):
            priorMonthDays = priorMonthDays + daysByMonth[m]
        day = days - priorMonthDays
        self.setNormalDate((year, month, day))

    def range(self, days):
        """Return a range of normalDates as a list.  Parameter
        may be an int or normalDate."""
        if type(days) is not IntType:
            days = days - self  # if not int, assume arg is normalDate type
        r = []
        for i in range(days):
            r.append(self + i)
        return r

    def __repr__(self):
        """print format: [-]yyyymmdd"""
        # Note: When disassembling a NormalDate string, be sure to
        # count from the right, i.e. epochMonth = int(`Epoch`[-4:-2]),
        # or the slice won't work for dates B.C.
        if self.normalDate < 0:
            return "%09d" % self.normalDate
        else:
            return "%08d" % self.normalDate

    def scalar(self):
        """days since baseline date: Jan 1, 1900"""
        (year, month, day) = self.toTuple()
        days = firstDayOfYear(year) + day - 1
        if self.isLeapYear():
            for m in xrange(month - 1):
                days = days + _daysInMonthLeapYear[m]
        else:
            for m in xrange(month - 1):
                days = days + _daysInMonthNormal[m]
        if year == 1582:
            if month > 10 or (month == 10 and day > 4):
                days = days - 10
        return days

    def setDay(self, day):
        """set the day of the month"""
        maxDay = self.lastDayOfMonth()
        if day < 1 or day > maxDay:
            msg = "day is outside of range 1 to %d" % maxDay
            raise NormalDateException(msg)
        (y, m, d) = self.toTuple()
        self.setNormalDate((y, m, day))

    def setMonth(self, month):
        """set the month [1-12]"""
        if month < 1 or month > 12:
            raise NormalDateException('month is outside range 1 to 12')
        (y, m, d) = self.toTuple()
        self.setNormalDate((y, month, d))

    def setNormalDate(self, normalDate):
        """
        accepts date as scalar string/integer (yyyymmdd) or tuple
        (year, month, day, ...)"""
        tn=type(normalDate)
        if tn is IntType:
            self.normalDate = normalDate
        elif tn is StringType:
            try:
                self.normalDate = int(normalDate)
            except:
                m = _iso_re.match(normalDate)
                if m:
                    self.setNormalDate(m.group(1)+m.group(2)+m.group(3))
                else:
                    raise NormalDateException("unable to setNormalDate(%s)" % `normalDate`)
        elif tn in _DateSeqTypes:
            self.normalDate = int("%04d%02d%02d" % normalDate[:3])
        elif tn is _NDType:
            self.normalDate = normalDate.normalDate
        elif isinstance(normalDate,(datetime.datetime,datetime.date)):
            self.normalDate = (normalDate.year*100+normalDate.month)*100+normalDate.day
        if not self._isValidNormalDate(self.normalDate):
            raise NormalDateException("unable to setNormalDate(%s)" % `normalDate`)

    def setYear(self, year):
        if year == 0:
            raise NormalDateException('cannot set year to zero')
        elif year < -9999:
            raise NormalDateException('year cannot be less than -9999')
        elif year > 9999:
            raise NormalDateException('year cannot be greater than 9999')
        (y, m, d) = self.toTuple()
        self.setNormalDate((year, m, d))

    __setstate__ = setNormalDate

    def __sub__(self, v):
        if type(v) is IntType:
            return self.__add__(-v)
        return self.scalar() - v.scalar()

    def __rsub__(self,v):
        if type(v) is IntType:
            return NormalDate(v) - self
        else:
            return v.scalar() - self.scalar()

    def toTuple(self):
        """return date as (year, month, day) tuple"""
        return (self.year(), self.month(), self.day())

    def year(self):
        """return year in yyyy format, negative values indicate B.C."""
        return int(repr(self.normalDate)[:-4])

#################  Utility functions  #################

def bigBang():
    """return lower boundary as a NormalDate"""
    return NormalDate((-9999, 1, 1))

def bigCrunch():
    """return upper boundary as a NormalDate"""
    return NormalDate((9999, 12, 31))

def dayOfWeek(y, m, d):
    """return integer representing day of week, Mon=0, Tue=1, etc."""
    if m == 1 or m == 2:
        m = m + 12
        y = y - 1
    return (d + 2*m + 3*(m+1)/5 + y + y/4 - y/100 + y/400) % 7

def firstDayOfYear(year):
    """number of days to the first of the year, relative to Jan 1, 1900"""
    if type(year) is not IntType:
        msg = "firstDayOfYear() expected integer, got %s" % type(year)
        raise NormalDateException(msg)
    if year == 0:
        raise NormalDateException('first day of year cannot be zero (0)')
    elif year < 0:  # BCE calculation
        firstDay = (year * 365) + int((year - 1) / 4) - 693596
    else:           # CE calculation
        leapAdjust = int((year + 3) / 4)
        if year > 1600:
            leapAdjust = leapAdjust - int((year + 99 - 1600) / 100) + \
                         int((year + 399 - 1600) / 400)
        firstDay = year * 365 + leapAdjust - 693963
        if year > 1582:
            firstDay = firstDay - 10
    return firstDay

def FND(d):
    '''convert to ND if required'''
    return (type(d) is _NDType) and d or ND(d)

Epoch=bigBang()
ND=NormalDate
_NDType = type(Epoch)
BDEpoch=ND(15821018)
BDEpochScalar = -115857

class BusinessDate(NormalDate):
    """
    Specialised NormalDate
    """
    def add(self, days):
        """add days to date; use negative integers to subtract"""
        if not type(days) is IntType:
            raise NormalDateException('add method parameter must be integer type')
        self.normalize(self.scalar() + days)

    def __add__(self, days):
        """add integer to BusinessDate and return a new, calculated value"""
        if not type(days) is IntType:
            raise NormalDateException('__add__ parameter must be integer type')
        cloned = self.clone()
        cloned.add(days)
        return cloned

    def __sub__(self, v):
        return type(v) is IntType and self.__add__(-v) or self.scalar() - v.scalar()

    def asNormalDate(self):
        return ND(self.normalDate)

    def daysBetweenDates(self, normalDate):
        return self.asNormalDate.daysBetweenDates(normalDate)

    def _checkDOW(self):
        if self.dayOfWeek()>4: raise NormalDateException("%s isn't a business day" % `self.normalDate`)

    def normalize(self, i):
        i = int(i)
        NormalDate.normalize(self,(i/5)*7+i%5+BDEpochScalar)

    def scalar(self):
        d = self.asNormalDate()
        i = d - BDEpoch     #luckily BDEpoch is a Monday so we don't have a problem
                            #concerning the relative weekday
        return 5*(i/7) + i%7

    def setNormalDate(self, normalDate):
        NormalDate.setNormalDate(self,normalDate)
        self._checkDOW()

if __name__ == '__main__':
    today = NormalDate()
    print "NormalDate test:"
    print "  Today (%s) is: %s %s" % (today, today.dayOfWeekAbbrev(), today.localeFormat())
    yesterday = today - 1
    print "  Yesterday was: %s %s" % (yesterday.dayOfWeekAbbrev(), yesterday.localeFormat())
    tomorrow = today + 1
    print "  Tomorrow will be: %s %s" % (tomorrow.dayOfWeekAbbrev(), tomorrow.localeFormat())
    print "  Days between tomorrow and yesterday: %d" % (tomorrow - yesterday)
    print today.formatMS('{d}/{m}/{yy}')
    print today.formatMS('{dd}/{m}/{yy}')
    print today.formatMS('{ddd} {d}/{m}/{yy}')
    print today.formatMS('{dddd} {d}/{m}/{yy}')
    print today.formatMS('{d}/{mm}/{yy}')
    print today.formatMS('{d}/{mmm}/{yy}')
    print today.formatMS('{d}/{mmmm}/{yy}')
    print today.formatMS('{d}/{m}/{yyyy}')
    b = BusinessDate('20010116')
    print 'b=',b,'b.scalar()', b.scalar()
