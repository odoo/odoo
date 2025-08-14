from odoo import Command
from odoo.tests import common, new_test_user


class TestPrivateReadGroupingSets(common.TransactionCase):

    def test_simple_read_grouping_sets(self):
        Model = self.env['test_read_group.aggregate']
        Partner = self.env['res.partner']
        partner_1 = Partner.create({'name': 'z_one'})
        partner_2 = Partner.create({'name': 'a_two'})
        Model.create({'key': 1, 'partner_id': partner_1.id, 'value': 1})
        Model.create({'key': 1, 'partner_id': partner_1.id, 'value': 2})
        Model.create({'key': 1, 'partner_id': partner_2.id, 'value': 3})
        Model.create({'key': 2, 'partner_id': partner_2.id, 'value': 4})
        Model.create({'key': 2, 'partner_id': partner_2.id})
        Model.create({'key': 2, 'value': 5})
        Model.create({'partner_id': partner_2.id, 'value': 5})
        Model.create({'value': 6})
        Model.create({})

        grouping_sets = [['key', 'partner_id'], ['key'], ['partner_id'], []]
        expected_result = [
            Model._read_group([], grouping_set, aggregates=['value:sum'])
            for grouping_set in grouping_sets
        ]

        with self.assertQueries(["""
            SELECT
                GROUPING(
                    "test_read_group_aggregate"."key",
                    "test_read_group_aggregate"."partner_id"
                ),
                "test_read_group_aggregate"."key",
                "test_read_group_aggregate"."partner_id",
                SUM("test_read_group_aggregate"."value")
            FROM
                "test_read_group_aggregate"
            GROUP BY
                GROUPING SETS (
                    ("test_read_group_aggregate"."key", "test_read_group_aggregate"."partner_id"),
                    ("test_read_group_aggregate"."key"),
                    ("test_read_group_aggregate"."partner_id"),
                    ()
                )
            ORDER BY
                "test_read_group_aggregate"."key" ASC,
                "test_read_group_aggregate"."partner_id" ASC
        """]):
            self.assertEqual(
                Model._read_grouping_sets([], grouping_sets, aggregates=['value:sum']),
                expected_result,
            )

        grouping_sets = [['key', 'partner_id'], ['key'], ['partner_id'], []]
        orders = ["partner_id, key", "key", 'partner_id', ""]
        expected_result = [
            Model._read_group([], grouping_set, aggregates=['value:sum'], order=order)
            for grouping_set, order in zip(grouping_sets, orders)
        ]

        # Forcing order with many2one, traverse use the order of the comodel (res.partner)
        with self.assertQueries(["""
            SELECT
                GROUPING(
                    "test_read_group_aggregate"."key",
                    "test_read_group_aggregate"."partner_id"
                ),
                "test_read_group_aggregate"."key",
                "test_read_group_aggregate"."partner_id",
                SUM("test_read_group_aggregate"."value")
            FROM
                "test_read_group_aggregate"
                LEFT JOIN "res_partner" AS "test_read_group_aggregate__partner_id" ON (
                    "test_read_group_aggregate"."partner_id" = "test_read_group_aggregate__partner_id"."id"
                )
            GROUP BY
                GROUPING SETS (
                    (
                        "test_read_group_aggregate"."key",
                        "test_read_group_aggregate"."partner_id",
                        "test_read_group_aggregate__partner_id"."complete_name",
                        "test_read_group_aggregate__partner_id"."id"
                    ),
                    ("test_read_group_aggregate"."key"),
                    (
                        "test_read_group_aggregate"."partner_id",
                        "test_read_group_aggregate__partner_id"."complete_name",
                        "test_read_group_aggregate__partner_id"."id"
                    ),
                    ()
                )
            ORDER BY
                "test_read_group_aggregate__partner_id"."complete_name" ASC,
                "test_read_group_aggregate__partner_id"."id" DESC,
                "test_read_group_aggregate"."key" ASC
        """]):
            self.assertEqual(
                Model._read_grouping_sets([], grouping_sets, aggregates=['value:sum'], order="partner_id, key"),
                expected_result,
            )

    def test_many2many_read_grouping_sets(self):
        User = self.env['test_read_group.user']
        mario, luigi = User.create([{'name': 'Mario'}, {'name': 'Luigi'}])
        tasks = self.env['test_read_group.task'].create([
            {   # both users
                'name': "Super Mario Bros.",
                'user_ids': [Command.set((mario + luigi).ids)],
                'integer': 1,
            },
            {   # mario only
                'name': "Paper Mario",
                'user_ids': [Command.set(mario.ids)],
                'customer_ids': [Command.set(luigi.ids)],
                'integer': 2,
            },
            {   # luigi only
                'name': "Luigi's Mansion",
                'user_ids': [Command.set(luigi.ids)],
                'customer_ids': [Command.set(mario.ids)],
                'integer': 3,
            },
            {   # no user
                'name': 'Donkey Kong',
                'customer_ids': [Command.set((mario + luigi).ids)],
            },
        ])

        domain = [('id', 'in', tasks.ids)]
        grouping_sets = [['user_ids', 'key'], ['key'], ['user_ids'], []]
        aggregates = ['name:array_agg', '__count', 'integer:sum']
        expected_result = [
            tasks._read_group(domain, groupby, aggregates)
            for groupby in grouping_sets
        ]

        with self.assertQueries([
            """
            SELECT
                GROUPING("test_read_group_task__user_ids"."user_id", "test_read_group_task"."key"),
                "test_read_group_task__user_ids"."user_id",
                "test_read_group_task"."key",
                ARRAY_AGG("test_read_group_task"."name" ORDER BY "test_read_group_task"."id"),
                COUNT(*),
                SUM("test_read_group_task"."integer")
            FROM "test_read_group_task"
                LEFT JOIN "test_read_group_task_user_rel" AS "test_read_group_task__user_ids" ON (
                    "test_read_group_task"."id" = "test_read_group_task__user_ids"."task_id"
                )
            WHERE "test_read_group_task"."id" IN %s
            GROUP BY GROUPING SETS (
                ("test_read_group_task__user_ids"."user_id", "test_read_group_task"."key"),
                ("test_read_group_task__user_ids"."user_id"))
            ORDER BY "test_read_group_task__user_ids"."user_id" ASC,
                "test_read_group_task"."key" ASC
            """,
            """
            SELECT
                GROUPING("test_read_group_task"."key"),
                "test_read_group_task"."key",
                ARRAY_AGG("test_read_group_task"."name" ORDER BY "test_read_group_task"."id"),
                COUNT(*),
                SUM("test_read_group_task"."integer")
            FROM "test_read_group_task"
            WHERE "test_read_group_task"."id" IN %s
            GROUP BY GROUPING SETS (("test_read_group_task"."key"), ())
            ORDER BY "test_read_group_task"."key" ASC
            """,
        ]):
            self.assertEqual(
                tasks._read_grouping_sets(domain, grouping_sets, aggregates),
                expected_result,
            )

        complete_order = "user_ids DESC, key"
        grouping_sets = [['user_ids', 'key'], ['key'], ['user_ids'], []]
        orders = ["user_ids DESC, key", "key", "user_ids DESC", '']
        aggregates = ['name:array_agg', '__count', 'integer:sum']
        expected_result = [
            tasks._read_group(domain, groupby, aggregates, order=order)
            for groupby, order in zip(grouping_sets, orders)
        ]

        with self.assertQueries([
            """
            SELECT
                GROUPING("test_read_group_task__user_ids"."user_id", "test_read_group_task"."key"),
                "test_read_group_task__user_ids"."user_id",
                "test_read_group_task"."key",
                ARRAY_AGG("test_read_group_task"."name" ORDER BY "test_read_group_task"."id"),
                COUNT(*),
                SUM("test_read_group_task"."integer")
            FROM "test_read_group_task"
                LEFT JOIN "test_read_group_task_user_rel" AS "test_read_group_task__user_ids" ON (
                    "test_read_group_task"."id" = "test_read_group_task__user_ids"."task_id"
                )
            WHERE "test_read_group_task"."id" IN %s
            GROUP BY GROUPING SETS (
                ("test_read_group_task__user_ids"."user_id", "test_read_group_task"."key"),
                ("test_read_group_task__user_ids"."user_id"))
            ORDER BY "test_read_group_task__user_ids"."user_id" DESC,
                "test_read_group_task"."key" ASC
            """,
            """
            SELECT
                GROUPING("test_read_group_task"."key"),
                "test_read_group_task"."key",
                ARRAY_AGG("test_read_group_task"."name" ORDER BY "test_read_group_task"."id"),
                COUNT(*),
                SUM("test_read_group_task"."integer")
            FROM "test_read_group_task"
            WHERE "test_read_group_task"."id" IN %s
            GROUP BY GROUPING SETS (("test_read_group_task"."key"), ())
            ORDER BY "test_read_group_task"."key" ASC
            """,
        ]):
            self.assertEqual(
                tasks._read_grouping_sets(domain, grouping_sets, aggregates, order=complete_order),
                expected_result,
            )

        cases = [
            {
                # Test 2 many2manys
                'grouping_sets': [
                    ['user_ids', 'customer_ids'], ['key'], ['user_ids'], ['customer_ids'], ['key', 'customer_ids'], []
                ],
                'aggregates': ['__count', 'integer:sum'],
                # 1 for ('user_ids', 'customer_ids') + 1 for ('user_ids',) + 1 for ('customer_ids',) + 1 for remaining (key, [])
                'nb_queries': 4,
            },
            {
                # Test that __count doesn't make a extra query
                'grouping_sets': [['user_ids', 'key'], ['key'], ['user_ids'], []],
                'aggregates': ['__count'],
                'nb_queries': 1,
            },
            {
                # Test that __count as order
                'grouping_sets': [['user_ids', 'customer_ids'], ['key'], ['user_ids'], []],
                'read_group_orders': [
                    "__count, user_ids, customer_ids",
                    "__count, key",
                    "__count, user_ids",
                    "__count",
                ],
                'complete_order': "__count, user_ids, customer_ids, key",
                'aggregates': ['__count', 'integer:min', 'integer:max', 'integer:count_distinct'],
                'nb_queries': 1,
            },
            {
                # Everything
                'grouping_sets': [
                    ['user_ids', 'customer_ids'],
                    ['key'],
                    ['integer'],
                    [],
                    ['customer_ids'],
                    ['key', 'customer_ids'],
                    ['integer', 'customer_ids'],
                ],
                'read_group_orders': [
                    "__count DESC, customer_ids DESC, user_ids",
                    "key, __count DESC",
                    "__count DESC, integer",
                    "__count DESC",
                    "__count DESC, customer_ids DESC",
                    "key, __count DESC, customer_ids DESC",
                    "__count DESC, customer_ids DESC, integer",
                ],
                'complete_order': "key, __count DESC, customer_ids DESC, integer, user_ids",
                'aggregates': ['integer:sum', '__count'],
                # 1 for ('user_ids', 'customer_ids') + 1 for ('customer_ids',) + 1 for remainings grouping set
                'nb_queries': 3,
            },
        ]

        for i, case in enumerate(cases):
            nb_queries = case['nb_queries']
            aggregates = case['aggregates']
            grouping_sets = case['grouping_sets']
            read_group_orders = case.get('read_group_orders', [""] * len(grouping_sets))
            complete_order = case.get('complete_order')

            expected_result = [
                tasks._read_group(domain, groupby, aggregates, order=order)
                for groupby, order in zip(grouping_sets, read_group_orders)
            ]
            with self.subTest(f"Case {i} - {grouping_sets!r} - {aggregates!r}"), self.assertQueryCount(nb_queries):
                result = tasks._read_grouping_sets(domain, grouping_sets, aggregates, order=complete_order)
                self.assertEqual(result, expected_result)


