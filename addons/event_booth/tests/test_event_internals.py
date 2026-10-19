# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo import Command
from odoo.addons.event_booth.tests.common import TestEventBoothCommon
from odoo.fields import Datetime as FieldsDatetime
from odoo.tests import Form, users, tagged
from odoo.tools import mute_logger


@tagged('post_install', '-at_install')
class TestEventData(TestEventBoothCommon):

    @mute_logger('odoo.models.unlink')
    @users('user_eventmanager')
    def test_event_configuration_booths_from_type(self):
        """ Test data computation (related to booths) of event coming from its event.type template. """
        # setup test records
        event_type_nobooth = self.env['event.type'].create({
            'name': 'No booth',
        })
        event_type_wbooths = self.env['event.type'].create({
            'name': 'Using booths',
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
        self.assertEqual(event.event_booth_category_ids, self.event_booth_category_1)
        self.assertEqual(event.event_booth_ids[1].message_partner_ids, self.env['res.partner'])

        # updating partner is independent from availability
        event.event_booth_ids[1].write({'partner_id': self.event_customer.id})
        self.assertEqual(event.event_booth_count, 2)
        self.assertEqual(event.event_booth_count_available, 2)
        self.assertEqual(event.event_booth_ids[1].message_partner_ids, self.env['res.partner'])

        # one booth is sold
        event.event_booth_ids[1].write({'state': 'unavailable'})
        self.assertEqual(event.event_booth_count, 2)
        self.assertEqual(event.event_booth_count_available, 1)

        # partner is reset: booth still unavailable but follower removed
        event.event_booth_ids[1].write({'partner_id': False})
        self.assertEqual(event.event_booth_count, 2)
        self.assertEqual(event.event_booth_count_available, 1)
        self.assertEqual(event.event_booth_ids[1].message_partner_ids, self.env['res.partner'])

        # change event type to one using booths: include event type booths and keep reserved booths
        with Form(event) as event_form:
            event_form.event_type_id = event_type_wbooths
        self.assertEqual(event.event_booth_count, 3)
        self.assertEqual(
            set(r['name'] for r in event.event_booth_ids),
            set(('Custom Standard Booth 2', 'Standard Booth', 'Premium Booth')),
            'Should keep booths with reservation, remove unused ones and add type ones'
        )
        self.assertEqual(event.event_booth_count_available, 2)
        self.assertEqual(event.event_booth_category_ids, self.event_booth_category_1 + self.event_booth_category_2)
