# coding: utf-8

"""
Miscellaneous data helpers, including functions for converting integers to and
from bytes and UTC timezone. Exports the following items:

 - OrderedDict()
 - int_from_bytes()
 - int_to_bytes()
 - timezone.utc
 - utc_with_dst
 - create_timezone()
 - inet_ntop()
 - inet_pton()
 - uri_to_iri()
 - iri_to_uri()
"""

from __future__ import unicode_literals, division, absolute_import, print_function

import math
import sys
from datetime import datetime, date, timedelta, tzinfo

from ._errors import unwrap
from ._iri import iri_to_uri, uri_to_iri  # noqa
from ._ordereddict import OrderedDict  # noqa
from ._types import type_name

if sys.platform == 'win32':
    from ._inet import inet_ntop, inet_pton
else:
    from socket import inet_ntop, inet_pton  # noqa


# Python 2
if sys.version_info <= (3,):

    def int_to_bytes(value, signed=False, width=None):
        """
        Converts an integer to a byte string

        :param value:
            The integer to convert

        :param signed:
            If the byte string should be encoded using two's complement

        :param width:
            If None, the minimal possible size (but at least 1),
            otherwise an integer of the byte width for the return value

        :return:
            A byte string
        """

        if value == 0 and width == 0:
            return b''

        # Handle negatives in two's complement
        is_neg = False
        if signed and value < 0:
            is_neg = True
            bits = int(math.ceil(len('%x' % abs(value)) / 2.0) * 8)
            value = (value + (1 << bits)) % (1 << bits)

        hex_str = '%x' % value
        if len(hex_str) & 1:
            hex_str = '0' + hex_str

        output = hex_str.decode('hex')

        if signed and not is_neg and ord(output[0:1]) & 0x80:
            output = b'\x00' + output

        if width is not None:
            if len(output) > width:
                raise OverflowError('int too big to convert')
            if is_neg:
                pad_char = b'\xFF'
            else:
                pad_char = b'\x00'
            output = (pad_char * (width - len(output))) + output
        elif is_neg and ord(output[0:1]) & 0x80 == 0:
            output = b'\xFF' + output

        return output

    def int_from_bytes(value, signed=False):
        """
        Converts a byte string to an integer

        :param value:
            The byte string to convert

        :param signed:
            If the byte string should be interpreted using two's complement

        :return:
            An integer
        """

        if value == b'':
            return 0

        num = long(value.encode("hex"), 16)  # noqa

        if not signed:
            return num

        # Check for sign bit and handle two's complement
        if ord(value[0:1]) & 0x80:
            bit_len = len(value) * 8
            return num - (1 << bit_len)

        return num

    class timezone(tzinfo):  # noqa
        """
        Implements datetime.timezone for py2.
        Only full minute offsets are supported.
        DST is not supported.
        """

        def __init__(self, offset, name=None):
            """
            :param offset:
                A timedelta with this timezone's offset from UTC

            :param name:
                Name of the timezone; if None, generate one.
            """

            if not timedelta(hours=-24) < offset < timedelta(hours=24):
                raise ValueError('Offset must be in [-23:59, 23:59]')

            if offset.seconds % 60 or offset.microseconds:
                raise ValueError('Offset must be full minutes')

            self._offset = offset

            if name is not None:
                self._name = name
            elif not offset:
                self._name = 'UTC'
            else:
                self._name = 'UTC' + _format_offset(offset)

        def __eq__(self, other):
            """
            Compare two timezones

            :param other:
                The other timezone to compare to

            :return:
                A boolean
            """

            if type(other) != timezone:
                return False
            return self._offset == other._offset

        def __getinitargs__(self):
            """
            Called by tzinfo.__reduce__ to support pickle and copy.

            :return:
                offset and name, to be used for __init__
            """

            return self._offset, self._name

        def tzname(self, dt):
            """
            :param dt:
                A datetime object; ignored.

            :return:
                Name of this timezone
            """

            return self._name

        def utcoffset(self, dt):
            """
            :param dt:
                A datetime object; ignored.

            :return:
                A timedelta object with the offset from UTC
            """

            return self._offset

        def dst(self, dt):
            """
            :param dt:
                A datetime object; ignored.

            :return:
                Zero timedelta
            """

            return timedelta(0)

    timezone.utc = timezone(timedelta(0))

