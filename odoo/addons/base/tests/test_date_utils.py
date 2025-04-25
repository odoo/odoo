# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import date, datetime

import pytz
from dateutil.relativedelta import relativedelta

from odoo.tests import BaseCase
from odoo.tools.date_utils import date_range, get_fiscal_year


class TestDateUtils(BaseCase):

    def test_fiscal_year(self):
        self.assertEqual(get_fiscal_year(date(2024, 12, 31)), (date(2024, 1, 1), date(2024, 12, 31)))
        self.assertEqual(get_fiscal_year(date(2024, 12, 31), 30, 11), (date(2024, 12, 1), date(2025, 11, 30)))
        self.assertEqual(get_fiscal_year(date(2024, 10, 31), 30, 11), (date(2023, 12, 1), date(2024, 11, 30)))
        self.assertEqual(get_fiscal_year(date(2024, 10, 31), 30, 12), (date(2023, 12, 31), date(2024, 12, 30)))

        self.assertEqual(get_fiscal_year(date(2024, 10, 31), month=11), (date(2023, 12, 1), date(2024, 11, 30)))
        self.assertEqual(get_fiscal_year(date(2024, 2, 29)), (date(2024, 1, 1), date(2024, 12, 31)))

        self.assertEqual(get_fiscal_year(date(2024, 12, 31), 29, 2), (date(2024, 3, 1), date(2025, 2, 28)))
        self.assertEqual(get_fiscal_year(date(2024, 12, 31), 28, 2), (date(2024, 3, 1), date(2025, 2, 28)))
        self.assertEqual(get_fiscal_year(date(2023, 12, 31), 28, 2), (date(2023, 3, 1), date(2024, 2, 29)))
        self.assertEqual(get_fiscal_year(date(2023, 12, 31), 29, 2), (date(2023, 3, 1), date(2024, 2, 29)))

        self.assertEqual(get_fiscal_year(date(2024, 2, 29), 28, 2), (date(2023, 3, 1), date(2024, 2, 29)))
        self.assertEqual(get_fiscal_year(date(2023, 2, 28), 28, 2), (date(2022, 3, 1), date(2023, 2, 28)))
        self.assertEqual(get_fiscal_year(date(2023, 2, 28), 29, 2), (date(2022, 3, 1), date(2023, 2, 28)))


