#@+leo-ver=4
#@+node:@file pcalendar.py
#@@language python
#@<< Copyright >>
#@+node:<< Copyright >>
############################################################################
#   Copyright (C) 2005, 2006, 2007, 2008 by Reithinger GmbH
#   mreithinger@web.de
#
#   This file is part of faces.
#
#   faces is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation; either version 2 of the License, or
#   (at your option) any later version.
#
#   faces is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program; if not, write to the
#   Free Software Foundation, Inc.,
#   59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
############################################################################

#@-node:<< Copyright >>
#@nl
"""
This module contains all classes and functions for the project plan calendar
"""
#@<< Imports >>
#@+node:<< Imports >>
from string import *
import datetime
import time
import re
import locale
import bisect
import sys

TIME_RANGE_PATTERN = re.compile("(\\d+):(\\d+)\\s*-\\s*(\\d+):(\\d+)")
TIME_DELTA_PATTERN = re.compile("([-+]?\\d+(\\.\\d+)?)([dwmyMH])")

DEFAULT_MINIMUM_TIME_UNIT = 15
DEFAULT_WORKING_DAYS_PER_WEEK  = 5
DEFAULT_WORKING_DAYS_PER_MONTH = 20
DEFAULT_WORKING_DAYS_PER_YEAR = 200
DEFAULT_WORKING_HOURS_PER_DAY = 8

DEFAULT_WORKING_TIMES = ( (8 * 60, 12 * 60 ),
                          (13 * 60, 17 * 60 ) )
DEFAULT_WORKING_DAYS = { 0 : DEFAULT_WORKING_TIMES,
                         1 : DEFAULT_WORKING_TIMES,
                         2 : DEFAULT_WORKING_TIMES,
                         3 : DEFAULT_WORKING_TIMES,
                         4 : DEFAULT_WORKING_TIMES,
                         5 : (),
                         6 : () }

#@-node:<< Imports >>
#@nl
#@+others
#@+node:to_time_range
def to_time_range(src):
    """
    converts a string to a timerange, i.e
    (from, to)
    from, to are ints, specifing the minutes since midnight
    """

    if not src: return ()

    mo = TIME_RANGE_PATTERN.match(src)
    if not mo:
        raise ValueError("%s is no time range" % src)

    from_time = int(mo.group(1)) * 60 + int(mo.group(2))
    to_time   = int(mo.group(3)) * 60 + int(mo.group(4))
    return from_time, to_time
#@-node:to_time_range
#@+node:to_datetime
def to_datetime(src):
    """
    a tolerant conversion function to convert different strings
    to a datetime.dateime
    """

    #to get the original value for wrappers
    new = getattr(src, "_value", src)
    while new is not src:
        src = new
        new = getattr(src, "_value", src)

    if isinstance(src, _WorkingDateBase):
        src = src.to_datetime()

    if isinstance(src, datetime.datetime):
        return src

    src = str(src)

    formats = [ "%x %H:%M",
                "%x",
                "%Y-%m-%d %H:%M",
                "%y-%m-%d %H:%M",
                "%d.%m.%Y %H:%M",
                "%d.%m.%y %H:%M",
                "%Y%m%d %H:%M",
                "%d/%m/%y %H:%M",
                "%d/%m/%Y %H:%M",
                "%d/%m/%Y",
                "%d/%m/%y",
                "%Y-%m-%d",
                "%y-%m-%d",
                "%d.%m.%Y",
                "%d.%m.%y",
                "%Y%m%d" ]
    for f in formats:
        try:
            conv = time.strptime(src, f)

            return datetime.datetime(*conv[0:-3])
        except Exception, e:
            pass

    raise TypeError("'%s' (%s) is not a datetime" % (src, str(type(src))))
