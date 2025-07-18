from datetime import datetime, time
from pytz import UTC, timezone

import babel

from odoo.tests import common, new_test_user
from odoo import Command


class TestFormattedReadGroup(common.TransactionCase):
    ''' Test formatted_read_group, similar tests are done in test_private_read_group 
    for _read_group.'''

    maxDiff = None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.base_user = new_test_user(cls.env, login='Base User', groups='base.group_user')

    def test_simple_formatted_read_group(self):
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

        self.assertEqual(
            Model.formatted_read_group([], groupby=['key'], aggregates=['value:sum']),
            [
                {'__extra_domain': [('key', '=', 1)], 'key': 1, 'value:sum': 6},
                {'__extra_domain': [('key', '=', 2)], 'key': 2, 'value:sum': 9},
                {'__extra_domain': [('key', '=', False)], 'key': False, 'value:sum': 11},
            ]
        )

        # groupby on many2one, the order use the order of the comodel (res.partner)
        self.assertEqual(
            Model.formatted_read_group([], groupby=['key', 'partner_id'], aggregates=['value:sum']),
            [
                {
                    '__extra_domain': ['&', ('key', '=', 1), ('partner_id', '=', partner_2.id)],
                    'key': 1,
                    'partner_id': (partner_2.id, 'a_two'),
                    'value:sum': 3,
                },
                {
                    '__extra_domain': ['&', ('key', '=', 1), ('partner_id', '=', partner_1.id)],
                    'key': 1,
                    'partner_id': (partner_1.id, 'z_one'),
                    'value:sum': 3,
                },
                {
                    '__extra_domain': ['&', ('key', '=', 2), ('partner_id', '=', partner_2.id)],
                    'key': 2,
                    'partner_id': (partner_2.id, 'a_two'),
                    'value:sum': 4,
                },
                {
                    '__extra_domain': ['&', ('key', '=', 2), ('partner_id', '=', False)],
                    'key': 2,
                    'partner_id': False,
                    'value:sum': 5,
                },
                {
                    '__extra_domain': ['&', ('key', '=', False), ('partner_id', '=', partner_2.id)],
                    'key': False,
                    'partner_id': (partner_2.id, 'a_two'),
                    'value:sum': 5,
                },
                {
                    '__extra_domain': ['&', ('key', '=', False), ('partner_id', '=', False)],
                    'key': False,
                    'partner_id': False,
                    'value:sum': 6,
                },
            ]
        )

        # force order on the aggregates, but keep the partner_id order after.
        self.assertEqual(
            Model.formatted_read_group([], groupby=['partner_id'], aggregates=['value:sum'], order='value:sum'),
            [
                {
                    '__extra_domain': [('partner_id', '=', partner_1.id)],
                    'partner_id': (partner_1.id, 'z_one'),
                    'value:sum': 3,
                },
                {
                    '__extra_domain': [('partner_id', '=', False)],
                    'partner_id': False,
                    'value:sum': 11,
                },
                {
                    '__extra_domain': [('partner_id', '=', partner_2.id)],
                    'partner_id': (partner_2.id, 'a_two'),
                    'value:sum': 12,
                },
            ]
        )

    def test_groupby_id(self):
        Model = self.env['test_read_group.aggregate']
        rec1, rec2 = Model.create([
            {'value': 1, 'display_name': 'record1'},
            {'value': 2, 'display_name': 'record2'},
        ])

        self.assertEqual(
            Model.formatted_read_group([], groupby=['id'], aggregates=['value:sum']),
            [
                {
                    '__extra_domain': [('id', '=', rec1.id)],
                    'id': (rec1.id, "record1"),
                    'value:sum': 1,
                },
                {
                    '__extra_domain': [('id', '=', rec2.id)],
                    'id': (rec2.id, "record2"),
                    'value:sum': 2,
                },
            ],
        )

    def test_limit_offset(self):
        Model = self.env['test_read_group.aggregate']
        Model.create({'key': 1, 'value': 1})
        Model.create({'key': 1, 'value': 2})
        Model.create({'key': 1, 'value': 3})
        Model.create({'key': 2, 'value': 4})
        Model.create({'key': 2})
        Model.create({'key': 2, 'value': 5})
        Model.create({})
        Model.create({'value': 6})

        self.assertEqual(
            Model.formatted_read_group([], groupby=['key'], aggregates=['value:sum'], limit=2),
            [
                {'__extra_domain': [('key', '=', 1)], 'key': 1, 'value:sum': 1 + 2 + 3},
                {'__extra_domain': [('key', '=', 2)], 'key': 2, 'value:sum': 4 + 5},
            ]
        )

        self.assertEqual(
            Model.formatted_read_group([], groupby=['key'], aggregates=['value:sum'], offset=1),
            [
                {'__extra_domain': [('key', '=', 2)], 'key': 2, 'value:sum': 4 + 5},
                {'__extra_domain': [('key', '=', False)], 'key': False, 'value:sum': 6},
            ]
        )

        self.assertEqual(
            Model.formatted_read_group([], groupby=['key'], aggregates=['value:sum'], offset=1, limit=2, order='key DESC'),
            [
                {'__extra_domain': [('key', '=', 2)], 'key': 2, 'value:sum': 4 + 5},
                {'__extra_domain': [('key', '=', 1)], 'key': 1, 'value:sum': 1 + 2 + 3},
            ]
        )

    def test_falsy_domain(self):
        Model = self.env['test_read_group.aggregate']

        with self.assertQueryCount(0):
            result = Model.formatted_read_group([('id', 'in', [])], groupby=['partner_id'])
            self.assertEqual(
                result,
                []
            )

        with self.assertQueryCount(0):
            result = Model.formatted_read_group(
                [('id', 'in', [])],
                groupby=[],
                aggregates=['__count', 'partner_id:count', 'partner_id:count_distinct'],
            )
            # When there are no groupby, we always get one group
            self.assertEqual(
                result,
                [
                    {
                        '__count': 0,
                        '__extra_domain': [(1, '=', 1)],
                        'partner_id:count': 0,
                        'partner_id:count_distinct': 0,
                    },
                ]
            )

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

        result = Model.formatted_read_group(
            [],
            groupby=['key'],
            aggregates=['bool_and:bool_and', 'bool_and:bool_or', 'bool_and:array_agg'],
        )
        self.assertEqual(
            result,
            [
                {
                    '__extra_domain': [('key', '=', 1)],
                    'bool_and:array_agg': [True, True],
                    'bool_and:bool_and': True,
                    'bool_and:bool_or': True,
                    'key': 1,
                },
                {
                    '__extra_domain': [('key', '=', 2)],
                    'bool_and:array_agg': [True, False],
                    'bool_and:bool_and': False,
                    'bool_and:bool_or': True,
                    'key': 2,
                },
                {
                    '__extra_domain': [('key', '=', 3)],
                    'bool_and:array_agg': [False, False],
                    'bool_and:bool_and': False,
                    'bool_and:bool_or': False,
                    'key': 3,
                },
                {
                    '__extra_domain': [('key', '=', 4)],
                    'bool_and:array_agg': [True, False],
                    'bool_and:bool_and': False,
                    'bool_and:bool_or': True,
                    'key': 4,
                },
            ]
        )

    def test_count_read_groups(self):
        Model = self.env['test_read_group.aggregate']
        Model.create({'key': 1})
        Model.create({'key': 1})
        Model.create({})

        self.assertEqual(
            Model.formatted_read_group([], aggregates=['key:count']),
            [{'__extra_domain': [(1, '=', 1)], 'key:count': 2}]
        )

        self.assertEqual(
            Model.formatted_read_group([], aggregates=['key:count_distinct']),
            [{'__extra_domain': [(1, '=', 1)], 'key:count_distinct': 1}]
        )

    def test_malformed_params(self):
        Model = self.env['test_read_group.order.line']
        # Test malformed groupby clause
        with self.assertRaises(ValueError):
            Model.formatted_read_group([], ['create_date:bad_granularity'])

        with self.assertRaises(ValueError):
            Model.formatted_read_group([], ['Other stuff create_date:week'])

        with self.assertRaises(ValueError):
            Model.formatted_read_group([], ['create_date'])  # No granularity

        with self.assertRaises(ValueError):
            Model.formatted_read_group([], ["'create_date:week"])

        with self.assertRaises(ValueError):
            Model.formatted_read_group([], ["'create_date:unknown_number"])

        # Test malformed aggregate clause
        with self.assertRaises(ValueError):
            Model.formatted_read_group([], aggregates=['value'])  # No aggregate

        with self.assertRaises(ValueError):
            Model.formatted_read_group([], aggregates=['__count_'])

        with self.assertRaises(ValueError):
            Model.formatted_read_group([], aggregates=['value:__count'])

        with self.assertRaises(ValueError):
            Model.formatted_read_group([], aggregates=['other value:sum'])

        with self.assertRaises(ValueError):
            Model.formatted_read_group([], aggregates=['value:array_agg OR'])

        with self.assertRaises(ValueError):
            Model.formatted_read_group([], aggregates=["'value:sum"])

        with self.assertRaises(ValueError):
            Model.formatted_read_group([], aggregates=['label:sum(value)'])

        with self.assertRaises(ValueError):
            Model.formatted_read_group([], aggregates=['order_id.create_date:min'])

        with self.assertRaisesRegex(
            ValueError,
            "Invalid field 'not_another_field' on model 'test_read_group.order.line' for 'not_another_field:sum'.",
        ):
            Model.formatted_read_group([], aggregates=['value:sum', 'not_another_field:sum'])

        # Test malformed order clause
        with self.assertRaises(ValueError):
            Model.formatted_read_group([], ['value'], order='__count DESC other')

        with self.assertRaises(ValueError):
            Model.formatted_read_group([], ['value'], order="value' DESC")

        with self.assertRaises(ValueError):
            Model.formatted_read_group([], ['value'], order='value ASCCC')

    def test_groupby_date(self):
        '''Test what happens when grouping on date fields'''
        Model = self.env['test_read_group.fill_temporal']
        Model.create({})  # Falsy date
        Model.create({'date': '2022-01-29'})  # Saturday (week of '2022-01-24')
        Model.create({'date': '2022-01-29'})  # Same day
        Model.create({'date': '2022-01-30'})  # Sunday
        Model.create({'date': '2022-01-31'})  # Monday (other week)
        Model.create({'date': '2022-02-01'})  # (other month)
        Model.create({'date': '2022-05-29'})  # other quarter
        Model.create({'date': '2023-01-29'})  # other year

        result = Model.formatted_read_group([], ['date:day'], ['__count'])
        self.assertEqual(
            result,
            [
                {
                    '__count': 2,
                    '__extra_domain': ['&', ('date', '>=', '2022-01-29'), ('date', '<', '2022-01-30')],
                    'date:day': ('2022-01-29', '29 Jan 2022'),
                },
                {
                    '__count': 1,
                    '__extra_domain': ['&', ('date', '>=', '2022-01-30'), ('date', '<', '2022-01-31')],
                    'date:day': ('2022-01-30', '30 Jan 2022'),
                },
                {
                    '__count': 1,
                    '__extra_domain': ['&', ('date', '>=', '2022-01-31'), ('date', '<', '2022-02-01')],
                    'date:day': ('2022-01-31', '31 Jan 2022'),
                },
                {
                    '__count': 1,
                    '__extra_domain': ['&', ('date', '>=', '2022-02-01'), ('date', '<', '2022-02-02')],
                    'date:day': ('2022-02-01', '01 Feb 2022'),
                },
                {
                    '__count': 1,
                    '__extra_domain': ['&', ('date', '>=', '2022-05-29'), ('date', '<', '2022-05-30')],
                    'date:day': ('2022-05-29', '29 May 2022'),
                },
                {
                    '__count': 1,
                    '__extra_domain': ['&', ('date', '>=', '2023-01-29'), ('date', '<', '2023-01-30')],
                    'date:day': ('2023-01-29', '29 Jan 2023'),
                },
                {'__count': 1, '__extra_domain': [('date', '=', False)], 'date:day': False},
            ]
        )

        result = Model.formatted_read_group([], ['date:week'], ['__count'])
        self.assertEqual(
            result,
            [
                {
                    '__count': 2,
                    '__extra_domain': ['&', ('date', '>=', '2022-01-23'), ('date', '<', '2022-01-30')],
                    'date:week': ('2022-01-23', 'W5 2022'),
                },
                {
                    '__count': 3,
                    '__extra_domain': ['&', ('date', '>=', '2022-01-30'), ('date', '<', '2022-02-06')],
                    'date:week': ('2022-01-30', 'W6 2022'),
                },
                {
                    '__count': 1,
                    '__extra_domain': ['&', ('date', '>=', '2022-05-29'), ('date', '<', '2022-06-05')],
                    'date:week': ('2022-05-29', 'W23 2022'),
                },
                {
                    '__count': 1,
                    '__extra_domain': ['&', ('date', '>=', '2023-01-29'), ('date', '<', '2023-02-05')],
                    'date:week': ('2023-01-29', 'W5 2023'),
                },
                {'__count': 1, '__extra_domain': [('date', '=', False)], 'date:week': False},
            ]
        )

        result = Model.formatted_read_group([], ['date:month'], ['__count'])
        self.assertEqual(
            result,
            [
                {
                    '__count': 4,
                    '__extra_domain': ['&', ('date', '>=', '2022-01-01'), ('date', '<', '2022-02-01')],
                    'date:month': ('2022-01-01', 'January 2022'),
                },
                {
                    '__count': 1,
                    '__extra_domain': ['&', ('date', '>=', '2022-02-01'), ('date', '<', '2022-03-01')],
                    'date:month': ('2022-02-01', 'February 2022'),
                },
                {
                    '__count': 1,
                    '__extra_domain': ['&', ('date', '>=', '2022-05-01'), ('date', '<', '2022-06-01')],
                    'date:month': ('2022-05-01', 'May 2022'),
                },
                {
                    '__count': 1,
                    '__extra_domain': ['&', ('date', '>=', '2023-01-01'), ('date', '<', '2023-02-01')],
                    'date:month': ('2023-01-01', 'January 2023'),
                },
                {'__count': 1, '__extra_domain': [('date', '=', False)], 'date:month': False},
            ]
        )

        result = Model.formatted_read_group([], ['date:quarter'], ['__count'])
        self.assertEqual(
            result,
            [
                {
                    '__count': 5,
                    '__extra_domain': ['&', ('date', '>=', '2022-01-01'), ('date', '<', '2022-04-01')],
                    'date:quarter': ('2022-01-01', 'Q1 2022'),
                },
                {
                    '__count': 1,
                    '__extra_domain': ['&', ('date', '>=', '2022-04-01'), ('date', '<', '2022-07-01')],
                    'date:quarter': ('2022-04-01', 'Q2 2022'),
                },
                {
                    '__count': 1,
                    '__extra_domain': ['&', ('date', '>=', '2023-01-01'), ('date', '<', '2023-04-01')],
                    'date:quarter': ('2023-01-01', 'Q1 2023'),
                },
                {'__count': 1, '__extra_domain': [('date', '=', False)], 'date:quarter': False},
            ]
        )

        result = Model.formatted_read_group([], ['date:year'], ['__count'])
        self.assertEqual(
            result,
            [
                {
                    '__count': 6,
                    '__extra_domain': ['&', ('date', '>=', '2022-01-01'), ('date', '<', '2023-01-01')],
                    'date:year': ('2022-01-01', '2022'),
                },
                {
                    '__count': 1,
                    '__extra_domain': ['&', ('date', '>=', '2023-01-01'), ('date', '<', '2024-01-01')],
                    'date:year': ('2023-01-01', '2023'),
                },
                {'__count': 1, '__extra_domain': [('date', '=', False)], 'date:year': False},
            ]
        )
        # Reverse order
        result = Model.formatted_read_group([], ['date:year'], ['__count'], order='date:year DESC')
        self.assertEqual(
            result,
            [
                {'__count': 1, '__extra_domain': [('date', '=', False)], 'date:year': False},
                {
                    '__count': 1,
                    '__extra_domain': ['&', ('date', '>=', '2023-01-01'), ('date', '<', '2024-01-01')],
                    'date:year': ('2023-01-01', '2023'),
                },
                {
                    '__count': 6,
                    '__extra_domain': ['&', ('date', '>=', '2022-01-01'), ('date', '<', '2023-01-01')],
                    'date:year': ('2022-01-01', '2022'),
                },
            ]
        )

        # order param not in the aggregate
        result = Model.formatted_read_group([], ['date:year'], [], order='__count, date:year')
        self.assertEqual(
            result,
            [
                {
                    '__extra_domain': ['&', ('date', '>=', '2023-01-01'), ('date', '<', '2024-01-01')],
                    'date:year': ('2023-01-01', '2023'),
                },
                {'__extra_domain': [('date', '=', False)], 'date:year': False},
                {
                    '__extra_domain': ['&', ('date', '>=', '2022-01-01'), ('date', '<', '2023-01-01')],
                    'date:year': ('2022-01-01', '2022'),
                },
            ]
        )

    def test_groupby_datetime(self):
        Model = self.env['test_read_group.fill_temporal']
        records = Model.create(
            [
                {'datetime': False, 'value': 13},
                {'datetime': '1916-08-18 12:30:00', 'value': 1},
                {'datetime': '1916-08-18 12:50:00', 'value': 3},
                {'datetime': '1916-08-19 01:30:00', 'value': 7},
                {'datetime': '1916-10-18 23:30:00', 'value': 5},
            ],
        )

        # With 'UTC' timezone (the default one)
        Model = Model.with_context(tz='UTC')

        self.assertEqual(
            Model.formatted_read_group([('id', 'in', records.ids)], ['datetime:day'], ['value:sum']),
            [
                {
                    '__extra_domain': [
                        '&',
                        ('datetime', '>=', '1916-08-18 00:00:00'),
                        ('datetime', '<', '1916-08-19 00:00:00'),
                    ],
                    'datetime:day': ('1916-08-18 00:00:00', '18 Aug 1916'),
                    'value:sum': 4,
                },
                {
                    '__extra_domain': [
                        '&',
                        ('datetime', '>=', '1916-08-19 00:00:00'),
                        ('datetime', '<', '1916-08-20 00:00:00'),
                    ],
                    'datetime:day': ('1916-08-19 00:00:00', '19 Aug 1916'),
                    'value:sum': 7,
                },
                {
                    '__extra_domain': [
                        '&',
                        ('datetime', '>=', '1916-10-18 00:00:00'),
                        ('datetime', '<', '1916-10-19 00:00:00'),
                    ],
                    'datetime:day': ('1916-10-18 00:00:00', '18 Oct 1916'),
                    'value:sum': 5,
                },
                {'__extra_domain': [('datetime', '=', False)], 'datetime:day': False, 'value:sum': 13},
            ]
        )
        self.assertEqual(
            Model.formatted_read_group([('id', 'in', records.ids)], ['datetime:hour'], ['value:sum']),
            [
                {
                    '__extra_domain': [
                        '&',
                        ('datetime', '>=', '1916-08-18 12:00:00'),
                        ('datetime', '<', '1916-08-18 13:00:00'),
                    ],
                    'datetime:hour': ('1916-08-18 12:00:00', '12:00 18 Aug'),
                    'value:sum': 4,
                },
                {
                    '__extra_domain': [
                        '&',
                        ('datetime', '>=', '1916-08-19 01:00:00'),
                        ('datetime', '<', '1916-08-19 02:00:00'),
                    ],
                    'datetime:hour': ('1916-08-19 01:00:00', '01:00 19 Aug'),
                    'value:sum': 7,
                },
                {
                    '__extra_domain': [
                        '&',
                        ('datetime', '>=', '1916-10-18 23:00:00'),
                        ('datetime', '<', '1916-10-19 00:00:00'),
                    ],
                    'datetime:hour': ('1916-10-18 23:00:00', '11:00 18 Oct'),
                    'value:sum': 5,
                },
                {'__extra_domain': [('datetime', '=', False)], 'datetime:hour': False, 'value:sum': 13},
            ]
        )

        # With 'Europe/Brussels' [+01:00 UTC | +02:00 UTC DST] timezone
        Model = Model.with_context(tz='Europe/Brussels')
        self.assertEqual(
            Model.formatted_read_group([('id', 'in', records.ids)], ['datetime:day'], ['value:sum']),
            [
                {
                    '__extra_domain': [
                        '&',
                        ('datetime', '>=', '1916-08-17 22:00:00'),
                        ('datetime', '<', '1916-08-18 22:00:00'),
                    ],
                    'datetime:day': ('1916-08-17 22:00:00', '18 Aug 1916'),
                    'value:sum': 4,
                },
                {
                    '__extra_domain': [
                        '&',
                        ('datetime', '>=', '1916-08-18 22:00:00'),
                        ('datetime', '<', '1916-08-19 22:00:00'),
                    ],
                    'datetime:day': ('1916-08-18 22:00:00', '19 Aug 1916'),
                    'value:sum': 7,
                },
                {
                    '__extra_domain': [
                        '&',
                        ('datetime', '>=', '1916-10-18 23:00:00'),
                        ('datetime', '<', '1916-10-19 23:00:00'),
                    ],
                    'datetime:day': ('1916-10-18 23:00:00', '19 Oct 1916'),
                    'value:sum': 5,
                },
                {'__extra_domain': [('datetime', '=', False)], 'datetime:day': False, 'value:sum': 13},
            ]
        )
        self.assertEqual(
            Model.formatted_read_group([('id', 'in', records.ids)], ['datetime:hour'], ['value:sum']),
            [
                {
                    '__extra_domain': [
                        '&',
                        ('datetime', '>=', '1916-08-18 12:00:00'),
                        ('datetime', '<', '1916-08-18 13:00:00'),
                    ],
                    'datetime:hour': ('1916-08-18 12:00:00', '02:00 18 Aug'),
                    'value:sum': 4,
                },
                {
                    '__extra_domain': [
                        '&',
                        ('datetime', '>=', '1916-08-19 01:00:00'),
                        ('datetime', '<', '1916-08-19 02:00:00'),
                    ],
                    'datetime:hour': ('1916-08-19 01:00:00', '03:00 19 Aug'),
                    'value:sum': 7,
                },
                {
                    '__extra_domain': [
                        '&',
                        ('datetime', '>=', '1916-10-18 23:00:00'),
                        ('datetime', '<', '1916-10-19 00:00:00'),
                    ],
                    'datetime:hour': ('1916-10-18 23:00:00', '12:00 19 Oct'),
                    'value:sum': 5,
                },
                {'__extra_domain': [('datetime', '=', False)], 'datetime:hour': False, 'value:sum': 13},
            ]
        )

        # With 'America/Anchorage' [-09:00 UTC | -08:00 UTC DST] timezone
        Model = Model.with_context(tz='America/Anchorage')
        self.assertEqual(
            Model.formatted_read_group([('id', 'in', records.ids)], ['datetime:day'], ['value:sum']),
            [
                {
                    '__extra_domain': [
                        '&',
                        ('datetime', '>=', '1916-08-18 10:00:00'),
                        ('datetime', '<', '1916-08-19 10:00:00'),
                    ],
                    'datetime:day': ('1916-08-18 10:00:00', '18 Aug 1916'),
                    'value:sum': 11,
                },
                {
                    '__extra_domain': [
                        '&',
                        ('datetime', '>=', '1916-10-18 10:00:00'),
                        ('datetime', '<', '1916-10-19 10:00:00'),
                    ],
                    'datetime:day': ('1916-10-18 10:00:00', '18 Oct 1916'),
                    'value:sum': 5,
                },
                {'__extra_domain': [('datetime', '=', False)], 'datetime:day': False, 'value:sum': 13},
            ]
        )
        # by hour
        self.assertEqual(
            Model.formatted_read_group([('id', 'in', records.ids)], ['datetime:hour'], ['value:sum']),
            [
                {
                    '__extra_domain': [
                        '&',
                        ('datetime', '>=', '1916-08-18 12:00:00'),
                        ('datetime', '<', '1916-08-18 13:00:00'),
                    ],
                    'datetime:hour': ('1916-08-18 12:00:00', '02:00 18 Aug'),
                    'value:sum': 4,
                },
                {
                    '__extra_domain': [
                        '&',
                        ('datetime', '>=', '1916-08-19 01:00:00'),
                        ('datetime', '<', '1916-08-19 02:00:00'),
                    ],
                    'datetime:hour': ('1916-08-19 01:00:00', '03:00 18 Aug'),
                    'value:sum': 7,
                },
                {
                    '__extra_domain': [
                        '&',
                        ('datetime', '>=', '1916-10-18 23:00:00'),
                        ('datetime', '<', '1916-10-19 00:00:00'),
                    ],
                    'datetime:hour': ('1916-10-18 23:00:00', '01:00 18 Oct'),
                    'value:sum': 5,
                },
                {'__extra_domain': [('datetime', '=', False)], 'datetime:hour': False, 'value:sum': 13},
            ]
        )

    def test_groupby_date_week_timezone(self):
        Model = self.env['test_read_group.fill_temporal']
        records = Model.create(
            [  # BE,  SY,  US
                {'date': '2022-01-01'},  # W52, W01, W01
                {'date': '2022-01-02'},  # W52, W01, W02
                {'date': '2022-01-03'},  # W01, W01, W02
                {'date': '2022-05-27'},  # W21, W21, W22
                {'date': '2022-05-28'},  # W21, W22, W22
                {'date': '2022-05-29'},  # W21, W22, W23
                {'date': '2022-05-30'},  # W22, W22, W23
                {'date': '2022-06-18'},  # W24, W25, W25
                {'date': '2022-06-19'},  # W24, W25, W26
                {'date': '2022-06-20'},  # W25, W25, W26
            ],
        )

        tz_by_lang = {
            'fr_BE': 'Europe/Brussels',
            'ar_SY': 'Asia/Damascus',
            'en_US': 'America/New_York',
        }

        def set_context(lang):
            '''Add `lang` & `tz` to context, and add localized `datetime` values.'''
            tz = tz_by_lang[lang]
            tzinfo = timezone(tz)
            for record in records:
                local_dt = tzinfo.localize(datetime.combine(record.date, time.min))
                record.datetime = local_dt.astimezone(UTC).replace(tzinfo=None)
            return Model.with_context(lang=lang, tz=tz)

        self.assertEqual(
            babel.Locale.parse('fr_BE').first_week_day,
            0,
        )
        self.assertEqual(
            babel.Locale.parse('ar_SY').first_week_day,
            5,
        )
        self.assertEqual(
            babel.Locale.parse('en_US').first_week_day,
            6,
        )

        excepted_results = {
            'fr_BE': [  # same as ISO
                {
                    'date:week': ('2021-12-27', 'W52 2021'),
                    '__extra_domain': ['&', ('date', '>=', '2021-12-27'), ('date', '<', '2022-01-03')],
                    '__count': 2,
                },
                {
                    'date:week': ('2022-01-03', 'W1 2022'),
                    '__extra_domain': ['&', ('date', '>=', '2022-01-03'), ('date', '<', '2022-01-10')],
                    '__count': 1,
                },
                {
                    'date:week': ('2022-05-23', 'W21 2022'),
                    '__extra_domain': ['&', ('date', '>=', '2022-05-23'), ('date', '<', '2022-05-30')],
                    '__count': 3,
                },
                {
                    'date:week': ('2022-05-30', 'W22 2022'),
                    '__extra_domain': ['&', ('date', '>=', '2022-05-30'), ('date', '<', '2022-06-06')],
                    '__count': 1,
                },
                {
                    'date:week': ('2022-06-13', 'W24 2022'),
                    '__extra_domain': ['&', ('date', '>=', '2022-06-13'), ('date', '<', '2022-06-20')],
                    '__count': 2,
                },
                {
                    'date:week': ('2022-06-20', 'W25 2022'),
                    '__extra_domain': ['&', ('date', '>=', '2022-06-20'), ('date', '<', '2022-06-27')],
                    '__count': 1,
                },
            ],
            'ar_SY': [  # non-iso, start of week = sat
                {
                    'date:week': ('2022-01-01', 'W1 2022'),
                    '__extra_domain': ['&', ('date', '>=', '2022-01-01'), ('date', '<', '2022-01-08')],
                    '__count': 3,
                },
                {
                    'date:week': ('2022-05-21', 'W21 2022'),
                    '__extra_domain': ['&', ('date', '>=', '2022-05-21'), ('date', '<', '2022-05-28')],
                    '__count': 1,
                },
                {
                    'date:week': ('2022-05-28', 'W22 2022'),
                    '__extra_domain': ['&', ('date', '>=', '2022-05-28'), ('date', '<', '2022-06-04')],
                    '__count': 3,
                },
                {
                    'date:week': ('2022-06-18', 'W25 2022'),
                    '__extra_domain': ['&', ('date', '>=', '2022-06-18'), ('date', '<', '2022-06-25')],
                    '__count': 3,
                },
            ],
            'en_US': [   # non-iso, start of week = sun
                {
                    'date:week': ('2021-12-26', 'W1 2022'),
                    '__extra_domain': ['&', ('date', '>=', '2021-12-26'), ('date', '<', '2022-01-02')],
                    '__count': 1,
                },
                {
                    'date:week': ('2022-01-02', 'W2 2022'),
                    '__extra_domain': ['&', ('date', '>=', '2022-01-02'), ('date', '<', '2022-01-09')],
                    '__count': 2,
                },
                {
                    'date:week': ('2022-05-22', 'W22 2022'),
                    '__extra_domain': ['&', ('date', '>=', '2022-05-22'), ('date', '<', '2022-05-29')],
                    '__count': 2,
                },
                {
                    'date:week': ('2022-05-29', 'W23 2022'),
                    '__extra_domain': ['&', ('date', '>=', '2022-05-29'), ('date', '<', '2022-06-05')],
                    '__count': 2,
                },
                {
                    'date:week': ('2022-06-12', 'W25 2022'),
                    '__extra_domain': ['&', ('date', '>=', '2022-06-12'), ('date', '<', '2022-06-19')],
                    '__count': 1,
                },
                {
                    'date:week': ('2022-06-19', 'W26 2022'),
                    '__extra_domain': ['&', ('date', '>=', '2022-06-19'), ('date', '<', '2022-06-26')],
                    '__count': 2,
                },
            ],
        }

        for timezone_key, excepted in excepted_results.items():
            with self.subTest(f'groupby absolute week with {timezone_key=}'):
                self.env['res.lang']._activate_lang(timezone_key)
                Model = set_context(timezone_key)
                groups = Model.formatted_read_group(
                    [],
                    groupby=['date:week'],
                    aggregates=['__count'],
                )
                self.assertEqual(groups, excepted)

                # verify grouping on datetime is identical to grouping on date
                groups = Model.formatted_read_group(
                    [],
                    groupby=['datetime:week'],
                    aggregates=['__count'],
                )
                self.assertDictEqual(
                    {week['datetime:week'][1]: week['__count'] for week in groups},
                    {week['date:week'][1]: week['__count'] for week in excepted},
                    'Grouping by datetime:week should be identical to date:week',
                )

        excepted = [
            # 2022-01-03
            {'date:iso_week_number': 1, '__extra_domain': [('date.iso_week_number', '=', 1)], '__count': 1},
            # 2022-05-27, 2022-05-28, 2022-05-29
            {'date:iso_week_number': 21, '__extra_domain': [('date.iso_week_number', '=', 21)], '__count': 3},
            # 2022-05-30
            {'date:iso_week_number': 22, '__extra_domain': [('date.iso_week_number', '=', 22)], '__count': 1},
            # 2022-06-18 and 2022-06-19
            {'date:iso_week_number': 24, '__extra_domain': [('date.iso_week_number', '=', 24)], '__count': 2},
            # 2022-06-20
            {'date:iso_week_number': 25, '__extra_domain': [('date.iso_week_number', '=', 25)], '__count': 1},
            # 2022-01-01 and 2022-01-02 (W52 of 2021)
            {'date:iso_week_number': 52, '__extra_domain': [('date.iso_week_number', '=', 52)], '__count': 2},
        ]

        for timezone_key in ('fr_BE', 'ar_SY', 'en_US'):
            with self.subTest(f'groupby relative week with {timezone_key=}'):
                # same test as above with week_number as aggregate
                Model = set_context(timezone_key)
                groups = Model.formatted_read_group(
                    [],
                    aggregates=['__count'],
                    groupby=['date:iso_week_number'],
                )
                self.assertEqual(groups, excepted)

    def test_groupby_date_part_number(self):
        '''Test grouping by date part number (ex. month_number gives 1 for January)'''
        Model = self.env['test_read_group.fill_temporal']
        Model.create({})  # Falsy date
        Model.create({'date': '2022-01-29', 'datetime': '2022-01-29 13:55:12'})  # W4, M1, Q1
        Model.create({'date': '2022-01-29', 'datetime': '2022-01-29 15:55:13'})  # W4, M1, Q1
        Model.create({'date': '2022-01-30', 'datetime': '2022-01-30 13:54:14'})  # W4, M1, Q1
        Model.create({'date': '2022-01-31', 'datetime': '2022-01-31 15:55:14'})  # W5, M1, Q1
        Model.create({'date': '2022-02-01', 'datetime': '2022-02-01 14:54:13'})  # W5, M2, Q1
        Model.create({'date': '2022-05-29', 'datetime': '2022-05-29 14:55:13'})  # W21, M5, Q2
        Model.create({'date': '2023-01-29', 'datetime': '2023-01-29 15:55:13'})  # W4, M1, Q1

        result = Model.formatted_read_group([], ['datetime:second_number'], ['__count'])
        self.assertEqual(
            result,
            [
                {
                    'datetime:second_number': 12,
                    '__extra_domain': [('datetime.second_number', '=', 12)],
                    '__count': 1,
                },
                {
                    'datetime:second_number': 13,
                    '__extra_domain': [('datetime.second_number', '=', 13)],
                    '__count': 4,
                },
                {
                    'datetime:second_number': 14,
                    '__extra_domain': [('datetime.second_number', '=', 14)],
                    '__count': 2,
                },
                {
                    'datetime:second_number': False,
                    '__extra_domain': [('datetime.second_number', '=', False)],
                    '__count': 1,
                },
            ]
        )

        result = Model.formatted_read_group([], ['datetime:minute_number'], ['__count'])
        self.assertEqual(
            result,
            [
                {
                    'datetime:minute_number': 54,
                    '__extra_domain': [('datetime.minute_number', '=', 54)],
                    '__count': 2,
                },
                {
                    'datetime:minute_number': 55,
                    '__extra_domain': [('datetime.minute_number', '=', 55)],
                    '__count': 5,
                },
                {
                    'datetime:minute_number': False,
                    '__extra_domain': [('datetime.minute_number', '=', False)],
                    '__count': 1,
                },
            ]
        )

        result = Model.formatted_read_group([], ['datetime:hour_number'], ['__count'])
        self.assertEqual(
            result,
            [
                {'datetime:hour_number': 13, '__extra_domain': [('datetime.hour_number', '=', 13)], '__count': 2},
                {'datetime:hour_number': 14, '__extra_domain': [('datetime.hour_number', '=', 14)], '__count': 2},
                {'datetime:hour_number': 15, '__extra_domain': [('datetime.hour_number', '=', 15)], '__count': 3},
                {
                    'datetime:hour_number': False,
                    '__extra_domain': [('datetime.hour_number', '=', False)],
                    '__count': 1,
                },
            ]
        )

        result = Model.formatted_read_group([], ['date:day_of_year'], ['__count'])
        self.assertEqual(
            result,
            [
                {'date:day_of_year': 29, '__extra_domain': [('date.day_of_year', '=', 29)], '__count': 3},
                {'date:day_of_year': 30, '__extra_domain': [('date.day_of_year', '=', 30)], '__count': 1},
                {'date:day_of_year': 31, '__extra_domain': [('date.day_of_year', '=', 31)], '__count': 1},
                {'date:day_of_year': 32, '__extra_domain': [('date.day_of_year', '=', 32)], '__count': 1},
                {'date:day_of_year': 149, '__extra_domain': [('date.day_of_year', '=', 149)], '__count': 1},
                {'date:day_of_year': False, '__extra_domain': [('date.day_of_year', '=', False)], '__count': 1},
            ]
        )

        result = Model.formatted_read_group([], ['date:day_of_month'], ['__count'])
        self.assertEqual(
            result,
            [
                {'date:day_of_month': 1, '__extra_domain': [('date.day_of_month', '=', 1)], '__count': 1},
                {'date:day_of_month': 29, '__extra_domain': [('date.day_of_month', '=', 29)], '__count': 4},
                {'date:day_of_month': 30, '__extra_domain': [('date.day_of_month', '=', 30)], '__count': 1},
                {'date:day_of_month': 31, '__extra_domain': [('date.day_of_month', '=', 31)], '__count': 1},
                {'date:day_of_month': False, '__extra_domain': [('date.day_of_month', '=', False)], '__count': 1},
            ]
        )

        result = Model.formatted_read_group([], ['date:day_of_week'], ['__count'])
        self.assertEqual(
            result,
            [
                {'date:day_of_week': 0, '__extra_domain': [('date.day_of_week', '=', 0)], '__count': 3},
                {'date:day_of_week': 1, '__extra_domain': [('date.day_of_week', '=', 1)], '__count': 1},
                {'date:day_of_week': 2, '__extra_domain': [('date.day_of_week', '=', 2)], '__count': 1},
                {'date:day_of_week': 6, '__extra_domain': [('date.day_of_week', '=', 6)], '__count': 2},
                {'date:day_of_week': False, '__extra_domain': [('date.day_of_week', '=', False)], '__count': 1},
            ]
        )

        result = Model.formatted_read_group([], ['date:iso_week_number'], ['__count'])
        self.assertEqual(
            result,
            [
                {'date:iso_week_number': 4, '__extra_domain': [('date.iso_week_number', '=', 4)], '__count': 4},
                {'date:iso_week_number': 5, '__extra_domain': [('date.iso_week_number', '=', 5)], '__count': 2},
                {'date:iso_week_number': 21, '__extra_domain': [('date.iso_week_number', '=', 21)], '__count': 1},
                {
                    'date:iso_week_number': False,
                    '__extra_domain': [('date.iso_week_number', '=', False)],
                    '__count': 1,
                },
            ]
        )

        result = Model.formatted_read_group([], ['date:month_number'], ['__count'])
        self.assertEqual(
            result,
            [
                {'date:month_number': 1, '__extra_domain': [('date.month_number', '=', 1)], '__count': 5},
                {'date:month_number': 2, '__extra_domain': [('date.month_number', '=', 2)], '__count': 1},
                {'date:month_number': 5, '__extra_domain': [('date.month_number', '=', 5)], '__count': 1},
                {'date:month_number': False, '__extra_domain': [('date.month_number', '=', False)], '__count': 1},
            ]
        )

        result = Model.formatted_read_group([], ['date:quarter_number'], ['__count'])
        self.assertEqual(
            result,
            [
                {'date:quarter_number': 1, '__extra_domain': [('date.quarter_number', '=', 1)], '__count': 6},
                {'date:quarter_number': 2, '__extra_domain': [('date.quarter_number', '=', 2)], '__count': 1},
                {
                    'date:quarter_number': False,
                    '__extra_domain': [('date.quarter_number', '=', False)],
                    '__count': 1,
                },
            ]
        )

        # Test datetime with quarter_number + DESC order
        result = Model.formatted_read_group(
            [], ['datetime:quarter_number'], ['__count'], order='datetime:quarter_number DESC',
        )
        self.assertEqual(
            result,
            [
                {
                    'datetime:quarter_number': False,
                    '__extra_domain': [('datetime.quarter_number', '=', False)],
                    '__count': 1,
                },
                {
                    'datetime:quarter_number': 2,
                    '__extra_domain': [('datetime.quarter_number', '=', 2)],
                    '__count': 1,
                },
                {
                    'datetime:quarter_number': 1,
                    '__extra_domain': [('datetime.quarter_number', '=', 1)],
                    '__count': 6,
                },
            ]
        )

        result = Model.formatted_read_group([], ['date:year_number'], ['__count'])
        self.assertEqual(
            result,
            [
                {'date:year_number': 2022, '__extra_domain': [('date.year_number', '=', 2022)], '__count': 6},
                {'date:year_number': 2023, '__extra_domain': [('date.year_number', '=', 2023)], '__count': 1},
                {'date:year_number': False, '__extra_domain': [('date.year_number', '=', False)], '__count': 1},
            ]
        )

    def test_groupby_datetime_part_with_timezone(self):
        Model = self.env['test_read_group.fill_temporal']
        self.env['res.lang']._activate_lang('NZ')
        # Monday, it is the 5th week in UTC and the 6th in NZ
        Model.create({'value': 98, 'datetime': '2023-02-05 23:55:00'})
        result = (Model.with_context({'tz': 'Pacific/Auckland'})  # GMT+12
                            .formatted_read_group([],
                                        aggregates=['__count', 'value:sum'],
                                        groupby=['datetime:iso_week_number']))
        self.assertEqual(result, [
                    {
                        'datetime:iso_week_number': 6,
                        '__count': 1,
                        'value:sum': 98,
                        '__extra_domain': [('datetime.iso_week_number', '=', 6)],
                    }])
        result = Model.with_context({'tz': 'Pacific/Auckland'}).search(result[0]['__extra_domain'])
        self.assertEqual(len(result), 1)
        self.assertEqual(result.value, 98)

    def test_groupby_date_part_with_timezone(self):
        Model = self.env['test_read_group.fill_temporal']
        Model.create({'value': 98, 'date': '2023-02-05'})
        self.env['res.lang']._activate_lang('NZ')
        self.env['res.lang']._activate_lang('fr_BE')
        result = (Model.with_context({'tz': 'fr_BE'})  # GMT+1, first day of week is Monday
                  .formatted_read_group([],
                              aggregates=['__count', 'value:sum'],
                              groupby=['date:day_of_week']))
        self.assertEqual(result, [
            {
                'date:day_of_week': 0,
                '__count': 1,
                'value:sum': 98,
                '__extra_domain': [('date.day_of_week', '=', 0)],
            }])
        res = Model.with_context({'tz': 'fr_BE'}).search(result[0]['__extra_domain'])
        self.assertEqual(len(res), 1)
        self.assertEqual(res.mapped('value'), [98])

        result = (Model.with_context({'tz': 'NZ'})  # GMT+12, first day of week is Sunday
                  .formatted_read_group([],
                              aggregates=['__count', 'value:sum'],
                              groupby=['date:day_of_week']))
        self.assertEqual(result, [
            {
                'date:day_of_week': 0,
                '__count': 1,
                'value:sum': 98,
                '__extra_domain': [('date.day_of_week', '=', 0)],
            }])

        res = Model.with_context({'tz': 'NZ'}).search(result[0]['__extra_domain'])
        self.assertEqual(len(res), 1)
        self.assertEqual(res.mapped('value'), [98])

    def test_groupby_day_of_week_ordered_with_user_lang(self):
        Model = self.env['test_read_group.fill_temporal']
        Model.create([
            {'value': 98, 'date': '2023-02-05'}, # Sunday
            {'value': 99, 'date': '2023-02-06'}, # Monday
        ])
        self.env['res.lang']._activate_lang('fr_BE')
        result = Model.formatted_read_group([],
                    aggregates=['__count', 'value:sum'],
                    groupby=['date:day_of_week'])
        self.assertEqual(result, [
            {
                'date:day_of_week': 0, # Sunday
                '__count': 1,
                'value:sum': 98,
                '__extra_domain': [('date.day_of_week', '=', 0)],
            },
            {
                'date:day_of_week': 1, # Monday
                '__count': 1,
                'value:sum': 99,
                '__extra_domain': [('date.day_of_week', '=', 1)],
            }])
        result = (Model.with_context({'tz': 'fr_BE'}) # first day of week is Monday
                  .formatted_read_group([],
                        aggregates=['__count', 'value:sum'],
                        groupby=['date:day_of_week']))
        self.assertEqual(result, [
            {
                'date:day_of_week': 1, # Monday
                '__count': 1,
                'value:sum': 99,
                '__extra_domain': [('date.day_of_week', '=', 1)],
            },
            {
                'date:day_of_week': 0, # Sunday
                '__count': 1,
                'value:sum': 98,
                '__extra_domain': [('date.day_of_week', '=', 0)],
            }])

    def test_groupby_day_of_week_descending_order_with_user_lang(self):
        Model = self.env['test_read_group.fill_temporal']
        Model.create([
            {'value': 98, 'date': '2023-02-05'}, # Sunday
            {'value': 99, 'date': '2023-02-06'}, # Monday
        ])
        self.env['res.lang']._activate_lang('fr_BE')
        result = Model.formatted_read_group([],
                    aggregates=['__count', 'value:sum'],
                    groupby=['date:day_of_week'],
                    order='date:day_of_week DESC')
        self.assertEqual(result, [
            {
                'date:day_of_week': 1, # Monday
                '__count': 1,
                'value:sum': 99,
                '__extra_domain': [('date.day_of_week', '=', 1)],
            },
            {
                'date:day_of_week': 0, # Sunday
                '__count': 1,
                'value:sum': 98,
                '__extra_domain': [('date.day_of_week', '=', 0)],
            }])
        result = (Model.with_context({'tz': 'fr_BE'}) # first day of week is Monday
                  .formatted_read_group([],
                        aggregates=['__count', 'value:sum'],
                        groupby=['date:day_of_week'],
                        order='date:day_of_week DESC'))
        self.assertEqual(result, [
            {
                'date:day_of_week': 0, # Sunday
                '__count': 1,
                'value:sum': 98,
                '__extra_domain': [('date.day_of_week', '=', 0)],
            },
            {
                'date:day_of_week': 1, # Monday
                '__count': 1,
                'value:sum': 99,
                '__extra_domain': [('date.day_of_week', '=', 1)],
            }])

    def test_groupby_many2many(self):
        User = self.env['test_read_group.user']
        mario, luigi = User.create([{'name': 'Mario'}, {'name': 'Luigi'}])
        tasks = self.env['test_read_group.task'].create(
            [
                {  # both users
                    'name': 'Super Mario Bros.',
                    'user_ids': [Command.set((mario + luigi).ids)],
                },
                {  # mario only
                    'name': 'Paper Mario',
                    'user_ids': [Command.set(mario.ids)],
                },
                {  # luigi only
                    'name': "Luigi's Mansion",
                    'user_ids': [Command.set(luigi.ids)],
                },
                {  # no user
                    'name': 'Donkey Kong',
                },
            ],
        )

        # TODO: should we order by the relation and not by the id also for many2many
        # (same than many2one) ? for public methods ?
        self.assertEqual(
            tasks.formatted_read_group(
                [('id', 'in', tasks.ids)],
                ['user_ids'],
                ['name:array_agg'],
            ),
            [
                {
                    '__extra_domain': [('user_ids', '=', mario.id)],
                    'name:array_agg': ['Super Mario Bros.', 'Paper Mario'],
                    'user_ids': (mario.id, 'Mario'),
                },
                {
                    '__extra_domain': [('user_ids', '=', luigi.id)],
                    'name:array_agg': ['Super Mario Bros.', "Luigi's Mansion"],
                    'user_ids': (luigi.id, 'Luigi'),
                },
                {
                    '__extra_domain': [('user_ids', 'not any', [])],
                    'name:array_agg': ['Donkey Kong'],
                    'user_ids': False,
                },
            ]
        )

        # Inverse the order, only inverse depending of id (see TODO above)
        self.assertEqual(
            tasks.formatted_read_group(
                [('id', 'in', tasks.ids)],
                ['user_ids'],
                ['name:array_agg'],
                order='user_ids DESC',
            ),
            [
                {
                    'user_ids': False,
                    '__extra_domain': [('user_ids', 'not any', [])],
                    'name:array_agg': ['Donkey Kong'],
                },
                {
                    'user_ids': (luigi.id, 'Luigi'),
                    '__extra_domain': [('user_ids', '=', luigi.id)],
                    'name:array_agg': ['Super Mario Bros.', "Luigi's Mansion"],
                },
                {
                    'user_ids': (mario.id, 'Mario'),
                    '__extra_domain': [('user_ids', '=', mario.id)],
                    'name:array_agg': ['Super Mario Bros.', 'Paper Mario'],
                },
            ]
        )

        # group tasks with some ir.rule on users
        users_model = self.env['ir.model']._get(mario._name)
        self.env['ir.rule'].create(
            {
                'name': 'Only The Lone Wanderer allowed',
                'model_id': users_model.id,
                'domain_force': [('id', '=', mario.id)],
            },
        )

        # as demo user, ir.rule should apply
        tasks = tasks.with_user(self.base_user)
        result = tasks.formatted_read_group([], groupby=['user_ids'], aggregates=['__count', 'name:array_agg'])
        self.assertEqual(
            result,
            [
                {
                    'user_ids': (mario.id, 'Mario'),
                    '__extra_domain': [('user_ids', '=', mario.id)],
                    '__count': 2,
                    'name:array_agg': ['Super Mario Bros.', 'Paper Mario'],
                },
                {
                    'user_ids': False,
                    '__extra_domain': [('user_ids', 'not any', [])],
                    '__count': 2,
                    'name:array_agg': ["Luigi's Mansion", 'Donkey Kong'],
                },
            ]
        )

        for group in result:
            self.assertEqual(
                group['__count'],
                tasks.search_count(group['__extra_domain']),
                'A search using the domain returned by the formatted_read_group should give the '
                'same number of records as counted in the group',
            )

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

        field_info = RelatedBase.fields_get(
            ['foo_id_name', 'foo_id_name_sudo', 'foo_id_bar_id_name', 'foo_id_bar_name', 'foo_id_bar_name_sudo'],
            ['groupable', 'aggregator'],
        )
        self.assertFalse(field_info['foo_id_name']['groupable'])
        self.assertNotIn('aggregator', field_info['foo_id_name'])

        self.assertTrue(field_info['foo_id_name_sudo']['groupable'])
        self.assertNotIn('aggregator', field_info['foo_id_name_sudo'])

        self.assertTrue(field_info['foo_id_bar_id_name']['groupable'])
        self.assertEqual(field_info['foo_id_bar_id_name']['aggregator'], 'count_distinct')

        self.assertTrue(field_info['foo_id_bar_name']['groupable'])
        self.assertEqual(field_info['foo_id_bar_name']['aggregator'], 'count_distinct')

        self.assertTrue(field_info['foo_id_bar_name_sudo']['groupable'])
        self.assertEqual(field_info['foo_id_bar_name_sudo']['aggregator'], 'count_distinct')

        RelatedBase.formatted_read_group([], ['foo_id_name_sudo'], ['__count'])
        self.assertEqual(
            RelatedBase.formatted_read_group([], ['foo_id_name_sudo'], ['__count']),
            [
                {
                    '__count': 2,
                    '__extra_domain': [('foo_id_name_sudo', '=', 'foo_a_bar_a')],
                    'foo_id_name_sudo': 'foo_a_bar_a',
                },
                {
                    '__count': 1,
                    '__extra_domain': [('foo_id_name_sudo', '=', 'foo_b_bar_false')],
                    'foo_id_name_sudo': 'foo_b_bar_false',
                },
                {'__count': 2, '__extra_domain': [('foo_id_name_sudo', '=', False)], 'foo_id_name_sudo': False},
            ]
        )

        # Same result for these 3 scenario, except name of the group
        for fname in ('foo_id_bar_id_name', 'foo_id_bar_name', 'foo_id_bar_name_sudo'):
            result = RelatedBase.formatted_read_group([], [fname], ['__count'])
            expected = [
                {'__count': 3, '__extra_domain': [(fname, '=', 'bar_a')], fname: 'bar_a'},
                {'__count': 2, '__extra_domain': [(fname, '=', False)], fname: False},
            ]
            self.assertEqual(result, expected)

        self.assertEqual(
            RelatedBase.formatted_read_group([], aggregates=['foo_id_bar_id_name:count_distinct']),
            [{'__extra_domain': [(1, '=', 1)], 'foo_id_bar_id_name:count_distinct': 1}],
        )

        # Cannot groupby on foo_names_sudo because it traverse One2many
        with self.assertRaises(ValueError):
            RelatedBar.formatted_read_group([], ['foo_names_sudo'])

    def test_inherited(self):
        RelatedBase = self.env['test_read_group.related_base']
        RelatedInherits = self.env['test_read_group.related_inherits']

        bases = RelatedBase.create(
            [
                {'name': 'a', 'value': 1},
                {'name': 'a', 'value': 2},
                {'name': 'b', 'value': 3},
                {'name': False, 'value': 4},
            ],
        )
        RelatedInherits.create(
            [
                {'base_id': bases[0].id},
                {'base_id': bases[0].id},
                {'base_id': bases[1].id},
                {'base_id': bases[2].id},
                {'base_id': bases[3].id},
            ],
        )

        # env.su => false
        RelatedInherits = RelatedInherits.with_user(self.base_user)

        field_info = RelatedInherits.fields_get(
            ['name', 'foo_id_name', 'foo_id_name_sudo', 'value'],
            ['groupable', 'aggregator'],
        )
        self.assertTrue(field_info['name']['groupable'])
        self.assertFalse(field_info['foo_id_name']['groupable'])
        self.assertTrue(field_info['foo_id_name_sudo']['groupable'])
        self.assertEqual(field_info['value']['aggregator'], 'sum')

        self.assertEqual(
            RelatedInherits.formatted_read_group([], ['name'], ['__count']),
            [
                {'__count': 3, '__extra_domain': [('name', '=', 'a')], 'name': 'a'},
                {'__count': 1, '__extra_domain': [('name', '=', 'b')], 'name': 'b'},
                {'__count': 1, '__extra_domain': [('name', '=', False)], 'name': False},
            ]
        )

        self.assertEqual(
            RelatedInherits.formatted_read_group([], ['name'], ['value:sum']),
            [
                {'__extra_domain': [('name', '=', 'a')], 'name': 'a', 'value:sum': 4},
                {'__extra_domain': [('name', '=', 'b')], 'name': 'b', 'value:sum': 3},
                {'__extra_domain': [('name', '=', False)], 'name': False, 'value:sum': 4},
            ]
        )

        self.assertEqual(
            RelatedInherits.formatted_read_group([], ['foo_id_name_sudo'], ['__count']),
            [
                {'__count': 5, '__extra_domain': [('foo_id_name_sudo', '=', False)], 'foo_id_name_sudo': False},
            ]
        )

        # Cannot groupby because foo_id_name is related_sudo=False
        with self.assertRaises(ValueError):
            RelatedInherits.formatted_read_group([], ['foo_id_name'])

    def test_related_many2many_groupby(self):
        bases = self.env['test_read_group.related_base'].create(
            [
                {'name': 'A'},
                {'name': 'B'},
                {'name': 'C'},
                {'name': 'D'},
            ],
        )
        bars = self.env['test_read_group.related_bar'].create(
            [
                {'base_ids': [Command.link(bases[0].id)]},
                {'base_ids': [Command.link(bases[0].id), Command.link(bases[1].id)]},
                {'base_ids': [Command.link(bases[2].id)]},
                {'base_ids': []},
            ],
        )

        RelatedFoo = self.env['test_read_group.related_foo']
        RelatedFoo.create(
            [
                {'bar_id': bars[0].id},
                {'bar_id': bars[0].id},
                {'bar_id': bars[1].id},
                {'bar_id': bars[2].id},
                {'bar_id': bars[3].id},
            ],
        )
        RelatedFoo = RelatedFoo.with_user(self.base_user)
        self.assertEqual(
            RelatedFoo.formatted_read_group([], ['bar_base_ids'], ['__count']),
            [
                {
                    '__count': 3,
                    '__extra_domain': [('bar_base_ids', '=', bases[0].id)],
                    'bar_base_ids': (bases[0].id, 'A'),
                },
                {
                    '__count': 1,
                    '__extra_domain': [('bar_base_ids', '=', bases[1].id)],
                    'bar_base_ids': (bases[1].id, 'B'),
                },
                {
                    '__count': 1,
                    '__extra_domain': [('bar_base_ids', '=', bases[2].id)],
                    'bar_base_ids': (bases[2].id, 'C'),
                },
                {
                    '__count': 1,
                    '__extra_domain': [('bar_base_ids', 'not any', [])],
                    'bar_base_ids': False,
                },
            ]
        )

        field_info = RelatedFoo.fields_get(['bar_base_ids'], ['groupable'])
        self.assertTrue(field_info['bar_base_ids']['groupable'])

        # With ir.rule on the comodel of the many2many
        related_base_model = self.env['ir.model']._get('test_read_group.related_base')
        self.env['ir.rule'].create(
            {
                'name': 'Only The Lone Wanderer allowed',
                'model_id': related_base_model.id,
                'domain_force': str([('name', '!=', 'A')]),
            },
        )

        self.assertEqual(
            RelatedFoo.formatted_read_group([], ['bar_base_ids'], ['__count']),
            [
                {
                    '__count': 1,
                    '__extra_domain': [('bar_base_ids', '=', bases[1].id)],
                    'bar_base_ids': (bases[1].id, 'B'),
                },
                {
                    '__count': 1,
                    '__extra_domain': [('bar_base_ids', '=', bases[2].id)],
                    'bar_base_ids': (bases[2].id, 'C'),
                },
                {
                    '__count': 3,
                    '__extra_domain': [('bar_base_ids', 'not any', [])],
                    'bar_base_ids': False,
                },
            ]
        )

    def test_order_by_many2one_id_perf(self):
        # ordering by a many2one ordered itself by id does not use useless join
        OrderLine = self.env['test_read_group.order.line']
        expected_query = '''
            SELECT "test_read_group_order_line"."order_id", COUNT(*)
            FROM "test_read_group_order_line"
            GROUP BY "test_read_group_order_line"."order_id"
            ORDER BY "test_read_group_order_line"."order_id"
        '''
        with self.assertQueries([expected_query + ' ASC']):
            OrderLine.formatted_read_group([], ['order_id'], ['__count'])
        with self.assertQueries([expected_query + ' DESC']):
            OrderLine.formatted_read_group([], ['order_id'], ['__count'], order='order_id DESC')

        # a hack to check model order
        expected_query = '''
            SELECT "test_read_group_order_line"."order_id", COUNT(*)
            FROM "test_read_group_order_line"
            LEFT JOIN "test_read_group_order" AS "test_read_group_order_line__order_id"
            ON ("test_read_group_order_line"."order_id" = "test_read_group_order_line__order_id"."id")
            GROUP BY "test_read_group_order_line"."order_id", (COALESCE("test_read_group_order_line__order_id"."company_dependent_name"->%s,to_jsonb(%s::VARCHAR))->>0)::VARCHAR
            ORDER BY (COALESCE("test_read_group_order_line__order_id"."company_dependent_name"->%s,to_jsonb(%s::VARCHAR))->>0)::VARCHAR
        '''
        self.env['ir.default'].set('test_read_group.order', 'company_dependent_name', 'name with space')
        OrderLine = OrderLine.with_context(test_read_group_order_company_dependent=True)
        OrderLine.formatted_read_group([], ['order_id'], ['__count'])
        with self.assertQueries([expected_query]):
            OrderLine.formatted_read_group([], ['order_id'], ['__count'])
        OrderLine.formatted_read_group([], ['order_id'], ['__count'], order='order_id DESC')
        with self.assertQueries([expected_query + ' DESC']):
            OrderLine.formatted_read_group([], ['order_id'], ['__count'], order='order_id DESC')

    def test_groupby_sequence_fnames_many2one(self):
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

        # warmup ormcache
        RelatedBase.formatted_read_group([], ['foo_id.bar_id'], ['__count'])

        expected_query = """
            SELECT "test_read_group_related_base__foo_id"."bar_id",
                    COUNT(*)
            FROM "test_read_group_related_base"
            LEFT JOIN "test_read_group_related_foo" AS "test_read_group_related_base__foo_id"
                ON ("test_read_group_related_base"."foo_id" = "test_read_group_related_base__foo_id"."id")
            GROUP BY "test_read_group_related_base__foo_id"."bar_id"
            ORDER BY "test_read_group_related_base__foo_id"."bar_id" ASC
        """
        with self.assertQueries([expected_query]):
            result = RelatedBase.formatted_read_group([], ['foo_id.bar_id'], ['__count'])
            self.assertEqual(
                result,
                [
                    {
                        "__count": 3,
                        "__extra_domain": [("foo_id", "any", [("bar_id", "=", bars[0].id)])],
                        "foo_id.bar_id": (bars[0].id, 'bar_a'),
                    },
                    {
                        "__count": 1,
                        "__extra_domain": [("foo_id", "any", [("bar_id", "=", bars[1].id)])],
                        "foo_id.bar_id": (bars[1].id, False),
                    },
                    {
                        "__count": 1,
                        "__extra_domain": ['|', ("foo_id", "not any", []), ("foo_id", "any", [("bar_id", "=", False)])],
                        "foo_id.bar_id": False,
                    },
                ],
            )
        for group in result:
            self.assertEqual(group['__count'], RelatedBase.search_count(group['__extra_domain']))

        # Test without sudo but without ir_rules
        RelatedBase = RelatedBase.with_user(self.base_user)

        # warmup ormcache
        RelatedBase.formatted_read_group([], ['foo_id.bar_id'], ['__count'])

        with self.assertQueries([expected_query]):
            result = RelatedBase.formatted_read_group([], ['foo_id.bar_id'], ['__count'])
            self.assertEqual(
                result,
                [
                    {
                        "__count": 3,
                        "__extra_domain": [("foo_id", "any", [("bar_id", "=", bars[0].id)])],
                        "foo_id.bar_id": (bars[0].id, 'bar_a'),
                    },
                    {
                        "__count": 1,
                        "__extra_domain": [("foo_id", "any", [("bar_id", "=", bars[1].id)])],
                        "foo_id.bar_id": (bars[1].id, False),
                    },
                    {
                        "__count": 1,
                        "__extra_domain": ['|', ("foo_id", "not any", []), ("foo_id", "any", [("bar_id", "=", False)])],
                        "foo_id.bar_id": False,
                    },
                ],
            )
        for group in result:
            self.assertEqual(group['__count'], RelatedBase.search_count(group['__extra_domain']))

        # Test without sudo + ir_rules
        users_model = self.env['ir.model']._get(RelatedFoo._name)
        self.env['ir.rule'].create({
            'name': "Only The Lone Wanderer allowed",
            'model_id': users_model.id,
            'domain_force': [('id', 'in', foos[1:].ids)],
        })
        RelatedBase = RelatedBase.with_user(self.base_user)

        # warmup ormcache
        RelatedBase.formatted_read_group([], ['foo_id.bar_id'], ['__count'])

        alias_join = f"test_read_group_related_base__foo_id__{self.base_user.id}"
        with self.assertQueries([f"""
            SELECT "{alias_join}"."bar_id",
                   COUNT(*)
            FROM "test_read_group_related_base"
            LEFT JOIN (
                SELECT "test_read_group_related_foo".*
                FROM "test_read_group_related_foo"
                WHERE "test_read_group_related_foo"."id" IN %s
            ) AS "{alias_join}"
                ON (
                    "test_read_group_related_base"."foo_id" = "{alias_join}"."id"
                )
            GROUP BY "{alias_join}"."bar_id"
            ORDER BY "{alias_join}"."bar_id" ASC
        """]):
            # foos[0] not accessible, then foo_id.bar_id result into empty recordset
            result = RelatedBase.formatted_read_group([], ['foo_id.bar_id'], ['__count'])
            self.assertEqual(
                result,
                [
                    {
                        "__count": 1,
                        "__extra_domain": [("foo_id", "any", [("bar_id", "=", bars[0].id)])],
                        "foo_id.bar_id": (bars[0].id, 'bar_a'),
                    },
                    {
                        "__count": 1,
                        "__extra_domain": [("foo_id", "any", [("bar_id", "=", bars[1].id)])],
                        "foo_id.bar_id": (bars[1].id, False),
                    },
                    {
                        "__count": 3,
                        "__extra_domain": ['|', ("foo_id", "not any", []), ("foo_id", "any", [("bar_id", "=", False)])],
                        "foo_id.bar_id": False,
                    },
                ],
            )
        for group in result:
            self.assertEqual(group['__count'], RelatedBase.search_count(group['__extra_domain']))

    def test_groupby_sequence_fnames_char(self):
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

        # Warmup ormcache
        RelatedBase.formatted_read_group([], ['foo_id.bar_id.name'], ['__count'])

        # Same query generated by grouping foo_id.bar_id.name/foo_id.bar_name/foo_id.bar_name_sudo
        query_expected = """
            SELECT "test_read_group_related_base__foo_id__bar_id"."name",
                    COUNT(*)
            FROM "test_read_group_related_base"
            LEFT JOIN "test_read_group_related_foo" AS "test_read_group_related_base__foo_id"
                ON ("test_read_group_related_base"."foo_id" = "test_read_group_related_base__foo_id"."id")
            LEFT JOIN "test_read_group_related_bar" AS "test_read_group_related_base__foo_id__bar_id"
                ON ("test_read_group_related_base__foo_id"."bar_id" = "test_read_group_related_base__foo_id__bar_id"."id")
            GROUP BY "test_read_group_related_base__foo_id__bar_id"."name"
            ORDER BY "test_read_group_related_base__foo_id__bar_id"."name" ASC
        """

        def domain_for_sequence(fname_sequence, value):
            if fname_sequence == 'foo_id.bar_id.name':
                if not value:
                    return [
                        '|',
                        ('foo_id', 'not any', []),
                        ('foo_id', 'any', [
                            '|',
                            ('bar_id', 'not any', []),
                            ('bar_id', 'any', [('name', '=', value)]),
                        ]),
                    ]
                return [('foo_id', 'any', [('bar_id', 'any', [('name', '=', value)])])]
            if fname_sequence == 'foo_id.bar_name_sudo':
                if not value:
                    return [
                        '|',
                        ('foo_id', 'not any', []),
                        ('foo_id', 'any', [('bar_name_sudo', '=', value)]),
                    ]
                return [('foo_id', 'any', [('bar_name_sudo', '=', value)])]
            # foo_id.bar_name
            if not value:
                return [
                        '|',
                        ('foo_id', 'not any', []),
                        ('foo_id', 'any', [('bar_name', '=', value)]),
                    ]
            return [('foo_id', 'any', [('bar_name', '=', value)])]

        for fname_sequence in ['foo_id.bar_id.name', 'foo_id.bar_name_sudo', 'foo_id.bar_name']:
            with self.assertQueries([query_expected]):
                result = RelatedBase.formatted_read_group([], [fname_sequence], ['__count'])
                self.assertEqual(
                    result,
                    [
                        {
                            "__count": 3,
                            "__extra_domain": domain_for_sequence(fname_sequence, "bar_a"),
                            fname_sequence: "bar_a",
                        },
                        {
                            "__count": 2,
                            "__extra_domain": domain_for_sequence(fname_sequence, False),
                            fname_sequence: False,
                        },
                    ],
                )
            for group in result:
                self.assertEqual(group['__count'], RelatedBase.search_count(group['__extra_domain']))

        # Cannot groupby on foo_ids.name because it traverse One2many
        with self.assertRaises(ValueError):
            RelatedBar.formatted_read_group([], ['foo_ids.name'])

        # Test without sudo but without ir_rules
        RelatedBase = RelatedBase.with_user(self.base_user)

        # Warmup ormcache
        RelatedBase.formatted_read_group([], ['foo_id.bar_id.name'], ['__count'])

        # Same query generated by grouping foo_id.bar_id.name/foo_id.bar_name_sudo
        expected_query = """
            SELECT "test_read_group_related_base__foo_id__bar_id"."name",
                    COUNT(*)
            FROM "test_read_group_related_base"
            LEFT JOIN "test_read_group_related_foo" AS "test_read_group_related_base__foo_id"
                ON ("test_read_group_related_base"."foo_id" = "test_read_group_related_base__foo_id"."id")
            LEFT JOIN "test_read_group_related_bar" AS "test_read_group_related_base__foo_id__bar_id"
                ON ("test_read_group_related_base__foo_id"."bar_id" = "test_read_group_related_base__foo_id__bar_id"."id")
            GROUP BY "test_read_group_related_base__foo_id__bar_id"."name"
            ORDER BY "test_read_group_related_base__foo_id__bar_id"."name" ASC
        """
        for fname_sequence in ['foo_id.bar_id.name', 'foo_id.bar_name_sudo']:
            with self.assertQueries([expected_query]):
                result = RelatedBase.formatted_read_group([], [fname_sequence], ['__count'])
                self.assertEqual(
                    result,
                    [
                        {
                            "__count": 3,
                            "__extra_domain": domain_for_sequence(fname_sequence, "bar_a"),
                            fname_sequence: "bar_a",
                        },
                        {
                            "__count": 2,
                            "__extra_domain": domain_for_sequence(fname_sequence, False),
                            fname_sequence: False,
                        },
                    ],
                )
            for group in result:
                self.assertEqual(group['__count'], RelatedBase.search_count(group['__extra_domain']))

        # Doesn't work since bar_name is unsudoed
        with self.assertRaises(ValueError):
            RelatedBase.formatted_read_group([], ['foo_id.bar_name'], ['__count'])

        # Test without sudo + ir_rules
        users_model = self.env['ir.model']._get(RelatedFoo._name)
        self.env['ir.rule'].create({
            'name': "Only The Lone Wanderer allowed",
            'model_id': users_model.id,
            'domain_force': [('id', 'in', foos[1:].ids)],
        })

        # Warmup ormcache
        RelatedBase.formatted_read_group([], ['foo_id.bar_id.name'], ['__count'])

        # Same query generated by grouping foo_id.bar_id.name/foo_id.bar_name_sudo
        alias_join = f"test_read_group_related_base__foo_id__{self.base_user.id}"
        expected_query = f"""
            SELECT "{alias_join}__bar_id"."name",
                   COUNT(*)
            FROM "test_read_group_related_base"
            LEFT JOIN (
                SELECT "test_read_group_related_foo".*
                FROM "test_read_group_related_foo"
                WHERE "test_read_group_related_foo"."id" IN %s
            ) AS "{alias_join}" ON (
                "test_read_group_related_base"."foo_id" = "{alias_join}"."id"
            )
            LEFT JOIN "test_read_group_related_bar" AS "{alias_join}__bar_id" ON (
                "{alias_join}"."bar_id" = "{alias_join}__bar_id"."id"
            )
            GROUP BY "{alias_join}__bar_id"."name"
            ORDER BY "{alias_join}__bar_id"."name" ASC
        """

        for fname_sequence in ['foo_id.bar_id.name', 'foo_id.bar_name_sudo']:
            with self.assertQueries([expected_query]):
                # foos[0] not accessible, then bar_a is only exist via foos[2]
                result = RelatedBase.formatted_read_group([], [fname_sequence], ['__count'])
                self.assertEqual(
                    result,
                    [
                        {
                            "__count": 1,
                            "__extra_domain": domain_for_sequence(fname_sequence, "bar_a"),
                            fname_sequence: "bar_a",
                        },
                        {
                            "__count": 4,
                            "__extra_domain": domain_for_sequence(fname_sequence, False),
                            fname_sequence: False,
                        },
                    ],
                )
            for group in result:
                self.assertEqual(group['__count'], RelatedBase.search_count(group['__extra_domain']))

    def test_groupby_sequence_fnames_date(self):
        RelatedFoo = self.env['test_read_group.related_foo']
        RelatedBase = self.env['test_read_group.related_base']

        foos = RelatedFoo.create([
            {'schedule_datetime': False},
            {'schedule_datetime': '1916-08-18 12:30:00'},
            {'schedule_datetime': '1916-08-18 12:50:00'},
            {'schedule_datetime': '1916-08-19 01:30:00'},
            {'schedule_datetime': '1916-10-18 23:30:00'},
        ])

        RelatedBase.create([
            {'foo_id': foos[0].id},
            {'foo_id': foos[1].id},
            {'foo_id': foos[2].id},
            {'foo_id': foos[3].id},
            {'foo_id': foos[4].id},
            {'foo_id': foos[4].id},
        ])

        # With 'UTC' timezone (the default one)
        RelatedBase = RelatedBase.with_context(tz='UTC')

        result = RelatedBase.formatted_read_group([], ['foo_id.schedule_datetime:day'], ['__count'])
        self.assertEqual(
            result,
            [
                {
                    '__extra_domain': [('foo_id', 'any', [
                        '&',
                        ('schedule_datetime', '>=', '1916-08-18 00:00:00'),
                        ('schedule_datetime', '<', '1916-08-19 00:00:00'),
                    ])],
                    'foo_id.schedule_datetime:day': ('1916-08-18 00:00:00', '18 Aug 1916'),
                    '__count': 2,
                },
                {
                    '__extra_domain': [('foo_id', 'any', [
                        '&',
                        ('schedule_datetime', '>=', '1916-08-19 00:00:00'),
                        ('schedule_datetime', '<', '1916-08-20 00:00:00'),
                    ])],
                    'foo_id.schedule_datetime:day': ('1916-08-19 00:00:00', '19 Aug 1916'),
                    '__count': 1,
                },
                {
                    '__extra_domain': [('foo_id', 'any', [
                        '&',
                        ('schedule_datetime', '>=', '1916-10-18 00:00:00'),
                        ('schedule_datetime', '<', '1916-10-19 00:00:00'),
                    ])],
                    'foo_id.schedule_datetime:day': ('1916-10-18 00:00:00', '18 Oct 1916'),
                    '__count': 2,
                },
                {
                    '__extra_domain': ['|',
                        ('foo_id', 'not any', []),
                        ('foo_id', 'any', [('schedule_datetime', '=', False)]),
                    ],
                    'foo_id.schedule_datetime:day': False,
                    '__count': 1,
                },
            ],
        )
        for group in result:
            self.assertEqual(group['__count'], RelatedBase.search_count(group['__extra_domain']))


class TestFormattedReadGroupMonetary(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # For Monetary Aggregates
        cls.usd = cls.env.ref('base.USD')
        cls.usd.active = True
        cls.eur = cls.env.ref('base.EUR')
        cls.eur.active = True

        cls.MonetaryAggRelated = cls.env['test_read_group.aggregate.monetary.related']
        cls.MonetaryAgg = cls.env['test_read_group.aggregate.monetary']

        cls.related_model_usd = cls.MonetaryAggRelated.create({'stored_currency_id': cls.usd.id})
        cls.related_model_eur = cls.MonetaryAggRelated.create({'stored_currency_id': cls.eur.id})

    def test_monetary_fields_agg_in_fields_get(self):
        field_infos = self.MonetaryAgg.fields_get()

        self.assertEqual(field_infos['total_in_currency_id'].get('aggregator'), 'sum')
        self.assertEqual(field_infos['total_in_related_stored_currency_id'].get('aggregator'), 'sum')
        self.assertFalse(field_infos['total_in_related_non_stored_currency_id'].get('aggregator'), False)
