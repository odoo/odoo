#
# test cases for datetime stuff
#

import datetime as datetimelib
import json

from odoo.tests import common
from odoo.tools.datetime import (
    date, datetime, relativedelta, timedelta, posix_to_ldml,
    parse, UTC, rrule, rruleset, DAILY,
)


class TestDatetime(common.TransactionCase):
    def assertEqualSameType(self, obj1, obj2):
        self.assertEqual(obj1, obj2)
        self.assertEqual(type(obj1), type(obj2))

    def test_001_init_date(self):
        """ Test many ways to instantiate dates """
        start = date(1932, 11, 2)
        self.assertEqual(start.year, 1932)
        self.assertEqual(start.month, 11)
        self.assertEqual(start.day, 2)

        copied = date.from_date(start)
        self.assertEqual(copied.year, 1932)
        self.assertEqual(copied.month, 11)
        self.assertEqual(copied.day, 2)
        self.assertNotEqual(id(copied), id(start))

        converted = datetime(1932, 11, 2, 8, 42, 21).date()
        self.assertEqual(converted.year, 1932)
        self.assertEqual(converted.month, 11)
        self.assertEqual(converted.day, 2)
        self.assertNotEqual(id(converted), id(start))

        end = date.from_string('1932-11-10')
        self.assertEqual(end.year, 1932)
        self.assertEqual(end.month, 11)
        self.assertEqual(end.day, 10)

        # May be False if done at midnight minus some nanoseconds...
        self.assertEqual(date.today(), datetimelib.date.today())

        with self.assertRaises(ValueError):
            date(88, 88, 88)

    def test_002_init_datetime(self):
        """ Test many ways to instantiate datetimes """
        start = datetime(1932, 11, 2)
        self.assertEqual(start.year, 1932)
        self.assertEqual(start.month, 11)
        self.assertEqual(start.day, 2)
        self.assertEqual(start.hour, 0)
        self.assertEqual(start.minute, 0)
        self.assertEqual(start.second, 0)
        self.assertEqual(start.microsecond, 0)

        start = datetime(1932, 11, 2, 8, 42, 21)
        self.assertEqual(start.year, 1932)
        self.assertEqual(start.month, 11)
        self.assertEqual(start.day, 2)
        self.assertEqual(start.hour, 8)
        self.assertEqual(start.minute, 42)
        self.assertEqual(start.second, 21)

        copied = datetime.from_date(start)
        self.assertEqual(copied.year, 1932)
        self.assertEqual(copied.month, 11)
        self.assertEqual(copied.day, 2)
        self.assertEqual(copied.hour, 0)
        self.assertEqual(copied.minute, 0)
        self.assertEqual(copied.second, 0)
        self.assertEqual(copied.microsecond, 0)

        copied = datetime.from_datetime(start)
        self.assertEqual(copied.year, 1932)
        self.assertEqual(copied.month, 11)
        self.assertEqual(copied.day, 2)
        self.assertEqual(copied.hour, 8)
        self.assertEqual(copied.minute, 42)
        self.assertEqual(copied.second, 21)
        self.assertEqual(copied.microsecond, 0)
        self.assertNotEqual(id(copied), id(start))

        copied = datetime.from_datetime(start, with_microsecond=True)
        self.assertEqual(copied.year, 1932)
        self.assertEqual(copied.month, 11)
        self.assertEqual(copied.day, 2)
        self.assertEqual(copied.hour, 8)
        self.assertEqual(copied.minute, 42)
        self.assertEqual(copied.second, 21)
        self.assertNotEqual(id(copied), id(start))

        end = datetime.from_string('1932-11-10')
        self.assertEqual(end.year, 1932)
        self.assertEqual(end.month, 11)
        self.assertEqual(end.day, 10)
        self.assertEqual(end.hour, 0)
        self.assertEqual(end.minute, 0)
        self.assertEqual(end.second, 0)
        self.assertEqual(end.microsecond, 0)

        end = datetime.from_string('1932-11-10 18:8:42')
        self.assertEqual(end.year, 1932)
        self.assertEqual(end.month, 11)
        self.assertEqual(end.day, 10)
        self.assertEqual(end.hour, 18)
        self.assertEqual(end.minute, 8)
        self.assertEqual(end.second, 42)

        end = datetime.from_string('1932-11-10 18:08:42')
        self.assertEqual(end.year, 1932)
        self.assertEqual(end.month, 11)
        self.assertEqual(end.day, 10)
        self.assertEqual(end.hour, 18)
        self.assertEqual(end.minute, 8)
        self.assertEqual(end.second, 42)

        end = datetime.from_string('1932-11-10 18:08:42')
        self.assertEqual(end.year, 1932)
        self.assertEqual(end.month, 11)
        self.assertEqual(end.day, 10)
        self.assertEqual(end.hour, 18)
        self.assertEqual(end.minute, 8)
        self.assertEqual(end.second, 42)
        self.assertEqual(end.microsecond, 0)

        hybrid = datetime.combine(start.date(), end.time())
        self.assertEqual(hybrid.year, 1932)
        self.assertEqual(hybrid.month, 11)
        self.assertEqual(hybrid.day, 2)
        self.assertEqual(hybrid.hour, 18)
        self.assertEqual(hybrid.minute, 8)
        self.assertEqual(hybrid.second, 42)
        self.assertEqual(hybrid.microsecond, 0)

        now = datetime.now()
        self.assertEqual(now.microsecond, 0)
        self.assertTrue(datetimelib.datetime.now(UTC) - now < timedelta(seconds=1))
        now = datetime.now(with_microsecond=True)
        self.assertTrue(datetimelib.datetime.now(UTC) - now < timedelta(seconds=1))

        with self.assertRaises(ValueError):
            datetime(88, 88, 88)

    def _cmp_date(self, start, end, start_std, end_std, start_str, end_str):
        """ Test all comparisons

        :param start: Start date or datetime
        :param end: End date or datetime
        :param start_std: Start date or datetime from standard library
        :param end_std: End date or datetime from standard library
        :param start_str: Start date or datetime in string
        :param end_str: End date or datetime in string
        """
        self.assertTrue(start < end)
        self.assertFalse(end < start)
        self.assertFalse(end < end)
        self.assertTrue(start < end_std)
        self.assertFalse(end < start_std)
        self.assertFalse(end < end_std)
        self.assertTrue(start < end_str)
        self.assertFalse(end < start_str)
        self.assertFalse(end < end_str)
        self.assertFalse(end_std < start)
        self.assertTrue(start_std < end)
        self.assertFalse(end_std < end)
        self.assertFalse(end_str < start)
        self.assertTrue(start_str < end)
        self.assertFalse(end_str < end)

        self.assertFalse(start > end)
        self.assertTrue(end > start)
        self.assertFalse(end > end)
        self.assertFalse(start > end_std)
        self.assertTrue(end > start_std)
        self.assertFalse(end > end_std)
        self.assertFalse(start > end_str)
        self.assertTrue(end > start_str)
        self.assertFalse(end > end_str)
        self.assertTrue(end_std > start)
        self.assertFalse(start_std > end)
        self.assertFalse(end_std > end)
        self.assertTrue(end_str > start)
        self.assertFalse(start_str > end)
        self.assertFalse(end_str > end)

        self.assertTrue(start <= end)
        self.assertFalse(end <= start)
        self.assertTrue(end <= end)
        self.assertTrue(start <= end_std)
        self.assertFalse(end <= start_std)
        self.assertTrue(end <= end_std)
        self.assertTrue(start <= end_str)
        self.assertFalse(end <= start_str)
        self.assertTrue(end <= end_str)
        self.assertFalse(end_std <= start)
        self.assertTrue(start_std <= end)
        self.assertTrue(end_std <= end)
        self.assertFalse(end_str <= start)
        self.assertTrue(start_str <= end)
        self.assertTrue(end_str <= end)

        self.assertFalse(start >= end)
        self.assertTrue(end >= start)
        self.assertTrue(end >= end)
        self.assertFalse(start >= end_std)
        self.assertTrue(end >= start_std)
        self.assertTrue(end >= end_std)
        self.assertFalse(start >= end_str)
        self.assertTrue(end >= start_str)
        self.assertTrue(end >= end_str)
        self.assertTrue(end_std >= start)
        self.assertFalse(start_std >= end)
        self.assertTrue(end_std >= end)
        self.assertTrue(end_str >= start)
        self.assertFalse(start_str >= end)
        self.assertTrue(end_str >= end)

        self.assertFalse(start == end)
        self.assertFalse(end == start)
        self.assertTrue(end == end)
        self.assertFalse(start == end_std)
        self.assertFalse(end == start_std)
        self.assertTrue(end == end_std)
        self.assertFalse(start == end_str)
        self.assertFalse(end == start_str)
        self.assertTrue(end == end_str)
        self.assertFalse(end_std == start)
        self.assertFalse(start_std == end)
        self.assertTrue(end_std == end)
        self.assertFalse(end_str == start)
        self.assertFalse(start_str == end)
        self.assertTrue(end_str == end)

        self.assertTrue(start != end)
        self.assertTrue(end != start)
        self.assertFalse(end != end)
        self.assertTrue(start != end_std)
        self.assertTrue(end != start_std)
        self.assertFalse(end != end_std)
        self.assertTrue(start != end_str)
        self.assertTrue(end != start_str)
        self.assertFalse(end != end_str)
        self.assertTrue(end_std != start)
        self.assertTrue(start_std != end)
        self.assertFalse(end_std != end)
        self.assertTrue(end_str != start)
        self.assertTrue(start_str != end)
        self.assertFalse(end_str != end)

    def test_011_compare_date(self):
        """ Test comparison between dates and dates/strings """
        self._cmp_date(
            date(1932, 11, 2),
            date(1932, 11, 10),
            datetimelib.date(1932, 11, 2),
            datetimelib.date(1932, 11, 10),
            '1932-11-2',
            '1932-11-10'
        )
        self._cmp_date(
            datetime(1932, 11, 2, 8, 42, 21).date(),
            datetime(1932, 11, 10, 18, 42, 27).date(),
            datetimelib.date(1932, 11, 2),
            datetimelib.date(1932, 11, 10),
            '1932-11-2',
            '1932-11-10'
        )

    def test_012_compare_datetime(self):
        """ Test comparison between datetimes and datetimes/strings """
        self._cmp_date(
            datetime(1932, 11, 2, 8, 42, 21),
            datetime(1932, 11, 10, 18, 42, 27),
            datetimelib.datetime(1932, 11, 2, 8, 42, 21, tzinfo=UTC),
            datetimelib.datetime(1932, 11, 10, 18, 42, 27, tzinfo=UTC),
            '1932-11-2',
            '1932-11-10 18:42:27'
        )

    def test_013_compare_date_datetime(self):
        """ Test comparison between dates and datetimes """
        start = date(1932, 11, 2)
        end = datetime(1932, 11, 10, 18, 42, 27)
        start_std = datetimelib.date(1932, 11, 2)
        end_std = datetimelib.datetime(1932, 11, 10, 18, 42, 27, tzinfo=UTC)

        self.assertTrue(start < end)
        self.assertFalse(end < start)
        self.assertTrue(start < end_std)
        self.assertFalse(end < start_std)
        with self.assertRaises(TypeError):
            self.assertFalse(end_std < start)
        self.assertTrue(start_std < end)

        self.assertFalse(start > end)
        self.assertTrue(end > start)
        self.assertFalse(start > end_std)
        self.assertTrue(end > start_std)
        with self.assertRaises(TypeError):
            self.assertTrue(end_std > start)
        self.assertFalse(start_std > end)

        self.assertTrue(start <= end)
        self.assertFalse(end <= start)
        self.assertTrue(start <= end_std)
        self.assertFalse(end <= start_std)
        with self.assertRaises(TypeError):
            self.assertFalse(end_std <= start)
        self.assertTrue(start_std <= end)

        self.assertFalse(start >= end)
        self.assertTrue(end >= start)
        self.assertFalse(start >= end_std)
        self.assertTrue(end >= start_std)
        with self.assertRaises(TypeError):
            self.assertTrue(end_std >= start)
        self.assertFalse(start_std >= end)

        self.assertFalse(start == end)
        self.assertFalse(end == start)
        self.assertFalse(start == end_std)
        self.assertFalse(end == start_std)
        self.assertFalse(end_std == start)
        self.assertFalse(start_std == end)

        self.assertTrue(start != end)
        self.assertTrue(end != start)
        self.assertTrue(start != end_std)
        self.assertTrue(end != start_std)
        self.assertTrue(end_std != start)
        self.assertTrue(start_std != end)

    def _arithmetic_check(self, start, end, start_std, end_std,
            start_str, end_str, period, relative_period):
        """ Check for arithmetics

        :param start: Start date or datetime
        :param end: End date or datetime
        :param start_std: Start date or datetime from standard library
        :param end_std: End date or datetime from standard library
        :param start_str: Start date or datetime in string
        :param end_str: End date or datetime in string
        :param period: Timedelta between start and end
        :param relative_period: Relative delta between start and end
        """
        self.assertEqual(end - start, period)
        self.assertEqual(start - end, -period)
        self.assertEqual(end - start_std, period)
        self.assertEqual(start_std - end, -period)
        self.assertEqual(end - start_str, period)
        self.assertEqual(start_str - end, -period)
        self.assertEqualSameType(end - period, start)
        self.assertEqualSameType(end - relative_period, start)
        self.assertEqual(end_std - period, start)
        self.assertEqualSameType(end_std - relative_period, start)
        with self.assertRaises(TypeError):
            period - end
        with self.assertRaises(TypeError):
            relative_period - end
        with self.assertRaises(TypeError):
            period - end_str
        with self.assertRaises(TypeError):
            relative_period - end_str
        with self.assertRaises(TypeError):
            period - end_std
        with self.assertRaises(TypeError):
            relative_period - end_std

        self.assertEqual(start_std + period, end)
        self.assertEqualSameType(start_std + relative_period, end)
        self.assertEqualSameType(start + period, end)
        self.assertEqualSameType(start + relative_period, end)
        self.assertEqualSameType(period + start, end)
        self.assertEqualSameType(relative_period + start, end)
        with self.assertRaises(TypeError):
            start + start_str
        with self.assertRaises(TypeError):
            start + start_std
        with self.assertRaises(TypeError):
            start + end
        with self.assertRaises(TypeError):
            start + 8

        with self.assertRaises(TypeError):
            start * end
        with self.assertRaises(TypeError):
            start * end_str
        with self.assertRaises(TypeError):
            start * end_std
        with self.assertRaises(TypeError):
            end_str * start
        with self.assertRaises(TypeError):
            end_std * start
        with self.assertRaises(TypeError):
            start * relative_period
        with self.assertRaises(TypeError):
            start * period
        with self.assertRaises(TypeError):
            relative_period * start
        with self.assertRaises(TypeError):
            period * start
        with self.assertRaises(TypeError):
            start * 3

        with self.assertRaises(TypeError):
            start / end
        with self.assertRaises(TypeError):
            start / end_str
        with self.assertRaises(TypeError):
            start / end_std
        with self.assertRaises(TypeError):
            end_str / start
        with self.assertRaises(TypeError):
            end_std / start
        with self.assertRaises(TypeError):
            start / relative_period
        with self.assertRaises(TypeError):
            start / period
        with self.assertRaises(TypeError):
            relative_period / start
        with self.assertRaises(TypeError):
            period / start
        with self.assertRaises(TypeError):
            start / 3

        with self.assertRaises(TypeError):
            start % end
        with self.assertRaises(TypeError):
            start % end_str
        with self.assertRaises(TypeError):
            start % end_std
        with self.assertRaises(TypeError):
            end_std % start
        with self.assertRaises(TypeError):
            start % relative_period
        with self.assertRaises(TypeError):
            start % period
        with self.assertRaises(TypeError):
            relative_period % start
        with self.assertRaises(TypeError):
            period % start
        with self.assertRaises(TypeError):
            start % 3

    def test_021_arithmetic_date(self):
        """ Test arithmetic operations on dates (using timedelta/relativedelta) """
        self._arithmetic_check(
            date(1932, 11, 2),
            date(1932, 11, 10),
            datetimelib.date(1932, 11, 2),
            datetimelib.date(1932, 11, 10),
            '1932-11-2',
            '1932-11-10',
            timedelta(days=8),
            relativedelta(days=8)
        )

    def test_022_arithmetic_datetime(self):
        """ Test arithmetic operations on datetimes (using timedelta/relativedelta) """
        self._arithmetic_check(
            datetime(1932, 11, 2, 8, 42, 21),
            datetime(1932, 11, 10, 18, 42, 27),
            datetimelib.datetime(1932, 11, 2, 8, 42, 21, tzinfo=UTC),
            datetimelib.datetime(1932, 11, 10, 18, 42, 27, tzinfo=UTC),
            '1932-11-2 8:42:21',
            '1932-11-10 18:42:27',
            timedelta(days=8, hours=10, seconds=6),
            relativedelta(days=8, hours=10, seconds=6)
        )

    def test_023_arithmetic_date_datetime(self):
        """ Test arithmetic operations mixing dates and datetimes (mostly expecting crashes) """
        start = date(1932, 11, 2)
        end = datetime(1932, 11, 10, 18, 42, 27)
        start_std = datetimelib.date(1932, 11, 2)
        end_std = datetimelib.datetime(1932, 11, 10, 18, 42, 27, tzinfo=UTC)
        period = timedelta(days=8)
        relative_period = relativedelta(days=8)

        with self.assertRaises(TypeError):
            start - end
        with self.assertRaises(TypeError):
            end - start
        with self.assertRaises(TypeError):
            end_std - start
        with self.assertRaises(TypeError):
            start_std - end

        self.assertEqualSameType(period + relative_period, relativedelta(days=16))
        self.assertEqualSameType(period * 2, timedelta(days=16))
        self.assertEqualSameType(relative_period * 2, relativedelta(days=16))
        self.assertEqualSameType(period - period, timedelta(0))
        self.assertEqualSameType(period / 2, timedelta(days=4))
        self.assertEqualSameType(relative_period / 2, relativedelta(days=4))
        with self.assertRaises(TypeError):
            period * period
        with self.assertRaises(TypeError):
            relative_period * period
        self.assertEqual(period / period, 1)
        with self.assertRaises(TypeError):
            relative_period / period
        with self.assertRaises(TypeError):
            period % 2
        with self.assertRaises(TypeError):
            relative_period % 2

    def test_031_date_tools(self):
        """ Test conveniance tools on dates """
        start = date(1932, 11, 2)

        self.assertEqualSameType(start.end_of('month'), date(1932, 11, 30))
        self.assertEqualSameType(start.end_of('year'), date(1932, 12, 31))
        self.assertEqualSameType(start.start_of('month'), date(1932, 11, 1))
        self.assertEqualSameType(start.start_of('year'), date(1932, 1, 1))

        self.assertEqualSameType(start.to_pydate(), datetimelib.date(1932, 11, 2))
        self.assertEqualSameType(start.replace(year=1931), date(1931, 11, 2))
        self.assertEqualSameType(start.replace(month=10, day=8), date(1932, 10, 8))
        self.assertEqualSameType(start.replace(1934), date(1934, 11, 2))
        with self.assertRaises(TypeError):
            start.replace(second=10)
        with self.assertRaises(TypeError):
            start.replace(minute=10)
        with self.assertRaises(TypeError):
            start.replace(hour=10)

    def test_032_datetime_tools(self):
        """ Test conveniance tools on datetimes """
        start = datetime(1932, 11, 2, 8, 42, 27)

        self.assertEqualSameType(start.end_of('month'), datetime(1932, 11, 30, 23, 59, 59))
        self.assertEqualSameType(start.end_of('year'), datetime(1932, 12, 31, 23, 59, 59))
        self.assertEqualSameType(start.start_of('month'), datetime(1932, 11, 1))
        self.assertEqualSameType(start.start_of('year'), datetime(1932, 1, 1))

        self.assertEqualSameType(start.to_pydate(), datetimelib.date(1932, 11, 2))
        self.assertEqualSameType(
            start.to_pydatetime(),
            datetimelib.datetime(1932, 11, 2, 8, 42, 27, tzinfo=UTC))
        self.assertEqualSameType(start.replace(year=1931), datetime(1931, 11, 2, 8, 42, 27))
        self.assertEqualSameType(start.replace(month=10, day=8), datetime(1932, 10, 8, 8, 42, 27))
        self.assertEqualSameType(start.replace(hour=10), datetime(1932, 11, 2, 10, 42, 27))
        self.assertEqualSameType(start.replace(minute=10), datetime(1932, 11, 2, 8, 10, 27))
        self.assertEqualSameType(start.replace(second=10), datetime(1932, 11, 2, 8, 42, 10))
        self.assertEqualSameType(start.replace(1934), datetime(1934, 11, 2, 8, 42, 27))

    def test_041_date_to_string(self):
        """ Test many ways to convert dates to string """
        end = date(1932, 11, 8)
        self.assertEqual(hash(end), hash(datetimelib.date(1932, 11, 8)))
        self.assertEqual(repr(end), '<date 1932-11-08>')
        self.assertEqual(str(end), '1932-11-08')
        self.assertEqual(end.to_isoformat(), '1932-11-08')

        end = datetime(1932, 11, 8, 18, 42, 27).date()
        self.assertEqual(hash(end), hash(datetimelib.date(1932, 11, 8)))
        self.assertEqual(repr(end), '<date 1932-11-08>')
        self.assertEqual(str(end), '1932-11-08')
        self.assertEqual(end.to_isoformat(), '1932-11-08')

    def test_042_datetime_to_string(self):
        """ Test many ways to convert datetimes to string """
        end = datetime(1932, 11, 8, 18, 42, 27)
        self.assertEqual(
            hash(end), hash(datetimelib.datetime(1932, 11, 8, 18, 42, 27, tzinfo=UTC)))
        self.assertEqual(repr(end), '<datetime 1932-11-08T18:42:27+00:00>')
        self.assertEqual(str(end), '1932-11-08 18:42:27')
        self.assertEqual(end.to_isoformat(), '1932-11-08T18:42:27+00:00')
        self.assertEqual(end.to_atom(), '1932-11-08T18:42:27Z')
        self.assertEqual(end.to_filename(), '1932-11-08_18-42-27')
        self.assertEqual(end.to_gcal(), '1932-11-08T18:42:27.000000z')
        self.assertEqual(end.to_ical(), '19321108T18:42:27Z')
        self.assertEqual(end.to_pofile(), '1932-11-08 18:42+0000')
        self.assertEqual(end.to_virtualid(), '19321108184227')

    def test_051_date_as_string(self):
        """ Test date manipulation as string """
        end = date(1932, 11, 10)
        self.assertTrue('1932-11' in end)
        self.assertFalse('1933-4' in end)
        self.assertEqual(len(end), 10)
        self.assertEqual(end[0], '1')
        self.assertEqual(end[1:5], '932-')

        idx = 0
        for char in end:
            self.assertEqual(char, '1932-11-10'[idx])
            idx += 1

        self.assertTrue(end.startswith('1932-'))
        self.assertTrue(end.endswith('-10'))
        self.assertFalse(end.startswith('Emu'))
        self.assertFalse(end.endswith('Emu'))

        self.assertEqual(end.index('1'), 0)
        self.assertEqual(end.index('9'), 1)
        with self.assertRaises(ValueError):
            end.index('4')

        self.assertEqual(end.rindex('1'), 8)
        self.assertEqual(end.rindex('9'), 1)
        with self.assertRaises(ValueError):
            end.rindex('4')

        begin = end.replace('-10', '-02')
        self.assertEqual(begin.year, 1932)
        self.assertEqual(begin.month, 11)
        self.assertEqual(begin.day, 2)

        self.assertEqual(end.find('19'), 0)
        self.assertEqual(end.find('32'), 2)
        self.assertEqual(end.find('1'), 0)
        self.assertEqual(end.find('Emu'), -1)

        self.assertEqual(end.rfind('19'), 0)
        self.assertEqual(end.rfind('32'), 2)
        self.assertEqual(end.rfind('1'), 8)
        self.assertEqual(end.rfind('Emu'), -1)

        self.assertEqual(end.split('-'), ['1932', '11', '10'])
        self.assertEqual(end.rsplit('-'), ['1932', '11', '10'])
        self.assertEqual(end.split('-', 1), ['1932', '11-10'])
        self.assertEqual(end.rsplit('-', 1), ['1932-11', '10'])
        self.assertEqual(end.strip('10'), '932-11-')
        self.assertEqual(end.lstrip('10'), '932-11-10')
        self.assertEqual(end.rstrip('10'), '1932-11-')

    def test_052_datetime_as_string(self):
        """ Test datetime manipulation as string """
        end = datetime(1932, 11, 10, 8, 42, 27)
        self.assertTrue('1932-11' in end)
        self.assertFalse('1933-4' in end)
        self.assertEqual(len(end), 19)
        self.assertEqual(end[0], '1')
        self.assertEqual(end[1:5], '932-')

        idx = 0
        for char in end:
            self.assertEqual(char, '1932-11-10 08:42:27'[idx])
            idx += 1

        self.assertTrue(end.startswith('1932-'))
        self.assertTrue(end.endswith(':27'))
        self.assertFalse(end.startswith('Emu'))
        self.assertFalse(end.endswith('Emu'))

        self.assertEqual(end.index('1'), 0)
        self.assertEqual(end.index('9'), 1)
        with self.assertRaises(ValueError):
            end.index('5')

        self.assertEqual(end.rindex('1'), 8)
        self.assertEqual(end.rindex('9'), 1)
        with self.assertRaises(ValueError):
            end.rindex('5')

        begin = end.replace('-10', '-02')
        self.assertEqual(begin.year, 1932)
        self.assertEqual(begin.month, 11)
        self.assertEqual(begin.day, 2)
        self.assertEqual(begin.hour, 8)
        self.assertEqual(begin.minute, 42)
        self.assertEqual(begin.second, 27)

        self.assertEqual(end.find('19'), 0)
        self.assertEqual(end.find('32'), 2)
        self.assertEqual(end.find('1'), 0)
        self.assertEqual(end.find('Emu'), -1)

        self.assertEqual(end.rfind('19'), 0)
        self.assertEqual(end.rfind('32'), 2)
        self.assertEqual(end.rfind('1'), 8)
        self.assertEqual(end.rfind('Emu'), -1)

        self.assertEqual(end.split('-'), ['1932', '11', '10 08:42:27'])
        self.assertEqual(end.rsplit('-'), ['1932', '11', '10 08:42:27'])
        self.assertEqual(end.split('-', 1), ['1932', '11-10 08:42:27'])
        self.assertEqual(end.rsplit('-', 1), ['1932-11', '10 08:42:27'])
        self.assertEqual(end.strip('1027'), '932-11-10 08:42:')
        self.assertEqual(end.lstrip('1027'), '932-11-10 08:42:27')
        self.assertEqual(end.rstrip('1027'), '1932-11-10 08:42:')

    def test_061_datetime_timezone(self):
        """ Test timezones and datetime """
        # Use a 60-years more recent date for modern rules on timezones
        begin = datetime(1992, 11, 2, 8, 42, 27, tzinfo='Australia/Sydney')
        self.assertEqual(begin.day, 2)
        self.assertEqual(begin.hour, 8)
        self.assertEqual(begin.minute, 42)
        self.assertEqual(str(begin), '1992-11-01 21:42:27')
        self.assertEqual(begin, '1992-11-1 21:42:27')

        begin_utc = begin.astimezone()
        self.assertEqual(begin_utc.year, 1992)
        self.assertEqual(begin_utc.month, 11)
        self.assertEqual(begin_utc.day, 1)
        self.assertEqual(begin_utc.hour, 21)
        self.assertEqual(begin_utc.minute, 42)
        self.assertEqual(begin_utc.to_string(), begin.to_string())
        self.assertEqual(begin_utc.hour, begin.to_utc().hour)

        begin_brussels = begin_utc.astimezone('Europe/Brussels')
        self.assertEqual(begin_brussels.year, 1992)
        self.assertEqual(begin_brussels.month, 11)
        self.assertEqual(begin_brussels.day, 1)
        self.assertEqual(begin_brussels.hour, 22)
        self.assertEqual(begin_brussels.minute, 42)
        self.assertEqual(begin_brussels, begin)
        self.assertEqual(begin_brussels - begin, timedelta(0))

        end_brussels = begin_brussels + relativedelta(months=8)
        self.assertEqual(end_brussels.year, 1993)
        self.assertEqual(end_brussels.month, 7)
        self.assertEqual(end_brussels.day, 1)
        self.assertEqual(end_brussels.hour, 22)
        self.assertEqual(end_brussels.to_utc().hour, 20)
        self.assertEqual(end_brussels.minute, 42)

    def test_062_datetime_parser(self):
        """ Test parser wrapper """
        begin = parse('32-11-2 8:3:4+2:00')
        self.assertEqual(begin.year, 2032)
        self.assertEqual(begin.month, 11)
        self.assertEqual(begin.day, 2)
        self.assertEqual(begin.hour, 8)
        self.assertEqual(begin.minute, 3)
        self.assertEqual(str(begin), '2032-11-02 06:03:04')

    def test_101_rrule(self):
        """ Test rrule wrapper """
        day = 2
        for current_day in rrule(DAILY, datetime(1932, 11, 2), count=8):
            self.assertEqualSameType(current_day, datetime(1932, 11, day))
            day += 1
        self.assertEqual(day, 10)

    def test_102_rrule_set(self):
        """ Test rrule set wrapper """
        day = 2
        emu = rruleset()
        emu.rrule(rrule(DAILY, dtstart=datetime(1932, 11, 2), count=8))
        for current_day in emu:
            self.assertEqualSameType(current_day, datetime(1932, 11, day))
            day += 1
        self.assertEqual(day, 10)

    def test_201_json(self):
        """ Test JSON conversion """
        result = json.dumps({
            'begin': datetime(1932, 11, 2, 8, 42, 27),
            'end': date(1932, 11, 10)
        })
        self.assertEqual(json.loads(result), {"begin": "1932-11-02 08:42:27", "end": "1932-11-10"})

    def test_301_posix_to_ldml(self):
        """ Test POSIX to LDML function """
        posix = "%ak %A %b %B %d %H:%I %j %m/%M %p"
        ldml = "E'k' EEEE MMM MMMM dd HH:hh DDD MM/mm a"
        self.assertEqual(posix_to_ldml(posix, None), ldml)
        posix = "%S %U %w %W %y %Y"
        ldml = "ss w e w yy yyyy"
        self.assertEqual(posix_to_ldml(posix, None), ldml)
        with self.assertRaises(KeyError):
            posix_to_ldml('%K', None)