#@-node:
#@+node:_to_days
def _to_days(src):
    """
    converts a string of the day abreviations mon, tue, wed,
    thu, fri, sat, sun to a dir with correct weekday indices.
    For Example
    convert_to_days('mon, tue, thu') results in
    { 0:1, 1:1, 3:1 }
    """

    tokens = src.split(",")
    result = { }
    for t in tokens:
        try:
            index =  { "mon" : 0,
                       "tue" : 1,
                       "wed" : 2,
                       "thu" : 3,
                       "fri" : 4,
                       "sat" : 5,
                       "sun" : 6 } [ lower(t.strip()) ]
            result[index] = 1
        except:
            raise ValueError("%s is not a day" % (t))

    return result
#@-node:_to_days
#@+node:_add_to_time_spans
def _add_to_time_spans(src, to_add, is_free):
    if not isinstance(to_add, (tuple, list)):
        to_add = (to_add,)

    tmp = []
    for start, end, f in src:
        tmp.append((start, True, f))
        tmp.append((end, False, f))

    for v in to_add:
        if isinstance(v, (tuple, list)):
            start = to_datetime(v[0])
            end = to_datetime(v[1])
        else:
            start = to_datetime(v)
            end = start.replace(hour=0, minute=0) + datetime.timedelta(1)

        tmp.append((start, start <= end, is_free))
        tmp.append((end, start > end, is_free))

    tmp.sort()

    # 0: date
    # 1: is_start
    # 2: is_free
    sequence = []
    free_count = 0
    work_count = 0
    last = None
    for date, is_start, is_free in tmp:
        if is_start:
            if is_free:
                if not free_count and not work_count:
                    last = date

                free_count += 1
            else:
                if not work_count:
                    if free_count: sequence.append((last, date, True))
                    last = date
                work_count += 1
        else:
            if is_free:
                assert(free_count > 0)
                free_count -= 1
                if not free_count and not work_count:
                    sequence.append((last, date, True))
            else:
                assert(work_count > 0)
                work_count -= 1
                if not work_count: sequence.append((last, date, False))
                if free_count: last = date

    return tuple(sequence)
#@-node:_add_to_time_spans
#@+node:to_timedelta
def to_timedelta(src, cal=None, is_duration=False):
    """
    converts a string to a datetime.timedelta. If cal is specified
    it will be used for getting the working times. if is_duration=True
    working times will not be considered. Valid units are
    d for Days
    w for Weeks
    m for Months
    y for Years
    H for Hours
    M for Minutes
    """

    cal = cal or _default_calendar
    if isinstance(src, datetime.timedelta):
        return datetime.timedelta(src.days, seconds=src.seconds, calendar=cal)

    if isinstance(src, (long, int, float)):
        src = "%sM" % str(src)

    if not isinstance(src, basestring):
        raise ValueError("%s is not a duration" % (repr(src)))

    src = src.strip()

    if is_duration:
        d_p_w = 7
        d_p_m = 30
        d_p_y = 360
        d_w_h = 24
    else:
        d_p_w = cal.working_days_per_week
        d_p_m = cal.working_days_per_month
        d_p_y = cal.working_days_per_year
        d_w_h = cal.working_hours_per_day

    def convert_minutes(minutes):
        minutes = int(minutes)
        hours   = minutes / 60
        minutes = minutes % 60
        days    = hours / d_w_h
        hours   = hours % d_w_h
        return [ days, 0, 0, 0, minutes, hours ]

    def convert_days(value):
        days = int(value)
        value -= days
        value *= d_w_h
        hours = int(value)
        value -= hours
        value *= 60
        minutes = round(value)
        return [ days, 0, 0, 0, minutes, hours ]

    sum_args = [ 0, 0, 0, 0, 0, 0 ]

    split = src.split(" ")
    for s in split:
        mo = TIME_DELTA_PATTERN.match(s)
        if not mo:
            raise ValueError(src +
                             " is not a valid duration: valid"
                             " units are: d w m y M H")

        unit = mo.group(3)
        val = float(mo.group(1))

        if unit == 'd':
            args = convert_days(val)
        elif unit == 'w':
            args = convert_days(val * d_p_w)
        elif unit == 'm':
            args = convert_days(val * d_p_m)
        elif unit == 'y':
            args = convert_days(val * d_p_y)
        elif unit == 'M':
            args = convert_minutes(val)
        elif unit == 'H':
            args = convert_minutes(val * 60)

        sum_args = [ a + b for a, b in zip(sum_args, args) ]

    sum_args = tuple(sum_args)
    return datetime.timedelta(*sum_args)
