# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo.addons.event_booth.tests.common import TestEventBoothCommon
from odoo.fields import Datetime as FieldsDatetime
from odoo.tests.common import users


class TestEventData(TestEventBoothCommon):

    @users('user_eventmanager')
    def test_event_booth_contact(self):
        """ Test contact details computation """
        customer = self.env['res.partner'].browse(self.event_customer.ids)
        category = self.env['event.booth.category'].browse(self.event_booth_category_1.ids)
        self.assertTrue(all(
            bool(customer[fname])
            for fname in ['name', 'email', 'country_id', 'phone']
            )
        )
        customer_email = customer.email

        event = self.env['event.event'].create({
            'name': 'Event',
            'date_begin': FieldsDatetime.to_string(datetime.today() + timedelta(days=1)),
            'date_end': FieldsDatetime.to_string(datetime.today() + timedelta(days=15)),
            'event_type_id': False,
        })
        self.assertEqual(event.event_booth_ids, self.env['event.booth'])

        booth = self.env['event.booth'].create({
            'name': 'Test Booth',
            'booth_category_id': category.id,
            'event_id': event.id,
            'partner_id': customer.id,
        })
        self.assertEqual(booth.contact_name, customer.name)
        self.assertEqual(booth.contact_email, customer_email)
        self.assertEqual(booth.contact_phone, customer.phone)
        self.assertFalse(booth.contact_mobile, 'Data has no mobile')

        booth.write({
            'contact_email': '"New Emails" <new.email@test.example.com',
            'contact_phone': False,
        })
        self.assertEqual(booth.contact_email, '"New Emails" <new.email@test.example.com')
        self.assertEqual(booth.contact_phone, False)
        self.assertEqual(customer.email, customer_email, 'No sync from booth to partner')

        # partial update of contact fields: we may end up with mixed contact information, is it a good idea ?
        booth.write({'partner_id': self.event_customer2.id})
        self.assertEqual(booth.contact_name, customer.name)
        self.assertEqual(booth.contact_email, '"New Emails" <new.email@test.example.com')
        self.assertEqual(booth.contact_phone, self.event_customer2.phone)
