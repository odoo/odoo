"""
win32timezone:
    Module for handling datetime.tzinfo time zones using the windows
registry for time zone information.  The time zone names are dependent
on the registry entries defined by the operating system.

    This module may be tested using the doctest module.

    Written by Jason R. Coombs (jaraco@jaraco.com).
    Copyright © 2003-2012.
    All Rights Reserved.

    This module is licensed for use in Mark Hammond's pywin32
library under the same terms as the pywin32 library.

    To use this time zone module with the datetime module, simply pass
the TimeZoneInfo object to the datetime constructor.  For example,

>>> import win32timezone, datetime
>>> assert 'Mountain Standard Time' in win32timezone.TimeZoneInfo.get_sorted_time_zone_names()
>>> MST = win32timezone.TimeZoneInfo('Mountain Standard Time')
>>> now = datetime.datetime.now(MST)

    The now object is now a time-zone aware object, and daylight savings-
aware methods may be called on it.

>>> now.utcoffset() in (datetime.timedelta(-1, 61200), datetime.timedelta(-1, 64800))
True

(note that the result of utcoffset call will be different based on when now was
generated, unless standard time is always used)

>>> now = datetime.datetime.now(win32timezone.TimeZoneInfo('Mountain Standard Time', True))
>>> now.utcoffset()
datetime.timedelta(days=-1, seconds=61200)

>>> aug2 = datetime.datetime(2003, 8, 2, tzinfo = MST)
>>> tuple(aug2.utctimetuple())
(2003, 8, 2, 6, 0, 0, 5, 214, 0)
>>> nov2 = datetime.datetime(2003, 11, 25, tzinfo = MST)
>>> tuple(nov2.utctimetuple())
(2003, 11, 25, 7, 0, 0, 1, 329, 0)

To convert from one timezone to another, just use the astimezone method.

>>> aug2.isoformat()
'2003-08-02T00:00:00-06:00'
>>> aug2est = aug2.astimezone(win32timezone.TimeZoneInfo('Eastern Standard Time'))
>>> aug2est.isoformat()
'2003-08-02T02:00:00-04:00'

calling the displayName member will return the display name as set in the
registry.

>>> est = win32timezone.TimeZoneInfo('Eastern Standard Time')
>>> str(est.displayName)
'(UTC-05:00) Eastern Time (US & Canada)'

>>> gmt = win32timezone.TimeZoneInfo('GMT Standard Time', True)
>>> str(gmt.displayName)
'(UTC+00:00) Dublin, Edinburgh, Lisbon, London'

To get the complete list of available time zone keys,
>>> zones = win32timezone.TimeZoneInfo.get_all_time_zones()

If you want to get them in an order that's sorted longitudinally
>>> zones = win32timezone.TimeZoneInfo.get_sorted_time_zones()

TimeZoneInfo now supports being pickled and comparison
>>> import pickle
>>> tz = win32timezone.TimeZoneInfo('China Standard Time')
>>> tz == pickle.loads(pickle.dumps(tz))
True

It's possible to construct a TimeZoneInfo from a TimeZoneDescription
including the currently-defined zone.
>>> code, info = win32timezone.TimeZoneDefinition.current()
>>> tz = win32timezone.TimeZoneInfo(info, not code)
>>> tz == pickle.loads(pickle.dumps(tz))
True

Although it's easier to use TimeZoneInfo.local() to get the local info
>>> tz == TimeZoneInfo.local()
True

>>> aest = win32timezone.TimeZoneInfo('AUS Eastern Standard Time')
>>> est = win32timezone.TimeZoneInfo('E. Australia Standard Time')
>>> dt = datetime.datetime(2006, 11, 11, 1, 0, 0, tzinfo = aest)
>>> estdt = dt.astimezone(est)
>>> estdt.strftime('%Y-%m-%d %H:%M:%S')
'2006-11-11 00:00:00'

>>> dt = datetime.datetime(2007, 1, 12, 1, 0, 0, tzinfo = aest)
>>> estdt = dt.astimezone(est)
>>> estdt.strftime('%Y-%m-%d %H:%M:%S')
'2007-01-12 00:00:00'

>>> dt = datetime.datetime(2007, 6, 13, 1, 0, 0, tzinfo = aest)
>>> estdt = dt.astimezone(est)
>>> estdt.strftime('%Y-%m-%d %H:%M:%S')
'2007-06-13 01:00:00'

Microsoft now has a patch for handling time zones in 2007 (see
https://learn.microsoft.com/en-us/troubleshoot/windows-client/system-management-components/daylight-saving-time-help-support)

As a result, patched systems will give an incorrect result for
dates prior to the designated year except for Vista and its
successors, which have dynamic time zone support.
>>> nov2_pre_change = datetime.datetime(2003, 11, 2, tzinfo = MST)
>>> old_response = (2003, 11, 2, 7, 0, 0, 6, 306, 0)
>>> incorrect_patch_response = (2003, 11, 2, 6, 0, 0, 6, 306, 0)
>>> pre_response = nov2_pre_change.utctimetuple()
>>> pre_response in (old_response, incorrect_patch_response)
True

Furthermore, unpatched systems pre-Vista will give an incorrect
result for dates after 2007.
>>> nov2_post_change = datetime.datetime(2007, 11, 2, tzinfo = MST)
>>> incorrect_unpatched_response = (2007, 11, 2, 7, 0, 0, 4, 306, 0)
>>> new_response = (2007, 11, 2, 6, 0, 0, 4, 306, 0)
>>> post_response = nov2_post_change.utctimetuple()
>>> post_response in (new_response, incorrect_unpatched_response)
True


There is a function you can call to get some capabilities of the time
zone data.
>>> caps = GetTZCapabilities()
>>> isinstance(caps, dict)
True
>>> 'MissingTZPatch' in caps
True
>>> 'DynamicTZSupport' in caps
True

>>> both_dates_correct = (pre_response == old_response and post_response == new_response)
>>> old_dates_wrong = (pre_response == incorrect_patch_response)
>>> new_dates_wrong = (post_response == incorrect_unpatched_response)

>>> caps['DynamicTZSupport'] == both_dates_correct
True

>>> (not caps['DynamicTZSupport'] and caps['MissingTZPatch']) == new_dates_wrong
True

>>> (not caps['DynamicTZSupport'] and not caps['MissingTZPatch']) == old_dates_wrong
True

This test helps ensure language support for unicode characters
>>> x = TIME_ZONE_INFORMATION(0, 'français')


Test conversion from one time zone to another at a DST boundary
===============================================================

>>> tz_hi = TimeZoneInfo('Hawaiian Standard Time')
>>> tz_pac = TimeZoneInfo('Pacific Standard Time')
>>> time_before = datetime.datetime(2011, 11, 5, 15, 59, 59, tzinfo=tz_hi)
>>> tz_hi.utcoffset(time_before)
datetime.timedelta(days=-1, seconds=50400)
>>> tz_hi.dst(time_before)
datetime.timedelta(0)

Hawaii doesn't need dynamic TZ info
>>> getattr(tz_hi, 'dynamicInfo', None)

Here's a time that gave some trouble as reported in #3523104
because one minute later, the equivalent UTC time changes from DST
in the U.S.
>>> dt_hi = datetime.datetime(2011, 11, 5, 15, 59, 59, 0, tzinfo=tz_hi)
>>> dt_hi.timetuple()
time.struct_time(tm_year=2011, tm_mon=11, tm_mday=5, tm_hour=15, tm_min=59, tm_sec=59, tm_wday=5, tm_yday=309, tm_isdst=0)
>>> dt_hi.utctimetuple()
time.struct_time(tm_year=2011, tm_mon=11, tm_mday=6, tm_hour=1, tm_min=59, tm_sec=59, tm_wday=6, tm_yday=310, tm_isdst=0)

Convert the time to pacific time.
>>> dt_pac = dt_hi.astimezone(tz_pac)
>>> dt_pac.timetuple()
time.struct_time(tm_year=2011, tm_mon=11, tm_mday=5, tm_hour=18, tm_min=59, tm_sec=59, tm_wday=5, tm_yday=309, tm_isdst=1)

Notice that the UTC time is almost 2am.
>>> dt_pac.utctimetuple()
time.struct_time(tm_year=2011, tm_mon=11, tm_mday=6, tm_hour=1, tm_min=59, tm_sec=59, tm_wday=6, tm_yday=310, tm_isdst=0)

Now do the same tests one minute later in Hawaii.
>>> time_after = datetime.datetime(2011, 11, 5, 16, 0, 0, 0, tzinfo=tz_hi)
>>> tz_hi.utcoffset(time_after)
datetime.timedelta(days=-1, seconds=50400)
>>> tz_hi.dst(time_before)
datetime.timedelta(0)

>>> dt_hi = datetime.datetime(2011, 11, 5, 16, 0, 0, 0, tzinfo=tz_hi)
>>> print(dt_hi.timetuple())
time.struct_time(tm_year=2011, tm_mon=11, tm_mday=5, tm_hour=16, tm_min=0, tm_sec=0, tm_wday=5, tm_yday=309, tm_isdst=0)
>>> print(dt_hi.utctimetuple())
time.struct_time(tm_year=2011, tm_mon=11, tm_mday=6, tm_hour=2, tm_min=0, tm_sec=0, tm_wday=6, tm_yday=310, tm_isdst=0)

According to the docs, this is what astimezone does.
>>> utc = (dt_hi - dt_hi.utcoffset()).replace(tzinfo=tz_pac)
>>> utc
datetime.datetime(2011, 11, 6, 2, 0, tzinfo=TimeZoneInfo('Pacific Standard Time'))
>>> tz_pac.fromutc(utc) == dt_hi.astimezone(tz_pac)
True
>>> tz_pac.fromutc(utc)
datetime.datetime(2011, 11, 5, 19, 0, tzinfo=TimeZoneInfo('Pacific Standard Time'))

Make sure the converted time is correct.
>>> dt_pac = dt_hi.astimezone(tz_pac)
>>> dt_pac.timetuple()
time.struct_time(tm_year=2011, tm_mon=11, tm_mday=5, tm_hour=19, tm_min=0, tm_sec=0, tm_wday=5, tm_yday=309, tm_isdst=1)
>>> dt_pac.utctimetuple()
time.struct_time(tm_year=2011, tm_mon=11, tm_mday=6, tm_hour=2, tm_min=0, tm_sec=0, tm_wday=6, tm_yday=310, tm_isdst=0)

Check some internal methods
>>> tz_pac._getStandardBias(datetime.datetime(2011, 1, 1))
datetime.timedelta(seconds=28800)
>>> tz_pac._getDaylightBias(datetime.datetime(2011, 1, 1))
datetime.timedelta(seconds=25200)

Test the offsets
>>> offset = tz_pac.utcoffset(datetime.datetime(2011, 11, 6, 2, 0))
>>> offset == datetime.timedelta(hours=-8)
True
>>> dst_offset = tz_pac.dst(datetime.datetime(2011, 11, 6, 2, 0) + offset)
>>> dst_offset == datetime.timedelta(hours=1)
True
>>> (offset + dst_offset) == datetime.timedelta(hours=-7)
True


Test offsets that occur right at the DST changeover
>>> datetime.datetime.utcfromtimestamp(1320570000).replace(
...     tzinfo=TimeZoneInfo.utc()).astimezone(tz_pac)
datetime.datetime(2011, 11, 6, 1, 0, tzinfo=TimeZoneInfo('Pacific Standard Time'))

"""

