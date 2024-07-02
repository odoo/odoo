from odoo.tests import common


class TestGroupExpand(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Model = cls.env['test_read_group.on_selection']

    def test_none(self):
        self.Model.create({'value': 1})
        self.Model.create({'value': 2})
        self.Model.create({'value': 3})

        groups = self.Model.web_read_group([], ['state'], ['__count', 'value:sum'])['groups']
        self.assertEqual(groups, [
            {
                'state': 'a',
                '__count': 0,
                'value:sum': False,
                '__domain_part': [('state', '=', 'a')],
            },
            {
                'state': 'b',
                '__count': 0,
                'value:sum': False,
                '__domain_part': [('state', '=', 'b')],
            },
            {
                'state': False,
                '__count': 3,
                'value:sum': 6,
                '__domain_part': [('state', '=', False)],
            },
        ])

    def test_partial(self):
        self.Model.create({'state': 'a', 'value': 1})
        self.Model.create({'state': 'a', 'value': 2})
        self.Model.create({'value': 3})

        groups = self.Model.web_read_group([], ['state'], ['__count', 'value:sum'])['groups']
        self.assertEqual(groups, [
            {
                'state': 'a',
                '__count': 2,
                'value:sum': 3,
                '__domain_part': [('state', '=', 'a')],
            },
            {
                'state': 'b',
                '__count': 0,
                'value:sum': False,
                '__domain_part': [('state', '=', 'b')],
            },
            {
                'state': False,
                '__count': 1,
                'value:sum': 3,
                '__domain_part': [('state', '=', False)],
            },
        ])

    def test_full(self):
        self.Model.create({'state': 'a', 'value': 1})
        self.Model.create({'state': 'b', 'value': 2})
        self.Model.create({'value': 3})

        groups = self.Model.web_read_group([], ['state'], ['__count', 'value:sum'])['groups']
        self.assertEqual(groups, [
            {
                'state': 'a',
                '__count': 1,
                'value:sum': 1,
                '__domain_part': [('state', '=', 'a')],
            },
            {
                'state': 'b',
                '__count': 1,
                'value:sum': 2,
                '__domain_part': [('state', '=', 'b')],
            },
            {
                'state': False,
                '__count': 1,
                'value:sum': 3,
                '__domain_part': [('state', '=', False)],
            },
        ])

    def test_static_group_expand(self):
        # this test verifies that the following happens when grouping by a Selection field with
        # group_expand=True:
        #   - the order of the returned groups is the same as the order in which the
        #     options are declared in the field definition.
        #   - the groups returned include the empty groups, i.e. all groups, even those
        #     that have no records assigned to them, this is a (wanted) side-effect of the
        #     implementation.
        #   - the false group, i.e. records without the Selection field set, is last.
        self.Model.create([
            {"value": 1, "static_expand": "a"},
            {"value": 2, "static_expand": "c"},
            {"value": 3},
        ])

        groups = self.Model.web_read_group(
            [],
            groupby=["static_expand"],
            aggregates=["__count", "value:sum"],
        )['groups']
        self.assertEqual(groups, [
            {
                'static_expand': 'c',
                '__count': 1,
                'value:sum': 2,
                '__domain_part': [('static_expand', '=', 'c')],
            },
            {
                'static_expand': 'b',
                '__count': 0,
                'value:sum': 0,
                '__domain_part': [('static_expand', '=', 'b')],
            },
            {
                'static_expand': 'a',
                '__count': 1,
                'value:sum': 1,
                '__domain_part': [('static_expand', '=', 'a')],
            },
            {
                'static_expand': False,
                '__count': 1,
                'value:sum': 3,
                '__domain_part': [('static_expand', '=', False)],
            },
        ])

    def test_dynamic_group_expand(self):
        # this test tests the same as the above test but with a Selection field whose
        # options are dynamic, this means that the result of read_group when grouping by this
        # field can change from one call to another.
        self.Model.create([
            {"value": 1, "dynamic_expand": "a"},
            {"value": 2, "dynamic_expand": "c"},
            {"value": 3},
        ])

        groups = self.Model.web_read_group(
            [],
            groupby=["dynamic_expand"],
            aggregates=["__count", "value:sum"],
        )['groups']

        self.assertEqual(groups, [
            {
                'dynamic_expand': 'c',
                '__count': 1,
                'value:sum': 2,
                '__domain_part': [('dynamic_expand', '=', 'c')],
            },
            {
                'dynamic_expand': 'b',
                '__count': 0,
                'value:sum': 0,
                '__domain_part': [('dynamic_expand', '=', 'b')],
            },
            {
                'dynamic_expand': 'a',
                '__count': 1,
                'value:sum': 1,
                '__domain_part': [('dynamic_expand', '=', 'a')],
            },
            {
                'dynamic_expand': False,
                '__count': 1,
                'value:sum': 3,
                '__domain_part': [('dynamic_expand', '=', False)],
            },
        ])

    def test_no_group_expand(self):
        # if group_expand is not defined on a Selection field, it should return only the necessary
        # groups and in alphabetical order (PostgreSQL ordering)
        self.Model.create([
            {"value": 1, "no_expand": "a"},
            {"value": 2, "no_expand": "c"},
            {"value": 3},
        ])

        groups = self.Model.web_read_group(
            [],
            groupby=["no_expand"],
            aggregates=["__count", "value:sum"],
        )['groups']

        self.assertEqual(groups, [
            {
                'no_expand': 'a',
                '__count': 1,
                'value:sum': 1,
                '__domain_part': [('no_expand', '=', 'a')],
            },
            {
                'no_expand': 'c',
                '__count': 1,
                'value:sum': 2,
                '__domain_part': [('no_expand', '=', 'c')],
            },
            {
                'no_expand': False,
                '__count': 1,
                'value:sum': 3,
                '__domain_part': [('no_expand', '=', False)],
            },
        ])

    def test_with_limit_offset_performance(self):
        order_1, order_2, order_3, order_4 = self.env['test_read_group.order'].create([
            {'name': 'O1', 'fold': False},
            {'name': 'O2', 'fold': True},
            {'name': 'O3 empty', 'fold': False},
            {'name': 'O4 empty', 'fold': True},
        ])
        Line = self.env['test_read_group.order.line']
        Line.create([
            {'order_expand_id': order_1.id, 'value': 1},
            {'order_expand_id': order_2.id, 'value': 2},
            {'order_expand_id': order_2.id, 'value': 2},
            {'order_expand_id': False, 'value': 3},
        ])

        # 1 for web_read_group + 1 to get length + 1 for fetch display_name/fold
        with self.assertQueryCount(3):
            self.env.invalidate_all()
            self.assertEqual(  # No group_expand limit reached directly
                Line.web_read_group([], ['order_expand_id'], ['value:sum'], limit=2),
                {
                    'groups': [
                        {
                            'order_expand_id': (order_1.id, 'O1'),
                            '__fold': False,
                            '__domain_part': [('order_expand_id', '=', order_1.id)],
                            'value:sum': 1,
                        },
                        {
                            'order_expand_id': (order_2.id, 'O2'),
                            '__fold': True,
                            '__domain_part': [('order_expand_id', '=', order_2.id)],
                            'value:sum': 4,
                        },
                    ],
                    'length': 3,
                },
            )
        # 1 for web_read_group + 1 for fetch display_name/fold
        with self.assertQueryCount(2):
            self.env.invalidate_all()
            self.assertEqual(  # No group_expand because offset
                Line.web_read_group([], ['order_expand_id'], ['value:sum'], offset=1),
                {
                    'groups': [
                        {
                            'order_expand_id': (order_2.id, 'O2'),
                            '__fold': True,
                            '__domain_part': [('order_expand_id', '=', order_2.id)],
                            'value:sum': 4,
                        },
                        {
                            'order_expand_id': False,
                            '__fold': False,
                            '__domain_part': [('order_expand_id', '=', False)],
                            'value:sum': 3,
                        },
                    ],
                    'length': 3,
                },
            )

        # 1 for web_read_group + group expand (discarded) + 1 for fetch display_name/fold
        with self.assertQueryCount(3):
            self.env.invalidate_all()
            self.assertEqual(  # No group_expand because limit reached when we try to add group_expand records
                Line.web_read_group([], ['order_expand_id'], ['value:sum'], limit=4),
                {
                    'groups': [
                        {
                            'order_expand_id': (order_1.id, 'O1'),
                            '__fold': False,
                            '__domain_part': [('order_expand_id', '=', order_1.id)],
                            'value:sum': 1,
                        },
                        {
                            'order_expand_id': (order_2.id, 'O2'),
                            '__fold': True,
                            '__domain_part': [('order_expand_id', '=', order_2.id)],
                            'value:sum': 4,
                        },
                        {
                            'order_expand_id': False,
                            '__fold': False,
                            '__domain_part': [('order_expand_id', '=', False)],
                            'value:sum': 3,
                        },
                    ],
                    'length': 3,
                },
            )

        result = {
            'groups': [
                {
                    'order_expand_id': (order_1.id, 'O1'),
                    '__fold': False,
                    '__domain_part': [('order_expand_id', '=', order_1.id)],
                    'value:sum': 1,
                },
                {
                    'order_expand_id': (order_2.id, 'O2'),
                    '__fold': True,
                    '__domain_part': [('order_expand_id', '=', order_2.id)],
                    'value:sum': 4,
                },
                {
                    'order_expand_id': (order_3.id, 'O3 empty'),
                    '__fold': False,
                    '__domain_part': [('order_expand_id', '=', order_3.id)],
                    'value:sum': False,
                },
                {
                    'order_expand_id': (order_4.id, 'O4 empty'),
                    '__fold': True,
                    '__domain_part': [('order_expand_id', '=', order_4.id)],
                    'value:sum': False,
                },
                {
                    'order_expand_id': False,
                    '__fold': False,
                    '__domain_part': [('order_expand_id', '=', False)],
                    'value:sum': 3,
                },
            ],
            'length': 5,
        }
        # 1 for web_read_group + group expand + 1 for fetch display_name/fold
        with self.assertQueryCount(3):
            self.env.invalidate_all()
            self.assertEqual(  # group_expand because limit isn't reached
                Line.web_read_group([], ['order_expand_id'], ['value:sum'], limit=6),
                result,
            )
        # 1 for web_read_group + group expand + 1 for fetch display_name/fold
        with self.assertQueryCount(3):
            self.env.invalidate_all()
            self.assertEqual(  # group_expand because there isn't limit
                Line.web_read_group([], ['order_expand_id'], ['value:sum']),
                result,
            )