#@-node:to_timedelta
#@+node:timedelta_to_str
def timedelta_to_str(delta, format, cal=None, is_duration=False):
    cal = cal or _default_calendar
    if is_duration:
        d_p_w = 7
        d_p_m = 30
        d_p_y = 365
        d_w_h = 24
    else:
        d_p_w = cal.working_days_per_week
        d_p_m = cal.working_days_per_month
        d_p_y = cal.working_days_per_year
        d_w_h = cal.working_hours_per_day

    has_years = format.find("%y") > -1
    has_minutes = format.find("%M") > -1
    has_hours = format.find("%H") > -1 or has_minutes
    has_days = format.find("%d") > -1
    has_weeks = format.find("%w") > -1
    has_months = format.find("%m") > -1

    result = format
    days = delta.days

    d_r = (days, format)
    minutes = delta.seconds / 60

    def rebase(d_r, cond1, cond2, letter, divisor):
        #rebase the days
        if not cond1: return d_r

        days, result = d_r

        if cond2:
            val = days / divisor
            if not val:
                result = re.sub("{[^{]*?%" + letter + "[^}]*?}", "", result)

            result = result.replace("%" + letter, str(val))
            days %= divisor
        else:
            result = result.replace("%" + letter,
                                    locale.format("%.2f",
                                                  (float(days) / divisor)))

        return (days, result)

    d_r = rebase(d_r, has_years, has_months or has_weeks or has_days, "y", d_p_y)
    d_r = rebase(d_r, has_months, has_weeks or has_days, "m", d_p_m)
    d_r = rebase(d_r, has_weeks, has_days, "w", d_p_w)
    days, result = d_r

    if not has_days:
        minutes += days * d_w_h * 60
        days = 0

    if has_hours:
        if not days:
            result = re.sub("{[^{]*?%d[^}]*?}", "", result)

        result = result.replace("%d", str(days))
    else:
        result = result.replace("%d",
                                "%.2f" % (days + float(minutes)
                                        / (d_w_h * 60)))

    if has_hours:
        if has_minutes:
            val = minutes / 60
            if not val:
                result = re.sub("{[^{]*?%H[^}]*?}", "", result)

            result = result.replace("%H", str(val))
            minutes %= 60
        else:
            result = result.replace("%H", "%.2f" % (float(minutes) / 60))

    if not minutes:
        result = re.sub("{[^{]*?%M[^}]*?}", "", result)

    result = result.replace("%M", str(minutes))

    result = result.replace("{", "")
    result = result.replace("}", "")
    return result.strip()
#@-node:timedelta_to_str
#@+node:strftime
def strftime(dt, format):
    """
    an extended version of strftime, that introduces some new
    directives:
    %IW   iso week number
    %IY   iso year
    %IB   full month name appropriate to iso week
    %ib   abbreviated month name appropriate to iso week
    %im   month as decimal number appropriate to iso week
    """
    iso = dt.isocalendar()
    if iso[0] != dt.year:
        iso_date = dt.replace(day=1, month=1)
        format = format \
                 .replace("%IB", iso_date.strftime("%B"))\
                 .replace("%ib", iso_date.strftime("%b"))\
                 .replace("%im", iso_date.strftime("%m"))
    else:
        format = format \
                 .replace("%IB", "%B")\
                 .replace("%ib", "%b")\
                 .replace("%im", "%m")

    format = format \
             .replace("%IW", str(iso[1]))\
             .replace("%IY", str(iso[0]))\

    return dt.strftime(format)
