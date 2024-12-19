# -*- coding: utf-8 -*-
from odoo.tests import common


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

    def test_group_by_aggregable(self):
        self.Model.create({'bool_and': False, 'key': 1, 'bool_array': True})
        self.Model.create({'bool_and': False, 'key': 2, 'bool_array': True})
        self.Model.create({'bool_and': False, 'key': 2, 'bool_array': True})
        self.Model.create({'bool_and': True, 'key': 2, 'bool_array': True})
        self.Model.create({'bool_and': True, 'key': 3, 'bool_array': True})
        self.Model.create({'bool_and': True, 'key': 3, 'bool_array': True})

        groups = self.Model.read_group(
            domain=[],
            fields=['key', 'bool_and', 'bool_array'],
            groupby=['bool_and', 'key'],
            lazy=False
        )

        self.assertEqual([
            {
                'bool_and': False,
                'key': 1,
                'bool_array': [True],
                '__count': 1,
                '__domain': ['&', ('bool_and', '=', False), ('key', '=', 1)]
            },
            {
                'bool_and': False,
                'key': 2,
                'bool_array': [True, True],
                '__count': 2,
                '__domain': ['&', ('bool_and', '=', False), ('key', '=', 2)]

            },
            {
                'bool_and': True,
                'key': 2,
                'bool_array': [True],
                '__count': 1,
                '__domain': ['&', ('bool_and', '=', True), ('key', '=', 2)]
            },
            {
                'bool_and': True,
                'key': 3,
                'bool_array': [True, True],
                '__count': 2,
                '__domain': ['&', ('bool_and', '=', True), ('key', '=', 3)]
            }
        ], groups)


class TestAggregate(common.TransactionCase):
    def setUp(self):
        super(TestAggregate, self).setUp()

        self.foo = self.env['res.partner'].create({'name': 'Foo'})
        self.bar = self.env['res.partner'].create({'name': 'Bar'})

        self.Model = self.env['test_read_group.aggregate']
        self.Model.create({'key': 1, 'value': 1, 'partner_id': False})
        self.Model.create({'key': 1, 'value': 2, 'partner_id': self.foo.id})
        self.Model.create({'key': 1, 'value': 3, 'partner_id': self.foo.id})
        self.Model.create({'key': 1, 'value': 4, 'partner_id': self.bar.id})

    def test_agg_default(self):
        """ test default aggregation on fields """
        fields = ['key', 'value', 'partner_id']
        groups = self.Model.read_group([], fields, ['key'])
        self.assertEqual(groups, [{
            'key': 1,
            'value': 10,
            'key_count': 4,
            '__domain': [('key', '=', 1)],
        }])

    def test_agg_explicit(self):
        """ test explicit aggregation on fields """
        fields = ['key', 'value:max', 'partner_id']
        groups = self.Model.read_group([], fields, ['key'])
        self.assertEqual(groups, [{
            'key': 1,
            'value': 4,
            'key_count': 4,
            '__domain': [('key', '=', 1)],
        }])
        fields = ['key', 'value', 'partner_id:array_agg']
        groups = self.Model.read_group([], fields, ['key'])
        self.assertEqual(groups, [{
            'key': 1,
            'value': 10,
            'partner_id': [None, self.foo.id, self.foo.id, self.bar.id],
            'key_count': 4,
            '__domain': [('key', '=', 1)],
        }])
        fields = ['key', 'value', 'partner_id:count']
        groups = self.Model.read_group([], fields, ['key'])
        self.assertEqual(groups, [{
            'key': 1,
            'value': 10,
            'partner_id': 3,
            'key_count': 4,
            '__domain': [('key', '=', 1)],
        }])
        fields = ['key', 'value', 'partner_id:count_distinct']
        groups = self.Model.read_group([], fields, ['key'])
        self.assertEqual(groups, [{
            'key': 1,
            'value': 10,
            'partner_id': 2,
            'key_count': 4,
            '__domain': [('key', '=', 1)],
        }])

    def test_agg_multi(self):
        """ test multiple aggregation on fields """
        fields = ['key', 'value_min:min(value)', 'value_max:max(value)', 'partner_id']
        groups = self.Model.read_group([], fields, ['key'])
        self.assertEqual(groups, [{
            'key': 1,
            'value_min': 1,
            'value_max': 4,
            'key_count': 4,
            '__domain': [('key', '=', 1)],
        }])

        fields = ['key', 'ids:array_agg(id)']
        groups = self.Model.read_group([], fields, ['key'])
        self.assertEqual(groups, [{
            'key': 1,
            'ids': self.Model.search([]).ids,
            'key_count': 4,
            '__domain': [('key', '=', 1)],
        }])


class TestAggregateMonetary(common.TransactionCase):
    def setUp(self):
        super(TestAggregateMonetary, self).setUp()

        self.Model = self.env['test_read_group.aggregate.monetary']

        cur1 = self.env['res.currency'].create({'name': 'XXX', 'symbol': 'X'})
        cur2 = self.env['res.currency'].create({'name': 'TTT', 'symbol': 'T'})

        self.Model.create({'key': 1, 'amount': 1, 'currency_id': cur1.id})
        self.Model.create({'key': 1, 'amount': 2, 'currency_id': cur2.id})
        self.Model.create({'key': 2, 'amount': 3, 'currency_id': cur1.id})
        self.Model.create({'key': 2, 'amount': 4, 'currency_id': cur1.id})

    def test_agg_monetary_do_not_sum(self):
        fields = ['key', 'amount']
        group_key_1 = self.Model.read_group([('key', '=', 1)], fields, ['key'])
        self.assertEqual(group_key_1, [{
            'key': 1,
            'amount': False,
            'key_count': 2,
            '__domain': ['&', ('key', '=', 1), ('key', '=', 1)],
        }])

    def test_agg_monetary_do_sum(self):
        fields = ['key', 'amount']
        group_key_2 = self.Model.read_group([('key', '=', 2)], fields, ['key'])
        self.assertEqual(group_key_2, [{
            'key': 2,
            'amount': 7,
            'key_count': 2,
            '__domain': ['&', ('key', '=', 2), ('key', '=', 2)],
        }])
