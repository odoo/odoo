# -*- coding: utf-8 -*-
from odoo.tests import common


class TestEmptyDate(common.TransactionCase):
    """ Test what happens when grouping on date fields and getting a "false"
    grouping value
    """
    def setUp(self):
        super(TestEmptyDate, self).setUp()
        self.Model = self.env['test_read_group.on_date']

    def test_empty_only(self):
        self.Model.create({'value': 1})
        self.Model.create({'value': 2})
        self.Model.create({'value': 3})

        gb = self.Model.read_group([], ['date', 'value'], ['date'], lazy=False)

        self.assertEqual(gb, [{
            '__count': 3,
            '__domain': [('date', '=', False)],
            '__range': {'date': False},
            'date': False,
            'value': 6
        }])

    def test_empty_by_span(self):
        self.Model.create({'value': 1})
        self.Model.create({'value': 2})
        self.Model.create({'value': 3})

        gb = self.Model.read_group([], ['date', 'value'], ['date:quarter'], lazy=False)

        self.assertEqual(gb, [{
            '__count': 3,
            '__domain': [('date', '=', False)],
            '__range': {'date:quarter': False},
            'date:quarter': False,
            'value': 6
        }])

    def test_mixed(self):
        self.Model.create({'date': False, 'value': 1})
        self.Model.create({'date': False, 'value': 2})
        self.Model.create({'date': '1916-12-18', 'value': 3})
        self.Model.create({'date': '1916-12-18', 'value': 4})

        gb = self.Model.read_group([], ['date', 'value'], ['date'], lazy=False)

        self.assertSequenceEqual(sorted(gb, key=lambda r: r['date'] or ''), [{
            '__count': 2,
            '__domain': [('date', '=', False)],
            '__range': {'date': False},
            'date': False,
            'value': 3,
        }, {
            '__count': 2,
            '__domain': ['&', ('date', '>=', '1916-12-01'), ('date', '<', '1917-01-01')],
            '__range': {'date': {'from': '1916-12-01', 'to': '1917-01-01'}},
            'date': 'December 1916',
            'value': 7,
        }])
