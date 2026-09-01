from unittest.mock import patch

from odoo.tests import tagged, common


@tagged('at_install', '-post_install')  # LEGACY at_install
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
                    'no_expand': 'c',
                    '__count': 1,
                    'value:sum': 2,
                    '__extra_domain': [('no_expand', '=', 'c')],
                },
                {
                    'no_expand': 'a',
                    '__count': 1,
                    'value:sum': 1,
                    '__extra_domain': [('no_expand', '=', 'a')],
                },
                {
                    'no_expand': False,
                    '__count': 1,
                    'value:sum': 3,
                    '__extra_domain': [('no_expand', '=', False)],
                },
            ],
        )

    def test_multi_level_group_expand(self):
        # 'state' and 'static_expand' are group_expand-flagged, 'no_expand' is not:
        # every 'state' group should appear (even empty ones), for each 'state'
        # group only the real 'no_expand' groups should appear, and for each real
        # (state, no_expand) pair every 'static_expand' group should appear.
        self.Model.create([
            {'state': 'a', 'no_expand': 'b', 'static_expand': 'a', 'value': 1},
            {'state': 'a', 'no_expand': 'b', 'static_expand': 'c', 'value': 2},
            {'state': 'a', 'no_expand': 'a', 'static_expand': 'a', 'value': 3},
            # no record at all for state == 'b'
        ])

        groups = self.Model.formatted_read_group(
            [], ['state', 'no_expand', 'static_expand'], ['__count', 'value:sum'],
        )
        self.assertEqual(
            [(g['state'], g['no_expand'], g['static_expand'], g['__count'], g['value:sum']) for g in groups],
            [
                ('a', 'b', 'c', 1, 2),
                ('a', 'b', 'b', 0, False),
                ('a', 'b', 'a', 1, 1),
                ('a', 'a', 'c', 0, False),
                ('a', 'a', 'b', 0, False),
                ('a', 'a', 'a', 1, 3),
                # state == 'b' has no data at all: a single placeholder row, no
                # sub-groups for 'no_expand'/'static_expand'
                ('b', False, False, 0, False),
            ],
        )

    def test_multi_level_group_expand_desc_order(self):
        self.Model.create([
            {'state': 'a', 'no_expand': 'b', 'static_expand': 'a', 'value': 1},
            {'state': 'a', 'no_expand': 'b', 'static_expand': 'c', 'value': 2},
        ])

        groups = self.Model.formatted_read_group(
            [], ['state', 'no_expand', 'static_expand'], ['__count'],
            order='state, no_expand, static_expand desc',
        )
        self.assertEqual(
            [(g['state'], g['no_expand'], g['static_expand']) for g in groups],
            [
                ('a', 'b', 'a'),
                ('a', 'b', 'b'),
                ('a', 'b', 'c'),
                ('b', False, False),
            ],
        )

    def test_multi_level_group_expand_having(self):
        # group_expand still shows every candidate group even though 'having'
        # filters out some of the real underlying SQL groups.
        self.Model.create([
            {'state': 'a', 'static_expand': 'a', 'value': 1},
            {'state': 'a', 'static_expand': 'c', 'value': 20},
        ])

        groups = self.Model.formatted_read_group(
            [], ['state', 'static_expand'], ['__count', 'value:sum'],
            having=[('value:sum', '>', 5)],
        )
        self.assertEqual(
            [(g['state'], g['static_expand'], g['__count'], g['value:sum']) for g in groups],
            [
                ('a', 'c', 1, 20),
                ('a', 'b', 0, False),
                ('a', 'a', 0, False),
                ('b', False, 0, False),
            ],
        )

    def test_multi_level_group_expand_relational(self):
        # A relational group_expand field used at a level beyond the first: real
        # groups from the (non-expand) first level, then a full expansion for the
        # second (relational) level, with correctly batched display names.
        order_1, order_2, order_3 = self.env['test_read_group.order'].create([
            {'name': 'O1'}, {'name': 'O2'}, {'name': 'O3 unused'},
        ])
        Line = self.env['test_read_group.order.line']
        Line.create([
            {'order_id': order_1.id, 'order_expand_id': order_1.id, 'value': 1},
            {'order_id': order_1.id, 'order_expand_id': order_2.id, 'value': 2},
        ])

        # read_group + group_expand candidates + 1 batched display_name fetch per
        # relational column (order_id, order_expand_id) -- each column's display
        # names are still fetched in a single query, not once per group.
        with self.assertQueryCount(4):
            self.env.invalidate_all()
            groups = Line.formatted_read_group([], ['order_id', 'order_expand_id'], ['value:sum'])

        self.assertEqual(
            [(g['order_id'], g['order_expand_id'], g['value:sum']) for g in groups],
            [
                ((order_1.id, 'O1'), (order_1.id, 'O1'), 1),
                ((order_1.id, 'O1'), (order_2.id, 'O2'), 2),
                ((order_1.id, 'O1'), (order_3.id, 'O3 unused'), False),
            ],
        )

    def test_multi_level_group_expand_shared_prefix_cache(self):
        # Within one formatted_read_grouping_sets call, an expand-flagged level
        # shared by several grouping sets is only resolved once.
        self.Model.create({'state': 'a', 'no_expand': 'b', 'value': 1})
        self.Model.create({'state': 'b', 'no_expand': 'a', 'value': 2})

        calls = []
        origin = type(self.Model)._expand_states

        def _expand_states_spy(self, values, domain):
            calls.append(domain)
            return origin(self, values, domain)

        with patch.object(type(self.Model), '_expand_states', _expand_states_spy):
            groups_list = self.Model.formatted_read_grouping_sets(
                [], [['state'], ['state', 'no_expand']], ['__count'],
            )

        self.assertEqual(len(calls), 1)
        self.assertEqual(
            [(g['state'], g['__count']) for g in groups_list[0]],
            [('a', 1), ('b', 1)],
        )
        self.assertEqual(
            [(g['state'], g['no_expand'], g['__count']) for g in groups_list[1]],
            [('a', 'b', 1), ('b', 'a', 1)],
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