from __future__ import annotations

import datetime
import functools
import logging
import operator
import re
import struct
import winreg
from itertools import count
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    ClassVar,
    Dict,
    Generator,
    Iterable,
    Mapping,
    TypeVar,
    overload,
)

import win32api

if TYPE_CHECKING:
    from _operator import _SupportsComparison

    from _typeshed import SupportsKeysAndGetItem
    from typing_extensions import Self

__author__ = "Jason R. Coombs <jaraco@jaraco.com>"

_RangeMapKT = TypeVar("_RangeMapKT", bound="_SupportsComparison")

_T = TypeVar("_T")
_VT = TypeVar("_VT")

log = logging.getLogger(__file__)


# A couple of objects for working with objects as if they were native C-type
# structures.
class _SimpleStruct:
    _fields_: ClassVar[list[tuple[str, type]]] = []  # must be overridden by subclasses

    def __init__(self, *args, **kw) -> None:
        for i, (name, typ) in enumerate(self._fields_):
            def_arg = None
            if i < len(args):
                def_arg = args[i]
            if name in kw:
                def_arg = kw[name]
            if def_arg is not None:
                if not isinstance(def_arg, tuple):
                    def_arg = (def_arg,)
            else:
                def_arg = ()
            if len(def_arg) == 1 and isinstance(def_arg[0], typ):
                # already an object of this type.
                # XXX - should copy.copy???
                def_val = def_arg[0]
            else:
                def_val = typ(*def_arg)
            setattr(self, name, def_val)

    def field_names(self) -> list[str]:
        return [f[0] for f in self._fields_]

    def __eq__(self, other) -> bool:
        if not hasattr(other, "_fields_"):
            return False
        if self._fields_ != other._fields_:
            return False
        for name, _ in self._fields_:
            if getattr(self, name) != getattr(other, name):
                return False
        return True

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)


