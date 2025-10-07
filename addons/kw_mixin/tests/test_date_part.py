import datetime

from odoo.tests.common import TransactionCase


class TestDatePart(TransactionCase):

    def test_100_year_mixin(self):
        get_year = self.env['kw.year.mixin'].get_year

        self.assertEqual(get_year('2022-05-15'), 2022)

    def test_200_dow_mixin(self):
        get_isoweekday = self.env['kw.dow.mixin'].get_isoweekday
        get_weekday_name = self.env['kw.dow.mixin'].get_weekday_name
        get_isoweekday_name = self.env['kw.dow.mixin'].get_isoweekday_name

        self.assertEqual(get_isoweekday(
            datetime.datetime(2022, 8, 18).date()), 4)
        self.assertEqual(get_isoweekday(datetime.datetime(2022, 8, 18)), 4)
        self.assertEqual(get_isoweekday('2022-08-18'), 4)
        self.assertEqual(get_isoweekday(2022), False)

        self.assertEqual(get_weekday_name(4), 'Thursday')
        self.assertEqual(get_isoweekday_name('2022-08-18'), 'Thursday')

    def test_300_week_mixin(self):
        get_week = self.env['kw.week.mixin'].get_week
        get_monday = self.env['kw.week.mixin'].get_monday

        self.assertEqual(get_week(
            datetime.datetime(2022, 8, 18).date()), 33)
        self.assertEqual(get_week(datetime.datetime(2022, 8, 18)), 33)
        self.assertEqual(get_week('2022-08-18'), 33)
        self.assertEqual(get_week(2022), False)

        self.assertEqual(get_monday(2022, 33), datetime.datetime(2022, 8, 15))
        self.assertEqual(get_monday(2021, 33), datetime.datetime(2021, 8, 16))
        self.assertEqual(get_monday(2020, 33), datetime.datetime(2020, 8, 10))
        self.assertEqual(get_monday(2019, 33), datetime.datetime(2019, 8, 12))
        self.assertEqual(get_monday(2018, 33), datetime.datetime(2018, 8, 13))
        self.assertEqual(get_monday(2017, 33), datetime.datetime(2017, 8, 14))
        self.assertEqual(get_monday(2016, 33), datetime.datetime(2016, 8, 15))
        self.assertEqual(get_monday(2015, 33), datetime.datetime(2015, 8, 10))
        self.assertEqual(get_monday(2014, 33), datetime.datetime(2014, 8, 11))
        self.assertEqual(get_monday(2013, 33), datetime.datetime(2013, 8, 12))
        self.assertEqual(get_monday(2012, 33), datetime.datetime(2012, 8, 13))
        self.assertEqual(get_monday(2011, 33), datetime.datetime(2011, 8, 15))

    def test_400_month_mixin(self):
        get_month = self.env['kw.month.mixin'].get_month

        self.assertEqual(get_month('2022-05-15'), 5)

    def test_500_quarter_mixin(self):
        get_quarter = self.env['kw.quarter.mixin'].get_quarter

        self.assertEqual(get_quarter('2022-05-15'), 2)
        self.assertEqual(get_quarter('2022-08-15'), 3)