#@-node:strftime
#@+node:union
def union(*calendars):
    """
    returns a calendar that unifies all working times
    """
    #@    << check arguments >>
    #@+node:<< check arguments >>
    if len(calendars) == 1:
        calendars = calendars[0]
    #@nonl
    #@-node:<< check arguments >>
    #@nl
    #@    << intersect vacations >>
    #@+node:<< intersect vacations >>
    free_time = []
    for c in calendars:
        for start, end, is_free in c.time_spans:
            if is_free:
                free_time.append((start, False))
                free_time.append((end, True))

    count = len(calendars)
    open = 0
    time_spans = []
    free_time.sort()
    for date, is_end in free_time:
        if is_end:
            if open == count:
                time_spans.append((start, date, True))
            open -= 1
        else:
            open += 1
            start = date
    #@-node:<< intersect vacations >>
    #@nl
    #@    << unify extra worktime >>
    #@+node:<< unify extra worktime >>
    for c in calendars:
        for start, end, is_free in c.time_spans:
            if not is_free:
                time_spans = _add_to_time_spans(time_spans, start, end)
    #@nonl
    #@-node:<< unify extra worktime >>
    #@nl
    #@    << unify working times >>
    #@+node:<< unify working times >>
    working_times = {}
    for d in range(0, 7):
        times = []
        for c in calendars:
            for start, end in c.working_times.get(d, []):
                times.append((start, False))
                times.append((end, True))

        times.sort()
        open = 0
        ti = []
        start = None
        for time, is_end in times:
            if not is_end:
                if not start: start = time
                open += 1
            else:
                open -= 1
                if not open:
                    ti.append((start, time))
                    start = None

        if ti:
            working_times[d] = ti
    #@-node:<< unify working times >>
    #@nl
    #@    << create result calendar >>
    #@+node:<< create result calendar >>
    result = Calendar()
    result.working_times = working_times
    result.time_spans = time_spans
    result._recalc_working_time()
    result._build_mapping()
    #@nonl
    #@-node:<< create result calendar >>
    #@nl
    return result
#@nonl
#@-node:union
#@+node:class _CalendarItem
class _CalendarItem(int):
    #@	<< class _CalendarItem declarations >>
    #@+node:<< class _CalendarItem declarations >>
    __slots__ = ()
    calender = None


    #@-node:<< class _CalendarItem declarations >>
    #@nl
    #@	@+others
    #@+node:__new__
    def __new__(cls, val):
        try:
            return int.__new__(cls, val)
        except OverflowError:
            return int.__new__(cls, sys.maxint)
    #@-node:__new__
    #@+node:round
    def round(self, round_up=True):
        m_t_u = self.calendar.minimum_time_unit

        minutes = int(self)
        base = (minutes / m_t_u) * m_t_u
        minutes %= m_t_u

        round_up = round_up and minutes > 0 or minutes > m_t_u / 2
        if round_up: base += m_t_u
        return self.__class__(base)
    #@-node:round
    #@-others