class TestFormattedReadGroupingSets(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.base_user = new_test_user(cls.env, login='Base User', groups='base.group_user')

    def test_simple_formatted_read_grouping_sets(self):
        Model = self.env['test_read_group.aggregate']
        Partner = self.env['res.partner']
        partner_1 = Partner.create({'name': 'z_one'})
        partner_2 = Partner.create({'name': 'a_two'})
        Model.create({'key': 1, 'partner_id': partner_1.id, 'value': 1})
        Model.create({'key': 1, 'partner_id': partner_1.id, 'value': 2})
        Model.create({'key': 1, 'partner_id': partner_2.id, 'value': 3})
        Model.create({'key': 2, 'partner_id': partner_2.id, 'value': 4})
        Model.create({'key': 2, 'partner_id': partner_2.id})
        Model.create({'key': 2, 'value': 5})
        Model.create({'partner_id': partner_2.id, 'value': 5})
        Model.create({'value': 6})
        Model.create({})

        grouping_sets = [['partner_id', 'key'], ['key'], ['partner_id'], []]
        expected_result = [
            Model.formatted_read_group([], grouping_set, aggregates=['value:sum'])
            for grouping_set in grouping_sets
        ]

        with self.assertQueries(["""
            SELECT
                GROUPING(
                    "test_read_group_aggregate"."partner_id",
                    "test_read_group_aggregate"."key"
                ),
                "test_read_group_aggregate"."partner_id",
                "test_read_group_aggregate"."key",
                SUM("test_read_group_aggregate"."value")
            FROM
                "test_read_group_aggregate"
                LEFT JOIN "res_partner" AS "test_read_group_aggregate__partner_id" ON (
                    "test_read_group_aggregate"."partner_id" = "test_read_group_aggregate__partner_id"."id"
                )
            GROUP BY
                GROUPING SETS (
                    (
                        "test_read_group_aggregate"."partner_id",
                        "test_read_group_aggregate__partner_id"."complete_name",
                        "test_read_group_aggregate__partner_id"."id",
                        "test_read_group_aggregate"."key"
                    ),
                    ("test_read_group_aggregate"."key"),
                    (
                        "test_read_group_aggregate"."partner_id",
                        "test_read_group_aggregate__partner_id"."complete_name",
                        "test_read_group_aggregate__partner_id"."id"
                    ),
                    ()
                )
            ORDER BY
                "test_read_group_aggregate__partner_id"."complete_name" ASC,
                "test_read_group_aggregate__partner_id"."id" DESC,
                "test_read_group_aggregate"."key" ASC
        """]):
            self.assertEqual(
                Model.formatted_read_grouping_sets([], grouping_sets, aggregates=['value:sum']),
                expected_result,
            )

    def test_many2many_formatted_read_grouping_sets(self):
        User = self.env['test_read_group.user']
        mario, luigi = User.create([{'name': 'Mario'}, {'name': 'Luigi'}])
        tasks = self.env['test_read_group.task'].create([
            {   # both users
                'name': "Super Mario Bros.",
                'user_ids': [Command.set((mario + luigi).ids)],
                'integer': 1,
            },
            {   # mario only
                'name': "Paper Mario",
                'user_ids': [Command.set(mario.ids)],
                'customer_ids': [Command.set(luigi.ids)],
                'integer': 2,
            },
            {   # luigi only
                'name': "Luigi's Mansion",
                'user_ids': [Command.set(luigi.ids)],
                'customer_ids': [Command.set(mario.ids)],
                'integer': 3,
            },
            {   # no user
                'name': 'Donkey Kong',
                'customer_ids': [Command.set((mario + luigi).ids)],
            },
        ])

        domain = [('id', 'in', tasks.ids)]
        grouping_sets = [['user_ids', 'key'], ['key'], ['user_ids'], []]
        aggregates = ['name:array_agg', '__count', 'integer:sum']
        expected_result = [
            tasks.formatted_read_group(domain, groupby, aggregates)
            for groupby in grouping_sets
        ]

        self.assertEqual(
            tasks.formatted_read_grouping_sets(domain, grouping_sets, aggregates),
            expected_result,
        )

        complete_order = "user_ids DESC, key"
        grouping_sets = [['user_ids', 'key'], ['key'], ['user_ids'], []]
        orders = ["user_ids DESC, key", "key", "user_ids DESC", '']
        aggregates = ['name:array_agg', '__count', 'integer:sum']
        expected_result = [
            tasks.formatted_read_group(domain, groupby, aggregates, order=order)
            for groupby, order in zip(grouping_sets, orders)
        ]

        self.assertEqual(
            tasks.formatted_read_grouping_sets(domain, grouping_sets, aggregates, order=complete_order),
            expected_result,
        )

        cases = [
            {
                # Test 2 many2manys
                'grouping_sets': [
                    ['user_ids', 'customer_ids'], ['key'], ['user_ids'], ['customer_ids'], ['key', 'customer_ids'], []
                ],
                'aggregates': ['__count', 'integer:sum'],
                # 1 for ('user_ids', 'customer_ids') + 1 for ('user_ids',) + 1 for ('customer_ids',) + 1 for remaining (key, [])
                'nb_queries': 4,
            },
            {
                # Test that __count doesn't make a extra query
                'grouping_sets': [['user_ids', 'key'], ['key'], ['user_ids'], []],
                'aggregates': ['__count'],
                'nb_queries': 1,
            },
            {
                # Test that __count as order
                'grouping_sets': [['user_ids', 'customer_ids'], ['key'], ['user_ids'], []],
                'read_group_orders': [
                    "__count, user_ids, customer_ids",
                    "__count, key",
                    "__count, user_ids",
                    "__count",
                ],
                'complete_order': "__count, user_ids, customer_ids, key",
                'aggregates': ['__count', 'integer:min', 'integer:max', 'integer:count_distinct'],
                'nb_queries': 1,
            },
            {
                # Everything
                'grouping_sets': [
                    ['user_ids', 'customer_ids'],
                    ['key'],
                    ['integer'],
                    [],
                    ['customer_ids'],
                    ['key', 'customer_ids'],
                    ['integer', 'customer_ids'],
                ],
                'read_group_orders': [
                    "__count DESC, customer_ids DESC, user_ids",
                    "key, __count DESC",
                    "__count DESC, integer",
                    "__count DESC",
                    "__count DESC, customer_ids DESC",
                    "key, __count DESC, customer_ids DESC",
                    "__count DESC, customer_ids DESC, integer",
                ],
                'complete_order': "key, __count DESC, customer_ids DESC, integer, user_ids",
                'aggregates': ['integer:sum', '__count'],
                # 1 for ('user_ids', 'customer_ids') + 1 for ('customer_ids',) + 1 for remainings grouping set
                'nb_queries': 3,
            },
        ]

        for i, case in enumerate(cases):
            nb_queries = case['nb_queries']
            aggregates = case['aggregates']
            grouping_sets = case['grouping_sets']
            read_group_orders = case.get('read_group_orders', [""] * len(grouping_sets))
            complete_order = case.get('complete_order')

            expected_result = [
                tasks.formatted_read_group(domain, groupby, aggregates, order=order)
                for groupby, order in zip(grouping_sets, read_group_orders)
            ]
            with self.subTest(f"Case {i} - {grouping_sets!r} - {aggregates!r}"), self.assertQueryCount(nb_queries):
                result = tasks.formatted_read_grouping_sets(domain, grouping_sets, aggregates, order=complete_order)
                self.assertEqual(result, expected_result)

    def test_related(self):
        RelatedBar = self.env['test_read_group.related_bar']
        RelatedFoo = self.env['test_read_group.related_foo']
        RelatedBase = self.env['test_read_group.related_base']

        bars = RelatedBar.create(
            [
                {'name': 'bar_a'},
                {'name': False},
            ],
        )

        foos = RelatedFoo.create(
            [
                {'name': 'foo_a_bar_a', 'bar_id': bars[0].id},
                {'name': 'foo_b_bar_false', 'bar_id': bars[1].id},
                {'name': False, 'bar_id': bars[0].id},
                {'name': False},
            ],
        )

        RelatedBase.create(
            [
                {'name': 'base_foo_a_1', 'foo_id': foos[0].id},
                {'name': 'base_foo_a_2', 'foo_id': foos[0].id},
                {'name': 'base_foo_b_bar_false', 'foo_id': foos[1].id},
                {'name': 'base_false_foo_bar_a', 'foo_id': foos[2].id},
                {'name': 'base_false_foo', 'foo_id': foos[3].id},
            ],
        )

        # env.su => false
        RelatedBase = RelatedBase.with_user(self.base_user)

        grouping_sets = [
            ['foo_id_name_sudo', 'foo_id_bar_id_name', 'name'],
            ['foo_id_name_sudo', 'foo_id_bar_id_name'],
            ['name'],
            [],
        ]
        self.assertEqual(
            RelatedBase.formatted_read_grouping_sets([], grouping_sets, ['__count', 'name:array_agg']),
            [
                RelatedBase.formatted_read_group([], groupby, ['__count', 'name:array_agg'])
                for groupby in grouping_sets
            ],
        )

        # Cannot groupby on foo_names_sudo because it traverse One2many
        with self.assertRaises(ValueError):
            RelatedBar.formatted_read_grouping_sets([], [['foo_names_sudo']], ['__count'])

    def test_groupby_sequence_fnames(self):
        RelatedBar = self.env['test_read_group.related_bar']
        RelatedFoo = self.env['test_read_group.related_foo']
        RelatedBase = self.env['test_read_group.related_base']

        bars = RelatedBar.create([
            {'name': 'bar_a'},
            {'name': False},
        ])

        foos = RelatedFoo.create([
            {'name': 'foo_a_bar_a', 'bar_id': bars[0].id},
            {'name': 'foo_b_bar_false', 'bar_id': bars[1].id},
            {'name': False, 'bar_id': bars[0].id},
            {'name': False},
        ])

        RelatedBase.create([
            {'name': 'base_foo_a_1', 'foo_id': foos[0].id},
            {'name': 'base_foo_a_2', 'foo_id': foos[0].id},
            {'name': 'base_foo_b_bar_false', 'foo_id': foos[1].id},
            {'name': 'base_false_foo_bar_a', 'foo_id': foos[2].id},
            {'name': 'base_false_foo', 'foo_id': foos[3].id},
        ])

        grouping_sets = [
            ['foo_id.bar_id.name', 'foo_id.bar_id', 'foo_id', 'name'],
            ['foo_id.bar_id.name', 'foo_id.bar_id'],
            ['name'],
            [],
        ]

        self.assertEqual(
            RelatedBase.formatted_read_grouping_sets([], grouping_sets, ['__count', 'name:array_agg']),
            [
                RelatedBase.formatted_read_group([], groupby, ['__count', 'name:array_agg'])
                for groupby in grouping_sets
            ],
        )

    def test_sequence_inherited_fname(self):
        RelatedBase = self.env['test_read_group.related_base']
        RelatedInherits = self.env['test_read_group.related_inherits']
        SequenceInherits = self.env['test_read_group.sequence_inherits']

        bases = RelatedBase.create([
            {'name': 'a', 'value': 1},
            {'name': 'a', 'value': 2},
            {'name': 'b', 'value': 3},
            {'name': False, 'value': 4},
        ])
        inherits_records = RelatedInherits.create([
            {'base_id': bases[0].id},
            {'base_id': bases[0].id},
            {'base_id': bases[1].id},
            {'base_id': bases[2].id},
            {'base_id': bases[3].id},
        ])

        SequenceInherits.create([
            {'inherited_id': inherits_records[0].id},
            {'inherited_id': inherits_records[1].id},
            {'inherited_id': inherits_records[2].id},
            {'inherited_id': inherits_records[3].id},
            {'inherited_id': inherits_records[3].id},
        ])

        # env.su => false
        SequenceInherits = SequenceInherits.with_user(self.base_user)

        inherits_model = self.env['ir.model']._get(RelatedInherits._name)
        self.env['ir.rule'].create({
            'name': "AAAAAAA",
            'model_id': inherits_model.id,
            'domain_force': [('id', 'in', inherits_records[1:].ids)],
        })

        grouping_sets = [['inherited_id.value'], ['inherited_id.base_id.name'], ['inherited_id.foo_id.name'], []]
        expected_result = [
            SequenceInherits.formatted_read_group([], groupby, ['__count'])
            for groupby in grouping_sets
        ]
        self.assertEqual(
            SequenceInherits.formatted_read_grouping_sets([], grouping_sets, ['__count']),
            expected_result,
        )

    def test_sequence_many2many(self):
        RelatedBase = self.env['test_read_group.related_base']
        RelatedBar = self.env['test_read_group.related_bar']
        RelatedFoo = self.env['test_read_group.related_foo']

        bases = RelatedBase.create(
            [
                {'name': 'A'},
                {'name': 'B'},
                {'name': 'C'},
                {'name': 'D'},
            ],
        )
        bars = RelatedBar.create(
            [
                {'base_ids': [Command.link(bases[0].id)]},
                {'base_ids': [Command.link(bases[0].id), Command.link(bases[1].id)]},
                {'base_ids': [Command.link(bases[2].id)]},
                {'base_ids': []},
            ],
        )
        foos = RelatedFoo.create(
            [
                {'bar_id': bars[0].id},
                {'bar_id': bars[0].id},
                {'bar_id': bars[1].id},
                {'bar_id': bars[2].id},
                {'bar_id': bars[3].id},
            ],
        )

        aggregates_sets = [['__count'], ['__count', 'id:sum'], ['id:max']]
        grouping_sets = [['bar_id.base_ids'], ['bar_id'], []]

        for aggregates in aggregates_sets:
            expected_result = [
                RelatedFoo.formatted_read_group([], groupby, aggregates)
                for groupby in grouping_sets
            ]
            self.assertEqual(
                RelatedFoo.formatted_read_grouping_sets([], grouping_sets, aggregates),
                expected_result,
            )

        bases[0].foo_id = foos[0].id
        (bases[1] + bases[2]).foo_id = foos[1].id

        grouping_sets = [['foo_id.bar_id.base_ids'], ['foo_id.bar_name'], ['value'], []]
        for aggregates in aggregates_sets:
            expected_result = [
                RelatedBase.formatted_read_group([], groupby, aggregates)
                for groupby in grouping_sets
            ]
            self.assertEqual(
                RelatedBase.formatted_read_grouping_sets([], grouping_sets, aggregates),
                expected_result,
            )

        # Targeting the same source field but with different path
        grouping_sets = [
            [],
            # Targeting the same many2many
            ['foo_id.bar_id.base_ids'],
            ['foo_id.bar_base_ids'],
            # All targeting foo_id.name
            ['foo_id.name'],
            ['foo_id.name'],
            ['foo_id_name'],
            ['foo_id_name_sudo'],
            ['foo_id_name_sudo', 'value'],
            # All targeting foo_id.bar_id.name
            ['foo_id.bar_id.name'],
            ['foo_id_bar_id_name'],
            ['foo_id_bar_name'],
        ]
        for aggregates in aggregates_sets:
            expected_result = [
                RelatedBase.formatted_read_group([], groupby, aggregates)
                for groupby in grouping_sets
            ]
            self.assertEqual(
                RelatedBase.formatted_read_grouping_sets([], grouping_sets, aggregates),
                expected_result,
            )
