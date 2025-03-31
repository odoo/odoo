# -*- coding: utf-8 -*-
"""Test for date ranges."""

from odoo.tests import common


class TestDateRange(common.TransactionCase):
    """Test for date ranges.

    When grouping on date/datetime fields, group.__range is populated with
    formatted string dates which can be accurately converted to date objects
    (backend and frontend), since the display value format can vary greatly and
    it is not always possible to translate that display value to a real date.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Model = cls.env['test_read_group.on_date']

    def test_undefined_range(self):
        """Test an undefined range.

        Records with an unset date value should be grouped in a group whose
        range is False.
        """
        self.Model.create({'date': False, 'value': 1})

        expected = [{
            '__domain': [('date', '=', False)],
            '__range': {'date': False},
            'date': False,
            'date_count': 1,
            'value': 1
        }]

        groups = self.Model.read_group([], fields=['date', 'value'], groupby=['date'])
        self.assertEqual(groups, expected)

    def test_with_default_granularity(self):
        """Test a range with the default granularity.

        The default granularity is 'month' and is implied when not specified.
        The key in group.__range should match the key in group.
        """
        self.Model.create({'date': '1916-02-11', 'value': 1})

        expected = [{
            '__domain': ['&', ('date', '>=', '1916-02-01'), ('date', '<', '1916-03-01')],
            '__range': {'date': {'from': '1916-02-01', 'to': '1916-03-01'}},
            'date': 'February 1916',
            'date_count': 1,
            'value': 1
        }]

        groups = self.Model.read_group([], fields=['date', 'value'], groupby=['date'])
        self.assertEqual(groups, expected)

    def test_lazy_with_multiple_granularities(self):
        """Test a range with multiple granularities in lazy mode

        The only value stored in __range should be the granularity of the first
        groupby.
        """
        self.Model.create({'date': '1916-02-11', 'value': 1})

        expected = [{
            '__domain': ['&', ('date', '>=', '1916-01-01'), ('date', '<', '1916-04-01')],
            '__context': {'group_by': ['date:day']},
            '__range': {'date:quarter': {'from': '1916-01-01', 'to': '1916-04-01'}},
            'date:quarter': 'Q1 1916',
            'date_count': 1,
            'value': 1
        }]

        groups = self.Model.read_group([], fields=['date', 'value'], groupby=['date:quarter', 'date:day'])
        self.assertEqual(groups, expected)

        expected = [{
            '__domain': ['&', ('date', '>=', '1916-02-11'), ('date', '<', '1916-02-12')],
            '__context': {'group_by': ['date:quarter']},
            '__range': {'date:day': {'from': '1916-02-11', 'to': '1916-02-12'}},
            'date:day': '11 Feb 1916',
            'date_count': 1,
            'value': 1
        }]

        groups = self.Model.read_group([], fields=['date', 'value'], groupby=['date:day', 'date:quarter'])
        self.assertEqual(groups, expected)

    def test_not_lazy_with_multiple_granularities(self):
        """Test a range with multiple granularities (not lazy)

        There should be a range for each granularity.
        """
        self.Model.create({'date': '1916-02-11', 'value': 1})

        expected = [{
            '__domain': ['&',
                '&', ('date', '>=', '1916-01-01'), ('date', '<', '1916-04-01'),
                '&', ('date', '>=', '1916-02-11'), ('date', '<', '1916-02-12')
            ],
            '__range': {
                'date:quarter': {'from': '1916-01-01', 'to': '1916-04-01'},
                'date:day': {'from': '1916-02-11', 'to': '1916-02-12'}
            },
            'date:quarter': 'Q1 1916',
            'date:day': '11 Feb 1916',
            '__count': 1,
            'value': 1
        }]

        groups = self.Model.read_group([], fields=['date', 'value'], groupby=['date:quarter', 'date:day'], lazy=False)
        self.assertEqual(groups, expected)

    def test_duplicate_month(self):
        records = self.Model.create([
            {'date': '2022-01-29', 'value': 1}])
        expected = [{
            '__domain': ['&', '&', ('id', 'in', records.ids), '&', ('date', '>=', '2022-01-01'), ('date', '<', '2022-02-01'), ('date', '=', 'January 2022')],
            '__count': 1,
            '__range': {'date:month': {'from': '2022-01-01', 'to': '2022-02-01'}},
            'value': 1,
            'date:month': 'January 2022'
        }]
        groups = self.Model.read_group(
            [('id', 'in', records.ids)], fields=['date', 'value'], groupby=['date:month', 'date:month'], lazy=False)
        self.assertEqual(groups, expected)


class TestRelativeDateGranularity(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Model = cls.env['test_read_group.fill_temporal']
        cls.Model.create([{"value": "1", "date": "2021-02-09", "datetime": "2021-02-09 15:55:12"},
                          {"value": "20", "date": "2021-06-01", "datetime": "2021-06-01 16:55:14"},
                          {"value": "300", "date": "2022-02-01", "datetime": "2022-02-01 15:22:12"}])

    def test_full_usecase_month(self):
        result = self.Model.read_group([],
                                       fields=['date', 'value'],
                                       groupby=['date:month_number'])
        self.assertEqual(result, [
            {
                'date:month_number': 2,
                'date_count': 2,
                'value': 301,
                '__domain': [('date.month_number', '=', 2)]
            }, {
                'date:month_number': 6,
                'date_count': 1,
                'value': 20,
                '__domain': [('date.month_number', '=', 6)]
            },
        ])
        res = self.Model.search(result[0]['__domain'])
        self.assertEqual(len(res), 2)
        self.assertEqual(res.mapped('value'), [1, 300])

    def test_full_usecase_iso_week(self):
        result = self.Model.read_group([],
                                       fields=['date', 'value'],
                                       groupby=['date:iso_week_number'])
        self.assertEqual(result, [
            {
                'date:iso_week_number': 5,
                'date_count': 1,
                'value': 300,
                '__domain': [('date.iso_week_number', '=', 5)]
            }, {
                'date:iso_week_number': 6,
                'date_count': 1,
                'value': 1,
                '__domain': [('date.iso_week_number', '=', 6)]
            }, {
                'date:iso_week_number': 22,
                'date_count': 1,
                'value': 20,
                '__domain': [('date.iso_week_number', '=', 22)]
            },
        ])
        res = self.Model.search(result[0]['__domain'])
        self.assertEqual(len(res), 1)
        self.assertEqual(res.mapped('value'), [300])

    def test_full_usecase_quarter(self):
        result = self.Model.read_group([],
                                       fields=['date', 'value'],
                                       groupby=['date:quarter_number'])
        self.assertEqual(result, [
            {
                'date:quarter_number': 1,
                'date_count': 2,
                'value': 301,
                '__domain': [('date.quarter_number', '=', 1)]
            }, {
                'date:quarter_number': 2,
                'date_count': 1,
                'value': 20,
                '__domain': [('date.quarter_number', '=', 2)]
            },
        ])
        res = self.Model.search(result[0]['__domain'])
        self.assertEqual(len(res), 2)
        self.assertEqual(res.mapped('value'), [1, 300])

    def test_full_usecase_year(self):
        result = self.Model.read_group([],
                                       fields=['date', 'value'],
                                       groupby=['date:year_number'])
        self.assertEqual(result, [
            {
                'date:year_number': 2021,
                'date_count': 2,
                'value': 21,
                '__domain': [('date.year_number', '=', 2021)]
            }, {
                'date:year_number': 2022,
                'date_count': 1,
                'value': 300,
                '__domain': [('date.year_number', '=', 2022)]
            },
        ])
        res = self.Model.search(result[0]['__domain'])
        self.assertEqual(len(res), 2)
        self.assertEqual(res.mapped('value'), [1, 20])

    def test_full_usecase_day_of_year(self):
        result = self.Model.read_group([],
                                       fields=['date', 'value'],
                                       groupby=['date:day_of_year'])
        self.assertEqual(result, [
            {
                'date:day_of_year': 32,
                'date_count': 1,
                'value': 300,
                '__domain': [('date.day_of_year', '=', 32)]
            }, {
                'date:day_of_year': 40,
                'date_count': 1,
                'value': 1,
                '__domain': [('date.day_of_year', '=', 40)]
            }, {
                'date:day_of_year': 152,
                'date_count': 1,
                'value': 20,
                '__domain': [('date.day_of_year', '=', 152)]
            },
        ])
        res = self.Model.search(result[0]['__domain'])
        self.assertEqual(len(res), 1)
        self.assertEqual(res.mapped('value'), [300])

    def test_full_usecase_day_of_month(self):
        result = self.Model.read_group([],
                                       fields=['date', 'value'],
                                       groupby=['date:day_of_month'])
        self.assertEqual(result, [
            {
                'date:day_of_month': 1,
                'date_count': 2,
                'value': 320,
                '__domain': [('date.day_of_month', '=', 1)]
            }, {
                'date:day_of_month': 9,
                'date_count': 1,
                'value': 1,
                '__domain': [('date.day_of_month', '=', 9)]
            },
        ])
        res = self.Model.search(result[0]['__domain'])
        self.assertEqual(len(res), 2)
        self.assertEqual(res.mapped('value'), [20, 300])

    def test_full_usecase_day_of_week(self):
        result = self.Model.read_group([],
                                       fields=['date', 'value'],
                                       groupby=['date:day_of_week'])
        self.assertEqual(result, [
            {
                'date:day_of_week': 2,
                'date_count': 3,
                'value': 321,
                '__domain': [('date.day_of_week', '=', 2)]
            },
        ])
        res = self.Model.search(result[0]['__domain'])
        self.assertEqual(len(res), 3)
        self.assertEqual(res.mapped('value'), [1, 20, 300])

    def test_full_usecase_hour_number(self):
        result = self.Model.read_group([],
                                       fields=['datetime', 'value'],
                                       groupby=['datetime:hour_number'])
        self.assertEqual(result, [
            {
                'datetime:hour_number': 15,
                'datetime_count': 2,
                'value': 301,
                '__domain': [('datetime.hour_number', '=', 15)]
            }, {
                'datetime:hour_number': 16,
                'datetime_count': 1,
                'value': 20,
                '__domain': [('datetime.hour_number', '=', 16)]
            },
        ])
        res = self.Model.search(result[0]['__domain'])
        self.assertEqual(len(res), 2)
        self.assertEqual(res.mapped('value'), [1, 300])

    def test_full_usecase_minute_number(self):
        result = self.Model.read_group([],
                                       fields=['datetime', 'value'],
                                       groupby=['datetime:minute_number'])
        self.assertEqual(result, [
            {
                'datetime:minute_number': 22,
                'datetime_count': 1,
                'value': 300,
                '__domain': [('datetime.minute_number', '=', 22)]
            }, {
                'datetime:minute_number': 55,
                'datetime_count': 2,
                'value': 21,
                '__domain': [('datetime.minute_number', '=', 55)]
            },
        ])
        res = self.Model.search(result[0]['__domain'])
        self.assertEqual(len(res), 1)
        self.assertEqual(res.mapped('value'), [300])

    def test_full_usecase_second_number(self):
        result = self.Model.read_group([],
                                       fields=['datetime', 'value'],
                                       groupby=['datetime:second_number'])
        self.assertEqual(result, [
            {
                'datetime:second_number': 12,
                'datetime_count': 2,
                'value': 301,
                '__domain': [('datetime.second_number', '=', 12)]
            }, {
                'datetime:second_number': 14,
                'datetime_count': 1,
                'value': 20,
                '__domain': [('datetime.second_number', '=', 14)]
            },
        ])
        res = self.Model.search(result[0]['__domain'])
        self.assertEqual(len(res), 2)
        self.assertEqual(res.mapped('value'), [1, 300])

    def test_unknown_granularity(self):
        with self.assertRaises(ValueError):
            self.Model.read_group([], fields=['date', 'value'], groupby=['date:unknown_number'])


class TestRelativeDateGranularityWithTimezones(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        # execute a read_group with a relative granularity, it will give us back a domain
        # that contains the relative granularity to find the origin records. Use this domain
        # to find those records. This is exactly the way the pivot view behaves.
        super().setUpClass()
        cls.Model = cls.env['test_read_group.fill_temporal']
        cls.env['res.lang']._activate_lang('fr_BE')
        cls.env['res.lang']._activate_lang('NZ')

    def test_usecase_with_timezones(self):
        # Monday, it is the 5th week in UTC and the 6th in NZ
        self.Model.create({"value": "98", "datetime": "2023-02-05 23:55:00"})
        result = (self.Model.with_context({'tz': 'Pacific/Auckland'})  # GMT+12
                            .read_group([],
                                        fields=['datetime', 'value'],
                                        groupby=['datetime:iso_week_number']))
        self.assertEqual(result, [
                    {
                        'datetime:iso_week_number': 6,
                        'datetime_count': 1,
                        'value': 98,
                        '__domain': [('datetime.iso_week_number', '=', 6)]
                    }])
        result = self.Model.with_context({'tz': 'Pacific/Auckland'}).search(result[0]['__domain'])
        self.assertEqual(len(result), 1)
        self.assertEqual(result.value, 98)

    def test_day_of_week_with_monday_as_first_day_of_week(self):
        self.Model.create({"value": "98", "date": "2023-02-05"})  # Sunday

        result = (self.Model.with_context({'tz': 'fr_BE'})  # GMT+1, first day of week is Monday
                  .read_group([],
                              fields=['date', 'value'],
                              groupby=['date:day_of_week']))
        self.assertEqual(result, [
            {
                'date:day_of_week': 6,
                'date_count': 1,
                'value': 98,
                '__domain': [('date.day_of_week', '=', 6)]
            }])
        res = self.Model.with_context({'tz': 'fr_BE'}).search(result[0]['__domain'])
        self.assertEqual(len(res), 1)
        self.assertEqual(res.mapped('value'), [98])

    def test_day_of_week_with_sunday_as_first_day_of_week(self):
        self.Model.create({"value": "98", "date": "2023-02-05"})  # Sunday

        result = (self.Model.with_context({'tz': 'NZ'})  # GMT+12, first day of week is Sunday
                  .read_group([],
                              fields=['date', 'value'],
                              groupby=['date:day_of_week']))
        self.assertEqual(result, [
            {
                'date:day_of_week': 0,
                'date_count': 1,
                'value': 98,
                '__domain': [('date.day_of_week', '=', 0)]
            }])

        res = self.Model.with_context({'tz': 'NZ'}).search(result[0]['__domain'])
        self.assertEqual(len(res), 1)
        self.assertEqual(res.mapped('value'), [98])