class SYSTEMTIME(_SimpleStruct):
    _fields_ = [
        ("year", int),
        ("month", int),
        ("day_of_week", int),
        ("day", int),
        ("hour", int),
        ("minute", int),
        ("second", int),
        ("millisecond", int),
    ]


class TIME_ZONE_INFORMATION(_SimpleStruct):
    _fields_ = [
        ("bias", int),
        ("standard_name", str),
        ("standard_start", SYSTEMTIME),
        ("standard_bias", int),
        ("daylight_name", str),
        ("daylight_start", SYSTEMTIME),
        ("daylight_bias", int),
    ]


class DYNAMIC_TIME_ZONE_INFORMATION(TIME_ZONE_INFORMATION):
    _fields_ = TIME_ZONE_INFORMATION._fields_ + [
        ("key_name", str),
        ("dynamic_daylight_time_disabled", bool),
    ]


class TimeZoneDefinition(DYNAMIC_TIME_ZONE_INFORMATION):
    """
    A time zone definition class based on the win32
    DYNAMIC_TIME_ZONE_INFORMATION structure.

    Describes a bias against UTC (bias), and two dates at which a separate
    additional bias applies (standard_bias and daylight_bias).
    """

    def __init__(self, *args, **kwargs) -> None:
        """
        >>> test_args = [1] * 44

        Try to construct a TimeZoneDefinition from:

        a) [DYNAMIC_]TIME_ZONE_INFORMATION args
        >>> TimeZoneDefinition(*test_args).bias
        datetime.timedelta(seconds=60)

        b) another TimeZoneDefinition or [DYNAMIC_]TIME_ZONE_INFORMATION
        >>> TimeZoneDefinition(TimeZoneDefinition(*test_args)).bias
        datetime.timedelta(seconds=60)
        >>> TimeZoneDefinition(DYNAMIC_TIME_ZONE_INFORMATION(*test_args)).bias
        datetime.timedelta(seconds=60)
        >>> TimeZoneDefinition(TIME_ZONE_INFORMATION(*test_args)).bias
        datetime.timedelta(seconds=60)

        c) a byte structure (using _from_bytes)
        >>> TimeZoneDefinition(bytes(test_args)).bias
        datetime.timedelta(days=11696, seconds=46140)
        """
        try:
            super().__init__(*args, **kwargs)
            return
        except (TypeError, ValueError):
            pass

        try:
            self.__init_from_other(*args, **kwargs)
            return
        except TypeError:
            pass

        try:
            self.__init_from_bytes(*args, **kwargs)
            return
        except TypeError:
            pass

        raise TypeError(f"Invalid arguments for {self.__class__}")

    def __init_from_bytes(
        self,
        bytes,
        standard_name="",
        daylight_name="",
        key_name="",
        daylight_disabled=False,
    ):
        format = "3l8h8h"
        components = struct.unpack(format, bytes)
        bias, standard_bias, daylight_bias = components[:3]
        standard_start = SYSTEMTIME(*components[3:11])
        daylight_start = SYSTEMTIME(*components[11:19])
        super().__init__(
            bias,
            standard_name,
            standard_start,
            standard_bias,
            daylight_name,
            daylight_start,
            daylight_bias,
            key_name,
            daylight_disabled,
        )

    def __init_from_other(self, other: TIME_ZONE_INFORMATION) -> None:
        if not isinstance(other, TIME_ZONE_INFORMATION):
            raise TypeError("Not a TIME_ZONE_INFORMATION")
        for name in other.field_names():
            # explicitly get the value from the underlying structure
            value = super(TIME_ZONE_INFORMATION, other).__getattribute__(name)
            setattr(self, name, value)
        # consider instead of the loop above just copying the memory directly
        # size = max(ctypes.sizeof(DYNAMIC_TIME_ZONE_INFO), ctypes.sizeof(other))
        # ctypes.memmove(ctypes.addressof(self), other, size)

    if TYPE_CHECKING:
        # TIME_ZONE_INFORMATION fields as obtained by __getattribute__
        bias: datetime.timedelta
        standard_name: str
        standard_start: SYSTEMTIME
        standard_bias: datetime.timedelta
        daylight_name: str
        daylight_start: SYSTEMTIME
        daylight_bias: datetime.timedelta

    def __getattribute__(self, attr: str) -> Any:
        value = super().__getattribute__(attr)
        if "bias" in attr:
            value = datetime.timedelta(minutes=value)
        return value

    @classmethod
    def current(cls):
        "Windows Platform SDK GetTimeZoneInformation"
        code, tzi = win32api.GetTimeZoneInformation(True)
        return code, cls(*tzi)

    def set(self) -> None:
        tzi = tuple(getattr(self, n) for n, t in self._fields_)
        win32api.SetTimeZoneInformation(tzi)

    def copy(self) -> Self:
        # XXX - this is no longer a copy!
        return self.__class__(self)

    def locate_daylight_start(self, year) -> datetime.datetime:
        return self._locate_day(year, self.daylight_start)

    def locate_standard_start(self, year) -> datetime.datetime:
        return self._locate_day(year, self.standard_start)

    @staticmethod
    def _locate_day(year, cutoff) -> datetime.datetime:
        """
        Takes a SYSTEMTIME object, such as retrieved from a TIME_ZONE_INFORMATION
        structure or call to GetTimeZoneInformation and interprets it based on the given
        year to identify the actual day.

        This method is necessary because the SYSTEMTIME structure refers to a day by its
        day of the week and week of the month (e.g. 4th saturday in March).

        >>> SATURDAY = 6
        >>> MARCH = 3
        >>> st = SYSTEMTIME(2000, MARCH, SATURDAY, 4, 0, 0, 0, 0)

        # according to my calendar, the 4th Saturday in March in 2009 was the 28th
        >>> expected_date = datetime.datetime(2009, 3, 28)
        >>> TimeZoneDefinition._locate_day(2009, st) == expected_date
        True
        """
        # MS stores Sunday as 0, Python datetime stores Monday as zero
        target_weekday = (cutoff.day_of_week + 6) % 7
        # For SYSTEMTIMEs relating to time zone information, cutoff.day
        #  is the week of the month
        week_of_month = cutoff.day
        # so the following is the first day of that week
        day = (week_of_month - 1) * 7 + 1
        result = datetime.datetime(
            year,
            cutoff.month,
            day,
            cutoff.hour,
            cutoff.minute,
            cutoff.second,
            cutoff.millisecond,
        )
        # now the result is the correct week, but not necessarily the correct day of the week
        days_to_go = (target_weekday - result.weekday()) % 7
        result += datetime.timedelta(days_to_go)
        # if we selected a day in the month following the target month,
        #  move back a week or two.
        # This is necessary because Microsoft defines the fifth week in a month
        #  to be the last week in a month and adding the time delta might have
        #  pushed the result into the next month.
        while result.month == cutoff.month + 1:
            result -= datetime.timedelta(weeks=1)
        return result


