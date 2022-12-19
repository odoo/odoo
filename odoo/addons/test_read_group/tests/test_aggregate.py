# -*- coding: utf-8 -*-
from odoo import fields
from odoo.tests import common
from odoo import Command


class TestReadAggregate(common.TransactionCase):

    def test_simple_aggregate(self):
        Model = self.env['test_read_group.aggregate']
        partner_1_id = self.env['res.partner'].create({'name': 'z_one'}).id
        partner_2_id = self.env['res.partner'].create({'name': 'a_two'}).id
        Model.create({'key': 1, 'partner_id': partner_1_id, 'value': 1})
        Model.create({'key': 1, 'partner_id': partner_1_id, 'value': 2})
        Model.create({'key': 1, 'partner_id': partner_2_id, 'value': 3})
        Model.create({'key': 2, 'partner_id': partner_2_id, 'value': 4})
        Model.create({'key': 2, 'partner_id': partner_2_id})
        Model.create({'key': 2, 'value': 5})
        Model.create({'partner_id': partner_2_id, 'value': 5})
        Model.create({'value': 6})
        Model.create({})

        with self.assertQueries([
            """
SELECT SUM("test_read_group_aggregate"."value") AS "value:sum", "test_read_group_aggregate"."key" AS "key"
FROM "test_read_group_aggregate"
GROUP BY "test_read_group_aggregate"."key"
ORDER BY "test_read_group_aggregate"."key" ASC
            """
        ]):
            self.assertEqual(
                Model.aggregate([], groupby=['key'], aggregates=['value:sum']).to_list(),
                [
                    {
                        'key': 1,
                        'value:sum': 1 + 2 + 3,
                    },
                    {
                        'key': 2,
                        'value:sum': 4 + 5,
                    },
                    {
                        'key': None,
                        'value:sum': 5 + 6,
                    },
                ]
            )

        with self.assertQueries([
            """
SELECT SUM("test_read_group_aggregate"."value") AS "value:sum", "test_read_group_aggregate"."key" AS "key", "test_read_group_aggregate"."partner_id" AS "partner_id"
FROM "test_read_group_aggregate"
    LEFT JOIN "res_partner" AS "test_read_group_aggregate__partner_id" ON ("test_read_group_aggregate"."partner_id" = "test_read_group_aggregate__partner_id"."id")
GROUP BY "test_read_group_aggregate"."key", "test_read_group_aggregate"."partner_id", "test_read_group_aggregate__partner_id"."display_name", "test_read_group_aggregate__partner_id"."id"
ORDER BY "test_read_group_aggregate"."key" ASC, "test_read_group_aggregate__partner_id"."display_name", "test_read_group_aggregate__partner_id"."id"
            """
        ]):
            self.assertEqual(
                Model.aggregate([], groupby=['key', 'partner_id'], aggregates=['value:sum']).to_list(),
                [
                    {
                        'key': 1,
                        'partner_id': partner_2_id,
                        'value:sum': 3,
                    },
                    {
                        'key': 1,
                        'partner_id': partner_1_id,
                        'value:sum': 1 + 2,
                    },
                    {
                        'key': 2,
                        'partner_id': partner_2_id,
                        'value:sum': 4,
                    },
                    {
                        'key': 2,
                        'partner_id': None,
                        'value:sum': 5,
                    },
                    {
                        'key': None,
                        'partner_id': partner_2_id,
                        'value:sum': 5,
                    },
                    {
                        'key': None,
                        'partner_id': None,
                        'value:sum': 6,
                    },
                ]
            )

        # Same than before but with private method, the order doesn't traverse many2one order, then the order is based on id of partner
        with self.assertQueries([
            """
SELECT SUM("test_read_group_aggregate"."value") AS "value:sum", "test_read_group_aggregate"."key" AS "key", "test_read_group_aggregate"."partner_id" AS "partner_id"
FROM "test_read_group_aggregate"
GROUP BY "test_read_group_aggregate"."key", "test_read_group_aggregate"."partner_id"
ORDER BY "test_read_group_aggregate"."key" ASC, "test_read_group_aggregate"."partner_id" ASC
            """
        ]):
            self.assertEqual(
                Model._aggregate([], groupby=['key', 'partner_id'], aggregates=['value:sum']).to_list(),
                [
                    {
                        'key': 1,
                        'partner_id': partner_1_id,
                        'value:sum': 1 + 2,
                    },
                    {
                        'key': 1,
                        'partner_id': partner_2_id,
                        'value:sum': 3,
                    },
                    {
                        'key': 2,
                        'partner_id': partner_2_id,
                        'value:sum': 4,
                    },
                    {
                        'key': 2,
                        'partner_id': None,
                        'value:sum': 5,
                    },
                    {
                        'key': None,
                        'partner_id': partner_2_id,
                        'value:sum': 5,
                    },
                    {
                        'key': None,
                        'partner_id': None,
                        'value:sum': 6,
                    },
                ]
            )

    def test_prefetch_for_as_records(self):
        Model = self.env['test_read_group.aggregate']
        Partner = self.env['res.partner']
        partner_1 = Partner.create({'name': 'z_one'})
        partner_2 = Partner.create({'name': 'a_two'})
        Model.create({'key': 1, 'partner_id': partner_1.id})
        Model.create({'key': 2, 'partner_id': partner_2.id})

        Partner.invalidate_model()

        res = Model._aggregate([], ['*:count'], ['partner_id'])

        iter_keys = iter(res.keys(as_records=True))
        [partner_1] = next(iter_keys)
        partner_1.name

        [partner_2] = next(iter_keys)
        with self.assertQueryCount(0):
            # Already prefetch with partner_1.name
            partner_2.name

        res = Model._aggregate([], ['partner_id:array_agg'], ['key'])

        Partner.invalidate_model()

        partner_1 = res.get_agg(1, as_record=True)
        partner_1.name

        partner_2 = res.get_agg(2, as_record=True)
        with self.assertQueryCount(0):
            # Already prefetch with partner_1.name
            partner_2.name

        Partner.invalidate_model()

        iter_keys = iter(res.values(as_records=True))
        [partner_1] = next(iter_keys)
        partner_1.name

        [partner_2] = next(iter_keys)
        with self.assertQueryCount(0):
            # Already prefetch with partner_1.name
            partner_2.name

    def test_result_object(self):
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

        # ----------- usage 84 % (random stat): ONE aggregate, ONE group key
        res = Model._aggregate([], ['*:count'], ['partner_id'])

        self.assertEqual(res[partner_1]['*:count'], 2)  # If one aggregate, no need to specify aggregate
        self.assertEqual(res[partner_1.id]['*:count'], 2)  # With recordset
        self.assertEqual(res[partner_1.id].get('*:count', 0), 2)  # default value 0
        self.assertEqual(res.get_agg(-42, '*:count', 42), 42)  # negative number to avoiding id domains

        # Check all iter methods with default converter
        self.assertEqual(
            list(res.items()),
            [((partner_1.id,), (2,)), ((partner_2.id,), (4,)), ((None,), (3,)),]
        )
        self.assertEqual(
            list(res.items(as_records=True)),
            [((partner_1,), (2,)), ((partner_2,), (4,)), ((Partner,), (3,)),]
        )
        self.assertEqual(
            list(res.keys()),
            [(partner_1.id,), (partner_2.id,), (None,),]
        )
        self.assertEqual(
            list(res.keys(as_records=True)),
            [(partner_1,), (partner_2,), (Partner,),]
        )
        self.assertEqual(
            list(res.values()),
            [(2,), (4,), (3,)]
        )
        self.assertEqual(
            list(res.values(as_records=True)),
            [(2,), (4,), (3,)]
        )

        for [partner_id], [count] in res.items():
            ...

        # ----------- usage 4 % (random stat): SEVERAL aggregate, ONE group key
        res = Model._aggregate([], ['*:count', 'value:sum'], ['key'])
        self.assertEqual(res[1].get('*:count', 0), 3)
        self.assertEqual(res[(1,)].get('*:count', 0), 3)  # Same
        self.assertEqual(res[(1,)].get('value:sum', 0), 6)
        self.assertEqual(res.get_agg(-8, '*:count', 'default'), 'default')
        # Or iter usage:
        for [key], [count, value_sum] in res.items():
            ...

        # ----------- usage 4 % (random stat): ONE aggregate, SEVERAL group keys
        res = Model._aggregate([], ['*:count'], ['key', 'partner_id'])
        self.assertEqual(res[(1, partner_1)].get('*:count', 0), 2)
        self.assertEqual(res[(1, partner_1.id)].get('*:count', 0), 2)
        self.assertEqual(res.get_agg((8, partner_1), '*:count', 'default'), 'default')
        # Or iter usage:
        for [key, partner_id], [count] in res.items():
            pass
        # ----------- usage 4 % (random stat): ONE/SEVERAL aggregate, NO group key
        res = Model._aggregate([], ['*:count', 'value:sum'])
        self.assertEqual(res.get_agg(aggregate='*:count'), 9)       # Groups has `()` as default value
        self.assertEqual(res[None].get('value:sum', 0), 26)  # Groups has `()` as default value

        res = Model._aggregate([], ['*:count'])  # almost == to search_count
        self.assertEqual(res[()].get('*:count'), 9)
        # ----------- usage 2/3 % (random stat): SEVERAL aggregate, SEVERAL group keys
        res = Model._aggregate([], ['*:count', 'value:sum'], ['key', 'partner_id'])
        self.assertEqual(res[(1, partner_1)].get('*:count', 0), 2)
        self.assertEqual(res[(1, partner_1.id)].get('value:sum', 0), 3)
        self.assertEqual(res.get_agg((8, partner_1), '*:count', 0), 0)
        self.assertEqual(res.get_agg((8, partner_1), 'value:sum', 0), 0)
        # Or iter usage:
        for [key, partner_id], [count, value_sum] in res.items():
            pass

        # ----------- usage 1/2 % (random stat): NO aggregate, SEVERAL groups keys
        # Can be useful if we want all distinct pair of groups
        # With one group, it is better to use array_agg_distinct.
        res = Model._aggregate([], [], ['key', 'partner_id'])
        self.assertEqual(
            list(res.keys(as_records=True)),
            [
                (1, partner_1),
                (1, partner_2),
                (2, partner_2),
                (2, Partner),
                (None, partner_2),
                (None, Partner),
            ]
        )

    def test_ambiguous_field_name(self):
        """ Check that aggregate doesn't generate ambiguous (display_name) alias for PostgreSQL
        """
        Model = self.env['test_read_group.aggregate']
        partner_1_id = self.env['res.partner'].create({'name': 'z_one'}).id
        Model.create({'key': 1, 'partner_id': partner_1_id, 'value': 1, 'display_name': 'blabla'})
        with self.assertQueries([
            """
SELECT COUNT(*) AS "*:count", "test_read_group_aggregate"."display_name" AS "display_name", "test_read_group_aggregate"."partner_id" AS "partner_id"
FROM "test_read_group_aggregate"
    LEFT JOIN "res_partner" AS "test_read_group_aggregate__partner_id" ON ("test_read_group_aggregate"."partner_id" = "test_read_group_aggregate__partner_id"."id")
GROUP BY "test_read_group_aggregate"."display_name", "test_read_group_aggregate"."partner_id", "test_read_group_aggregate__partner_id"."display_name", "test_read_group_aggregate__partner_id"."id"
ORDER BY "test_read_group_aggregate__partner_id"."display_name" DESC, "test_read_group_aggregate__partner_id"."id" DESC
            """
        ]):
            self.assertEqual(
                Model.aggregate([], ['*:count'], ['display_name', 'partner_id'], order="partner_id DESC").to_list(),
                [{'display_name': 'blabla', 'partner_id': partner_1_id, '*:count': 1}]
            )

    def test_bool_aggregates(self):
        Model = self.env['test_read_group.aggregate.boolean']
        Model.create({'key': 1, 'bool_and': True})
        Model.create({'key': 1, 'bool_and': True})

        Model.create({'key': 2, 'bool_and': True})
        Model.create({'key': 2, 'bool_and': False})

        Model.create({'key': 3, 'bool_and': False})
        Model.create({'key': 3, 'bool_and': False})

        Model.create({'key': 4, 'bool_and': True, 'bool_or': True, 'bool_array': True})
        Model.create({'key': 4})

        self.assertEqual(
            Model.aggregate([], groupby=['key'], aggregates=['bool_and:bool_and', 'bool_and:bool_or', 'bool_and:array_agg_distinct']).to_list(),
            [
                {'key': 1, 'bool_and:bool_and': True, 'bool_and:bool_or': True, 'bool_and:array_agg_distinct': [True]},
                {'key': 2, 'bool_and:bool_and': False, 'bool_and:bool_or': True, 'bool_and:array_agg_distinct': [False, True]},
                {'key': 3, 'bool_and:bool_and': False, 'bool_and:bool_or': False, 'bool_and:array_agg_distinct': [False]},
                {'key': 4, 'bool_and:bool_and': False, 'bool_and:bool_or': True, 'bool_and:array_agg_distinct': [False, True]},
            ]
        )

    def test_count_aggregates(self):
        Model = self.env['test_read_group.aggregate']
        Model.create({'key': 1})
        Model.create({'key': 1})
        Model.create({})

        self.assertEqual(
            Model.aggregate([], aggregates=['key:count']).to_list(),
            [
                {'key:count': 2},
            ]
        )

        self.assertEqual(
            Model.aggregate([], aggregates=['key:count_distinct']).to_list(),
            [
                {'key:count_distinct': 1},
            ]
        )

    def test_array_aggregates(self):
        Model = self.env['test_read_group.aggregate']
        Model.create({'key': 1})
        Model.create({'key': 1})
        Model.create({'key': 2})

        self.assertEqual(
            Model.aggregate([], aggregates=['key:array_agg']).to_list(),
            [
                {'key:array_agg': [1, 1, 2]},
            ]
        )

        self.assertEqual(
            Model.aggregate([], aggregates=['key:array_agg_distinct']).to_list(),
            [
                {'key:array_agg_distinct': [1, 2]},
            ]
        )

    def test_flush_aggregate(self):
        Model = self.env['test_read_group.aggregate']
        a = Model.create({'key': 1, 'value': 5})
        b = Model.create({'key': 1, 'value': 5})

        self.assertEqual(
            Model.aggregate([], groupby=['key'], aggregates=['value:sum']).to_list(),
            [
                {'key': 1, 'value:sum': 5 + 5},
            ]
        )

        # Test flush of domain
        a.key = 2
        self.assertEqual(
            Model.aggregate([('key', '>', 1)], groupby=['key'], aggregates=['value:sum']).to_list(),
            [
                {'key': 2, 'value:sum': 5},
            ]
        )

        # test flush of groupby clause
        a.key = 3
        self.assertEqual(
            Model.aggregate([], groupby=['key'], aggregates=['value:sum']).to_list(),
            [
                {'key': 1, 'value:sum': 5},
                {'key': 3, 'value:sum': 5},
            ]
        )

        # Test flush of aggregates
        b.value = 8
        self.assertEqual(
            Model.aggregate([], groupby=['key'], aggregates=['value:sum']).to_list(),
            [
                {'key': 1, 'value:sum': 8},
                {'key': 3, 'value:sum': 5},
            ]
        )

    def test_having_clause(self):
        Model = self.env['test_read_group.aggregate']
        Model.create({'key': 1, 'value': 8})
        Model.create({'key': 1, 'value': 2})

        Model.create({'key': 2, 'value': 5})

        Model.create({'key': 3, 'value': 2})
        Model.create({'key': 3, 'value': 4})
        Model.create({'key': 3, 'value': 1})
        with self.assertQueries([
            """
SELECT SUM("test_read_group_aggregate"."value") AS "value:sum", "test_read_group_aggregate"."key" AS "key"
FROM "test_read_group_aggregate"
GROUP BY "test_read_group_aggregate"."key"
HAVING SUM("test_read_group_aggregate"."value") > %s
ORDER BY "test_read_group_aggregate"."key" ASC
            """
        ]):
            self.assertEqual(
                Model._aggregate([], groupby=['key'], aggregates=['value:sum'], having=[("value:sum", '>', 8)]).to_list(),
                [{'key': 1, 'value:sum': 2 + 8}]
            )

        with self.assertQueries([
            """
SELECT SUM("test_read_group_aggregate"."value") AS "value:sum", COUNT(*) AS "*:count", "test_read_group_aggregate"."key" AS "key"
FROM "test_read_group_aggregate"
GROUP BY "test_read_group_aggregate"."key"
HAVING (COUNT(*) < %s AND SUM("test_read_group_aggregate"."value") > %s)
ORDER BY "test_read_group_aggregate"."key" ASC
            """
        ]):
            self.assertEqual(
                Model._aggregate(
                    [],
                    groupby=['key'],
                    aggregates=['value:sum', '*:count'],
                    having=[
                        ('*:count', '<', 3),
                        ("value:sum", '>', 4),
                    ]
                ).to_list(),
                [
                    {'key': 1, 'value:sum': 2 + 8, "*:count": 2},
                    {'key': 2, 'value:sum': 5, "*:count": 1},
                ]
            )

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

        gb = Model.aggregate([], ['*:count'], ['date:day']).to_list()

        self.assertEqual(gb, [
            {
                'date:day': fields.Date.to_date('2022-01-29'),
                '*:count': 2,
            },
            {
                'date:day': fields.Date.to_date('2022-01-30'),
                '*:count': 1,
            },
            {
                'date:day': fields.Date.to_date('2022-01-31'),
                '*:count': 1,
            },
            {
                'date:day': fields.Date.to_date('2022-02-01'),
                '*:count': 1,
            },
            {
                'date:day': fields.Date.to_date('2022-05-29'),
                '*:count': 1,
            },
            {
                'date:day': fields.Date.to_date('2023-01-29'),
                '*:count': 1,
            },
            {
                'date:day': None,
                '*:count': 1,
            }
        ])

        gb = Model.aggregate([], ['*:count'], ['date:week']).to_list()

        self.assertEqual(gb, [
            {
                'date:week': fields.Date.to_date('2022-01-24'),
                '*:count': 3,
            },
            {
                'date:week': fields.Date.to_date('2022-01-31'),
                '*:count': 2,
            },
            {
                'date:week': fields.Date.to_date('2022-05-23'),
                '*:count': 1,
            },
            {
                'date:week': fields.Date.to_date('2023-01-23'),
                '*:count': 1,
            },
            {
                'date:week': None,
                '*:count': 1,
            }
        ])

        gb = Model.aggregate([], ['*:count'], ['date:week']).to_list()

        self.assertEqual(gb, [
            {
                'date:week': fields.Date.to_date('2022-01-24'),
                '*:count': 3,
            },
            {
                'date:week': fields.Date.to_date('2022-01-31'),
                '*:count': 2,
            },
            {
                'date:week': fields.Date.to_date('2022-05-23'),
                '*:count': 1,
            },
            {
                'date:week': fields.Date.to_date('2023-01-23'),
                '*:count': 1,
            },
            {
                'date:week': None,
                '*:count': 1,
            }
        ])

        gb = Model.aggregate([], ['*:count'], ['date:month']).to_list()
        self.assertEqual(gb, [
            {
                'date:month': fields.Date.to_date('2022-01-01'),
                '*:count': 4,
            },
            {
                'date:month': fields.Date.to_date('2022-02-01'),
                '*:count': 1,
            },
            {
                'date:month': fields.Date.to_date('2022-05-01'),
                '*:count': 1,
            },
            {
                'date:month': fields.Date.to_date('2023-01-01'),
                '*:count': 1,
            },
            {
                'date:month': None,
                '*:count': 1,
            }
        ])

        gb = Model.aggregate([], ['*:count'], ['date:quarter']).to_list()
        self.assertEqual(gb, [
            {
                'date:quarter': fields.Date.to_date('2022-01-01'),
                '*:count': 5,
            },
            {
                'date:quarter': fields.Date.to_date('2022-04-01'),
                '*:count': 1,
            },
            {
                'date:quarter': fields.Date.to_date('2023-01-01'),
                '*:count': 1,
            },
            {
                'date:quarter': None,
                '*:count': 1,
            }
        ])

        gb = Model.aggregate([], ['*:count'], ['date:year']).to_list()
        self.assertEqual(gb, [
            {
                'date:year': fields.Date.to_date('2022-01-01'),
                '*:count': 6,
            },
            {
                'date:year': fields.Date.to_date('2023-01-01'),
                '*:count': 1,
            },
            {
                'date:year': None,
                '*:count': 1,
            }
        ])
        # Reverse order
        gb = Model.aggregate([], ['*:count'], ['date:year'], order="date:year DESC").to_list()
        self.assertEqual(gb, [
            {
                'date:year': None,
                '*:count': 1,
            },
            {
                'date:year': fields.Date.to_date('2023-01-01'),
                '*:count': 1,
            },
            {
                'date:year': fields.Date.to_date('2022-01-01'),
                '*:count': 6,
            }
        ])

    def test_groupby_datetime(self):
        Model = self.env['test_read_group.fill_temporal']
        create_values = [
            {'datetime': False, 'value': 13},
            {'datetime': '1916-08-18 01:50:00', 'value': 3},
            {'datetime': '1916-08-19 01:30:00', 'value': 7},
            {'datetime': '1916-10-18 02:30:00', 'value': 5},
        ]
        # Time Zone                      UTC     UTC DST
        tzs = ["America/Anchorage",  # −09:00    −08:00
               "Europe/Brussels",    # +01:00    +02:00
               "Pacific/Kwajalein"]  # +12:00    +12:00
        for tz in tzs:
            Model = Model.with_context(tz=tz)
            records = Model.create(create_values)
            Model._aggregate([('id', 'in', records.ids)], ['value:sum'], ['datetime:hour']).to_list()
            self.assertEqual(
                Model._aggregate([('id', 'in', records.ids)], ['value:sum'], ['datetime:hour']).to_list(),
                [
                    {
                        'value:sum': 3,
                        'datetime:hour': fields.Datetime.context_timestamp(
                            Model, fields.Datetime.to_datetime('1916-08-18 01:00:00')
                        ).replace(tzinfo=None),
                    },
                    {
                        'value:sum': 7,
                        'datetime:hour': fields.Datetime.context_timestamp(
                            Model, fields.Datetime.to_datetime('1916-08-19 01:00:00')
                        ).replace(tzinfo=None),
                    },
                    {
                        'value:sum': 5,
                        'datetime:hour': fields.Datetime.context_timestamp(
                            Model, fields.Datetime.to_datetime('1916-10-18 02:00:00')
                        ).replace(tzinfo=None),
                    },
                    {
                        'value:sum': 13,
                        'datetime:hour': None,
                    },
                ]
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

        result1 = model.aggregate(domain1, ['*:count']).to_list()
        self.assertEqual(len(result1), 1)
        self.assertEqual(result1[0]['*:count'], 2)

        result2 = model.aggregate(domain2, ['*:count']).to_list()
        self.assertEqual(len(result2), 1)
        self.assertEqual(result2[0]['*:count'], 2)

        # same requests, with auto_join
        self.patch(type(model).line_ids, 'auto_join', True)

        self.assertEqual(len(model.search(domain1)), 2)
        self.assertEqual(len(model.search(domain2)), 2)

        result1 = model.aggregate(domain1, ['*:count']).to_list()
        self.assertEqual(len(result1), 1)
        self.assertEqual(result1[0]['*:count'], 2)

        result2 = model.aggregate(domain2, ['*:count']).to_list()
        self.assertEqual(len(result2), 1)
        self.assertEqual(result2[0]['*:count'], 2)

    def test_many2many_groupby(self):
        users = self.env['test_read_group.user'].create([
            {'name': 'Mario'},
            {'name': 'Luigi'},
        ])
        tasks = self.env['test_read_group.task'].create([
            {   # both users
                'name': "Super Mario Bros.",
                'user_ids': [Command.set(users.ids)],
            },
            {   # mario only
                'name': "Paper Mario",
                'user_ids': [Command.set(users[0].ids)],
            },
            {   # luigi only
                'name': "Luigi's Mansion",
                'user_ids': [Command.set(users[1].ids)],
            },
            {   # no user
                'name': 'Donkey Kong',
            },
        ])

        # TODO: should we order by the relation and not by the id also for many2many (same than many2one) ?
        self.assertEqual(tasks.aggregate(
                [('id', 'in', tasks.ids)],
                ['name:array_agg'],
                ['user_ids'],
            ).to_list(), 
            [
                {   # tasks of Mario
                    'user_ids': users[0].id,
                    'name:array_agg': ["Paper Mario", "Super Mario Bros."],
                },
                {   # tasks of Luigi
                    'user_ids': users[1].id,
                    'name:array_agg': ["Luigi's Mansion", "Super Mario Bros."],
                },
                {   # tasks of nobody
                    'user_ids': None,
                    'name:array_agg': ["Donkey Kong"],
                },
            ]
        )