# Python 3
else:

    from datetime import timezone  # noqa

    def int_to_bytes(value, signed=False, width=None):
        """
        Converts an integer to a byte string

        :param value:
            The integer to convert

        :param signed:
            If the byte string should be encoded using two's complement

        :param width:
            If None, the minimal possible size (but at least 1),
            otherwise an integer of the byte width for the return value

        :return:
            A byte string
        """

        if width is None:
            if signed:
                if value < 0:
                    bits_required = abs(value + 1).bit_length()
                else:
                    bits_required = value.bit_length()
                if bits_required % 8 == 0:
                    bits_required += 1
            else:
                bits_required = value.bit_length()
            width = math.ceil(bits_required / 8) or 1
        return value.to_bytes(width, byteorder='big', signed=signed)

    def int_from_bytes(value, signed=False):
        """
        Converts a byte string to an integer

        :param value:
            The byte string to convert

        :param signed:
            If the byte string should be interpreted using two's complement

        :return:
            An integer
        """

        return int.from_bytes(value, 'big', signed=signed)


def _format_offset(off):
    """
    Format a timedelta into "[+-]HH:MM" format or "" for None
    """

    if off is None:
        return ''
    mins = off.days * 24 * 60 + off.seconds // 60
    sign = '-' if mins < 0 else '+'
    return sign + '%02d:%02d' % divmod(abs(mins), 60)


class _UtcWithDst(tzinfo):
    """
    Utc class where dst does not return None; required for astimezone
    """

    def tzname(self, dt):
        return 'UTC'

    def utcoffset(self, dt):
        return timedelta(0)

    def dst(self, dt):
        return timedelta(0)


utc_with_dst = _UtcWithDst()

_timezone_cache = {}


def create_timezone(offset):
    """
    Returns a new datetime.timezone object with the given offset.
    Uses cached objects if possible.

    :param offset:
        A datetime.timedelta object; It needs to be in full minutes and between -23:59 and +23:59.

    :return:
        A datetime.timezone object
    """

    try:
        tz = _timezone_cache[offset]
    except KeyError:
        tz = _timezone_cache[offset] = timezone(offset)
    return tz


class extended_date(object):
    """
    A datetime.datetime-like object that represents the year 0. This is just
    to handle 0000-01-01 found in some certificates. Python's datetime does
    not support year 0.

    The proleptic gregorian calendar repeats itself every 400 years. Therefore,
    the simplest way to format is to substitute year 2000.
    """

    def __init__(self, year, month, day):
        """
        :param year:
            The integer 0

        :param month:
            An integer from 1 to 12

        :param day:
            An integer from 1 to 31
        """

        if year != 0:
            raise ValueError('year must be 0')

        self._y2k = date(2000, month, day)

    @property
    def year(self):
        """
        :return:
            The integer 0
        """

        return 0

    @property
    def month(self):
        """
        :return:
            An integer from 1 to 12
        """

        return self._y2k.month

    @property
    def day(self):
        """
        :return:
            An integer from 1 to 31
        """

        return self._y2k.day

    def strftime(self, format):
        """
        Formats the date using strftime()

        :param format:
            A strftime() format string

        :return:
            A str, the formatted date as a unicode string
            in Python 3 and a byte string in Python 2
        """

        # Format the date twice, once with year 2000, once with year 4000.
        # The only differences in the result will be in the millennium. Find them and replace by zeros.
        y2k = self._y2k.strftime(format)
        y4k = self._y2k.replace(year=4000).strftime(format)
        return ''.join('0' if (c2, c4) == ('2', '4') else c2 for c2, c4 in zip(y2k, y4k))

    def isoformat(self):
        """
        Formats the date as %Y-%m-%d

        :return:
            The date formatted to %Y-%m-%d as a unicode string in Python 3
            and a byte string in Python 2
        """

        return self.strftime('0000-%m-%d')

    def replace(self, year=None, month=None, day=None):
        """
        Returns a new datetime.date or asn1crypto.util.extended_date
        object with the specified components replaced

        :return:
            A datetime.date or asn1crypto.util.extended_date object
        """

        if year is None:
            year = self.year
        if month is None:
            month = self.month
        if day is None:
            day = self.day

        if year > 0:
            cls = date
        else:
            cls = extended_date

        return cls(
            year,
            month,
            day
        )

    def __str__(self):
        """
        :return:
            A str representing this extended_date, e.g. "0000-01-01"
        """

        return self.strftime('%Y-%m-%d')

    def __eq__(self, other):
        """
        Compare two extended_date objects

        :param other:
            The other extended_date to compare to

        :return:
            A boolean
        """

        # datetime.date object wouldn't compare equal because it can't be year 0
        if not isinstance(other, self.__class__):
            return False
        return self.__cmp__(other) == 0

    def __ne__(self, other):
        """
        Compare two extended_date objects

        :param other:
            The other extended_date to compare to

        :return:
            A boolean
        """

        return not self.__eq__(other)

    def _comparison_error(self, other):
        raise TypeError(unwrap(
            '''
            An asn1crypto.util.extended_date object can only be compared to
            an asn1crypto.util.extended_date or datetime.date object, not %s
            ''',
            type_name(other)
        ))

    def __cmp__(self, other):
        """
        Compare two extended_date or datetime.date objects

        :param other:
            The other extended_date object to compare to

        :return:
            An integer smaller than, equal to, or larger than 0
        """

        # self is year 0, other is >= year 1
        if isinstance(other, date):
            return -1

        if not isinstance(other, self.__class__):
            self._comparison_error(other)

        if self._y2k < other._y2k:
            return -1
        if self._y2k > other._y2k:
            return 1
        return 0

    def __lt__(self, other):
        return self.__cmp__(other) < 0

    def __le__(self, other):
        return self.__cmp__(other) <= 0

    def __gt__(self, other):
        return self.__cmp__(other) > 0

    def __ge__(self, other):
        return self.__cmp__(other) >= 0