#@-node:class _CalendarItem
#@+node:class _Minutes
class _Minutes(_CalendarItem):
    #@	<< class _Minutes declarations >>
    #@+node:<< class _Minutes declarations >>
    __slots__ = ()
    STR_FORMAT = "{%dd}{ %HH}{ %MM}"


    #@-node:<< class _Minutes declarations >>
    #@nl
    #@	@+others
    #@+node:__new__
    def __new__(cls, src=0, is_duration=False):
        """
        converts a timedelta in working minutes.
        """
        if isinstance(src, cls) or type(src) is int:
            return _CalendarItem.__new__(cls, src)

        cal = cls.calendar
        if not isinstance(src, datetime.timedelta):
            src = to_timedelta(src, cal, is_duration)

        d_w_h = is_duration and 24 or cal.working_hours_per_day
        src = src.days * d_w_h * 60 + src.seconds / 60
        return _CalendarItem.__new__(cls, src)
    #@-node:__new__
    #@+node:__cmp__
    def __cmp__(self, other):
        return cmp(int(self), int(self.__class__(other)))
    #@-node:__cmp__
    #@+node:__add__
    def __add__(self, other):
        try:
            return self.__class__(int(self) + int(self.__class__(other)))
        except:
            return NotImplemented
    #@-node:__add__
    #@+node:__sub__
    def __sub__(self, other):
        try:
            return self.__class__(int(self) - int(self.__class__(other)))
        except:
            return NotImplemented
    #@-node:__sub__
    #@+node:to_timedelta
    def to_timedelta(self, is_duration=False):
        d_w_h = is_duration and 24 or self.calendar.working_hours_per_day
        minutes = int(self)
        hours = minutes / 60
        minutes = minutes % 60
        days = hours / d_w_h
        hours = hours % d_w_h
        return datetime.timedelta(days, hours=hours, minutes=minutes)
    #@nonl
    #@-node:to_timedelta
    #@+node:strftime
    def strftime(self, format=None, is_duration=False):
        td = self.to_timedelta(is_duration)
        return timedelta_to_str(td, format or self.STR_FORMAT,
                                self.calendar, is_duration)
    #@nonl
    #@-node:strftime
    #@-others
#@-node:class _Minutes
#@+node:class _WorkingDateBase
class _WorkingDateBase(_CalendarItem):
    """
    A daytetime which has only valid values within the
    workingtimes of a specific calendar
    """
    #@	<< class _WorkingDateBase declarations >>
    #@+node:<< class _WorkingDateBase declarations >>
    timetuple = True
    STR_FORMAT = "%x %H:%M"
    _minutes = _Minutes
    __slots__ = ()


    #@-node:<< class _WorkingDateBase declarations >>
    #@nl
    #@	@+others
    #@+node:__new__
    def __new__(cls, src):
        #cls.__bases__[0] is the base of
        #the calendar specific StartDate and EndDate

        if isinstance(src, cls.__bases__[0]) or type(src) in (int, float):
            return _CalendarItem.__new__(cls, src)


        src = cls.calendar.from_datetime(to_datetime(src))
        return _CalendarItem.__new__(cls, src)
    #@-node:__new__
    #@+node:__repr__
    def __repr__(self):
        return self.strftime()
    #@-node:__repr__
    #@+node:to_datetime
    def to_datetime(self):
        return self.to_starttime()
    #@-node:to_datetime
    #@+node:to_starttime
    def to_starttime(self):
        return self.calendar.to_starttime(self)
    #@-node:to_starttime
    #@+node:to_endtime
    def to_endtime(self):
        return self.calendar.to_endtime(self)
    #@-node:to_endtime
    #@+node:__cmp__
    def __cmp__(self, other):
        return cmp(int(self), int(self.__class__(other)))
    #@-node:__cmp__
    #@+node:__add__
    def __add__(self, other):
        try:
            return self.__class__(int(self) + int(self._minutes(other)))
        except ValueError, e:
            raise e
        except:
            return NotImplemented
    #@-node:__add__
    #@+node:__sub__
    def __sub__(self, other):
        if isinstance(other, (datetime.timedelta, str, _Minutes)):
            try:
                other = self._minutes(other)
            except:
                pass

        if isinstance(other, self._minutes):
            return self.__class__(int(self) - int(other))

        try:
            return self._minutes(int(self) - int(self.__class__(other)))
        except:
            return NotImplemented
    #@-node:__sub__
    #@+node:strftime
    def strftime(self, format=None):
        return strftime(self.to_datetime(), format or self.STR_FORMAT)
    #@-node:strftime
    #@-others
