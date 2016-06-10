# -*- coding: utf-8 -*-
from openerp.tests import common


class TestGroupBooleans(common.TransactionCase):

    def setUp(self):
        super(TestGroupBooleans, self).setUp()
        self.Model = self.env['test_read_group.aggregate.boolean']

    def test_no_value(self):
        groups = self.Model.read_group(
            domain=[],
            fields=['key', 'bool_and', 'bool_or', 'bool_array'],
            groupby=['key'],
        )

        self.assertEqual([], groups)

    def test_agg_and(self):
        # and(true, true)
        self.Model.create({
            'key': 1,
            'bool_and': True
        })
        self.Model.create({
            'key': 1,
            'bool_and': True
        })
        # and(true, false)
        self.Model.create({'key': 2, 'bool_and': True})
        self.Model.create({'key': 2, 'bool_and': False})
        # and(false, false)
        self.Model.create({'key': 3, 'bool_and': False})
        self.Model.create({'key': 3, 'bool_and': False})

        groups = self.Model.read_group(
            domain=[],
            fields=['key', 'bool_and'],
            groupby=['key'],
        )

        self.assertEqual([
            {
                'key_count': 2,
                '__domain': [('key', '=', 1)],
                'key': 1,
                'bool_and': True
            },
            {
                'key_count': 2,
                '__domain': [('key', '=', 2)],
                'key': 2,
                'bool_and': False
            },
            {
                'key_count': 2,
                '__domain': [('key', '=', 3)],
                'key': 3,
                'bool_and': False
            },
        ], groups)


    def test_agg_or(self):
        # or(true, true)
        self.Model.create({
            'key': 1,
            'bool_or': True
        })
        self.Model.create({
            'key': 1,
            'bool_or': True
        })
        # or(true, false)
        self.Model.create({'key': 2, 'bool_or': True})
        self.Model.create({'key': 2, 'bool_or': False})
        # or(false, false)
        self.Model.create({'key': 3, 'bool_or': False})
        self.Model.create({'key': 3, 'bool_or': False})

        groups = self.Model.read_group(
            domain=[],
            fields=['key', 'bool_or'],
            groupby=['key'],
        )

        self.assertEqual([
            {
                'key_count': 2,
                '__domain': [('key', '=', 1)],
                'key': 1,
                'bool_or': True
            },
            {
                'key_count': 2,
                '__domain': [('key', '=', 2)],
                'key': 2,
                'bool_or': True
            },
            {
                'key_count': 2,
                '__domain': [('key', '=', 3)],
                'key': 3,
                'bool_or': False
            },
        ], groups)

    def test_agg_array(self):
        # array(true, true)
        self.Model.create({
            'key': 1,
            'bool_array': True
        })
        self.Model.create({
            'key': 1,
            'bool_array': True
        })
        # array(true, false)
        self.Model.create({'key': 2, 'bool_array': True})
        self.Model.create({'key': 2, 'bool_array': False})
        # array(false, false)
        self.Model.create({'key': 3, 'bool_array': False})
        self.Model.create({'key': 3, 'bool_array': False})

        groups = self.Model.read_group(
            domain=[],
            fields=['key', 'bool_array'],
            groupby=['key'],
        )

        self.assertEqual([
            {
                'key_count': 2,
                '__domain': [('key', '=', 1)],
                'key': 1,
                'bool_array': [True, True]
            },
            {
                'key_count': 2,
                '__domain': [('key', '=', 2)],
                'key': 2,
                'bool_array': [True, False]
            },
            {
                'key_count': 2,
                '__domain': [('key', '=', 3)],
                'key': 3,
                'bool_array': [False, False]
            },
        ], groups)