class extended_datetime(object):
    """
    A datetime.datetime-like object that represents the year 0. This is just
    to handle 0000-01-01 found in some certificates. Python's datetime does
    not support year 0.

    The proleptic gregorian calendar repeats itself every 400 years. Therefore,
    the simplest way to format is to substitute year 2000.
    """

    # There are 97 leap days during 400 years.
    DAYS_IN_400_YEARS = 400 * 365 + 97
    DAYS_IN_2000_YEARS = 5 * DAYS_IN_400_YEARS

    def __init__(self, year, *args, **kwargs):
        """
        :param year:
            The integer 0

        :param args:
            Other positional arguments; see datetime.datetime.

        :param kwargs:
            Other keyword arguments; see datetime.datetime.
        """

        if year != 0:
            raise ValueError('year must be 0')

        self._y2k = datetime(2000, *args, **kwargs)

    @property
    def year(self):
        """
        :return:
            The integer 0
        """

        return 0

    @property
    def month(self):
        """
        :return:
            An integer from 1 to 12
        """

        return self._y2k.month

    @property
    def day(self):
        """
        :return:
            An integer from 1 to 31
        """

        return self._y2k.day

    @property
    def hour(self):
        """
        :return:
            An integer from 1 to 24
        """

        return self._y2k.hour

    @property
    def minute(self):
        """
        :return:
            An integer from 1 to 60
        """

        return self._y2k.minute

    @property
    def second(self):
        """
        :return:
            An integer from 1 to 60
        """

        return self._y2k.second

    @property
    def microsecond(self):
        """
        :return:
            An integer from 0 to 999999
        """

        return self._y2k.microsecond

    @property
    def tzinfo(self):
        """
        :return:
            If object is timezone aware, a datetime.tzinfo object, else None.
        """

        return self._y2k.tzinfo

    def utcoffset(self):
        """
        :return:
            If object is timezone aware, a datetime.timedelta object, else None.
        """

        return self._y2k.utcoffset()

    def time(self):
        """
        :return:
            A datetime.time object
        """

        return self._y2k.time()

    def date(self):
        """
        :return:
            An asn1crypto.util.extended_date of the date
        """

        return extended_date(0, self.month, self.day)

    def strftime(self, format):
        """
        Performs strftime(), always returning a str

        :param format:
            A strftime() format string

        :return:
            A str of the formatted datetime
        """

        # Format the datetime twice, once with year 2000, once with year 4000.
        # The only differences in the result will be in the millennium. Find them and replace by zeros.
        y2k = self._y2k.strftime(format)
        y4k = self._y2k.replace(year=4000).strftime(format)
        return ''.join('0' if (c2, c4) == ('2', '4') else c2 for c2, c4 in zip(y2k, y4k))

    def isoformat(self, sep='T'):
        """
        Formats the date as "%Y-%m-%d %H:%M:%S" with the sep param between the
        date and time portions

        :param set:
            A single character of the separator to place between the date and
            time

        :return:
            The formatted datetime as a unicode string in Python 3 and a byte
            string in Python 2
        """

        s = '0000-%02d-%02d%c%02d:%02d:%02d' % (self.month, self.day, sep, self.hour, self.minute, self.second)
        if self.microsecond:
            s += '.%06d' % self.microsecond
        return s + _format_offset(self.utcoffset())

    def replace(self, year=None, *args, **kwargs):
        """
        Returns a new datetime.datetime or asn1crypto.util.extended_datetime
        object with the specified components replaced

        :param year:
            The new year to substitute. None to keep it.

        :param args:
            Other positional arguments; see datetime.datetime.replace.

        :param kwargs:
            Other keyword arguments; see datetime.datetime.replace.

        :return:
            A datetime.datetime or asn1crypto.util.extended_datetime object
        """

        if year:
            return self._y2k.replace(year, *args, **kwargs)

        return extended_datetime.from_y2k(self._y2k.replace(2000, *args, **kwargs))

    def astimezone(self, tz):
        """
        Convert this extended_datetime to another timezone.

        :param tz:
            A datetime.tzinfo object.

        :return:
            A new extended_datetime or datetime.datetime object
        """

        return extended_datetime.from_y2k(self._y2k.astimezone(tz))

    def timestamp(self):
        """
        Return POSIX timestamp. Only supported in python >= 3.3

        :return:
            A float representing the seconds since 1970-01-01 UTC. This will be a negative value.
        """

        return self._y2k.timestamp() - self.DAYS_IN_2000_YEARS * 86400

    def __str__(self):
        """
        :return:
            A str representing this extended_datetime, e.g. "0000-01-01 00:00:00.000001-10:00"
        """

        return self.isoformat(sep=' ')

    def __eq__(self, other):
        """
        Compare two extended_datetime objects

        :param other:
            The other extended_datetime to compare to

        :return:
            A boolean
        """

        # Only compare against other datetime or extended_datetime objects
        if not isinstance(other, (self.__class__, datetime)):
            return False

        # Offset-naive and offset-aware datetimes are never the same
        if (self.tzinfo is None) != (other.tzinfo is None):
            return False

        return self.__cmp__(other) == 0

    def __ne__(self, other):
        """
        Compare two extended_datetime objects

        :param other:
            The other extended_datetime to compare to

        :return:
            A boolean
        """

        return not self.__eq__(other)

    def _comparison_error(self, other):
        """
        Raises a TypeError about the other object not being suitable for
        comparison

        :param other:
            The object being compared to
        """

        raise TypeError(unwrap(
            '''
            An asn1crypto.util.extended_datetime object can only be compared to
            an asn1crypto.util.extended_datetime or datetime.datetime object,
            not %s
            ''',
            type_name(other)
        ))

    def __cmp__(self, other):
        """
        Compare two extended_datetime or datetime.datetime objects

        :param other:
            The other extended_datetime or datetime.datetime object to compare to

        :return:
            An integer smaller than, equal to, or larger than 0
        """

        if not isinstance(other, (self.__class__, datetime)):
            self._comparison_error(other)

        if (self.tzinfo is None) != (other.tzinfo is None):
            raise TypeError("can't compare offset-naive and offset-aware datetimes")

        diff = self - other
        zero = timedelta(0)
        if diff < zero:
            return -1
        if diff > zero:
            return 1
        return 0

    def __lt__(self, other):
        return self.__cmp__(other) < 0

    def __le__(self, other):
        return self.__cmp__(other) <= 0

    def __gt__(self, other):
        return self.__cmp__(other) > 0

    def __ge__(self, other):
        return self.__cmp__(other) >= 0

    def __add__(self, other):
        """
        Adds a timedelta

        :param other:
            A datetime.timedelta object to add.

        :return:
            A new extended_datetime or datetime.datetime object.
        """

        return extended_datetime.from_y2k(self._y2k + other)

    def __sub__(self, other):
        """
        Subtracts a timedelta or another datetime.

        :param other:
            A datetime.timedelta or datetime.datetime or extended_datetime object to subtract.

        :return:
            If a timedelta is passed, a new extended_datetime or datetime.datetime object.
            Else a datetime.timedelta object.
        """

        if isinstance(other, timedelta):
            return extended_datetime.from_y2k(self._y2k - other)

        if isinstance(other, extended_datetime):
            return self._y2k - other._y2k

        if isinstance(other, datetime):
            return self._y2k - other - timedelta(days=self.DAYS_IN_2000_YEARS)

        return NotImplemented

    def __rsub__(self, other):
        return -(self - other)

    @classmethod
    def from_y2k(cls, value):
        """
        Revert substitution of year 2000.

        :param value:
            A datetime.datetime object which is 2000 years in the future.
        :return:
            A new extended_datetime or datetime.datetime object.
        """

        year = value.year - 2000

        if year > 0:
            new_cls = datetime
        else:
            new_cls = cls

        return new_cls(
            year,
            value.month,
            value.day,
            value.hour,
            value.minute,
            value.second,
            value.microsecond,
            value.tzinfo
        )
