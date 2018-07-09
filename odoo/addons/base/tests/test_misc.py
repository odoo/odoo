# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
from dateutil.relativedelta import relativedelta
import pytz
import unittest

from odoo.tools import misc, date_utils
from odoo.tests.common import TransactionCase, tagged


@tagged('standard', 'at_install')
class TestCountingStream(unittest.TestCase):
    def test_empty_stream(self):
        s = misc.CountingStream(iter([]))
        self.assertEqual(s.index, -1)
        self.assertIsNone(next(s, None))
        self.assertEqual(s.index, 0)

    def test_single(self):
        s = misc.CountingStream(range(1))
        self.assertEqual(s.index, -1)
        self.assertEqual(next(s, None), 0)
        self.assertIsNone(next(s, None))
        self.assertEqual(s.index, 1)

    def test_full(self):
        s = misc.CountingStream(range(42))
        for _ in s:
            pass
        self.assertEqual(s.index, 42)

    def test_repeated(self):
        """ Once the CountingStream has stopped iterating, the index should not
        increase anymore (the internal state should not be allowed to change)
        """
        s = misc.CountingStream(iter([]))
        self.assertIsNone(next(s, None))
        self.assertEqual(s.index, 0)
        self.assertIsNone(next(s, None))
        self.assertEqual(s.index, 0)


class TestDateRangeFunction(unittest.TestCase):
    """Test on date_range generator.

    date_range is an helper genetor used to fill dates interval.
    """

    def test_date_range_with_two_timezone_naive_datetime_start_1st_jan(self):
        """Simplest test on date_range.

        We generate a range of one year, start_date and end_date have naive
        timezone.
        """
        start_date = datetime.datetime(1985, 1, 1)
        end_date = datetime.datetime(1986, 1, 1)

        expected = [
            datetime.datetime(1985, 1, 1, 0, 0),
            datetime.datetime(1985, 2, 1, 0, 0),
            datetime.datetime(1985, 3, 1, 0, 0),
            datetime.datetime(1985, 4, 1, 0, 0),
            datetime.datetime(1985, 5, 1, 0, 0),
            datetime.datetime(1985, 6, 1, 0, 0),
            datetime.datetime(1985, 7, 1, 0, 0),
            datetime.datetime(1985, 8, 1, 0, 0),
            datetime.datetime(1985, 9, 1, 0, 0),
            datetime.datetime(1985, 10, 1, 0, 0),
            datetime.datetime(1985, 11, 1, 0, 0),
            datetime.datetime(1985, 12, 1, 0, 0),
            datetime.datetime(1986, 1, 1, 0, 0)
        ]

        dates = [date for date in date_utils.date_range(start_date, end_date)]

        assert dates == expected

    def test_date_range_with_two_timezone_aware_datetime(self):
        """Test date range with two timezone aware datetime.

        Generate a range between two datetimes having aware timezones.
        """
        context_timezone = pytz.timezone('Europe/Brussels')

        start_date = datetime.datetime(1985, 1, 1)
        start_date = context_timezone.localize(start_date)
        end_date = datetime.datetime(1986, 1, 1)
        end_date = context_timezone.localize(end_date)

        timezone = pytz.timezone('Europe/Brussels')

        expected = [
            #            DATE                      DST
            (datetime.datetime(1985, 1, 1, 0, 0), False),
            (datetime.datetime(1985, 2, 1, 0, 0), False),
            (datetime.datetime(1985, 3, 1, 0, 0), False),
            (datetime.datetime(1985, 4, 1, 0, 0), True),
            (datetime.datetime(1985, 5, 1, 0, 0), True),
            (datetime.datetime(1985, 6, 1, 0, 0), True),
            (datetime.datetime(1985, 7, 1, 0, 0), True),
            (datetime.datetime(1985, 8, 1, 0, 0), True),
            (datetime.datetime(1985, 9, 1, 0, 0), True),
            (datetime.datetime(1985, 10, 1, 0, 0), False),
            (datetime.datetime(1985, 11, 1, 0, 0), False),
            (datetime.datetime(1985, 12, 1, 0, 0), False),
            (datetime.datetime(1986, 1, 1, 0, 0), False),
        ]

        expected = [timezone.localize(dt, is_dst=is_dst) for dt, is_dst in expected]

        dates = [date for date in date_utils.date_range(start_date, end_date)]

        assert dates == expected

    def test_date_range_with_one_timezone_aware_datetime_and_naive_one(self):
        """Test date range with one timezone aware datetime and naive one.

        a difference between two timezone should raise an error
        """
        context_timezone = pytz.timezone('Europe/Brussels')

        start_date = datetime.datetime(1985, 1, 1)
        end_date = datetime.datetime(1986, 1, 1)
        end_date = context_timezone.localize(end_date)

        with self.assertRaises(Exception) as context:
            dates = [date for date in date_utils.date_range(start_date, end_date)]

        self.assertTrue(isinstance(context.exception, AssertionError))

    def test_date_range_with_hour_(self):
        """Test date range with hour and naive timezone datetime."""
        start_date = datetime.datetime(1985, 1, 1)
        end_date = datetime.datetime(1985, 1, 2)
        step_dt = relativedelta(hours=1)

        dates = [date for date in date_utils.date_range(start_date, end_date, step_dt)]

        assert len(dates) == 25

    def test_date_range_with_equal_start_and_end_date_should_raise_an_exception(self):
        """Test date range with same date should raise."""
        start_date = datetime.datetime(1985, 1, 1)
        end_date = datetime.datetime(1985, 1, 1)

        with self.assertRaises(Exception) as context:
            dates = [date for date in date_utils.date_range(start_date, end_date)]

        self.assertTrue(isinstance(context.exception, ValueError))