class TimeZoneInfo(datetime.tzinfo):
    """
    Main class for handling Windows time zones.
    Usage:
        TimeZoneInfo(<Time Zone Standard Name>, [<Fix Standard Time>])

    If <Fix Standard Time> evaluates to True, daylight savings time is
    calculated in the same way as standard time.

    >>> tzi = TimeZoneInfo('Pacific Standard Time')
    >>> march31 = datetime.datetime(2000,3,31)

    We know that time zone definitions haven't changed from 2007
    to 2012, so regardless of whether dynamic info is available,
    there should be consistent results for these years.
    >>> subsequent_years = [march31.replace(year=year)
    ...     for year in range(2007, 2013)]
    >>> offsets = set(tzi.utcoffset(year) for year in subsequent_years)
    >>> len(offsets)
    1

    Cannot create a `TimeZoneInfo` with an invalid name.
    >>> TimeZoneInfo('Does not exist')
    Traceback (most recent call last):
    ...
    ValueError: Timezone Name 'Does not exist' not found
    >>> TimeZoneInfo(None)
    Traceback (most recent call last):
    ...
    ValueError: subkey name cannot be empty
    >>> TimeZoneInfo("")
    Traceback (most recent call last):
    ...
    ValueError: subkey name cannot be empty
    """

    # this key works for WinNT+, but not for the Win95 line.
    tzRegKey = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Time Zones"

    def __init__(
        self,
        param: str | TimeZoneDefinition,
        fix_standard_time: bool = False,
    ) -> None:
        if isinstance(param, TimeZoneDefinition):
            self._LoadFromTZI(param)
        else:
            self.timeZoneName = param
            self._LoadInfoFromKey()
        self.fixedStandardTime = fix_standard_time

    # For tzinfo pickle support
    def __getinitargs__(self) -> tuple[TimeZoneDefinition, bool]:
        return (self.staticInfo, self.fixedStandardTime)

    def _FindTimeZoneKey(self) -> _RegKeyDict:
        """Find the registry key for the time zone name (self.timeZoneName)."""
        # for multi-language compatability, match the time zone name in the
        # "Std" key of the time zone key.
        zoneNames = dict(self._get_indexed_time_zone_keys("Std"))
        # Also match the time zone key name itself, to be compatible with
        # English-based hard-coded time zones.
        timeZoneName = zoneNames.get(self.timeZoneName, self.timeZoneName)
        key = _RegKeyDict.open(winreg.HKEY_LOCAL_MACHINE, self.tzRegKey)
        try:
            result = key.subkey(timeZoneName)
        except FileNotFoundError:
            # Don't catch ValueError, keep the original error message
            raise ValueError(f"Timezone Name {timeZoneName!r} not found")
        return result

    def _LoadInfoFromKey(self) -> None:
        """Loads the information from an opened time zone registry key
        into relevant fields of this TZI object"""
        key = self._FindTimeZoneKey()
        self.displayName = key["Display"]
        self.standardName = key["Std"]
        self.daylightName = key["Dlt"]
        self.staticInfo = TimeZoneDefinition(key["TZI"])
        self._LoadDynamicInfoFromKey(key)

    def _LoadFromTZI(self, tzi: TimeZoneDefinition):
        self.timeZoneName = tzi.standard_name
        self.displayName = "Unknown"
        self.standardName = tzi.standard_name
        self.daylightName = tzi.daylight_name
        self.staticInfo = tzi

    def _LoadDynamicInfoFromKey(self, key) -> None:
        """
        >>> tzi = TimeZoneInfo('Central Standard Time')

        Here's how the RangeMap is supposed to work:
        >>> m = RangeMap(zip([2006,2007], 'BC'),
        ...     sort_params = {"reverse": True},
        ...     key_match_comparator=operator.ge)
        >>> m.get(2000, 'A')
        'A'
        >>> m[2006]
        'B'
        >>> m[2007]
        'C'
        >>> m[2008]
        'C'

        >>> m[RangeMap.last_item]
        'B'

        >>> m.get(2008, m[RangeMap.last_item])
        'C'


        Now test the dynamic info (but fallback to our simple RangeMap
        on systems that don't have dynamicInfo).

        >>> dinfo = getattr(tzi, 'dynamicInfo', m)
        >>> 2007 in dinfo
        True
        >>> 2008 in dinfo
        False
        >>> dinfo[2007] == dinfo[2008] == dinfo[2012]
        True
        """
        try:
            info = key.subkey("Dynamic DST")
        except FileNotFoundError:
            return
        del info["FirstEntry"]
        del info["LastEntry"]

        infos = [
            (int(year), TimeZoneDefinition(values)) for year, values in info.items()
        ]
        # create a range mapping that searches by descending year and matches
        # if the target year is greater or equal.
        self.dynamicInfo = RangeMap(
            infos,
            sort_params={"reverse": True},
            key_match_comparator=operator.ge,
        )

    def __repr__(self) -> str:
        result = f"{self.__class__.__name__}({self.timeZoneName!r}"
        if self.fixedStandardTime:
            result += ", True"
        result += ")"
        return result

    def __str__(self) -> str:
        return self.displayName

    @overload  # type: ignore[override] # Split definition into overrides
    def tzname(self, dt: datetime.datetime) -> str: ...
    @overload
    def tzname(self, dt: None) -> None: ...
    def tzname(self, dt: datetime.datetime | None) -> str | None:
        """
        >>> MST = TimeZoneInfo('Mountain Standard Time')
        >>> MST.tzname(datetime.datetime(2003, 8, 2))
        'Mountain Daylight Time'
        >>> MST.tzname(datetime.datetime(2003, 11, 25))
        'Mountain Standard Time'
        >>> MST.tzname(None)

        """
        # https://docs.python.org/3/library/datetime.html#datetime.tzinfo.tzname
        # > [...] returning `None` is appropriate if the class wishes to say
        # > that `time` objects don’t participate in the `tzinfo` protocols.
        if dt is None:
            return None

        dst = self.dst(dt)
        winInfo = self.getWinInfo(dt.year)
        if dst == -winInfo.daylight_bias:
            return self.daylightName
        elif dst == -winInfo.standard_bias:
            return self.standardName

        raise ValueError(
            "Unexpected daylight bias",
            dt,
            dst,
            winInfo.daylight_bias,
            winInfo.standard_bias,
        )

    def getWinInfo(self, targetYear: int) -> TimeZoneDefinition:
        """
        Return the most relevant "info" for this time zone
        in the target year.
        """
        if not getattr(self, "dynamicInfo", {}):
            return self.staticInfo
        # Find the greatest year entry in self.dynamicInfo which is for
        #  a year greater than or equal to our targetYear. If not found,
        #  default to the earliest year.
        return self.dynamicInfo.get(targetYear, self.dynamicInfo[RangeMap.last_item])

    def _getStandardBias(self, dt):
        winInfo = self.getWinInfo(dt.year)
        return winInfo.bias + winInfo.standard_bias

    def _getDaylightBias(self, dt):
        winInfo = self.getWinInfo(dt.year)
        return winInfo.bias + winInfo.daylight_bias

    @overload  # type: ignore[override] # False-positive, our overload covers all base types
    def utcoffset(self, dt: None) -> None: ...
    @overload
    def utcoffset(self, dt: datetime.datetime) -> datetime.timedelta: ...
    def utcoffset(self, dt: datetime.datetime | None) -> datetime.timedelta | None:
        "Calculates the utcoffset according to the datetime.tzinfo spec"
        if dt is None:
            return None
        winInfo = self.getWinInfo(dt.year)
        return -winInfo.bias + self.dst(dt)

    @overload  # type: ignore[override] # False-positive, our overload covers all base types
    def dst(self, dt: None) -> None: ...
    @overload
    def dst(self, dt: datetime.datetime) -> datetime.timedelta: ...
    def dst(self, dt: datetime.datetime | None) -> datetime.timedelta | None:
        """
        Calculate the daylight savings offset according to the
        datetime.tzinfo spec.
        """
        if dt is None:
            return None
        winInfo = self.getWinInfo(dt.year)
        if not self.fixedStandardTime and self._inDaylightSavings(dt):
            result = winInfo.daylight_bias
        else:
            result = winInfo.standard_bias
        return -result

    def _inDaylightSavings(self, dt):
        dt = dt.replace(tzinfo=None)
        winInfo = self.getWinInfo(dt.year)
        try:
            dstStart = self.GetDSTStartTime(dt.year)
            dstEnd = self.GetDSTEndTime(dt.year)

            # at the end of DST, when clocks are moved back, there's a period
            #  of daylight_bias where it's ambiguous whether we're in DST or
            #  not.
            dstEndAdj = dstEnd + winInfo.daylight_bias

            # the same thing could theoretically happen at the start of DST
            #  if there's a standard_bias (which I suspect is always 0).
            dstStartAdj = dstStart + winInfo.standard_bias

            if dstStart < dstEnd:
                in_dst = dstStartAdj <= dt < dstEndAdj
            else:
                # in the southern hemisphere, daylight savings time
                #  typically ends before it begins in a given year.
                in_dst = not (dstEndAdj < dt <= dstStartAdj)
        except ValueError:
            # there was an error parsing the time zone, which is normal when a
            #  start and end time are not specified.
            in_dst = False

        return in_dst

    def GetDSTStartTime(self, year: int) -> datetime.datetime:
        "Given a year, determines the time when daylight savings time starts"
        return self.getWinInfo(year).locate_daylight_start(year)

    def GetDSTEndTime(self, year: int) -> datetime.datetime:
        "Given a year, determines the time when daylight savings ends."
        return self.getWinInfo(year).locate_standard_start(year)

    def __eq__(self, other: object) -> bool:
        return self.__dict__ == other.__dict__

    def __ne__(self, other: object) -> bool:
        return self.__dict__ != other.__dict__

    @classmethod
    def local(cls) -> Self:
        """Returns the local time zone as defined by the operating system in the
        registry.
        >>> localTZ = TimeZoneInfo.local()
        >>> now_local = datetime.datetime.now(localTZ)
        >>> now_UTC = datetime.datetime.utcnow()  # deprecated
        >>> (now_UTC - now_local) < datetime.timedelta(seconds = 5)
        Traceback (most recent call last):
        ...
        TypeError: can't subtract offset-naive and offset-aware datetimes

        >>> now_UTC = now_UTC.replace(tzinfo = TimeZoneInfo('GMT Standard Time', True))

        Now one can compare the results of the two offset aware values
        >>> (now_UTC - now_local) < datetime.timedelta(seconds = 5)
        True

        Or use the newer `datetime.timezone.utc`
        >>> now_UTC = datetime.datetime.now(datetime.timezone.utc)
        >>> (now_UTC - now_local) < datetime.timedelta(seconds = 5)
        True
        """
        code, info = TimeZoneDefinition.current()
        # code is 0 if daylight savings is disabled or not defined
        #  code is 1 or 2 if daylight savings is enabled, 2 if currently active
        fix_standard_time = not code
        # note that although the given information is sufficient
        # to construct a WinTZI object, it's
        # not sufficient to represent the time zone in which
        # the current user is operating due
        # to dynamic time zones.
        return cls(info, fix_standard_time)

    _tzutc: ClassVar[Self | None] = None

    @classmethod
    def utc(cls) -> Self:
        """Returns a time-zone representing UTC.

        Same as TimeZoneInfo('GMT Standard Time', True) but caches the result
        for performance.

        >>> isinstance(TimeZoneInfo.utc(), TimeZoneInfo)
        True
        """
        if not cls._tzutc:
            cls._tzutc = cls("GMT Standard Time", True)
        return cls._tzutc

    # helper methods for accessing the timezone info from the registry
    @staticmethod
    def _get_time_zone_key(subkey=None):
        "Return the registry key that stores time zone details"
        key = _RegKeyDict.open(winreg.HKEY_LOCAL_MACHINE, TimeZoneInfo.tzRegKey)
        if subkey:
            key = key.subkey(subkey)
        return key

    @staticmethod
    def _get_time_zone_key_names():
        "Returns the names of the (registry keys of the) time zones"
        return TimeZoneInfo._get_time_zone_key().subkeys()

    @staticmethod
    def _get_indexed_time_zone_keys(index_key="Index"):
        """
        Get the names of the registry keys indexed by a value in that key,
        ignoring any keys for which that value is empty or missing.
        """
        key_names = list(TimeZoneInfo._get_time_zone_key_names())

        def get_index_value(key_name):
            key = TimeZoneInfo._get_time_zone_key(key_name)
            return key.get(index_key)

        values = map(get_index_value, key_names)

        return (
            (value, key_name) for value, key_name in zip(values, key_names) if value
        )

    @staticmethod
    def get_sorted_time_zone_names() -> list[str]:
        """
        Return a list of time zone names that can
        be used to initialize TimeZoneInfo instances.
        """
        tzs = TimeZoneInfo.get_sorted_time_zones()
        return [tz.standardName for tz in tzs]

    @staticmethod
    def get_all_time_zones() -> list[TimeZoneInfo]:
        return [TimeZoneInfo(n) for n in TimeZoneInfo._get_time_zone_key_names()]

    @staticmethod
    def get_sorted_time_zones(key=None) -> list[TimeZoneInfo]:
        """
        Return the time zones sorted by some key.
        key must be a function that takes a TimeZoneInfo object and returns
        a value suitable for sorting on.
        The key defaults to the bias (descending), as is done in Windows
        (see https://web.archive.org/web/20130723075340/http://blogs.msdn.com/b/michkap/archive/2006/12/22/1350684.aspx)
        """
        key = key or (lambda tzi: -tzi.staticInfo.bias)
        zones = TimeZoneInfo.get_all_time_zones()
        zones.sort(key=key)
        return zones


