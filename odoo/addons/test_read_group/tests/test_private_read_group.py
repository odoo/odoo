# -*- coding: utf-8 -*-
from odoo import fields
from odoo.tests import common
from odoo import Command


class TestPrivateReadGroup(common.TransactionCase):

    def test_simple_private_read_group(self):
        Model = self.env['test_read_group.aggregate']
        partner_1 = self.env['res.partner'].create({'name': 'z_one'})
        partner_2 = self.env['res.partner'].create({'name': 'a_two'})
        Model.create({'key': 1, 'partner_id': partner_1.id, 'value': 1})
        Model.create({'key': 1, 'partner_id': partner_1.id, 'value': 2})
        Model.create({'key': 1, 'partner_id': partner_2.id, 'value': 3})
        Model.create({'key': 2, 'partner_id': partner_2.id, 'value': 4})
        Model.create({'key': 2, 'partner_id': partner_2.id})
        Model.create({'key': 2, 'value': 5})
        Model.create({'partner_id': partner_2.id, 'value': 5})
        Model.create({'value': 6})
        Model.create({})

        with self.assertQueries(["""
            SELECT "test_read_group_aggregate"."key",
                   SUM("test_read_group_aggregate"."value")
            FROM "test_read_group_aggregate"
            GROUP BY "test_read_group_aggregate"."key"
            ORDER BY "test_read_group_aggregate"."key" ASC
        """]):
            self.assertEqual(
                Model._read_group([], groupby=['key'], aggregates=['value:sum']),
                [
                    (1, 1 + 2 + 3),
                    (2, 4 + 5),
                    (False, 5 + 6),
                ],
            )

        # Forcing order with many2one, traverse use the order of the comodel (res.partner)
        with self.assertQueries(["""
            SELECT "test_read_group_aggregate"."key",
                   "test_read_group_aggregate"."partner_id",
                   SUM("test_read_group_aggregate"."value")
            FROM "test_read_group_aggregate"
            LEFT JOIN "res_partner" AS "test_read_group_aggregate__partner_id"
                ON ("test_read_group_aggregate"."partner_id" = "test_read_group_aggregate__partner_id"."id")
            GROUP BY "test_read_group_aggregate"."key",
                     "test_read_group_aggregate"."partner_id",
                     "test_read_group_aggregate__partner_id"."complete_name",
                     "test_read_group_aggregate__partner_id"."id"
            ORDER BY "test_read_group_aggregate"."key" ASC,
                     "test_read_group_aggregate__partner_id"."complete_name" ASC,
                     "test_read_group_aggregate__partner_id"."id" DESC
        """]):
            self.assertEqual(
                Model._read_group([], groupby=['key', 'partner_id'], aggregates=['value:sum'], order="key, partner_id"),
                [
                    (1, partner_2, 3),
                    (1, partner_1, 1 + 2),
                    (2, partner_2, 4),
                    (2, self.env['res.partner'], 5),
                    (False, partner_2, 5),
                    (False, self.env['res.partner'], 6),
                ],
            )

        # Same than before but with private method, the order doesn't traverse
        # many2one order, then the order is based on id of partner
        with self.assertQueries(["""
            SELECT "test_read_group_aggregate"."key",
                   "test_read_group_aggregate"."partner_id",
                   SUM("test_read_group_aggregate"."value")
            FROM "test_read_group_aggregate"
            GROUP BY "test_read_group_aggregate"."key",
                     "test_read_group_aggregate"."partner_id"
            ORDER BY "test_read_group_aggregate"."key" ASC,
                     "test_read_group_aggregate"."partner_id" ASC
        """]):
            self.assertEqual(
                Model._read_group([], groupby=['key', 'partner_id'], aggregates=['value:sum']),
                [
                    (1, partner_1, 1 + 2),
                    (1, partner_2, 3),
                    (2, partner_2, 4),
                    (2, self.env['res.partner'], 5),
                    (False, partner_2, 5),
                    (False, self.env['res.partner'], 6),
                ],
            )

    def test_falsy_domain(self):
        Model = self.env['test_read_group.aggregate']

        with self.assertQueryCount(0):
            result = Model._read_group([('id', 'in', [])], groupby=['partner_id'], aggregates=[])
            self.assertEqual(result, [])

        with self.assertQueryCount(0):
            result = Model._read_group(
                [('id', 'in', [])],
                groupby=[],
                aggregates=['__count', 'partner_id:count', 'partner_id:count_distinct'],
            )
            # When there are no groupby, postgresql return always one row, check
            # that it is the case when the domain is falsy and the query is not
            # made at all
            self.assertEqual(result, [(0, 0, 0)])

    def test_prefetch_for_records(self):
        Model = self.env['test_read_group.aggregate']
        Partner = self.env['res.partner']
        partner_1 = Partner.create({'name': 'z_one'})
        partner_2 = Partner.create({'name': 'a_two'})
        Model.create({'key': 1, 'partner_id': partner_1.id})
        Model.create({'key': 2, 'partner_id': partner_2.id})

        self.env.invalidate_all()

        result = Model._read_group([], ['partner_id'], [])

        # partner_1 and partner_2 are records
        self.assertEqual(result, [(partner_1,), (partner_2,)])
        [[value1], [value2]] = result
        value1.name
        with self.assertQueryCount(0):
            # already prefetched with value1.name above
            value2.name

        self.env.invalidate_all()

        result = Model._read_group([], ['key'], ['partner_id:recordset'])
        self.assertEqual(result, [(1, partner_1), (2, partner_2)])
        [[__, value1], [__, value2]] = result
        value1.name
        with self.assertQueryCount(0):
            # already prefetched with value1.name above
            value2.name

    def test_ambiguous_field_name(self):
        """ Check that _read_group doesn't generate ambiguous (display_name) alias for PostgreSQL
        """
        Model = self.env['test_read_group.aggregate']
        partner_1 = self.env['res.partner'].create({'name': 'z_one'})
        Model.create({'key': 1, 'partner_id': partner_1.id, 'value': 1, 'display_name': 'blabla'})

        with self.assertQueries(["""
            SELECT "test_read_group_aggregate"."display_name",
                   "test_read_group_aggregate"."partner_id",
                   COUNT(*)
            FROM "test_read_group_aggregate"
            LEFT JOIN "res_partner" AS "test_read_group_aggregate__partner_id"
                ON ("test_read_group_aggregate"."partner_id" = "test_read_group_aggregate__partner_id"."id")
            GROUP BY "test_read_group_aggregate"."display_name",
                     "test_read_group_aggregate"."partner_id",
                     "test_read_group_aggregate__partner_id"."complete_name",
                     "test_read_group_aggregate__partner_id"."id"
            ORDER BY "test_read_group_aggregate__partner_id"."complete_name" DESC,
                     "test_read_group_aggregate__partner_id"."id" ASC
        """]):
            result = Model._read_group(
                [],
                groupby=['display_name', 'partner_id'],
                aggregates=['__count'],
                order="partner_id DESC",
            )
            self.assertEqual(result, [('blabla', partner_1, 1)])

    def test_bool_read_groups(self):
        Model = self.env['test_read_group.aggregate.boolean']
        Model.create({'key': 1, 'bool_and': True})
        Model.create({'key': 1, 'bool_and': True})

        Model.create({'key': 2, 'bool_and': True})
        Model.create({'key': 2, 'bool_and': False})

        Model.create({'key': 3, 'bool_and': False})
        Model.create({'key': 3, 'bool_and': False})

        Model.create({'key': 4, 'bool_and': True, 'bool_or': True, 'bool_array': True})
        Model.create({'key': 4})

        result = Model._read_group(
            [],
            groupby=['key'],
            aggregates=['bool_and:bool_and', 'bool_and:bool_or', 'bool_and:array_agg'],
        )
        self.assertEqual(result, [
            (1, True, True, [True, True]),
            (2, False, True, [True, False]),
            (3, False, False, [False, False]),
            (4, False, True, [True, False]),
        ])

    def test_count_read_groups(self):
        Model = self.env['test_read_group.aggregate']
        Model.create({'key': 1})
        Model.create({'key': 1})
        Model.create({})

        self.assertEqual(
            Model._read_group([], aggregates=['key:count']),
            [(2,)],
        )

        self.assertEqual(
            Model._read_group([], aggregates=['key:count_distinct']),
            [(1,)],
        )

    def test_array_read_groups(self):
        Model = self.env['test_read_group.aggregate']
        Model.create({'partner_id': 1})
        Model.create({'partner_id': 1})
        Model.create({'partner_id': 2})

        self.assertEqual(
            Model._read_group([], aggregates=['partner_id:array_agg']),
            [([1, 1, 2],)],
        )

        self.assertEqual(
            Model._read_group([], aggregates=['partner_id:recordset']),
            [(self.env['res.partner'].browse([1, 2]),)],
        )

    def test_flush_read_group(self):
        Model = self.env['test_read_group.aggregate']
        a = Model.create({'key': 1, 'value': 5})
        b = Model.create({'key': 1, 'value': 5})

        self.assertEqual(
            Model._read_group([], groupby=['key'], aggregates=['value:sum']),
            [(1, 5 + 5)],
        )

        # Test flush of domain
        a.key = 2
        self.assertEqual(
            Model._read_group([('key', '>', 1)], groupby=['key'], aggregates=['value:sum']),
            [
                (2, 5),
            ],
        )

        # test flush of groupby clause
        a.key = 3
        self.assertEqual(
            Model._read_group([], groupby=['key'], aggregates=['value:sum']),
            [
                (1, 5),
                (3, 5),
            ],
        )

        # Test flush of _read_groups
        b.value = 8
        self.assertEqual(
            Model._read_group([], groupby=['key'], aggregates=['value:sum']),
            [
                (1, 8),
                (3, 5),
            ],
        )

    def test_having_clause(self):
        Model = self.env['test_read_group.aggregate']
        Model.create({'key': 1, 'value': 8})
        Model.create({'key': 1, 'value': 2})
        Model.create({'key': 2, 'value': 5})
        Model.create({'key': 3, 'value': 2})
        Model.create({'key': 3, 'value': 4})
        Model.create({'key': 3, 'value': 1})

        with self.assertQueries(["""
            SELECT "test_read_group_aggregate"."key",
                   SUM("test_read_group_aggregate"."value")
            FROM "test_read_group_aggregate"
            GROUP BY "test_read_group_aggregate"."key"
            HAVING SUM("test_read_group_aggregate"."value") > %s
            ORDER BY "test_read_group_aggregate"."key" ASC
        """]):
            self.assertEqual(
                Model._read_group(
                    [],
                    groupby=['key'],
                    aggregates=['value:sum'],
                    having=[('value:sum', '>', 8)],
                ),
                [(1, 2 + 8)],
            )

        with self.assertQueries(["""
            SELECT "test_read_group_aggregate"."key",
                   SUM("test_read_group_aggregate"."value"),
                   COUNT(*)
            FROM "test_read_group_aggregate"
            GROUP BY "test_read_group_aggregate"."key"
            HAVING (COUNT(*) < %s AND SUM("test_read_group_aggregate"."value") > %s)
            ORDER BY "test_read_group_aggregate"."key" ASC
        """]):
            self.assertEqual(
                Model._read_group(
                    [],
                    groupby=['key'],
                    aggregates=['value:sum', '__count'],
                    having=[('__count', '<', 3), ("value:sum", '>', 4)],
                ),
                [
                    (1, 2 + 8, 2),
                    (2, 5, 1),
                ],
            )

    def test_malformed_params(self):
        Model = self.env['test_read_group.fill_temporal']
        # Test malformed groupby clause
        with self.assertRaises(ValueError):
            Model._read_group([], ['date:bad_granularity'])

        with self.assertRaises(ValueError):
            Model._read_group([], ['Other stuff date:week'])

        with self.assertRaises(ValueError):
            Model._read_group([], ['date'])  # No granularity

        with self.assertRaises(ValueError):
            Model._read_group([], ['"date:week'])

        # Test malformed aggregate clause
        with self.assertRaises(ValueError):
            Model._read_group([], aggregates=['value'])  # No aggregate

        with self.assertRaises(ValueError):
            Model._read_group([], aggregates=['__count_'])

        with self.assertRaises(ValueError):
            Model._read_group([], aggregates=['value:__count'])

        with self.assertRaises(ValueError):
            Model._read_group([], aggregates=['other value:sum'])

        with self.assertRaises(ValueError):
            Model._read_group([], aggregates=['value:array_agg OR'])

        with self.assertRaises(ValueError):
            Model._read_group([], aggregates=['"value:sum'])

        with self.assertRaises(ValueError):
            Model._read_group([], aggregates=['label:sum(value)'])

        # Test malformed having clause
        with self.assertRaises(ValueError):
            Model._read_group([], ['value'], having=[('__count', '>')])

        with self.assertRaises(ValueError):
            Model._read_group([], ['value'], having=["COUNT(*) > 2"])

        with self.assertRaises(ValueError):
            Model._read_group([], ['value'], having=[('"="')])

        # Test malformed order clause
        with self.assertRaises(ValueError):
            Model._read_group([], ['value'], order='__count DESC other')

        with self.assertRaises(ValueError):
            Model._read_group([], ['value'], order='value" DESC')

        with self.assertRaises(ValueError):
            Model._read_group([], ['value'], order='value ASCCC')

    def test_groupby_date(self):
        """ Test what happens when grouping on date fields """
        Model = self.env['test_read_group.fill_temporal']
        Model.create({})  # Falsy date
        Model.create({'date': '2022-01-29'})  # Saturday (week of '2022-01-24')
        Model.create({'date': '2022-01-29'})  # Same day
        Model.create({'date': '2022-01-30'})  # Sunday
        Model.create({'date': '2022-01-31'})  # Monday (other week)
        Model.create({'date': '2022-02-01'})  # (other month)
        Model.create({'date': '2022-05-29'})  # other quarter
        Model.create({'date': '2023-01-29'})  # other year

        result = Model._read_group([], [], ['date:array_agg'])
        self.assertEqual(result, [
            (
                [
                    None,
                    fields.Date.to_date('2022-01-29'),
                    fields.Date.to_date('2022-01-29'),
                    fields.Date.to_date('2022-01-30'),
                    fields.Date.to_date('2022-01-31'),
                    fields.Date.to_date('2022-02-01'),
                    fields.Date.to_date('2022-05-29'),
                    fields.Date.to_date('2023-01-29'),
                ],
            ),
        ])

        result = Model._read_group([], ['date:day'], ['__count'])
        self.assertEqual(result, [
            (fields.Date.to_date('2022-01-29'), 2),
            (fields.Date.to_date('2022-01-30'), 1),
            (fields.Date.to_date('2022-01-31'), 1),
            (fields.Date.to_date('2022-02-01'), 1),
            (fields.Date.to_date('2022-05-29'), 1),
            (fields.Date.to_date('2023-01-29'), 1),
            (False, 1),
        ])

        result = Model._read_group([], ['date:week'], ['__count'])
        self.assertEqual(result, [
            (fields.Date.to_date('2022-01-23'), 2),
            (fields.Date.to_date('2022-01-30'), 3),
            (fields.Date.to_date('2022-05-29'), 1),
            (fields.Date.to_date('2023-01-29'), 1),
            (False, 1),
        ])

        result = Model._read_group([], ['date:month'], ['__count'])
        self.assertEqual(result, [
            (fields.Date.to_date('2022-01-01'), 4),
            (fields.Date.to_date('2022-02-01'), 1),
            (fields.Date.to_date('2022-05-01'), 1),
            (fields.Date.to_date('2023-01-01'), 1),
            (False, 1),
        ])

        result = Model._read_group([], ['date:quarter'], ['__count'])
        self.assertEqual(result, [
            (fields.Date.to_date('2022-01-01'), 5),
            (fields.Date.to_date('2022-04-01'), 1),
            (fields.Date.to_date('2023-01-01'), 1),
            (False, 1),
        ])

        result = Model._read_group([], ['date:year'], ['__count'])
        self.assertEqual(result, [
            (fields.Date.to_date('2022-01-01'), 6),
            (fields.Date.to_date('2023-01-01'), 1),
            (False, 1),
        ])
        # Reverse order
        result = Model._read_group([], ['date:year'], ['__count'], order="date:year DESC")
        self.assertEqual(result, [
            (False, 1),
            (fields.Date.to_date('2023-01-01'), 1),
            (fields.Date.to_date('2022-01-01'), 6),
        ])

    def test_groupby_datetime(self):
        Model = self.env['test_read_group.fill_temporal']
        records = Model.create([
            {'datetime': False, 'value': 13},
            {'datetime': '1916-08-18 12:30:00', 'value': 1},
            {'datetime': '1916-08-18 12:50:00', 'value': 3},
            {'datetime': '1916-08-19 01:30:00', 'value': 7},
            {'datetime': '1916-10-18 23:30:00', 'value': 5},
        ])

        # With "UTC" timezone (the default one)
        Model = Model.with_context(tz="UTC")

        self.assertEqual(
            Model._read_group([('id', 'in', records.ids)], ['datetime:day'], ['value:sum']),
            [
                (
                    fields.Datetime.to_datetime('1916-08-18 00:00:00'),
                    3 + 1,
                ),
                (
                    fields.Datetime.to_datetime('1916-08-19 00:00:00'),
                    7,
                ),
                (
                    fields.Datetime.to_datetime('1916-10-18 00:00:00'),
                    5,
                ),
                (
                    False,
                    13,
                ),
            ],
        )
        self.assertEqual(
            Model._read_group([('id', 'in', records.ids)], ['datetime:hour'], ['value:sum']),
            [
                (
                    fields.Datetime.to_datetime('1916-08-18 12:00:00'),
                    3 + 1,
                ),
                (
                    fields.Datetime.to_datetime('1916-08-19 01:00:00'),
                    7,
                ),
                (
                    fields.Datetime.to_datetime('1916-10-18 23:00:00'),
                    5,
                ),
                (
                    False,
                    13,
                ),
            ],
        )

        # With "Europe/Brussels" [+01:00 UTC | +02:00 UTC DST] timezone
        Model = Model.with_context(tz="Europe/Brussels")
        self.assertEqual(
            Model._read_group([('id', 'in', records.ids)], ['datetime:day'], ['value:sum']),
            [
                (
                    fields.Datetime.to_datetime('1916-08-18 00:00:00'),
                    3 + 1,
                ),
                (
                    fields.Datetime.to_datetime('1916-08-19 00:00:00'),
                    7,
                ),
                (
                    fields.Datetime.to_datetime('1916-10-19 00:00:00'),
                    5,
                ),
                (
                    False,
                    13,
                ),
            ],
        )
        self.assertEqual(
            Model._read_group([('id', 'in', records.ids)], ['datetime:hour'], ['value:sum']),
            [
                (
                    fields.Datetime.to_datetime('1916-08-18 14:00:00'),
                    3 + 1,
                ),
                (
                    fields.Datetime.to_datetime('1916-08-19 03:00:00'),
                    7,
                ),
                (
                    fields.Datetime.to_datetime('1916-10-19 00:00:00'),
                    5,
                ),
                (
                    False,
                    13,
                ),
            ],
        )

        # With "America/Anchorage" [-09:00 UTC | -08:00 UTC DST] timezone
        Model = Model.with_context(tz="America/Anchorage")
        self.assertEqual(
            Model._read_group([('id', 'in', records.ids)], ['datetime:day'], ['value:sum']),
            [
                (
                    fields.Datetime.to_datetime('1916-08-18 00:00:00'),
                    7 + 3 + 1,
                ),
                (
                    fields.Datetime.to_datetime('1916-10-18 00:00:00'),
                    5,
                ),
                (
                    False,
                    13,
                ),
            ],
        )
        # by hour
        self.assertEqual(
            Model._read_group([('id', 'in', records.ids)], ['datetime:hour'], ['value:sum']),
            [
                (
                    fields.Datetime.to_datetime('1916-08-18 02:00:00'),
                    3 + 1,
                ),
                (
                    fields.Datetime.to_datetime('1916-08-18 15:00:00'),
                    7,
                ),
                (
                    fields.Datetime.to_datetime('1916-10-18 13:00:00'),
                    5,
                ),
                (
                    False,
                    13,
                ),
            ],
        )

    def test_aggregate_datetime(self):
        Model = self.env['test_read_group.fill_temporal']
        records = Model.create([
            {'datetime': False, 'value': 13},
            {'datetime': '1916-08-18 01:50:00', 'value': 3},
            {'datetime': '1916-08-19 01:30:00', 'value': 7},
            {'datetime': '1916-10-18 02:30:00', 'value': 5},
        ])
        self.assertEqual(
            Model._read_group([('id', 'in', records.ids)], [], ['datetime:max']),
            [
                (
                    fields.Datetime.to_datetime('1916-10-18 02:30:00'),
                ),
            ],
        )

        self.assertEqual(
            Model._read_group([('id', 'in', records.ids)], [], ['datetime:array_agg']),
            [(
                [
                    None,
                    fields.Datetime.to_datetime('1916-08-18 01:50:00'),
                    fields.Datetime.to_datetime('1916-08-19 01:30:00'),
                    fields.Datetime.to_datetime('1916-10-18 02:30:00'),
                ],
            )],
        )

    def test_auto_join(self):
        """ Test what happens when grouping with a domain using a one2many field with auto_join. """
        model = self.env['test_read_group.order']
        records = model.create([{
            'line_ids': [Command.create({'value': 1}), Command.create({'value': 2})],
        }, {
            'line_ids': [Command.create({'value': 1})],
        }])

        domain1 = [('id', 'in', records.ids), ('line_ids.value', '=', 1)]
        domain2 = [('id', 'in', records.ids), ('line_ids.value', '>', 0)]

        # reference results
        self.assertEqual(len(model.search(domain1)), 2)
        self.assertEqual(len(model.search(domain2)), 2)

        result1 = model._read_group(domain1, aggregates=['__count'])
        self.assertEqual(result1, [(2,)])

        result2 = model._read_group(domain2, aggregates=['__count'])
        self.assertEqual(result1, [(2,)])

        # same requests, with auto_join
        self.patch(type(model).line_ids, 'auto_join', True)

        self.assertEqual(len(model.search(domain1)), 2)
        self.assertEqual(len(model.search(domain2)), 2)

        result1 = model._read_group(domain1, aggregates=['__count'])
        self.assertEqual(result1, [(2,)])

        result2 = model._read_group(domain2, aggregates=['__count'])
        self.assertEqual(result2, [(2,)])

    def test_groupby_many2many(self):
        User = self.env['test_read_group.user']
        mario, luigi = User.create([{'name': 'Mario'}, {'name': 'Luigi'}])
        tasks = self.env['test_read_group.task'].create([
            {   # both users
                'name': "Super Mario Bros.",
                'user_ids': [Command.set((mario + luigi).ids)],
            },
            {   # mario only
                'name': "Paper Mario",
                'user_ids': [Command.set(mario.ids)],
            },
            {   # luigi only
                'name': "Luigi's Mansion",
                'user_ids': [Command.set(luigi.ids)],
            },
            {   # no user
                'name': 'Donkey Kong',
            },
        ])

        # TODO: should we order by the relation and not by the id also for many2many (same than many2one) ? for public methods ?
        self.assertEqual(tasks._read_group(
                [('id', 'in', tasks.ids)],
                ['user_ids'],
                ['name:array_agg'],
            ),
            [
                (mario, ["Super Mario Bros.", "Paper Mario"]),      # tasks of Mario
                (luigi, ["Super Mario Bros.", "Luigi's Mansion"]),  # tasks of Luigi
                (User, ["Donkey Kong"]),                            # tasks of nobody
            ],
        )

    def test_order_by_many2one_id(self):
        # ordering by a many2one ordered itself by id does not use useless join
        expected_query = '''
            SELECT "test_read_group_order_line"."order_id", COUNT(*)
            FROM "test_read_group_order_line"
            GROUP BY "test_read_group_order_line"."order_id"
            ORDER BY "test_read_group_order_line"."order_id"
        '''
        with self.assertQueries([expected_query + ' ASC']):
            self.env["test_read_group.order.line"].read_group(
                [], ["order_id"], "order_id"
            )
        with self.assertQueries([expected_query + ' DESC']):
            self.env["test_read_group.order.line"].read_group(
                [], ["order_id"], "order_id", orderby="order_id DESC"
            )