class TestDateRangeFunction(BaseCase):
    """ Test on date_range generator. """

    def test_date_range_with_naive_datetimes(self):
        """ Check date_range with naive datetimes. """
        start = datetime(1985, 1, 1)
        end = datetime(1986, 1, 1)

        expected = [
            datetime(1985, 1, 1, 0, 0),
            datetime(1985, 2, 1, 0, 0),
            datetime(1985, 3, 1, 0, 0),
            datetime(1985, 4, 1, 0, 0),
            datetime(1985, 5, 1, 0, 0),
            datetime(1985, 6, 1, 0, 0),
            datetime(1985, 7, 1, 0, 0),
            datetime(1985, 8, 1, 0, 0),
            datetime(1985, 9, 1, 0, 0),
            datetime(1985, 10, 1, 0, 0),
            datetime(1985, 11, 1, 0, 0),
            datetime(1985, 12, 1, 0, 0),
            datetime(1986, 1, 1, 0, 0)
        ]

        dates = list(date_range(start, end))
        self.assertEqual(dates, expected)

    def test_date_range_with_date(self):
        """ Check date_range with naive datetimes. """
        start = date(1985, 1, 1)
        end = date(1986, 1, 1)

        expected = [
            date(1985, 1, 1),
            date(1985, 2, 1),
            date(1985, 3, 1),
            date(1985, 4, 1),
            date(1985, 5, 1),
            date(1985, 6, 1),
            date(1985, 7, 1),
            date(1985, 8, 1),
            date(1985, 9, 1),
            date(1985, 10, 1),
            date(1985, 11, 1),
            date(1985, 12, 1),
            date(1986, 1, 1),
        ]

        self.assertEqual(list(date_range(start, end)), expected)

    def test_date_range_with_timezone_aware_datetimes_other_than_utc(self):
        """ Check date_range with timezone-aware datetimes other than UTC."""
        timezone = pytz.timezone('Europe/Brussels')

        start = datetime(1985, 1, 1)
        end = datetime(1986, 1, 1)
        start = timezone.localize(start)
        end = timezone.localize(end)

        expected = [datetime(1985, 1, 1, 0, 0),
                    datetime(1985, 2, 1, 0, 0),
                    datetime(1985, 3, 1, 0, 0),
                    datetime(1985, 4, 1, 0, 0),
                    datetime(1985, 5, 1, 0, 0),
                    datetime(1985, 6, 1, 0, 0),
                    datetime(1985, 7, 1, 0, 0),
                    datetime(1985, 8, 1, 0, 0),
                    datetime(1985, 9, 1, 0, 0),
                    datetime(1985, 10, 1, 0, 0),
                    datetime(1985, 11, 1, 0, 0),
                    datetime(1985, 12, 1, 0, 0),
                    datetime(1986, 1, 1, 0, 0)]

        expected = [timezone.localize(e) for e in expected]

        dates = list(date_range(start, end))
        self.assertEqual(expected, dates)

    def test_date_range_with_mismatching_zones(self):
        """ Check date_range with mismatching zone should raise an exception."""
        start_timezone = pytz.timezone('Europe/Brussels')
        end_timezone = pytz.timezone('America/Recife')

        start = datetime(1985, 1, 1)
        end = datetime(1986, 1, 1)
        start = start_timezone.localize(start)
        end = end_timezone.localize(end)

        with self.assertRaises(ValueError):
            list(date_range(start, end))

    def test_date_range_with_inconsistent_datetimes(self):
        """ Check date_range with a timezone-aware datetime and a naive one."""
        context_timezone = pytz.timezone('Europe/Brussels')

        start = datetime(1985, 1, 1)
        end = datetime(1986, 1, 1)
        end = context_timezone.localize(end)

        with self.assertRaises(ValueError):
            list(date_range(start, end))

    def test_date_range_with_hour(self):
        """ Test date range with hour and naive datetime."""
        start = datetime(2018, 3, 25)
        end = datetime(2018, 3, 26)
        step = relativedelta(hours=1)

        expected = [
            datetime(2018, 3, 25, 0, 0),
            datetime(2018, 3, 25, 1, 0),
            datetime(2018, 3, 25, 2, 0),
            datetime(2018, 3, 25, 3, 0),
            datetime(2018, 3, 25, 4, 0),
            datetime(2018, 3, 25, 5, 0),
            datetime(2018, 3, 25, 6, 0),
            datetime(2018, 3, 25, 7, 0),
            datetime(2018, 3, 25, 8, 0),
            datetime(2018, 3, 25, 9, 0),
            datetime(2018, 3, 25, 10, 0),
            datetime(2018, 3, 25, 11, 0),
            datetime(2018, 3, 25, 12, 0),
            datetime(2018, 3, 25, 13, 0),
            datetime(2018, 3, 25, 14, 0),
            datetime(2018, 3, 25, 15, 0),
            datetime(2018, 3, 25, 16, 0),
            datetime(2018, 3, 25, 17, 0),
            datetime(2018, 3, 25, 18, 0),
            datetime(2018, 3, 25, 19, 0),
            datetime(2018, 3, 25, 20, 0),
            datetime(2018, 3, 25, 21, 0),
            datetime(2018, 3, 25, 22, 0),
            datetime(2018, 3, 25, 23, 0),
            datetime(2018, 3, 26, 0, 0)
        ]

        dates = list(date_range(start, end, step))
        self.assertEqual(dates, expected)

    def test_step_is_positive(self):
        start = datetime(2018, 3, 25)
        end = datetime(2018, 3, 26)
        with self.assertRaises(ValueError):
            list(date_range(start, end, relativedelta()))
        with self.assertRaises(ValueError):
            list(date_range(start, end, relativedelta(hours=-1)))
