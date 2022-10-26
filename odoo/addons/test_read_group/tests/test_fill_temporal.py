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
            '__range': {'date': {'from': '1916-08-01', 'to': '1916-09-01'}},
            'date': 'August 1916',
            'date_count': 1,
            'value': 2
        }, {
            '__domain': ['&', ('date', '>=', '1916-09-01'), ('date', '<', '1916-10-01')],
            '__range': {'date': {'from': '1916-09-01', 'to': '1916-10-01'}},
            'date': 'September 1916',
            'date_count': 0,
            'value': False
        }, {
            '__domain': ['&', ('date', '>=', '1916-10-01'), ('date', '<', '1916-11-01')],
            '__range': {'date': {'from': '1916-10-01', 'to': '1916-11-01'}},
            'date': 'October 1916',
            'date_count': 1,
            'value': 3
        }, {
            '__domain': ['&', ('date', '>=', '1916-11-01'), ('date', '<', '1916-12-01')],
            '__range': {'date': {'from': '1916-11-01', 'to': '1916-12-01'}},
            'date': 'November 1916',
            'date_count': 0,
            'value': False
        }, {
            '__domain': ['&', ('date', '>=', '1916-12-01'), ('date', '<', '1917-01-01')],
            '__range': {'date': {'from': '1916-12-01', 'to': '1917-01-01'}},
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
            '__range': {'date': {'from': '1915-01-01', 'to': '1915-02-01'}},
            'date': 'January 1915',
            'date_count': 1,
            'value': 3
        }, {
            '__domain': ['&', ('date', '>=', '1915-02-01'), ('date', '<', '1915-03-01')],
            '__range': {'date': {'from': '1915-02-01', 'to': '1915-03-01'}},
            'date': 'February 1915',
            'date_count': 0,
            'value': False
        }, {
            '__domain': ['&', ('date', '>=', '1915-03-01'), ('date', '<', '1915-04-01')],
            '__range': {'date': {'from': '1915-03-01', 'to': '1915-04-01'}},
            'date': 'March 1915',
            'date_count': 0,
            'value': False
        }, {
            '__domain': ['&', ('date', '>=', '1915-04-01'), ('date', '<', '1915-05-01')],
            '__range': {'date': {'from': '1915-04-01', 'to': '1915-05-01'}},
            'date': 'April 1915',
            'date_count': 0,
            'value': False
        }, {
            '__domain': ['&', ('date', '>=', '1915-05-01'), ('date', '<', '1915-06-01')],
            '__range': {'date': {'from': '1915-05-01', 'to': '1915-06-01'}},
            'date': 'May 1915',
            'date_count': 0,
            'value': False
        }, {
            '__domain': ['&', ('date', '>=', '1915-06-01'), ('date', '<', '1915-07-01')],
            '__range': {'date': {'from': '1915-06-01', 'to': '1915-07-01'}},
            'date': 'June 1915',
            'date_count': 0,
            'value': False
        }, {
            '__domain': ['&', ('date', '>=', '1915-07-01'), ('date', '<', '1915-08-01')],
            '__range': {'date': {'from': '1915-07-01', 'to': '1915-08-01'}},
            'date': 'July 1915',
            'date_count': 0,
            'value': False
        }, {
            '__domain': ['&', ('date', '>=', '1915-08-01'), ('date', '<', '1915-09-01')],
            '__range': {'date': {'from': '1915-08-01', 'to': '1915-09-01'}},
            'date': 'August 1915',
            'date_count': 0,
            'value': False
        }, {
            '__domain': ['&', ('date', '>=', '1915-09-01'), ('date', '<', '1915-10-01')],
            '__range': {'date': {'from': '1915-09-01', 'to': '1915-10-01'}},
            'date': 'September 1915',
            'date_count': 0,
            'value': False
        }, {
            '__domain': ['&', ('date', '>=', '1915-10-01'), ('date', '<', '1915-11-01')],
            '__range': {'date': {'from': '1915-10-01', 'to': '1915-11-01'}},
            'date': 'October 1915',
            'date_count': 0,
            'value': False
        }, {
            '__domain': ['&', ('date', '>=', '1915-11-01'), ('date', '<', '1915-12-01')],
            '__range': {'date': {'from': '1915-11-01', 'to': '1915-12-01'}},
            'date': 'November 1915',
            'date_count': 0,
            'value': False
        }, {
            '__domain': ['&', ('date', '>=', '1915-12-01'), ('date', '<', '1916-01-01')],
            '__range': {'date': {'from': '1915-12-01', 'to': '1916-01-01'}},
            'date': 'December 1915',
            'date_count': 0,
            'value': False
        }, {
            '__domain': ['&', ('date', '>=', '1916-01-01'), ('date', '<', '1916-02-01')],
            '__range': {'date': {'from': '1916-01-01', 'to': '1916-02-01'}},
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
                     '__range': {'date': False},
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
            '__range': {'date': {'from': '1916-08-01', 'to': '1916-09-01'}},
            'date': 'August 1916',
            'date_count': 2,
            'value': 7
        }, {
            '__domain': ['&', ('date', '>=', '1916-09-01'), ('date', '<', '1916-10-01')],
            '__range': {'date': {'from': '1916-09-01', 'to': '1916-10-01'}},
            'date': 'September 1916',
            'date_count': 0,
            'value': 0
        }, {
            '__domain': ['&', ('date', '>=', '1916-10-01'), ('date', '<', '1916-11-01')],
            '__range': {'date': {'from': '1916-10-01', 'to': '1916-11-01'}},
            'date': 'October 1916',
            'date_count': 2,
            'value': 9
        }, {
            '__domain': [('date', '=', False)],
            '__range': {'date': False},
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
            '__range': {'date': {'from': '1916-08-01', 'to': '1916-09-01'}},
            'date': 'August 1916',
            'date_count': 2,
            'value': 7
        }, {
            '__domain': ['&', ('date', '>=', '1916-09-01'), ('date', '<', '1916-10-01')],
            '__range': {'date': {'from': '1916-09-01', 'to': '1916-10-01'}},
            'date': 'September 1916',
            'date_count': 0,
            'value': False
        }, {
            '__domain': ['&', ('date', '>=', '1916-10-01'), ('date', '<', '1916-11-01')],
            '__range': {'date': {'from': '1916-10-01', 'to': '1916-11-01'}},
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
            '__range': {'datetime': {'from': '1916-08-01 00:00:00', 'to': '1916-09-01 00:00:00'}},
            'datetime': 'August 1916',
            'datetime_count': 2,
            'value': 10
        }, {
            '__domain': ['&',
                      ('datetime', '>=', '1916-09-01 00:00:00'),
                      ('datetime', '<', '1916-10-01 00:00:00')],
            '__range': {'datetime': {'from': '1916-09-01 00:00:00', 'to': '1916-10-01 00:00:00'}},
            'datetime': 'September 1916',
            'datetime_count': 0,
            'value': False
        }, {
            '__domain': ['&',
                      ('datetime', '>=', '1916-10-01 00:00:00'),
                      ('datetime', '<', '1916-11-01 00:00:00')],
            '__range': {'datetime': {'from': '1916-10-01 00:00:00', 'to': '1916-11-01 00:00:00'}},
            'datetime': 'October 1916',
            'datetime_count': 3,
            'value': 26
        }, {
            '__domain': [('datetime', '=', False)],
            '__range': {'datetime': False},
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
            '__range': {'datetime:hour': {'from': '1916-01-01 01:00:00', 'to': '1916-01-01 02:00:00'}},
            'datetime:hour': '01:00 01 Jan',
            'datetime_count': 2,
            'value': 10
        }, {
            '__domain': ['&',
                         ('datetime', '>=', '1916-01-01 02:00:00'),
                         ('datetime', '<', '1916-01-01 03:00:00')],
            '__range': {'datetime:hour': {'from': '1916-01-01 02:00:00', 'to': '1916-01-01 03:00:00'}},
            'datetime:hour': '02:00 01 Jan',
            'datetime_count': 1,
            'value': 3
        }, {
            '__domain': ['&',
                         ('datetime', '>=', '1916-01-01 03:00:00'),
                         ('datetime', '<', '1916-01-01 04:00:00')],
            '__range': {'datetime:hour': {'from': '1916-01-01 03:00:00', 'to': '1916-01-01 04:00:00'}},
            'datetime:hour': '03:00 01 Jan',
            'datetime_count': 0,
            'value': False
        }, {
            '__domain': ['&',
                         ('datetime', '>=', '1916-01-01 04:00:00'),
                         ('datetime', '<', '1916-01-01 05:00:00')],
            '__range': {'datetime:hour': {'from': '1916-01-01 04:00:00', 'to': '1916-01-01 05:00:00'}},
            'datetime:hour': '04:00 01 Jan',
            'datetime_count': 0,
            'value': False
        }, {
            '__domain': ['&',
                         ('datetime', '>=', '1916-01-01 05:00:00'),
                         ('datetime', '<', '1916-01-01 06:00:00')],
            '__range': {'datetime:hour': {'from': '1916-01-01 05:00:00', 'to': '1916-01-01 06:00:00'}},
            'datetime:hour': '05:00 01 Jan',
            'datetime_count': 0,
            'value': False
        }, {
            '__domain': ['&',
                         ('datetime', '>=', '1916-01-01 06:00:00'),
                         ('datetime', '<', '1916-01-01 07:00:00')],
            '__range': {'datetime:hour': {'from': '1916-01-01 06:00:00', 'to': '1916-01-01 07:00:00'}},
            'datetime:hour': '06:00 01 Jan',
            'datetime_count': 0,
            'value': False
        }, {
            '__domain': ['&',
                         ('datetime', '>=', '1916-01-01 07:00:00'),
                         ('datetime', '<', '1916-01-01 08:00:00')],
            '__range': {'datetime:hour': {'from': '1916-01-01 07:00:00', 'to': '1916-01-01 08:00:00'}},
            'datetime:hour': '07:00 01 Jan',
            'datetime_count': 0,
            'value': False
        }, {
            '__domain': ['&',
                         ('datetime', '>=', '1916-01-01 08:00:00'),
                         ('datetime', '<', '1916-01-01 09:00:00')],
            '__range': {'datetime:hour': {'from': '1916-01-01 08:00:00', 'to': '1916-01-01 09:00:00'}},
            'datetime:hour': '08:00 01 Jan',
            'datetime_count': 0,
            'value': False
        }, {
            '__domain': ['&',
                         ('datetime', '>=', '1916-01-01 09:00:00'),
                         ('datetime', '<', '1916-01-01 10:00:00')],
            '__range': {'datetime:hour': {'from': '1916-01-01 09:00:00', 'to': '1916-01-01 10:00:00'}},
            'datetime:hour': '09:00 01 Jan',
            'datetime_count': 0,
            'value': False
        }, {
            '__domain': ['&',
                         ('datetime', '>=', '1916-01-01 10:00:00'),
                         ('datetime', '<', '1916-01-01 11:00:00')],
            '__range': {'datetime:hour': {'from': '1916-01-01 10:00:00', 'to': '1916-01-01 11:00:00'}},
            'datetime:hour': '10:00 01 Jan',
            'datetime_count': 0,
            'value': False
        }, {
            '__domain': ['&',
                         ('datetime', '>=', '1916-01-01 11:00:00'),
                         ('datetime', '<', '1916-01-01 12:00:00')],
            '__range': {'datetime:hour': {'from': '1916-01-01 11:00:00', 'to': '1916-01-01 12:00:00'}},
            'datetime:hour': '11:00 01 Jan',
            'datetime_count': 0,
            'value': False
        }, {
            '__domain': ['&',
                         ('datetime', '>=', '1916-01-01 12:00:00'),
                         ('datetime', '<', '1916-01-01 13:00:00')],
            '__range': {'datetime:hour': {'from': '1916-01-01 12:00:00', 'to': '1916-01-01 13:00:00'}},
            'datetime:hour': '12:00 01 Jan',
            'datetime_count': 0,
            'value': False
        }, {
            '__domain': ['&',
                         ('datetime', '>=', '1916-01-01 13:00:00'),
                         ('datetime', '<', '1916-01-01 14:00:00')],
            '__range': {'datetime:hour': {'from': '1916-01-01 13:00:00', 'to': '1916-01-01 14:00:00'}},
            'datetime:hour': '01:00 01 Jan',
            'datetime_count': 1,
            'value': 5
        }, {
            '__domain': ['&',
                         ('datetime', '>=', '1916-01-01 14:00:00'),
                         ('datetime', '<', '1916-01-01 15:00:00')],
            '__range': {'datetime:hour': {'from': '1916-01-01 14:00:00', 'to': '1916-01-01 15:00:00'}},
            'datetime:hour': '02:00 01 Jan',
            'datetime_count': 0,
            'value': False
        }, {
            '__domain': ['&',
                         ('datetime', '>=', '1916-01-01 15:00:00'),
                         ('datetime', '<', '1916-01-01 16:00:00')],
            '__range': {'datetime:hour': {'from': '1916-01-01 15:00:00', 'to': '1916-01-01 16:00:00'}},
            'datetime:hour': '03:00 01 Jan',
            'datetime_count': 0,
            'value': False
        }, {
            '__domain': ['&',
                         ('datetime', '>=', '1916-01-01 16:00:00'),
                         ('datetime', '<', '1916-01-01 17:00:00')],
            '__range': {'datetime:hour': {'from': '1916-01-01 16:00:00', 'to': '1916-01-01 17:00:00'}},
            'datetime:hour': '04:00 01 Jan',
            'datetime_count': 0,
            'value': False
        }, {
            '__domain': ['&',
                         ('datetime', '>=', '1916-01-01 17:00:00'),
                         ('datetime', '<', '1916-01-01 18:00:00')],
            '__range': {'datetime:hour': {'from': '1916-01-01 17:00:00', 'to': '1916-01-01 18:00:00'}},
            'datetime:hour': '05:00 01 Jan',
            'datetime_count': 0,
            'value': False
        }, {
            '__domain': ['&',
                         ('datetime', '>=', '1916-01-01 18:00:00'),
                         ('datetime', '<', '1916-01-01 19:00:00')],
            '__range': {'datetime:hour': {'from': '1916-01-01 18:00:00', 'to': '1916-01-01 19:00:00'}},
            'datetime:hour': '06:00 01 Jan',
            'datetime_count': 0,
            'value': False
        }, {
            '__domain': ['&',
                         ('datetime', '>=', '1916-01-01 19:00:00'),
                         ('datetime', '<', '1916-01-01 20:00:00')],
            '__range': {'datetime:hour': {'from': '1916-01-01 19:00:00', 'to': '1916-01-01 20:00:00'}},
            'datetime:hour': '07:00 01 Jan',
            'datetime_count': 0,
            'value': False
        }, {
            '__domain': ['&',
                         ('datetime', '>=', '1916-01-01 20:00:00'),
                         ('datetime', '<', '1916-01-01 21:00:00')],
            '__range': {'datetime:hour': {'from': '1916-01-01 20:00:00', 'to': '1916-01-01 21:00:00'}},
            'datetime:hour': '08:00 01 Jan',
            'datetime_count': 0,
            'value': False
        }, {
            '__domain': ['&',
                         ('datetime', '>=', '1916-01-01 21:00:00'),
                         ('datetime', '<', '1916-01-01 22:00:00')],
            '__range': {'datetime:hour': {'from': '1916-01-01 21:00:00', 'to': '1916-01-01 22:00:00'}},
            'datetime:hour': '09:00 01 Jan',
            'datetime_count': 0,
            'value': False
        }, {
            '__domain': ['&',
                         ('datetime', '>=', '1916-01-01 22:00:00'),
                         ('datetime', '<', '1916-01-01 23:00:00')],
            '__range': {'datetime:hour': {'from': '1916-01-01 22:00:00', 'to': '1916-01-01 23:00:00'}},
            'datetime:hour': '10:00 01 Jan',
            'datetime_count': 0,
            'value': False
        }, {
            '__domain': ['&',
                         ('datetime', '>=', '1916-01-01 23:00:00'),
                         ('datetime', '<', '1916-01-02 00:00:00')],
            '__range': {'datetime:hour': {'from': '1916-01-01 23:00:00', 'to': '1916-01-02 00:00:00'}},
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
            '__range': {'datetime:hour': {'from': '1915-12-31 22:00:00', 'to': '1915-12-31 23:00:00'}},
            'datetime:hour': '04:00 01 Jan',
            'datetime_count': 1,
            'value': 2
        }, {
            '__domain': ['&',
                         ('datetime', '>=', '1915-12-31 23:00:00'),
                         ('datetime', '<', '1916-01-01 00:00:00')],
            '__range': {'datetime:hour': {'from': '1915-12-31 23:00:00', 'to': '1916-01-01 00:00:00'}},
            'datetime:hour': '05:00 01 Jan',
            'datetime_count': 0,
            'value': False
        }, {
            '__domain': ['&',
                         ('datetime', '>=', '1916-01-01 00:00:00'),
                         ('datetime', '<', '1916-01-01 01:00:00')],
            '__range': {'datetime:hour': {'from': '1916-01-01 00:00:00', 'to': '1916-01-01 01:00:00'}},
            'datetime:hour': '06:00 01 Jan',
            'datetime_count': 0,
            'value': False
        }, {
            '__domain': ['&',
                         ('datetime', '>=', '1916-01-01 01:00:00'),
                         ('datetime', '<', '1916-01-01 02:00:00')],
            '__range': {'datetime:hour': {'from': '1916-01-01 01:00:00', 'to': '1916-01-01 02:00:00'}},
            'datetime:hour': '07:00 01 Jan',
            'datetime_count': 0,
            'value': False
        }, {
            '__domain': ['&',
                         ('datetime', '>=', '1916-01-01 02:00:00'),
                         ('datetime', '<', '1916-01-01 03:00:00')],
            '__range': {'datetime:hour': {'from': '1916-01-01 02:00:00', 'to': '1916-01-01 03:00:00'}},
            'datetime:hour': '08:00 01 Jan',
            'datetime_count': 0,
            'value': False
        }, {
            '__domain': ['&',
                         ('datetime', '>=', '1916-01-01 03:00:00'),
                         ('datetime', '<', '1916-01-01 04:00:00')],
            '__range': {'datetime:hour': {'from': '1916-01-01 03:00:00', 'to': '1916-01-01 04:00:00'}},
            'datetime:hour': '09:00 01 Jan',
            'datetime_count': 1,
            'value': 3
        }]

        model_fill = self.Model.with_context(tz='Asia/Hovd', fill_temporal=True)
        groups = model_fill.read_group([], fields=['datetime', 'value'],
                                       groupby=['datetime:hour'])

        self.assertEqual(groups, expected)

    def test_quarter_with_timezones(self):
        """Test quarter with timezones.

        We group year by quarter and check that it is consistent with timezone.
        """
        self.Model.create({'datetime': '2016-01-01 03:30:00', 'value': 2})
        self.Model.create({'datetime': '2016-12-30 22:30:00', 'value': 3})

        expected = [{
            '__domain': ['&',
                ('datetime', '>=', '2015-12-31 17:00:00'),
                ('datetime', '<', '2016-03-31 16:00:00')],
            '__range': {'datetime:quarter': {'from': '2015-12-31 17:00:00', 'to': '2016-03-31 16:00:00'}},
            'datetime:quarter': 'Q1 2016',
            'datetime_count': 1,
            'value': 2
        }, {
            '__domain': ['&',
                       ('datetime', '>=', '2016-03-31 16:00:00'),
                       ('datetime', '<', '2016-06-30 16:00:00')],
            '__range': {'datetime:quarter': {'from': '2016-03-31 16:00:00', 'to': '2016-06-30 16:00:00'}},
            'datetime:quarter': 'Q2 2016',
            'datetime_count': 0,
            'value': False
        }, {
            '__domain': ['&',
                       ('datetime', '>=', '2016-06-30 16:00:00'),
                       ('datetime', '<', '2016-09-30 17:00:00')],
            '__range': {'datetime:quarter': {'from': '2016-06-30 16:00:00', 'to': '2016-09-30 17:00:00'}},
            'datetime:quarter': 'Q3 2016',
            'datetime_count': 0,
            'value': False
        }, {
            '__domain': ['&',
                       ('datetime', '>=', '2016-09-30 17:00:00'),
                       ('datetime', '<', '2016-12-31 17:00:00')],
            '__range': {'datetime:quarter': {'from': '2016-09-30 17:00:00', 'to': '2016-12-31 17:00:00'}},
            'datetime:quarter': 'Q4 2016',
            'datetime_count': 1,
            'value': 3
        }]

        model_fill = self.Model.with_context(tz='Asia/Hovd', fill_temporal=True)
        groups = model_fill.read_group([], fields=['datetime', 'value'],
                                       groupby=['datetime:quarter'])

        self.assertEqual(groups, expected)

    def test_edge_fx_tz(self):
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
            '__range': {'datetime': {'from': '2017-12-31 17:00:00', 'to': '2018-01-31 17:00:00'}},
            'datetime': 'January 2018',
            'datetime_count': 1,
            'value': 42
        }]

        model_fill = self.Model.with_context(tz='Asia/Hovd', fill_temporal=True)
        groups = model_fill.read_group([], fields=['datetime', 'value'], groupby=['datetime'])

        self.assertEqual(groups, expected)

    def test_with_bounds(self):
        """Test the alternative dictionary format for the fill_temporal context key (fill_from, fill_to).

        We apply the fill_temporal logic only to a cibled portion of the result of a read_group.
        [fill_from, fill_to] are the inclusive bounds of this portion.
        Data outside those bounds will not be filtered out
        Bounds will be converted to the start of the period which they belong to (depending
        on the granularity of the groupby). This means that we can put any date of the period as the bound
        and it will still work.
        """
        self.Model.create({'date': '1916-02-15', 'value': 1})
        self.Model.create({'date': '1916-06-15', 'value': 2})
        self.Model.create({'date': '1916-11-15', 'value': 3})

        expected = [{
            '__domain': ['&', ('date', '>=', '1916-02-01'), ('date', '<', '1916-03-01')],
            '__range': {'date': {'from': '1916-02-01', 'to': '1916-03-01'}},
            'date': 'February 1916',
            'date_count': 1,
            'value': 1
        }, {
            '__domain': ['&', ('date', '>=', '1916-05-01'), ('date', '<', '1916-06-01')],
            '__range': {'date': {'from': '1916-05-01', 'to': '1916-06-01'}},
            'date': 'May 1916',
            'date_count': 0,
            'value': False
        }, {
            '__domain': ['&', ('date', '>=', '1916-06-01'), ('date', '<', '1916-07-01')],
            '__range': {'date': {'from': '1916-06-01', 'to': '1916-07-01'}},
            'date': 'June 1916',
            'date_count': 1,
            'value': 2
        }, {
            '__domain': ['&', ('date', '>=', '1916-07-01'), ('date', '<', '1916-08-01')],
            '__range': {'date': {'from': '1916-07-01', 'to': '1916-08-01'}},
            'date': 'July 1916',
            'date_count': 0,
            'value': False
        }, {
            '__domain': ['&', ('date', '>=', '1916-08-01'), ('date', '<', '1916-09-01')],
            '__range': {'date': {'from': '1916-08-01', 'to': '1916-09-01'}},
            'date': 'August 1916',
            'date_count': 0,
            'value': False
        }, {
            '__domain': ['&', ('date', '>=', '1916-11-01'), ('date', '<', '1916-12-01')],
            '__range': {'date': {'from': '1916-11-01', 'to': '1916-12-01'}},
            'date': 'November 1916',
            'date_count': 1,
            'value': 3
        }]

        model_fill = self.Model.with_context(fill_temporal={"fill_from": '1916-05-15', "fill_to": '1916-08-15'})
        groups = model_fill.read_group([], fields=['date', 'value'], groupby=['date'])

        self.assertEqual(groups, expected)

    def test_upper_bound(self):
        """Test the alternative dictionary format for the fill_temporal context key (fill_to).

        Same as with both bounds, but this time the first bound is the earliest group with data
        (since only fill_to is set)
        """
        self.Model.create({'date': '1916-02-15', 'value': 1})

        expected = [{
            '__domain': ['&', ('date', '>=', '1916-02-01'), ('date', '<', '1916-03-01')],
            '__range': {'date': {'from': '1916-02-01', 'to': '1916-03-01'}},
            'date': 'February 1916',
            'date_count': 1,
            'value': 1
        }, {
            '__domain': ['&', ('date', '>=', '1916-03-01'), ('date', '<', '1916-04-01')],
            '__range': {'date': {'from': '1916-03-01', 'to': '1916-04-01'}},
            'date': 'March 1916',
            'date_count': 0,
            'value': False
        }, {
            '__domain': ['&', ('date', '>=', '1916-04-01'), ('date', '<', '1916-05-01')],
            '__range': {'date': {'from': '1916-04-01', 'to': '1916-05-01'}},
            'date': 'April 1916',
            'date_count': 0,
            'value': False
        }]

        model_fill = self.Model.with_context(fill_temporal={"fill_to": '1916-04-15'})
        groups = model_fill.read_group([], fields=['date', 'value'], groupby=['date'])

        self.assertEqual(groups, expected)

    def test_lower_bound(self):
        """Test the alternative dictionary format for the fill_temporal context key (fill_from).

        Same as with both bounds, but this time the second bound is the lastest group with data
        (since only fill_from is set)
        """
        self.Model.create({'date': '1916-04-15', 'value': 1})

        expected = [{
            '__domain': ['&', ('date', '>=', '1916-02-01'), ('date', '<', '1916-03-01')],
            '__range': {'date': {'from': '1916-02-01', 'to': '1916-03-01'}},
            'date': 'February 1916',
            'date_count': 0,
            'value': False
        }, {
            '__domain': ['&', ('date', '>=', '1916-03-01'), ('date', '<', '1916-04-01')],
            '__range': {'date': {'from': '1916-03-01', 'to': '1916-04-01'}},
            'date': 'March 1916',
            'date_count': 0,
            'value': False
        }, {
            '__domain': ['&', ('date', '>=', '1916-04-01'), ('date', '<', '1916-05-01')],
            '__range': {'date': {'from': '1916-04-01', 'to': '1916-05-01'}},
            'date': 'April 1916',
            'date_count': 1,
            'value': 1
        }]

        model_fill = self.Model.with_context(fill_temporal={"fill_from": '1916-02-15'})
        groups = model_fill.read_group([], fields=['date', 'value'], groupby=['date'])

        self.assertEqual(groups, expected)

    def test_empty_context_key(self):
        """Test the alternative dictionary format for the fill_temporal context key.

        When fill_temporal context key is set to an empty dictionary, it must be equivalent to being True
        """
        self.Model.create({'date': '1916-02-15', 'value': 1})
        self.Model.create({'date': '1916-04-15', 'value': 2})

        expected = [{
            '__domain': ['&', ('date', '>=', '1916-02-01'), ('date', '<', '1916-03-01')],
            '__range': {'date': {'from': '1916-02-01', 'to': '1916-03-01'}},
            'date': 'February 1916',
            'date_count': 1,
            'value': 1
        }, {
            '__domain': ['&', ('date', '>=', '1916-03-01'), ('date', '<', '1916-04-01')],
            '__range': {'date': {'from': '1916-03-01', 'to': '1916-04-01'}},
            'date': 'March 1916',
            'date_count': 0,
            'value': False
        }, {
            '__domain': ['&', ('date', '>=', '1916-04-01'), ('date', '<', '1916-05-01')],
            '__range': {'date': {'from': '1916-04-01', 'to': '1916-05-01'}},
            'date': 'April 1916',
            'date_count': 1,
            'value': 2
        }]

        model_fill = self.Model.with_context(fill_temporal={})
        groups = model_fill.read_group([], fields=['date', 'value'], groupby=['date'])

        self.assertEqual(groups, expected)

    def test_min_groups(self):
        """Test the alternative dictionary format for the fill_temporal context key (min_groups).

        We guarantee that at least a certain amount of contiguous groups is returned, from the
        earliest group with data.
        """
        self.Model.create({'date': '1916-02-15', 'value': 1})

        expected = [{
            '__domain': ['&', ('date', '>=', '1916-02-01'), ('date', '<', '1916-03-01')],
            '__range': {'date': {'from': '1916-02-01', 'to': '1916-03-01'}},
            'date': 'February 1916',
            'date_count': 1,
            'value': 1
        }, {
            '__domain': ['&', ('date', '>=', '1916-03-01'), ('date', '<', '1916-04-01')],
            '__range': {'date': {'from': '1916-03-01', 'to': '1916-04-01'}},
            'date': 'March 1916',
            'date_count': 0,
            'value': False
        }]

        model_fill = self.Model.with_context(fill_temporal={"min_groups": 2})
        groups = model_fill.read_group([], fields=['date', 'value'], groupby=['date'])

        self.assertEqual(groups, expected)

    def test_with_bounds_and_min_groups(self):
        """Test the alternative dictionary format for the fill_temporal context key (fill_from, fill_to, min_groups).

        We guarantee that at least a certain amount of contiguous groups is returned, from the
        fill_from bound. The fill_from bound has precedence over the first group with data regarding min_groups
        (min_groups will first try to anchor itself on fill_from, or, if not specified, on the first group with data).
        This amount is not restricted by the fill_to bound, so, if necessary, the fill_temporal
        logic will be applied until min_groups is guaranteed, even for groups later than fill_to
        Groups outside the specifed bounds are not counted as part of min_groups, unless added specifically
        to guarantee min_groups.
        """
        self.Model.create({'date': '1916-02-15', 'value': 1})
        self.Model.create({'date': '1916-06-15', 'value': 2})
        self.Model.create({'date': '1916-11-15', 'value': 3})

        expected = [{
            '__domain': ['&', ('date', '>=', '1916-02-01'), ('date', '<', '1916-03-01')],
            '__range': {'date': {'from': '1916-02-01', 'to': '1916-03-01'}},
            'date': 'February 1916',
            'date_count': 1,
            'value': 1
        }, {
            '__domain': ['&', ('date', '>=', '1916-05-01'), ('date', '<', '1916-06-01')],
            '__range': {'date': {'from': '1916-05-01', 'to': '1916-06-01'}},
            'date': 'May 1916',
            'date_count': 0,
            'value': False
        }, {
            '__domain': ['&', ('date', '>=', '1916-06-01'), ('date', '<', '1916-07-01')],
            '__range': {'date': {'from': '1916-06-01', 'to': '1916-07-01'}},
            'date': 'June 1916',
            'date_count': 1,
            'value': 2
        }, {
            '__domain': ['&', ('date', '>=', '1916-07-01'), ('date', '<', '1916-08-01')],
            '__range': {'date': {'from': '1916-07-01', 'to': '1916-08-01'}},
            'date': 'July 1916',
            'date_count': 0,
            'value': False
        }, {
            '__domain': ['&', ('date', '>=', '1916-08-01'), ('date', '<', '1916-09-01')],
            '__range': {'date': {'from': '1916-08-01', 'to': '1916-09-01'}},
            'date': 'August 1916',
            'date_count': 0,
            'value': False
        }, {
            '__domain': ['&', ('date', '>=', '1916-11-01'), ('date', '<', '1916-12-01')],
            '__range': {'date': {'from': '1916-11-01', 'to': '1916-12-01'}},
            'date': 'November 1916',
            'date_count': 1,
            'value': 3
        }]

        model_fill = self.Model.with_context(fill_temporal={"fill_from": '1916-05-15', "fill_to": '1916-07-15', "min_groups": 4})
        groups = model_fill.read_group([], fields=['date', 'value'], groupby=['date'])

        self.assertEqual(groups, expected)
