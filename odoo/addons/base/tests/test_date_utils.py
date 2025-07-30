# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import date, datetime, time, timedelta, timezone
from functools import partial

import pytz
from dateutil.relativedelta import relativedelta
from freezegun import freeze_time

from odoo.tests import BaseCase, TransactionCase
from odoo.tools.date_utils import (
    add,
    date_range,
    end_of,
    get_fiscal_year,
    localized,
    parse_date,
    parse_iso_date,
    start_of,
    subtract,
    to_timezone,
)


class TestDateUtils(TransactionCase):

    @freeze_time('2024-05-01 14:00:00')
    def test_localized_timezone(self):
        dt = datetime.now()
        self.assertIsNotNone(localized(dt).tzinfo)
        tz = timezone(timedelta(hours=5))
        self.assertIs(localized(dt.astimezone(tz)).tzinfo, tz)

        dtz = dt.astimezone(tz)
        self.assertEqual(dtz.hour, 19)
        self.assertIs(dtz.tzinfo, tz)
        self.assertEqual(to_timezone(None)(dtz), dt)
        self.assertEqual(to_timezone(tz)(dt), dtz)

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

    def test_offset_utils(self):
        """ test date/datetime fields helpers """
        d = date(2077, 10, 23)
        dt = datetime(2077, 10, 23, 9, 42)

        # addition
        self.assertEqual(add(d, days=5), date(2077, 10, 28))
        self.assertEqual(add(dt, seconds=10), datetime(2077, 10, 23, 9, 42, 10))

        # subtraction
        self.assertEqual(subtract(d, months=1), date(2077, 9, 23))
        self.assertEqual(subtract(dt, hours=2), datetime(2077, 10, 23, 7, 42, 0))

        # start_of
        # year
        self.assertEqual(start_of(d, 'year'), date(2077, 1, 1))
        self.assertEqual(start_of(dt, 'year'), datetime(2077, 1, 1))

        # quarter
        q1 = date(2077, 1, 1)
        q2 = date(2077, 4, 1)
        q3 = date(2077, 7, 1)
        q4 = date(2077, 10, 1)
        self.assertEqual(start_of(d.replace(month=3), 'quarter'), q1)
        self.assertEqual(start_of(d.replace(month=5), 'quarter'), q2)
        self.assertEqual(start_of(d.replace(month=7), 'quarter'), q3)
        self.assertEqual(start_of(d, 'quarter'), q4)
        self.assertEqual(start_of(dt, 'quarter'), datetime.combine(q4, time.min))

        # month
        self.assertEqual(start_of(d, 'month'), date(2077, 10, 1))
        self.assertEqual(start_of(dt, 'month'), datetime(2077, 10, 1))

        # week
        self.assertEqual(start_of(d, 'week'), date(2077, 10, 18))
        self.assertEqual(start_of(dt, 'week'), datetime(2077, 10, 18))

        # day
        self.assertEqual(start_of(d, 'day'), d)
        self.assertEqual(start_of(dt, 'day'), dt.replace(hour=0, minute=0, second=0))

        # hour
        with self.assertRaises(ValueError):
            start_of(d, 'hour')
        self.assertEqual(start_of(dt, 'hour'), dt.replace(minute=0, second=0))

        # invalid
        with self.assertRaises(ValueError):
            start_of(dt, 'poop')

        # end_of
        # year
        self.assertEqual(end_of(d, 'year'), d.replace(month=12, day=31))
        self.assertEqual(end_of(dt, 'year'),
                         datetime.combine(d.replace(month=12, day=31), time.max))

        # quarter
        q1 = date(2077, 3, 31)
        q2 = date(2077, 6, 30)
        q3 = date(2077, 9, 30)
        q4 = date(2077, 12, 31)
        self.assertEqual(end_of(d.replace(month=2), 'quarter'), q1)
        self.assertEqual(end_of(d.replace(month=4), 'quarter'), q2)
        self.assertEqual(end_of(d.replace(month=9), 'quarter'), q3)
        self.assertEqual(end_of(d, 'quarter'), q4)
        self.assertEqual(end_of(dt, 'quarter'), datetime.combine(q4, time.max))

        # month
        self.assertEqual(end_of(d, 'month'), d.replace(day=31))
        self.assertEqual(end_of(dt, 'month'),
                         datetime.combine(date(2077, 10, 31), time.max))

        # week
        self.assertEqual(end_of(d, 'week'), date(2077, 10, 24))
        self.assertEqual(end_of(dt, 'week'),
                         datetime.combine(datetime(2077, 10, 24), time.max))

        # day
        self.assertEqual(end_of(d, 'day'), d)
        self.assertEqual(end_of(dt, 'day'), datetime.combine(dt, time.max))

        # hour
        with self.assertRaises(ValueError):
            end_of(d, 'hour')
        self.assertEqual(end_of(dt, 'hour'),
                         datetime.combine(dt, time.max).replace(hour=dt.hour))

        # invalid
        with self.assertRaises(ValueError):
            end_of(dt, 'crap')

    def test_parse_iso_date(self):
        self.assertEqual(parse_iso_date('2024-01-05'), date(2024, 1, 5))
        self.assertEqual(parse_iso_date('2024-01-05 00:30:00'), datetime(2024, 1, 5, 0, 30))
        self.assertEqual(parse_iso_date('2024-01-05 00:00:00'), datetime(2024, 1, 5))

        with self.assertRaises(ValueError):
            parse_iso_date('2024-01-05 00:00:00+02:00')

        with self.assertRaises(ValueError):
            parse_iso_date('123')
        with self.assertRaises(ValueError):
            parse_iso_date('2024-14-05')
        with self.assertRaises(ValueError):
            parse_iso_date('2024-14-05 11')

    def test_parse_date(self):
        env = self.env
        self.assertEqual(parse_date('2024-01-05', env), date(2024, 1, 5))
        self.assertEqual(parse_date('2024-01-05 00:30:00', env), datetime(2024, 1, 5, 0, 30))
        self.assertEqual(parse_date('2024-01-05 00:00:00', env), datetime(2024, 1, 5))

        with self.assertRaises(ValueError):
            parse_date('2024-01-05 00:00:00+02:00', env)

    @freeze_time('2024-01-05 13:05:00')
    def test_parse_date_relative_utc(self):
        self.env["res.lang"]._lang_get(self.env.user.lang).week_start = "1"
        env = self.env(context={'tz': 'UTC'})
        parse = partial(parse_date, env=env)

        self.assertEqual(parse('=1d'), datetime(2024, 1, 1))
        self.assertEqual(parse('=2000y'), datetime(2000, 1, 5))
        self.assertEqual(parse('+3d'), datetime(2024, 1, 8, 13, 5))
        self.assertEqual(parse('-1m'), datetime(2023, 12, 5, 13, 5))
        self.assertEqual(parse('+3d +1w -1m -2y'), datetime(2021, 12, 15, 13, 5))

        self.assertEqual(parse('-02H -15M'), datetime(2024, 1, 5, 10, 50))
        self.assertEqual(parse('=02H =15M'), datetime(2024, 1, 5, 2, 15))
        self.assertEqual(parse('+02H +15M'), datetime(2024, 1, 5, 15, 20))
        self.assertEqual(parse('=11d +2H +15M'), datetime(2024, 1, 11, 2, 15))

        self.assertEqual(parse('today'), date(2024, 1, 5))
        self.assertEqual(parse('today +1w'), date(2024, 1, 12))

        # 2024-01-05 is Friday
        self.assertEqual(parse('=monday'), datetime(2024, 1, 1))
        self.assertEqual(parse('=sunday'), datetime(2024, 1, 7))
        # next Monday, previous Monday
        self.assertEqual(parse('+monday'), datetime(2024, 1, 8, 13, 5))
        self.assertEqual(parse('-monday'), datetime(2024, 1, 1, 13, 5))
        # next Friday, previous Friday -> same Friday!
        self.assertEqual(parse('+friday'), datetime(2024, 1, 5, 13, 5))
        self.assertEqual(parse('-friday'), datetime(2024, 1, 5, 13, 5))
        # actual next Friday, actual previous Friday
        self.assertEqual(parse('+1d +friday'), datetime(2024, 1, 12, 13, 5))
        self.assertEqual(parse('-1d -friday'), datetime(2023, 12, 29, 13, 5))
        # next Sunday, previous Sunday
        self.assertEqual(parse('+sunday'), datetime(2024, 1, 7, 13, 5))
        self.assertEqual(parse('-sunday'), datetime(2023, 12, 31, 13, 5))

        # week_start = 1 (Monday)
        self.assertEqual(parse('=week_start'), datetime(2024, 1, 1))
        self.assertEqual(parse('+week_start'), datetime(2024, 1, 8, 13, 5))
        self.assertEqual(parse('-week_start'), datetime(2024, 1, 1, 13, 5))

        # week_start = 6 (Saturday)
        self.env["res.lang"]._lang_get(self.env.user.lang).week_start = "6"
        self.assertEqual(parse('=week_start'), datetime(2023, 12, 30))
        self.assertEqual(parse('+week_start'), datetime(2024, 1, 6, 13, 5))
        self.assertEqual(parse('-week_start'), datetime(2023, 12, 30, 13, 5))
        self.assertEqual(parse('=sunday'), datetime(2023, 12, 31))

        # week_start = 5 (Friday)
        self.env["res.lang"]._lang_get(self.env.user.lang).week_start = "5"
        self.assertEqual(parse('=week_start'), datetime(2024, 1, 5))
        self.assertEqual(parse('+week_start'), datetime(2024, 1, 5, 13, 5))
        self.assertEqual(parse('-week_start'), datetime(2024, 1, 5, 13, 5))
        self.assertEqual(parse('=thursday'), datetime(2024, 1, 11))
        self.assertEqual(parse('=friday'), datetime(2024, 1, 5))

    @freeze_time('2024-01-05 13:05:00')
    def test_parse_date_relative_tz(self):
        env = self.env(context={'tz': 'Etc/GMT-1'})
        parse = partial(parse_date, env=env)

        self.assertEqual(parse('now'), datetime(2024, 1, 5, 13, 5))
        self.assertEqual(parse('=5H'), datetime(2024, 1, 5, 4))
        self.assertEqual(parse('-55M'), datetime(2024, 1, 5, 12, 10))

        self.assertEqual(parse('today'), date(2024, 1, 5))
        with freeze_time('2024-01-04 23:05:00'):
            self.assertEqual(parse('today'), date(2024, 1, 5))


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