class TestFormatLangDate(TransactionCase):
    def test_00_accepted_types(self):
        date_datetime = datetime.datetime.strptime('2017-01-31 12:00:00', "%Y-%m-%d %H:%M:%S")
        date_date = date_datetime.date()
        date_str = '2017-01-31'

        self.assertEqual(misc.format_date(self.env, date_datetime), '01/31/2017')
        self.assertEqual(misc.format_date(self.env, date_date), '01/31/2017')
        self.assertEqual(misc.format_date(self.env, date_str), '01/31/2017')
        self.assertEqual(misc.format_date(self.env, ''), '')
        self.assertEqual(misc.format_date(self.env, False), '')
        self.assertEqual(misc.format_date(self.env, None), '')

    def test_01_code_and_format(self):
        date_str = '2017-01-31'
        lang = self.env['res.lang']

        # Activate French and Simplified Chinese (test with non-ASCII characters)
        lang.search([('active', '=', False), ('code', 'in', ['fr_FR', 'zh_CN'])]).write({'active': True})

        # Change a single parameter
        self.assertEqual(misc.format_date(lang.with_context(lang='fr_FR').env, date_str), '31/01/2017')
        self.assertEqual(misc.format_date(lang.env, date_str, lang_code='fr_FR'), '31/01/2017')
        self.assertEqual(misc.format_date(lang.env, date_str, date_format='MMM d, y'), 'Jan 31, 2017')

        # Change 2 parameters
        self.assertEqual(misc.format_date(lang.with_context(lang='zh_CN').env, date_str, lang_code='fr_FR'), '31/01/2017')
        self.assertEqual(misc.format_date(lang.with_context(lang='zh_CN').env, date_str, date_format='MMM d, y'), u'1\u6708 31, 2017')
        self.assertEqual(misc.format_date(lang.env, date_str, lang_code='fr_FR', date_format='MMM d, y'), 'janv. 31, 2017')

        # Change 3 parameters
        self.assertEqual(misc.format_date(lang.with_context(lang='zh_CN').env, date_str, lang_code='en_US', date_format='MMM d, y'), 'Jan 31, 2017')