class _RegKeyDict(Dict[str, str]):
    def __init__(self, key: winreg._KeyType):
        dict.__init__(self)
        self.key = key
        self.__load_values()

    @classmethod
    def open(
        cls, key: winreg._KeyType, sub_key: str, reserved: int = 0, access: int = 131097
    ) -> _RegKeyDict:
        return _RegKeyDict(winreg.OpenKeyEx(key, sub_key, reserved, access))

    def subkey(self, name: str) -> _RegKeyDict:
        if not name:
            raise ValueError("subkey name cannot be empty")
        return _RegKeyDict(winreg.OpenKeyEx(self.key, name))

    def __load_values(self):
        pairs = [(n, v) for (n, v, t) in self._enumerate_reg_values(self.key)]
        self.update(pairs)

    def subkeys(self):
        return self._enumerate_reg_keys(self.key)

    @staticmethod
    def _enumerate_reg_values(key):
        return _RegKeyDict._enumerate_reg(key, winreg.EnumValue)

    @staticmethod
    def _enumerate_reg_keys(key):
        return _RegKeyDict._enumerate_reg(key, winreg.EnumKey)

    @staticmethod
    def _enumerate_reg(
        key: _T, func: Callable[[_T, int], _VT]
    ) -> Generator[_VT, None, None]:
        "Enumerates an open registry key as an iterable generator"
        try:
            for index in count():
                yield func(key, index)
        except OSError:
            pass