#@-node:class _WorkingDateBase
#@+node:class Calendar
class Calendar(object):
    """
    A calendar to specify working times and vacations.
    The calendars epoch start at 1.1.1979
    """
    #@	<< declarations >>
    #@+node:<< declarations >>
    # january the first must be a monday
    EPOCH = datetime.datetime(1979, 1, 1)
    minimum_time_unit = DEFAULT_MINIMUM_TIME_UNIT
    working_days_per_week = DEFAULT_WORKING_DAYS_PER_WEEK
    working_days_per_month = DEFAULT_WORKING_DAYS_PER_MONTH
    working_days_per_year = DEFAULT_WORKING_DAYS_PER_YEAR
    working_hours_per_day = DEFAULT_WORKING_HOURS_PER_DAY
    now = EPOCH


    #@-node:<< declarations >>
    #@nl
    #@	@+others
    #@+node:__init__
    def __init__(self):

        self.time_spans = ()
        self._dt_num_can = ()
        self._num_dt_can = ()
        self.working_times = { }
        self._recalc_working_time()
        self._make_classes()
    #@-node:__init__
    #@+node:__or__
    def __or__(self, other):
        if isinstance(other, Calendar):
            return union(self, other)

        return NotImplemented
    #@nonl
    #@-node:__or__
    #@+node:clone
    def clone(self):
        result = Calendar()
        result.working_times = self.working_times.copy()
        result.time_spans = self.time_spans
        result._recalc_working_time()
        result._build_mapping()
        return result
    #@nonl
    #@-node:clone
    #@+node:set_working_days
    def set_working_days(self, day_range, trange, *further_tranges):
        """
        Sets the working days of an calendar
        day_range is a string of day abbreviations like 'mon, tue'
        trange and further_tranges is a time range string like
        '8:00-10:00'
        """
        time_ranges = [ trange ] + list(further_tranges)
        time_ranges = filter(bool, map(to_time_range, time_ranges))
        days = _to_days(day_range)

        for k in days.keys():
            self.working_times[k] = time_ranges

        self._recalc_working_time()
        self._build_mapping()
    #@-node:set_working_days
    #@+node:set_vacation
    def set_vacation(self, value):
        """
        Sets vacation time.
        value is either a datetime literal or
        a sequence of items that can be
        a datetime literals and or pair of datetime literals
        """
        self.time_spans = _add_to_time_spans(self.time_spans, value, True)
        self._build_mapping()
    #@-node:set_vacation
    #@+node:set_extra_work
    def set_extra_work(self, value):
        """
        Sets extra working time
        value is either a datetime literal or
        a sequence of items that can be
        a datetime literals and or pair of datetime literals
        """
        self.time_spans = _add_to_time_spans(self.time_spans, value, False)
        self._build_mapping()
    #@-node:set_extra_work
    #@+node:from_datetime
    def from_datetime(self, value):
        assert(isinstance(value, datetime.datetime))
        delta = value - self.EPOCH
        days = delta.days
        minutes = delta.seconds / 60

#        calculate the weektime
        weeks = days / 7
        wtime = self.week_time * weeks

#        calculate the daytime
        days %= 7
        dtime = sum(self.day_times[:days])

#        calculate the minute time
        slots = self.working_times.get(days, DEFAULT_WORKING_DAYS[days])
        mtime = 0
        for start, end in slots:
            if minutes > end:
                mtime += end - start
            else:
                if minutes > start:
                    mtime += minutes - start
                break

        result = wtime + dtime + mtime

