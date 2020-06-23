# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
from dateutil.relativedelta import relativedelta
import pytz

from odoo.tools import misc, date_utils, remove_accents
from odoo.tests.common import TransactionCase, BaseCase


class TestCountingStream(BaseCase):
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


class TestDateRangeFunction(BaseCase):
    """ Test on date_range generator. """

    def test_date_range_with_naive_datetimes(self):
        """ Check date_range with naive datetimes. """
        start = datetime.datetime(1985, 1, 1)
        end = datetime.datetime(1986, 1, 1)

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

        dates = [date for date in date_utils.date_range(start, end)]

        self.assertEqual(dates, expected)

    def test_date_range_with_timezone_aware_datetimes_other_than_utc(self):
        """ Check date_range with timezone-aware datetimes other than UTC."""
        timezone = pytz.timezone('Europe/Brussels')

        start = datetime.datetime(1985, 1, 1)
        end = datetime.datetime(1986, 1, 1)
        start = timezone.localize(start)
        end = timezone.localize(end)

        expected = [datetime.datetime(1985, 1, 1, 0, 0),
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
                    datetime.datetime(1986, 1, 1, 0, 0)]

        expected = [timezone.localize(e) for e in expected]

        dates = [date for date in date_utils.date_range(start, end)]

        self.assertEqual(expected, dates)

    def test_date_range_with_mismatching_zones(self):
        """ Check date_range with mismatching zone should raise an exception."""
        start_timezone = pytz.timezone('Europe/Brussels')
        end_timezone = pytz.timezone('America/Recife')

        start = datetime.datetime(1985, 1, 1)
        end = datetime.datetime(1986, 1, 1)
        start = start_timezone.localize(start)
        end = end_timezone.localize(end)

        with self.assertRaises(ValueError):
            dates = [date for date in date_utils.date_range(start, end)]

    def test_date_range_with_inconsistent_datetimes(self):
        """ Check date_range with a timezone-aware datetime and a naive one."""
        context_timezone = pytz.timezone('Europe/Brussels')

        start = datetime.datetime(1985, 1, 1)
        end = datetime.datetime(1986, 1, 1)
        end = context_timezone.localize(end)

        with self.assertRaises(ValueError):
            dates = [date for date in date_utils.date_range(start, end)]

    def test_date_range_with_hour(self):
        """ Test date range with hour and naive datetime."""
        start = datetime.datetime(2018, 3, 25)
        end = datetime.datetime(2018, 3, 26)
        step = relativedelta(hours=1)

        expected = [
            datetime.datetime(2018, 3, 25, 0, 0),
            datetime.datetime(2018, 3, 25, 1, 0),
            datetime.datetime(2018, 3, 25, 2, 0),
            datetime.datetime(2018, 3, 25, 3, 0),
            datetime.datetime(2018, 3, 25, 4, 0),
            datetime.datetime(2018, 3, 25, 5, 0),
            datetime.datetime(2018, 3, 25, 6, 0),
            datetime.datetime(2018, 3, 25, 7, 0),
            datetime.datetime(2018, 3, 25, 8, 0),
            datetime.datetime(2018, 3, 25, 9, 0),
            datetime.datetime(2018, 3, 25, 10, 0),
            datetime.datetime(2018, 3, 25, 11, 0),
            datetime.datetime(2018, 3, 25, 12, 0),
            datetime.datetime(2018, 3, 25, 13, 0),
            datetime.datetime(2018, 3, 25, 14, 0),
            datetime.datetime(2018, 3, 25, 15, 0),
            datetime.datetime(2018, 3, 25, 16, 0),
            datetime.datetime(2018, 3, 25, 17, 0),
            datetime.datetime(2018, 3, 25, 18, 0),
            datetime.datetime(2018, 3, 25, 19, 0),
            datetime.datetime(2018, 3, 25, 20, 0),
            datetime.datetime(2018, 3, 25, 21, 0),
            datetime.datetime(2018, 3, 25, 22, 0),
            datetime.datetime(2018, 3, 25, 23, 0),
            datetime.datetime(2018, 3, 26, 0, 0)
        ]

        dates = [date for date in date_utils.date_range(start, end, step)]

        self.assertEqual(dates, expected)


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


class TestRemoveAccents(BaseCase):
    def test_empty_string(self):
        self.assertEqual(remove_accents(False), False)
        self.assertEqual(remove_accents(''), '')
        self.assertEqual(remove_accents(None), None)

    def test_latin(self):
        self.assertEqual(remove_accents('Niño Hernández'), 'Nino Hernandez')
        self.assertEqual(remove_accents('Anaïs Clémence'), 'Anais Clemence')

    def test_non_latin(self):
        self.assertEqual(remove_accents('العربية'), 'العربية')
        self.assertEqual(remove_accents('русский алфавит'), 'русскии алфавит')
