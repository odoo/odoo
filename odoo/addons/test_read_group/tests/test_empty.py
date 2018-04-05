# -*- coding: utf-8 -*-
from odoo.tests import common
from odoo.tools.datetime import datetime


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
            'date:quarter': False,
            'value': 6
        }])

    def test_mixed(self):
        self.Model.create({'date': False, 'value': 1})
        self.Model.create({'date': False, 'value': 2})
        self.Model.create({'date': datetime(1916, 12, 18), 'value': 3})
        self.Model.create({'date': datetime(1916, 12, 18), 'value': 4})

        gb = self.Model.read_group([], ['date', 'value'], ['date'], lazy=False)
        gb = sorted(gb, key=lambda r: r['date'] or '')

        self.assertEqual(len(gb), 2)
        self.assertTrue(gb[0]['__count'], gb[1]['__count'] == 2)
        self.assertEqual(gb[0]['__domain'], [('date', '=', False)])
        self.assertEqual(len(gb[1]['__domain']), 3)
        self.assertEqual(gb[1]['__domain'][0], '&')
        self.assertEqual(len(gb[1]['__domain'][1]), 3)

        # Do this stuff because timezone is completly random...
        self.assertEqual(gb[1]['__domain'][1][0], 'date')
        self.assertEqual(gb[1]['__domain'][1][1], '>=')
        self.assertEqual(gb[1]['__domain'][1][2].strftime('%Y%m%d%H%M%S'), '19161201000000')
        self.assertEqual(gb[1]['__domain'][2][0], 'date')
        self.assertEqual(gb[1]['__domain'][2][1], '<')
        self.assertEqual(gb[1]['__domain'][2][2].strftime('%Y%m%d%H%M%S'), '19170101000000')
        self.assertEqual(gb[0]['date'], False)
        self.assertEqual(gb[1]['date'], 'December 1916')
        self.assertEqual(gb[0]['value'], 3)
        self.assertEqual(gb[1]['value'], 7)
