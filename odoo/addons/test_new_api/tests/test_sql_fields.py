# Part of Odoo. See LICENSE file for full copyright and licensing details.
from dateutil.relativedelta import relativedelta

from odoo.tests.common import TransactionCase
from odoo import fields
from odoo.fields import Command


class TestSqlFields(TransactionCase):

    def setUp(self):
        super(TestSqlFields, self).setUp()
        self.model = self.env['test_new_api.sql']

    def test_selection(self):
        today = fields.Date.today()
        yesterday = today - relativedelta(days=1)
        tomorrow = today + relativedelta(days=1)

        self.model.create({'deadline': yesterday})
        self.model.create({'deadline': today})
        self.model.create({'deadline': today})
        self.model.create({'deadline': tomorrow})
        self.model.create({'deadline': tomorrow})
        self.model.create({'deadline': tomorrow})

        self.assertEqual(1, self.model.search_count([('state', '=', 'overdue')]))
        self.assertEqual(2, self.model.search_count([('state', '=', 'today')]))
        self.assertEqual(3, self.model.search_count([('state', '=', 'planned')]))

        res = self.model.read_group([], ['state'], ['state'], orderby="state")
        self.assertEqual(res, [
            {'__domain': [('state', '=', 'overdue')],
             'state': 'overdue',
             'state_count': 1},
            {'__domain': [('state', '=', 'planned')],
             'state': 'planned',
             'state_count': 3},
            {'__domain': [('state', '=', 'today')],
             'state': 'today',
             'state_count': 2},
        ])

    def test_join(self):
        partner = self.env['res.partner'].create({'name': 'xxx'})
        record = self.model.create({"partner_id": partner.id})
        self.assertEqual('xxx', record.partner_name)

    def test_one2many(self):
        r1 = self.model.create({
            "line_ids": [
                Command.create({
                    "qty": 1,
                    "price": 100,
                }),
                Command.create({
                    "qty": 2,
                    "price": 50,
                }),
                Command.create({
                    "qty": 4,
                    "price": 25,
                }),
            ]

        })
        self.assertEqual(300, r1.total)

        r2 = self.model.create({
            "line_ids": [
                Command.create({
                    "qty": 1,
                    "price": 300,
                }),
                Command.create({
                    "qty": 10,
                    "price": 0,
                }),
            ]

        })
        self.assertEqual(300, r2.total)

        res = self.model.read_group([], ['total'], ['total'])
        self.assertEqual([
            {'__domain': [('total', '=', 300.0)],
             'total': 300.0,
             'total_count': 2
            }], res)