def utcnow() -> datetime.datetime:
    """
    Return the UTC time now with timezone awareness as enabled
    by this module
    >>> now = utcnow()

    >>> (now - datetime.datetime.now(datetime.timezone.utc)) < datetime.timedelta(seconds = 5)
    True
    >>> type(now.tzinfo) is TimeZoneInfo
    True
    """
    return datetime.datetime.now(TimeZoneInfo.utc())


def now() -> datetime.datetime:
    """
    Return the local time now with timezone awareness as enabled
    by this module
    >>> now_local = now()

    >>> (now_local - datetime.datetime.now(datetime.timezone.utc)) < datetime.timedelta(seconds = 5)
    True
    >>> type(now_local.tzinfo) is TimeZoneInfo
    True
    """
    return datetime.datetime.now(TimeZoneInfo.local())


def GetTZCapabilities() -> dict[str, bool]:
    """
    Run a few known tests to determine the capabilities of
    the time zone database on this machine.
    Note Dynamic Time Zone support is not available on any
    platform at this time; this
    is a limitation of this library, not the platform."""
    tzi = TimeZoneInfo("Mountain Standard Time")
    MissingTZPatch = datetime.datetime(2007, 11, 2, tzinfo=tzi).utctimetuple() != (
        2007,
        11,
        2,
        6,
        0,
        0,
        4,
        306,
        0,
    )
    DynamicTZSupport = not MissingTZPatch and datetime.datetime(
        2003, 11, 2, tzinfo=tzi
    ).utctimetuple() == (2003, 11, 2, 7, 0, 0, 6, 306, 0)
    del tzi
    return locals()