#        map exceptional timespans
        dt_num_can = self._dt_num_can
        pos = bisect.bisect(dt_num_can, (value,)) - 1
        if pos >= 0:
            start, end, nstart, nend, cend = dt_num_can[pos]
            if value < end:
                if nstart < nend:
                    delta = value - start
                    delta = delta.days * 24 * 60 + delta.seconds / 60
                    result = nstart + delta
                else:
                    result = nstart
            else:
                result += (nend - cend) # == (result - cend) + nend

        return result
    #@-node:from_datetime
    #@+node:split_time
    def split_time(self, value):
        #map exceptional timespans
        num_dt_can = self._num_dt_can
        pos = bisect.bisect(num_dt_can, (value, sys.maxint)) - 1
        if pos >= 0:
            nstart, nend, start, end, cend = num_dt_can[pos]
            if value < nend:
                value = start + datetime.timedelta(minutes=value - nstart)
                delta = value - self.EPOCH
                return delta.days / 7, delta.days % 7, delta.seconds / 60, -1
            else:
                value += (cend - nend) # (value - nend + cend)
                #calculate the weeks since the epoch

        weeks = value / self.week_time
        value %= self.week_time

        #calculate the remaining days
        days = 0
        for day_time in self.day_times:
            if value < day_time: break
            value -= day_time
            days += 1

        #calculate the remaining minutes
        minutes = 0
        slots = self.working_times.get(days, DEFAULT_WORKING_DAYS[days])
        index = 0
        for start, end in slots:
            delta = end - start
            if delta > value:
                minutes = start + value
                break
            else:
                value -= delta

            index += 1

        return weeks, days, minutes, index
    #@-node:split_time
    #@+node:to_starttime
    def to_starttime(self, value):
        weeks, days, minutes, index = self.split_time(value)
        return self.EPOCH + datetime.timedelta(weeks=weeks,
                                               days=days,
                                               minutes=minutes)
    #@-node:to_starttime
    #@+node:to_endtime
    def to_endtime(self, value):
        return self.to_starttime(value - 1) + datetime.timedelta(minutes=1)
    #@-node:to_endtime
    #@+node:get_working_times
    def get_working_times(self, day):
        return self.working_times.get(day, DEFAULT_WORKING_DAYS[day])
    #@-node:get_working_times
    #@+node:_build_mapping
    def _build_mapping(self):
        self._dt_num_can = self._num_dt_can = ()
        dt_num_can = []
        num_dt_can = []

        delta = self.Minutes()
        for start, end, is_free in self.time_spans:
            cstart = self.StartDate(start)
            cend = self.EndDate(end)
            nstart = cstart + delta

            if not is_free:
                d = end - start
                d = d.days * 24 * 60 + d.seconds / 60
                nend = nstart + d
            else:
                nend = nstart

            delta += (nend - nstart) - (cend - cstart)
            dt_num_can.append((start, end, nstart, nend, cend))
            num_dt_can.append((nstart, nend, start, end, cend))

        self._dt_num_can = tuple(dt_num_can)
        self._num_dt_can = tuple(num_dt_can)

    #@-node:_build_mapping
    #@+node:_recalc_working_time
    def _recalc_working_time(self):
        def slot_sum_time(day):
            slots = self.working_times.get(day, DEFAULT_WORKING_DAYS[day])
            return sum(map(lambda slot: slot[1] - slot[0], slots))

        self.day_times = map(slot_sum_time, range(0, 7))
        self.week_time = sum(self.day_times)

    #@-node:_recalc_working_time
    #@+node:_make_classes
    def _make_classes(self):
        #ensure that the clases are instance specific
        class minutes(_Minutes):
            calendar = self
            __slots__ = ()

        class db(_WorkingDateBase):
            calendar = self
            _minutes = minutes
            __slots__ = ()

        class wdt(db): __slots__ = ()
        class edt(db):
            __slots__ = ()

            def to_datetime(self):
                return self.to_endtime()

        self.Minutes, self.StartDate, self.EndDate = minutes, wdt, edt

        self.WorkingDate = self.StartDate

    #@-node:_make_classes
    #@-others


_default_calendar = Calendar()

WorkingDate = _default_calendar.WorkingDate
StartDate = _default_calendar.StartDate
EndDate = _default_calendar.EndDate
Minutes = _default_calendar.Minutes
#@-node:class Calendar
#@-others

if __name__ == '__main__':
    cal = Calendar()

    start = EndDate("10.1.2005")

    delay = Minutes("4H")

    start2 = cal.StartDate(start)

    start3 = cal.StartDate("10.1.2005")
#@-node:@file pcalendar.py
#@-leo

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
