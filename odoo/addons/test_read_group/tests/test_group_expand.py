# -*- coding: utf-8 -*-
from odoo.tests import common


class TestGroupOnSelection(common.TransactionCase):
    def setUp(self):
        super(TestGroupOnSelection, self).setUp()
        self.Model = self.env['test_read_group.on_selection']

    def test_none(self):
        self.Model.create({'value': 1})
        self.Model.create({'value': 2})
        self.Model.create({'value': 3})

        groups = self.Model.read_group([], fields=['state', 'value'], groupby=['state'])
        self.assertEqual(groups, [
            {
                'state': 'a',
                'state_count': 0,
                'value': False,
                '__domain': [('state', '=', 'a')],
            },
            {
                'state': 'b',
                'state_count': 0,
                'value': False,
                '__domain': [('state', '=', 'b')],
            },
            {
                'state': False,
                'state_count': 3,
                'value': 6,
                '__domain': [('state', '=', False)],
            },
        ])

    def test_partial(self):
        self.Model.create({'state': 'a', 'value': 1})
        self.Model.create({'state': 'a', 'value': 2})
        self.Model.create({'value': 3})

        groups = self.Model.read_group([], fields=['state', 'value'], groupby=['state'])
        self.assertEqual(groups, [
            {
                'state': 'a',
                'state_count': 2,
                'value': 3,
                '__domain': [('state', '=', 'a')],
            },
            {
                'state': 'b',
                'state_count': 0,
                'value': False,
                '__domain': [('state', '=', 'b')],
            },
            {
                'state': False,
                'state_count': 1,
                'value': 3,
                '__domain': [('state', '=', False)],
            },
        ])

    def test_full(self):
        self.Model.create({'state': 'a', 'value': 1})
        self.Model.create({'state': 'b', 'value': 2})
        self.Model.create({'value': 3})

        groups = self.Model.read_group([], fields=['state', 'value'], groupby=['state'])
        self.assertEqual(groups, [
            {
                'state': 'a',
                'state_count': 1,
                'value': 1,
                '__domain': [('state', '=', 'a')],
            },
            {
                'state': 'b',
                'state_count': 1,
                'value': 2,
                '__domain': [('state', '=', 'b')],
            },
            {
                'state': False,
                'state_count': 1,
                'value': 3,
                '__domain': [('state', '=', False)],
            },
        ])
