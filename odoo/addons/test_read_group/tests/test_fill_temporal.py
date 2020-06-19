# -*- coding: utf-8 -*-
"""Test for fill temporal."""

from odoo.tests import common

class TestFillTemporal(common.TransactionCase):
    """Test for fill temporal.

    This feature is mainly used in graph view. For more informations, read the
    documentation of models's '_read_group_fill_temporal' method.
    """

    def setUp(self):
        super(TestFillTemporal, self).setUp()
        self.Model = self.env['test_read_group.fill_temporal']

    def test_date_range_and_flag(self):
        """Simple date range test, the flag is also tested.

        One of the most simple test. It must verify that dates 'holes' are filled
        only when the fill_temporal flag is set.
        """
        self.Model.create({'date': '1916-08-18', 'value': 2})
        self.Model.create({'date': '1916-10-19', 'value': 3})
        self.Model.create({'date': '1916-12-19', 'value': 5})

        expected = [{
            '__domain': ['&', ('date', '>=', '1916-08-01'), ('date', '<', '1916-09-01')],
            'date': 'August 1916',
            'date_count': 1,
            'value': 2
        }, {
            '__domain': ['&', ('date', '>=', '1916-09-01'), ('date', '<', '1916-10-01')],
            'date': 'September 1916',
            'date_count': 0,
            'value': False
        }, {
            '__domain': ['&', ('date', '>=', '1916-10-01'), ('date', '<', '1916-11-01')],
            'date': 'October 1916',
            'date_count': 1,
            'value': 3
        }, {
            '__domain': ['&', ('date', '>=', '1916-11-01'), ('date', '<', '1916-12-01')],
            'date': 'November 1916',
            'date_count': 0,
            'value': False
        }, {
            '__domain': ['&', ('date', '>=', '1916-12-01'), ('date', '<', '1917-01-01')],
            'date': 'December 1916',
            'date_count': 1,
            'value': 5
        }]

        groups = self.Model.read_group([], fields=['date', 'value'], groupby=['date'])

        self.assertEqual(groups, [group for group in expected if group['date_count']])

        model_fill = self.Model.with_context(fill_temporal=True)
        groups = model_fill.read_group([], fields=['date', 'value'], groupby=['date'])

        self.assertEqual(groups, expected)

    def test_date_range_with_context_timezone(self):
        """Test if date are date_trunced correctly by pgres.

        This test was added in attempt to fix a bug appearing with babel that
        we use to translate the dates. Typically after a daylight saving, A
        whole year was displayed in a graph like this (APR missing and OCT
        appearing twice) :

            JAN   FEB   MAR   MAY   JUN   JUL   AUG   SEP   OCT   OCT   NOV
                           ^^^                                    ^^^
        """
        self.Model.create({'date': '1915-01-01', 'value': 3})
        self.Model.create({'date': '1916-01-01', 'value': 5})

        expected = [{
            '__domain': ['&', ('date', '>=', '1915-01-01'), ('date', '<', '1915-02-01')],
            'date': 'January 1915',
            'date_count': 1,
            'value': 3
        }, {
            '__domain': ['&', ('date', '>=', '1915-02-01'), ('date', '<', '1915-03-01')],
            'date': 'February 1915',
            'date_count': 0,
            'value': False
        }, {
            '__domain': ['&', ('date', '>=', '1915-03-01'), ('date', '<', '1915-04-01')],
            'date': 'March 1915',
            'date_count': 0,
            'value': False
        }, {
            '__domain': ['&', ('date', '>=', '1915-04-01'), ('date', '<', '1915-05-01')],
            'date': 'April 1915',
            'date_count': 0,
            'value': False
        }, {
            '__domain': ['&', ('date', '>=', '1915-05-01'), ('date', '<', '1915-06-01')],
            'date': 'May 1915',
            'date_count': 0,
            'value': False
        }, {
            '__domain': ['&', ('date', '>=', '1915-06-01'), ('date', '<', '1915-07-01')],
            'date': 'June 1915',
            'date_count': 0,
            'value': False
        }, {
            '__domain': ['&', ('date', '>=', '1915-07-01'), ('date', '<', '1915-08-01')],
            'date': 'July 1915',
            'date_count': 0,
            'value': False
        }, {
            '__domain': ['&', ('date', '>=', '1915-08-01'), ('date', '<', '1915-09-01')],
            'date': 'August 1915',
            'date_count': 0,
            'value': False
        }, {
            '__domain': ['&', ('date', '>=', '1915-09-01'), ('date', '<', '1915-10-01')],
            'date': 'September 1915',
            'date_count': 0,
            'value': False
        }, {
            '__domain': ['&', ('date', '>=', '1915-10-01'), ('date', '<', '1915-11-01')],
            'date': 'October 1915',
            'date_count': 0,
            'value': False
        }, {
            '__domain': ['&', ('date', '>=', '1915-11-01'), ('date', '<', '1915-12-01')],
            'date': 'November 1915',
            'date_count': 0,
            'value': False
        }, {
            '__domain': ['&', ('date', '>=', '1915-12-01'), ('date', '<', '1916-01-01')],
            'date': 'December 1915',
            'date_count': 0,
            'value': False
        }, {
            '__domain': ['&', ('date', '>=', '1916-01-01'), ('date', '<', '1916-02-01')],
            'date': 'January 1916',
            'date_count': 1,
            'value': 5
        }]

        # Time Zone                      UTC     UTC DST
        tzs = ["America/Anchorage",  # −09:00    −08:00
               "Europe/Brussels",    # +01:00    +02:00
               "Pacific/Kwajalein"]  # +12:00    +12:00

        for tz in tzs:
            model_fill = self.Model.with_context(tz=tz, fill_temporal=True)
            groups = model_fill.read_group([], fields=['date', 'value'], groupby=['date'])
            self.assertEqual(groups, expected)

    def test_only_with_only_null_date(self):
        """We should have the same result when fill_temporal is set or not."""
        self.Model.create({'date': False, 'value': 13})
        self.Model.create({'date': False, 'value': 11})
        self.Model.create({'date': False, 'value': 17})

        expected = [{'__domain': [('date', '=', False)],
                     'date_count': 3,
                     'value': 41,
                     'date': False}]

        groups = self.Model.read_group([], fields=['date', 'value'], groupby=['date'])
        self.assertEqual(groups, expected)

        model_fill = self.Model.with_context(fill_temporal=True)
        groups = model_fill.read_group([], fields=['date', 'value'], groupby=['date'])
        self.assertEqual(groups, expected)

    def test_date_range_and_null_date(self):
        """Test data with null and non-null dates."""
        self.Model.create({'date': '1916-08-19', 'value': 4})
        self.Model.create({'date': False, 'value': 13})
        self.Model.create({'date': '1916-10-18', 'value': 5})
        self.Model.create({'date': '1916-08-18', 'value': 3})
        self.Model.create({'date': '1916-10-19', 'value': 4})
        self.Model.create({'date': False, 'value': 11})

        expected = [{
            '__domain': ['&', ('date', '>=', '1916-08-01'), ('date', '<', '1916-09-01')],
            'date': 'August 1916',
            'date_count': 2,
            'value': 7
        }, {
            '__domain': ['&', ('date', '>=', '1916-09-01'), ('date', '<', '1916-10-01')],
            'date': 'September 1916',
            'date_count': 0,
            'value': 0
        }, {
            '__domain': ['&', ('date', '>=', '1916-10-01'), ('date', '<', '1916-11-01')],
            'date': 'October 1916',
            'date_count': 2,
            'value': 9
        }, {
            '__domain': [('date', '=', False)],
            'date': False,
            'date_count': 2,
            'value': 24
        }]

        groups = self.Model.read_group([], fields=['date', 'value'], groupby=['date'])

        self.assertEqual(groups, [group for group in expected if group['date_count']])

        model_fill = self.Model.with_context(fill_temporal=True)
        groups = model_fill.read_group([], fields=['date', 'value'], groupby=['date'])

        self.assertEqual(groups, expected)

    def test_order_date_desc(self):
        """Test if changing Model._order has influence on the result."""
        self.Model.create({'date': '1916-08-18', 'value': 3})
        self.Model.create({'date': '1916-08-19', 'value': 4})
        self.Model.create({'date': '1916-10-18', 'value': 5})
        self.Model.create({'date': '1916-10-19', 'value': 4})
        self.patch(type(self.Model), '_order', 'date desc')

        expected = [{
            '__domain': ['&', ('date', '>=', '1916-08-01'), ('date', '<', '1916-09-01')],
            'date': 'August 1916',
            'date_count': 2,
            'value': 7
        }, {
            '__domain': ['&', ('date', '>=', '1916-09-01'), ('date', '<', '1916-10-01')],
            'date': 'September 1916',
            'date_count': 0,
            'value': False
        }, {
            '__domain': ['&', ('date', '>=', '1916-10-01'), ('date', '<', '1916-11-01')],
            'date': 'October 1916',
            'date_count': 2,
            'value': 9
        }]

        groups = self.Model.read_group([], fields=['date', 'value'], groupby=['date'])
        self.assertEqual(groups, [group for group in expected if group['date_count']])

        model_fill = self.Model.with_context(fill_temporal=True)
        groups = model_fill.read_group([], fields=['date', 'value'], groupby=['date'])
        self.assertEqual(groups, expected)

    def test_timestamp_without_timezone(self):
        """Test datetimes.

        Date stored with an hour inside the Odoo model are processed as timestamp
        without timezone by postgres.
        """
        self.Model.create({'datetime': '1916-08-19 01:30:00', 'value': 7})
        self.Model.create({'datetime': False, 'value': 13})
        self.Model.create({'datetime': '1916-10-18 02:30:00', 'value': 5})
        self.Model.create({'datetime': '1916-08-18 01:50:00', 'value': 3})
        self.Model.create({'datetime': False, 'value': 11})
        self.Model.create({'datetime': '1916-10-19 23:59:59', 'value': 2})
        self.Model.create({'datetime': '1916-10-19', 'value': 19})

        expected = [{
            '__domain': ['&',
                      ('datetime', '>=', '1916-08-01 00:00:00'),
                      ('datetime', '<', '1916-09-01 00:00:00')],
            'datetime': 'August 1916',
            'datetime_count': 2,
            'value': 10
        }, {
            '__domain': ['&',
                      ('datetime', '>=', '1916-09-01 00:00:00'),
                      ('datetime', '<', '1916-10-01 00:00:00')],
            'datetime': 'September 1916',
            'datetime_count': 0,
            'value': False
        }, {
            '__domain': ['&',
                      ('datetime', '>=', '1916-10-01 00:00:00'),
                      ('datetime', '<', '1916-11-01 00:00:00')],
            'datetime': 'October 1916',
            'datetime_count': 3,
            'value': 26
        }, {
            '__domain': [('datetime', '=', False)],
            'datetime': False,
            'datetime_count': 2,
            'value': 24
        }]

        groups = self.Model.read_group([], fields=['datetime', 'value'], groupby=['datetime'])

        self.assertEqual(groups, [group for group in expected if group['datetime_count']])

        model_fill = self.Model.with_context(fill_temporal=True)
        groups = model_fill.read_group([], fields=['datetime', 'value'], groupby=['datetime'])

        self.assertEqual(groups, expected)

    def test_with_datetimes_and_groupby_per_hour(self):
        """Test with datetimes and groupby per hour.

        Test if datetimes are filled correctly when grouping by hours instead of
        months.
        """
        self.Model.create({'datetime': '1916-01-01 01:30:00', 'value': 2})
        self.Model.create({'datetime': '1916-01-01 01:50:00', 'value': 8})
        self.Model.create({'datetime': '1916-01-01 02:30:00', 'value': 3})
        self.Model.create({'datetime': '1916-01-01 13:50:00', 'value': 5})
        self.Model.create({'datetime': '1916-01-01 23:50:00', 'value': 7})

        expected = [{
            '__domain': ['&',
                         ('datetime', '>=', '1916-01-01 01:00:00'),
                         ('datetime', '<', '1916-01-01 02:00:00')],
            'datetime:hour': '01:00 01 Jan',
            'datetime_count': 2,
            'value': 10
        }, {
            '__domain': ['&',
                         ('datetime', '>=', '1916-01-01 02:00:00'),
                         ('datetime', '<', '1916-01-01 03:00:00')],
            'datetime:hour': '02:00 01 Jan',
            'datetime_count': 1,
            'value': 3
        }, {
            '__domain': ['&',
                         ('datetime', '>=', '1916-01-01 03:00:00'),
                         ('datetime', '<', '1916-01-01 04:00:00')],
            'datetime:hour': '03:00 01 Jan',
            'datetime_count': 0,
            'value': False
        }, {
            '__domain': ['&',
                         ('datetime', '>=', '1916-01-01 04:00:00'),
                         ('datetime', '<', '1916-01-01 05:00:00')],
            'datetime:hour': '04:00 01 Jan',
            'datetime_count': 0,
            'value': False
        }, {
            '__domain': ['&',
                         ('datetime', '>=', '1916-01-01 05:00:00'),
                         ('datetime', '<', '1916-01-01 06:00:00')],
            'datetime:hour': '05:00 01 Jan',
            'datetime_count': 0,
            'value': False
        }, {
            '__domain': ['&',
                         ('datetime', '>=', '1916-01-01 06:00:00'),
                         ('datetime', '<', '1916-01-01 07:00:00')],
            'datetime:hour': '06:00 01 Jan',
            'datetime_count': 0,
            'value': False
        }, {
            '__domain': ['&',
                         ('datetime', '>=', '1916-01-01 07:00:00'),
                         ('datetime', '<', '1916-01-01 08:00:00')],
            'datetime:hour': '07:00 01 Jan',
            'datetime_count': 0,
            'value': False
        }, {
            '__domain': ['&',
                         ('datetime', '>=', '1916-01-01 08:00:00'),
                         ('datetime', '<', '1916-01-01 09:00:00')],
            'datetime:hour': '08:00 01 Jan',
            'datetime_count': 0,
            'value': False
        }, {
            '__domain': ['&',
                         ('datetime', '>=', '1916-01-01 09:00:00'),
                         ('datetime', '<', '1916-01-01 10:00:00')],
            'datetime:hour': '09:00 01 Jan',
            'datetime_count': 0,
            'value': False
        }, {
            '__domain': ['&',
                         ('datetime', '>=', '1916-01-01 10:00:00'),
                         ('datetime', '<', '1916-01-01 11:00:00')],
            'datetime:hour': '10:00 01 Jan',
            'datetime_count': 0,
            'value': False
        }, {
            '__domain': ['&',
                         ('datetime', '>=', '1916-01-01 11:00:00'),
                         ('datetime', '<', '1916-01-01 12:00:00')],
            'datetime:hour': '11:00 01 Jan',
            'datetime_count': 0,
            'value': False
        }, {
            '__domain': ['&',
                         ('datetime', '>=', '1916-01-01 12:00:00'),
                         ('datetime', '<', '1916-01-01 13:00:00')],
            'datetime:hour': '12:00 01 Jan',
            'datetime_count': 0,
            'value': False
        }, {
            '__domain': ['&',
                         ('datetime', '>=', '1916-01-01 13:00:00'),
                         ('datetime', '<', '1916-01-01 14:00:00')],
            'datetime:hour': '01:00 01 Jan',
            'datetime_count': 1,
            'value': 5
        }, {
            '__domain': ['&',
                         ('datetime', '>=', '1916-01-01 14:00:00'),
                         ('datetime', '<', '1916-01-01 15:00:00')],
            'datetime:hour': '02:00 01 Jan',
            'datetime_count': 0,
            'value': False
        }, {
            '__domain': ['&',
                         ('datetime', '>=', '1916-01-01 15:00:00'),
                         ('datetime', '<', '1916-01-01 16:00:00')],
            'datetime:hour': '03:00 01 Jan',
            'datetime_count': 0,
            'value': False
        }, {
            '__domain': ['&',
                         ('datetime', '>=', '1916-01-01 16:00:00'),
                         ('datetime', '<', '1916-01-01 17:00:00')],
            'datetime:hour': '04:00 01 Jan',
            'datetime_count': 0,
            'value': False
        }, {
            '__domain': ['&',
                         ('datetime', '>=', '1916-01-01 17:00:00'),
                         ('datetime', '<', '1916-01-01 18:00:00')],
            'datetime:hour': '05:00 01 Jan',
            'datetime_count': 0,
            'value': False
        }, {
            '__domain': ['&',
                         ('datetime', '>=', '1916-01-01 18:00:00'),
                         ('datetime', '<', '1916-01-01 19:00:00')],
            'datetime:hour': '06:00 01 Jan',
            'datetime_count': 0,
            'value': False
        }, {
            '__domain': ['&',
                         ('datetime', '>=', '1916-01-01 19:00:00'),
                         ('datetime', '<', '1916-01-01 20:00:00')],
            'datetime:hour': '07:00 01 Jan',
            'datetime_count': 0,
            'value': False
        }, {
            '__domain': ['&',
                         ('datetime', '>=', '1916-01-01 20:00:00'),
                         ('datetime', '<', '1916-01-01 21:00:00')],
            'datetime:hour': '08:00 01 Jan',
            'datetime_count': 0,
            'value': False
        }, {
            '__domain': ['&',
                         ('datetime', '>=', '1916-01-01 21:00:00'),
                         ('datetime', '<', '1916-01-01 22:00:00')],
            'datetime:hour': '09:00 01 Jan',
            'datetime_count': 0,
            'value': False
        }, {
            '__domain': ['&',
                         ('datetime', '>=', '1916-01-01 22:00:00'),
                         ('datetime', '<', '1916-01-01 23:00:00')],
            'datetime:hour': '10:00 01 Jan',
            'datetime_count': 0,
            'value': False
        }, {
            '__domain': ['&',
                         ('datetime', '>=', '1916-01-01 23:00:00'),
                         ('datetime', '<', '1916-01-02 00:00:00')],
            'datetime:hour': '11:00 01 Jan',
            'datetime_count': 1,
            'value': 7
        }]

        model_fill = self.Model.with_context(fill_temporal=True)
        groups = model_fill.read_group([], fields=['datetime', 'value'], groupby=['datetime:hour'])

        self.assertEqual(groups, expected)

    def test_hour_with_timezones(self):
        """Test hour with timezones.

        What we do here is similar to test_with_datetimes_and_groupby_per_hour
        but with a timezone in the user context.
        """
        self.Model.create({'datetime': '1915-12-31 22:30:00', 'value': 2})
        self.Model.create({'datetime': '1916-01-01 03:30:00', 'value': 3})

        expected = [{
            '__domain': ['&',
                         ('datetime', '>=', '1915-12-31 22:00:00'),
                         ('datetime', '<', '1915-12-31 23:00:00')],
            'datetime:hour': '04:00 01 Jan',
            'datetime_count': 1,
            'value': 2
        }, {
            '__domain': ['&',
                         ('datetime', '>=', '1915-12-31 23:00:00'),
                         ('datetime', '<', '1916-01-01 00:00:00')],
            'datetime:hour': '05:00 01 Jan',
            'datetime_count': 0,
            'value': False
        }, {
            '__domain': ['&',
                         ('datetime', '>=', '1916-01-01 00:00:00'),
                         ('datetime', '<', '1916-01-01 01:00:00')],
            'datetime:hour': '06:00 01 Jan',
            'datetime_count': 0,
            'value': False
        }, {
            '__domain': ['&',
                         ('datetime', '>=', '1916-01-01 01:00:00'),
                         ('datetime', '<', '1916-01-01 02:00:00')],
            'datetime:hour': '07:00 01 Jan',
            'datetime_count': 0,
            'value': False
        }, {
            '__domain': ['&',
                         ('datetime', '>=', '1916-01-01 02:00:00'),
                         ('datetime', '<', '1916-01-01 03:00:00')],
            'datetime:hour': '08:00 01 Jan',
            'datetime_count': 0,
            'value': False
        }, {
            '__domain': ['&',
                         ('datetime', '>=', '1916-01-01 03:00:00'),
                         ('datetime', '<', '1916-01-01 04:00:00')],
            'datetime:hour': '09:00 01 Jan',
            'datetime_count': 1,
            'value': 3
        }]

        model_fill = self.Model.with_context(tz='Asia/Hovd', fill_temporal=True)
        groups = model_fill.read_group([], fields=['datetime', 'value'],
                                       groupby=['datetime:hour'])

        self.assertEqual(groups, expected)

    def test_egde_fx_tz(self):
        """We test if different edge effect by using a different timezone from the user context

        Suppose a user resident near Hovd, a city in Mongolia. he sells a product
        at exacltly 4:00 AM on 1st January 2018. Using its context, that datetime
        is previously converted to UTC time by the ORM so as being stored properly
        inside the datebase. We are in winter time so 'Asia/Hovd' is UTC+7 :

                 '2018-01-01 04:00:00'   -->  '2017-12-31 21:00:00'

        If that same user groups by datetime, we must ensure that the last
        displayed date is in January and not in December.
        """
        self.Model.create({'datetime': '2017-12-31 21:00:00', 'value': 42})

        expected = [{
            '__domain': ['&',
                         ('datetime', '>=', '2017-12-31 17:00:00'),
                         ('datetime', '<', '2018-01-31 17:00:00')],
            'datetime': 'January 2018',
            'datetime_count': 1,
            'value': 42
        }]

        model_fill = self.Model.with_context(tz='Asia/Hovd', fill_temporal=True)
        groups = model_fill.read_group([], fields=['datetime', 'value'], groupby=['datetime'])

        self.assertEqual(groups, expected)
