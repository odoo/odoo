# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo import Command
from odoo.addons.event_booth_sale.tests.common import TestEventBoothSaleCommon
from odoo.fields import Datetime as FieldsDatetime
from odoo.tests.common import users, Form


class TestEventData(TestEventBoothSaleCommon):

    @users('user_eventmanager')
    def test_event_configuration_booths_from_type(self):
        """ Test data computation (related to booths) of event coming from its event.type template. """
        # setup test records
        event_type_nobooth = self.env['event.type'].create({
            'name': 'No booth',
            'use_booth': False,
        })
        event_type_wbooths = self.env['event.type'].create({
            'name': 'Using booths',
            'use_booth': True,
            'event_type_booth_ids': [
                Command.clear(),
                Command.create({
                    'name': 'Standard Booth',
                    'booth_category_id': self.event_booth_category_1.id,
                }),
                Command.create({
                    'name': 'Premium Booth',
                    'booth_category_id': self.event_booth_category_2.id,
                })
            ]
        })

        # no booth by default as no booths on type
        event = self.env['event.event'].create({
            'name': 'Event',
            'date_begin': FieldsDatetime.to_string(datetime.today() + timedelta(days=1)),
            'date_end': FieldsDatetime.to_string(datetime.today() + timedelta(days=15)),
            'event_type_id': event_type_nobooth.id
        })
        self.assertEqual(event.event_booth_ids, self.env['event.booth'])

        # manually create booths: ok
        event.write({
            'event_booth_ids': [
                Command.create({
                    'name': 'Custom Standard Booth 1',
                    'booth_category_id': self.event_booth_category_1.id,
                }),
                Command.create({
                    'name': 'Custom Standard Booth 2',
                    'booth_category_id': self.event_booth_category_1.id,
                })
            ]
        })
        self.assertEqual(event.event_booth_count, 2)
        self.assertEqual(event.event_booth_count_available, 2)
        self.assertEqual(event.event_booth_ids.product_id, self.event_booth_product)

        # one booth is sold
        event.event_booth_ids[1].write({'partner_id': self.event_customer.id})
        self.assertEqual(event.event_booth_count, 2)
        self.assertEqual(event.event_booth_count_available, 1)

        # change event type to one using booths: reset to type booths as no reserved booth
        event_form = Form(event)
        event_form.event_type_id = event_type_wbooths
        self.assertEqual(event_form.event_booth_count, 3)
        self.assertEqual(
            set(r['name'] for r in event_form.event_booth_ids._records),
            set(('Custom Standard Booth 2', 'Standard Booth', 'Premium Booth')),
            'Should keep booths with reservation, remove unused ones and add type ones'
        )
        event_form.save()
        self.assertEqual(event.event_booth_count_available, 2)