class DLLHandleCache:
    def __init__(self) -> None:
        self.__cache: dict[str, int] = {}

    def __getitem__(self, filename: str) -> int:
        key = filename.lower()
        return self.__cache.setdefault(key, win32api.LoadLibrary(key))


DLLCache = DLLHandleCache()


def resolveMUITimeZone(spec: str) -> str | None:
    """Resolve a multilingual user interface resource for the time zone name

    spec should be of the format @path,-stringID[;comment]
    see https://learn.microsoft.com/en-ca/windows/win32/api/timezoneapi/ns-timezoneapi-time_zone_information
    for details

    >>> import sys
    >>> result = resolveMUITimeZone('@tzres.dll,-110')
    >>> expectedResultType = [type(None),str][sys.getwindowsversion() >= (6,)]
    >>> type(result) is expectedResultType
    True
    """
    pattern = re.compile(r"@(?P<dllname>.*),-(?P<index>\d+)(?:;(?P<comment>.*))?")
    matcher = pattern.match(spec)
    assert matcher, "Could not parse MUI spec"

    groupdict = matcher.groupdict()
    try:
        handle = DLLCache[groupdict["dllname"]]
        result: str | None = win32api.LoadString(handle, int(groupdict["index"]))
    except win32api.error:
        result = None
    return result


