from unittest.mock import patch

from odoo.tests import common


class TestGroupExpand(common.TransactionCase):
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(**cls.env.context, read_group_expand=True))
        cls.Model = cls.env['test_read_group.on_selection']

    def test_none(self):
        self.Model.create({'value': 1})
        self.Model.create({'value': 2})
        self.Model.create({'value': 3})

        groups = self.Model.formatted_read_group([], ['state'], ['__count', 'value:sum'])
        self.assertEqual(
            groups,
            [
                {
                    'state': 'a',
                    '__count': 0,
                    'value:sum': False,
                    '__extra_domain': [('state', '=', 'a')],
                },
                {
                    'state': 'b',
                    '__count': 0,
                    'value:sum': False,
                    '__extra_domain': [('state', '=', 'b')],
                },
                {
                    'state': False,
                    '__count': 3,
                    'value:sum': 6,
                    '__extra_domain': [('state', '=', False)],
                },
            ],
        )

    def test_partial(self):
        self.Model.create({'state': 'a', 'value': 1})
        self.Model.create({'state': 'a', 'value': 2})
        self.Model.create({'value': 3})

        groups = self.Model.formatted_read_group([], ['state'], ['__count', 'value:sum'])
        self.assertEqual(
            groups,
            [
                {
                    'state': 'a',
                    '__count': 2,
                    'value:sum': 3,
                    '__extra_domain': [('state', '=', 'a')],
                },
                {
                    'state': 'b',
                    '__count': 0,
                    'value:sum': False,
                    '__extra_domain': [('state', '=', 'b')],
                },
                {
                    'state': False,
                    '__count': 1,
                    'value:sum': 3,
                    '__extra_domain': [('state', '=', False)],
                },
            ],
        )

    def test_full(self):
        self.Model.create({'state': 'a', 'value': 1})
        self.Model.create({'state': 'b', 'value': 2})
        self.Model.create({'value': 3})

        groups = self.Model.formatted_read_group([], ['state'], ['__count', 'value:sum'])
        self.assertEqual(
            groups,
            [
                {
                    'state': 'a',
                    '__count': 1,
                    'value:sum': 1,
                    '__extra_domain': [('state', '=', 'a')],
                },
                {
                    'state': 'b',
                    '__count': 1,
                    'value:sum': 2,
                    '__extra_domain': [('state', '=', 'b')],
                },
                {
                    'state': False,
                    '__count': 1,
                    'value:sum': 3,
                    '__extra_domain': [('state', '=', False)],
                },
            ],
        )

    def test_static_group_expand(self):
        # this test verifies that the following happens when grouping by a Selection field with
        # group_expand=True:
        #   - the order of the returned groups is the same as the order in which the
        #     options are declared in the field definition.
        #   - the groups returned include the empty groups, i.e. all groups, even those
        #     that have no records assigned to them, this is a (wanted) side-effect of the
        #     implementation.
        #   - the false group, i.e. records without the Selection field set, is last.
        self.Model.create(
            [
                {"value": 1, "static_expand": "a"},
                {"value": 2, "static_expand": "c"},
                {"value": 3},
            ]
        )

        groups = self.Model.formatted_read_group(
            [],
            groupby=["static_expand"],
            aggregates=["__count", "value:sum"],
        )
        self.assertEqual(
            groups,
            [
                {
                    'static_expand': 'c',
                    '__count': 1,
                    'value:sum': 2,
                    '__extra_domain': [('static_expand', '=', 'c')],
                },
                {
                    'static_expand': 'b',
                    '__count': 0,
                    'value:sum': 0,
                    '__extra_domain': [('static_expand', '=', 'b')],
                },
                {
                    'static_expand': 'a',
                    '__count': 1,
                    'value:sum': 1,
                    '__extra_domain': [('static_expand', '=', 'a')],
                },
                {
                    'static_expand': False,
                    '__count': 1,
                    'value:sum': 3,
                    '__extra_domain': [('static_expand', '=', False)],
                },
            ],
        )

    def test_dynamic_group_expand(self):
        # this test tests the same as the above test but with a Selection field whose
        # options are dynamic, this means that the result of formatted_read_group when grouping by this
        # field can change from one call to another.
        self.Model.create(
            [
                {"value": 1, "dynamic_expand": "a"},
                {"value": 2, "dynamic_expand": "c"},
                {"value": 3},
            ]
        )

        groups = self.Model.formatted_read_group(
            [],
            groupby=["dynamic_expand"],
            aggregates=["__count", "value:sum"],
        )

        self.assertEqual(
            groups,
            [
                {
                    'dynamic_expand': 'c',
                    '__count': 1,
                    'value:sum': 2,
                    '__extra_domain': [('dynamic_expand', '=', 'c')],
                },
                {
                    'dynamic_expand': 'b',
                    '__count': 0,
                    'value:sum': 0,
                    '__extra_domain': [('dynamic_expand', '=', 'b')],
                },
                {
                    'dynamic_expand': 'a',
                    '__count': 1,
                    'value:sum': 1,
                    '__extra_domain': [('dynamic_expand', '=', 'a')],
                },
                {
                    'dynamic_expand': False,
                    '__count': 1,
                    'value:sum': 3,
                    '__extra_domain': [('dynamic_expand', '=', False)],
                },
            ],
        )

    def test_no_group_expand(self):
        # if group_expand is not defined on a Selection field, it should return only the necessary
        # groups and in alphabetical order (PostgreSQL ordering)
        self.Model.create(
            [
                {"value": 1, "no_expand": "a"},
                {"value": 2, "no_expand": "c"},
                {"value": 3},
            ]
        )

        groups = self.Model.formatted_read_group(
            [],
            groupby=["no_expand"],
            aggregates=["__count", "value:sum"],
        )

        self.assertEqual(
            groups,
            [
                {
                    'no_expand': 'a',
                    '__count': 1,
                    'value:sum': 1,
                    '__extra_domain': [('no_expand', '=', 'a')],
                },
                {
                    'no_expand': 'c',
                    '__count': 1,
                    'value:sum': 2,
                    '__extra_domain': [('no_expand', '=', 'c')],
                },
                {
                    'no_expand': False,
                    '__count': 1,
                    'value:sum': 3,
                    '__extra_domain': [('no_expand', '=', False)],
                },
            ],
        )

    def test_with_limit_offset_performance(self):
        order_1, order_2, order_3, order_4 = self.env['test_read_group.order'].create(
            [
                {'name': 'O1', 'fold': False},
                {'name': 'O2', 'fold': True},
                {'name': 'O3 empty', 'fold': False},
                {'name': 'O4 empty', 'fold': True},
            ]
        )
        Line = self.env['test_read_group.order.line']
        Line.create(
            [
                {'order_expand_id': order_1.id, 'value': 1},
                {'order_expand_id': order_2.id, 'value': 2},
                {'order_expand_id': order_2.id, 'value': 2},
                {'order_expand_id': False, 'value': 3},
            ]
        )

        # 1 for formatted_read_group + 1 for fetch display_name/fold
        with self.assertQueryCount(2):
            self.env.invalidate_all()
            self.assertEqual(  # No group_expand limit reached directly
                Line.formatted_read_group([], ['order_expand_id'], ['value:sum'], limit=2),
                [
                    {
                        'order_expand_id': (order_1.id, 'O1'),
                        '__fold': False,
                        '__extra_domain': [('order_expand_id', '=', order_1.id)],
                        'value:sum': 1,
                    },
                    {
                        'order_expand_id': (order_2.id, 'O2'),
                        '__fold': True,
                        '__extra_domain': [('order_expand_id', '=', order_2.id)],
                        'value:sum': 4,
                    },
                ],
            )

        # 1 for formatted_read_group + 1 for fetch display_name/fold
        with self.assertQueryCount(2):
            self.env.invalidate_all()
            self.assertEqual(  # No group_expand because offset
                Line.formatted_read_group([], ['order_expand_id'], ['value:sum'], offset=1),
                [
                    {
                        'order_expand_id': (order_2.id, 'O2'),
                        '__fold': True,
                        '__extra_domain': [('order_expand_id', '=', order_2.id)],
                        'value:sum': 4,
                    },
                    {
                        'order_expand_id': False,
                        '__fold': False,
                        '__extra_domain': [('order_expand_id', '=', False)],
                        'value:sum': 3,
                    },
                ],
            )

        # 1 for formatted_read_group + group expand (discarded) + 1 for fetch display_name/fold
        with self.assertQueryCount(3):
            self.env.invalidate_all()
            self.assertEqual(  # No group_expand because limit reached when we try to add group_expand records
                Line.formatted_read_group([], ['order_expand_id'], ['value:sum'], limit=4),
                [
                    {
                        'order_expand_id': (order_1.id, 'O1'),
                        '__fold': False,
                        '__extra_domain': [('order_expand_id', '=', order_1.id)],
                        'value:sum': 1,
                    },
                    {
                        'order_expand_id': (order_2.id, 'O2'),
                        '__fold': True,
                        '__extra_domain': [('order_expand_id', '=', order_2.id)],
                        'value:sum': 4,
                    },
                    {
                        'order_expand_id': False,
                        '__fold': False,
                        '__extra_domain': [('order_expand_id', '=', False)],
                        'value:sum': 3,
                    },
                ],
            )

        result = [
            {
                'order_expand_id': (order_1.id, 'O1'),
                '__fold': False,
                '__extra_domain': [('order_expand_id', '=', order_1.id)],
                'value:sum': 1,
            },
            {
                'order_expand_id': (order_2.id, 'O2'),
                '__fold': True,
                '__extra_domain': [('order_expand_id', '=', order_2.id)],
                'value:sum': 4,
            },
            {
                'order_expand_id': (order_3.id, 'O3 empty'),
                '__fold': False,
                '__extra_domain': [('order_expand_id', '=', order_3.id)],
                'value:sum': False,
            },
            {
                'order_expand_id': (order_4.id, 'O4 empty'),
                '__fold': True,
                '__extra_domain': [('order_expand_id', '=', order_4.id)],
                'value:sum': False,
            },
            {
                'order_expand_id': False,
                '__fold': False,
                '__extra_domain': [('order_expand_id', '=', False)],
                'value:sum': 3,
            },
        ]
        # 1 for formatted_read_group + group expand + 1 for fetch display_name/fold
        with self.assertQueryCount(3):
            self.env.invalidate_all()
            self.assertEqual(  # group_expand because limit isn't reached
                Line.formatted_read_group([], ['order_expand_id'], ['value:sum'], limit=6),
                result,
            )
        # 1 for formatted_read_group + group expand + 1 for fetch display_name/fold
        with self.assertQueryCount(3):
            self.env.invalidate_all()
            self.assertEqual(  # group_expand because there isn't limit
                Line.formatted_read_group([], ['order_expand_id'], ['value:sum']),
                result,
            )

    def test_performance_prefetch_fold_display_name(self):
        order_1, order_2, order_3, order_unused = self.env["test_read_group.order"].create(
            [
                {"name": "O1", "fold": False},
                {"name": "O2", "fold": True},
                {"name": "O3", "fold": True},
                {"name": "Not used", "fold": True},
            ],
        )
        Line = self.env["test_read_group.order.line"]
        all_lines = Line.create(
            [
                {"order_expand_id": order_1.id, "value": 1},
                {"order_expand_id": order_2.id, "value": 2},
                {"order_expand_id": order_2.id, "value": 2},
                {"order_expand_id": order_3.id, "value": 3},
                {"order_expand_id": False, "value": 3},
            ],
        )

        # 1 for formatted_read_group + 1 for group_expand + 1 for fetch display_name/fold
        with self.assertQueryCount(3):
            self.env.invalidate_all()
            self.assertEqual(
                Line.formatted_read_group([], ["order_expand_id"], ["value:sum"]),
                [
                    {
                        "order_expand_id": (order_1.id, "O1"),
                        "__extra_domain": [("order_expand_id", "=", order_1.id)],
                        "value:sum": 1,
                        "__fold": False,
                    },
                    {
                        "order_expand_id": (order_2.id, "O2"),
                        "__extra_domain": [("order_expand_id", "=", order_2.id)],
                        "value:sum": 4,
                        "__fold": True,
                    },
                    {
                        "order_expand_id": (order_3.id, "O3"),
                        "__extra_domain": [("order_expand_id", "=", order_3.id)],
                        "value:sum": 3,
                        "__fold": True,
                    },
                    {
                        "order_expand_id": (order_unused.id, "Not used"),
                        "__extra_domain": [("order_expand_id", "=", order_unused.id)],
                        "value:sum": False,
                        "__fold": True,
                    },
                    {
                        "order_expand_id": False,
                        "__extra_domain": [("order_expand_id", "=", False)],
                        "value:sum": 3,
                        "__fold": False,
                    },
                ],
            )

        # Same result for formatted_grouping_sets
        self.assertEqual(
            Line.formatted_read_grouping_sets([], [["order_expand_id"], []], ["value:sum"]),
            [
                Line.formatted_read_group([], ["order_expand_id"], ["value:sum"]),
                Line.formatted_read_group([], [], ["value:sum"]),
            ],
        )

        # Modify the data so that each record has the same order,
        # and test that the _compute_display_name is called once with the correct recordset.
        all_lines.order_expand_id = order_1.id
        self.env.invalidate_all()

        old_compute_display_name = self.registry["test_read_group.order"]._compute_display_name

        with patch.object(
            self.registry["test_read_group.order"],
            "_compute_display_name",
            side_effect=old_compute_display_name,
            autospec=True,
        ) as compute_display_name_spy:
            self.assertEqual(
                Line.formatted_read_group([], ["order_expand_id"], ["value:sum"]),
                [
                    {
                        "__extra_domain": [("order_expand_id", "=", order_1.id)],
                        "order_expand_id": (order_1.id, "O1"),
                        "value:sum": 11,
                        '__fold': False,
                    },
                    {
                        '__extra_domain': [('order_expand_id', '=', order_2.id)],
                        '__fold': True,
                        'order_expand_id': (order_2.id, 'O2'),
                        'value:sum': False,
                    },
                    {
                        '__extra_domain': [('order_expand_id', '=', order_3.id)],
                        '__fold': True,
                        'order_expand_id': (order_3.id, 'O3'),
                        'value:sum': False,
                    },
                    {
                        '__extra_domain': [('order_expand_id', '=', order_unused.id)],
                        '__fold': True,
                        'order_expand_id': (order_unused.id, 'Not used'),
                        'value:sum': False,
                    },
                ],
            )
            compute_display_name_spy.assert_called_once()
            self.assertEqual(
                compute_display_name_spy.call_args.args[0].ids,
                (order_1 + order_2 + order_3 + order_unused).ids,
            )
