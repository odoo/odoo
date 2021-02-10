# Part of Odoo. See LICENSE file for full copyright and licensing details.
from dateutil.relativedelta import relativedelta

from odoo.tests.common import TransactionCase
from odoo import fields
from odoo.fields import Command


class TestAdhocFields(TransactionCase):

    def setUp(self):
        super(TestAdhocFields, self).setUp()
        self.model = self.env['test_read_group.adhoc']

    def test_computed(self):
        today = fields.Date.today()
        yesterday = today - relativedelta(days=1)
        tomorrow = today + relativedelta(days=1)

        self.model.create({'deadline': yesterday})
        self.model.create({'deadline': today})
        self.model.create({'deadline': today})
        self.model.create({'deadline': tomorrow})
        self.model.create({'deadline': tomorrow})
        self.model.create({'deadline': tomorrow})

        res = self.model.read_group([], ['state'], ['state'], orderby='state')
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

    def test_related(self):
        self.model.create({
            'partner_id': self.env['res.partner'].create({
                'name': 'p1',
                'city': 'Ufa'
            }).id
        })
        self.model.create({
            'partner_id': self.env['res.partner'].create({
                'name': 'p2',
                'city': 'Ufa'
            }).id
        })
        self.model.create({
            'partner_id': self.env['res.partner'].create({
                'name': 'p3',
                'city': 'Moscow'
            }).id
        })
        res = self.model.read_group([], ['partner_id.city'], ['partner_id.city'], orderby='partner_id.city')
        self.assertEqual(res, [
            {'__domain': [('partner_id.city', '=', 'Moscow')],
             'partner_id.city': 'Moscow',
             'partner_id.city_count': 1},
            {'__domain': [('partner_id.city', '=', 'Ufa')],
             'partner_id.city': 'Ufa',
             'partner_id.city_count': 2}
        ])
        res = self.model.read_group([], ['partner_id.create_date'], ['partner_id.create_date'])
        self.assertEqual(res[0]['partner_id.create_date_count'], 3)
        res = self.model.read_group([], ['partner_id.create_date'], ['partner_id.create_date:year'])
        self.assertEqual(res[0]['partner_id.create_date_count'], 3)

    def test_one2many(self):
        self.model.create({
            'line_ids': [
                Command.create({
                    'packages_count': 1,
                    'qty': 100,
                }),
                Command.create({
                    'packages_count': 2,
                    'qty': 50,
                }),
                Command.create({
                    'packages_count': 4,
                    'qty': 25,
                }),
            ]

        })
        self.model.create({
            'line_ids': [
                Command.create({
                    'packages_count': 1,
                    'qty': 300,
                }),
                Command.create({
                    'packages_count': 10,
                    'qty': 0,
                }),
            ]

        })

        res = self.model.read_group([], ['total'], ['total'])
        self.assertEqual(res, [
            {'__domain': [('total', '=', 300.0)],
             'total': 300.0,
             'total_count': 2}
        ])
