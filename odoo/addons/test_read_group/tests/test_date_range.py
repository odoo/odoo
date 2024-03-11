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