# from jaraco.collections 5.1
class RangeMap(Dict[_RangeMapKT, _VT]):
    """
    A dictionary-like object that uses the keys as bounds for a range.
    Inclusion of the value for that range is determined by the
    key_match_comparator, which defaults to less-than-or-equal.
    A value is returned for a key if it is the first key that matches in
    the sorted list of keys.

    One may supply keyword parameters to be passed to the sort function used
    to sort keys (i.e. key, reverse) as sort_params.

    Create a map that maps 1-3 -> 'a', 4-6 -> 'b'

    >>> r = RangeMap({3: 'a', 6: 'b'})  # boy, that was easy
    >>> r[1], r[2], r[3], r[4], r[5], r[6]
    ('a', 'a', 'a', 'b', 'b', 'b')

    Even float values should work so long as the comparison operator
    supports it.

    >>> r[4.5]
    'b'

    Notice that the way rangemap is defined, it must be open-ended
    on one side.

    >>> r[0]
    'a'
    >>> r[-1]
    'a'

    One can close the open-end of the RangeMap by using undefined_value

    >>> r = RangeMap({0: RangeMap.undefined_value, 3: 'a', 6: 'b'})
    >>> r[0]
    Traceback (most recent call last):
    ...
    KeyError: 0

    One can get the first or last elements in the range by using RangeMap.Item

    >>> last_item = RangeMap.Item(-1)
    >>> r[last_item]
    'b'

    .last_item is a shortcut for Item(-1)

    >>> r[RangeMap.last_item]
    'b'

    Sometimes it's useful to find the bounds for a RangeMap

    >>> r.bounds()
    (0, 6)

    RangeMap supports .get(key, default)

    >>> r.get(0, 'not found')
    'not found'

    >>> r.get(7, 'not found')
    'not found'

    One often wishes to define the ranges by their left-most values,
    which requires use of sort params and a key_match_comparator.

    >>> r = RangeMap({1: 'a', 4: 'b'},
    ...     sort_params=dict(reverse=True),
    ...     key_match_comparator=operator.ge)
    >>> r[1], r[2], r[3], r[4], r[5], r[6]
    ('a', 'a', 'a', 'b', 'b', 'b')

    That wasn't nearly as easy as before, so an alternate constructor
    is provided:

    >>> r = RangeMap.left({1: 'a', 4: 'b', 7: RangeMap.undefined_value})
    >>> r[1], r[2], r[3], r[4], r[5], r[6]
    ('a', 'a', 'a', 'b', 'b', 'b')

    """

    def __init__(
        self,
        source: (
            SupportsKeysAndGetItem[_RangeMapKT, _VT] | Iterable[tuple[_RangeMapKT, _VT]]
        ),
        sort_params: Mapping[str, Any] = {},
        key_match_comparator: Callable[[_RangeMapKT, _RangeMapKT], bool] = operator.le,
    ) -> None:
        dict.__init__(self, source)
        self.sort_params = sort_params
        self.match = key_match_comparator

    @classmethod
    def left(
        cls,
        source: (
            SupportsKeysAndGetItem[_RangeMapKT, _VT] | Iterable[tuple[_RangeMapKT, _VT]]
        ),
    ) -> Self:
        return cls(
            source, sort_params={"reverse": True}, key_match_comparator=operator.ge
        )

    def __getitem__(self, item: _RangeMapKT) -> _VT:
        sorted_keys = sorted(self, **self.sort_params)
        if isinstance(item, RangeMap.Item):
            result = self.__getitem__(sorted_keys[item])
        else:
            key = self._find_first_match_(sorted_keys, item)
            result = dict.__getitem__(self, key)
            if result is RangeMap.undefined_value:
                raise KeyError(key)
        return result

    @overload  # type: ignore[override] # Signature simplified over dict and Mapping
    def get(self, key: _RangeMapKT, default: _T) -> _VT | _T: ...
    @overload
    def get(self, key: _RangeMapKT, default: None = None) -> _VT | None: ...
    def get(self, key: _RangeMapKT, default: _T | None = None) -> _VT | _T | None:
        """
        Return the value for key if key is in the dictionary, else default.
        If default is not given, it defaults to None, so that this method
        never raises a KeyError.
        """
        # Necessary to use our own __getitem__ and not dict's
        try:
            return self[key]
        except KeyError:
            return default

    def _find_first_match_(
        self, keys: Iterable[_RangeMapKT], item: _RangeMapKT
    ) -> _RangeMapKT:
        is_match = functools.partial(self.match, item)
        matches = filter(is_match, keys)
        try:
            return next(matches)
        except StopIteration:
            raise KeyError(item) from None

    def bounds(self) -> tuple[_RangeMapKT, _RangeMapKT]:
        sorted_keys = sorted(self, **self.sort_params)
        return (sorted_keys[RangeMap.first_item], sorted_keys[RangeMap.last_item])

    # some special values for the RangeMap
    undefined_value = type("RangeValueUndefined", (), {})()

    class Item(int):
        """RangeMap Item"""

    first_item = Item(0)
    last_item = Item(-1)
