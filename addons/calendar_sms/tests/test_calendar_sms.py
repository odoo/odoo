# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta
from odoo import fields
from odoo.addons.sms.tests.common import SMSCase
from odoo.tests.common import TransactionCase


class TestCalendarSms(TransactionCase, SMSCase):

    @classmethod
    def setUpClass(cls):
        super(TestCalendarSms, cls).setUpClass()

        now = fields.datetime.now()

        cls.partner_phone = cls.env['res.partner'].create({
            'name': 'Partner With Phone Number',
            'phone': '0477777777',
            'country_id': cls.env.ref('base.be').id,
        })

        cls.partner_phone_2 = cls.env['res.partner'].create({
            'name': 'Partner With Phone Number',
            'phone': '0488888888',
            'country_id': cls.env.ref('base.be').id,
        })

        cls.partner_phone_3 = cls.env['res.partner'].create({
            'name': 'Partner With Phone Number',
            'phone': '0499999999',
            'country_id': cls.env.ref('base.be').id,
        })

        cls.partner_no_phone = cls.env['res.partner'].create({
            'name': 'Partner With No Phone Number',
            'country_id': cls.env.ref('base.be').id,
        })

        cls.alarm_1h = cls.env['calendar.alarm'].create({
            'name': 'Reminder 1 Hour',
            'duration': 1,
            'interval': 'hours',
            'alarm_type': 'sms',
        })
        cls.alarm_24h = cls.env['calendar.alarm'].create({
            'name': 'Reminder 24 Hours',
            'duration': 24,
            'interval': 'hours',
            'alarm_type': 'sms',
        })

        cls.event_1h = cls.env['calendar.event'].create({
            'name': 'Event in 1h',
            'start': now + timedelta(hours=1),
            'stop': now + timedelta(hours=2),
            'alarm_ids': [(4, cls.alarm_1h.id), (4, cls.alarm_24h.id)],
            'attendee_ids': [(0, 0, {'partner_id': cls.partner_phone.id})],
        })

        cls.event_1h_dup = cls.env['calendar.event'].create({
            'name': 'Event in 1h',
            'start': now + timedelta(hours=1),
            'stop': now + timedelta(hours=2),
            'alarm_ids': [(4, cls.alarm_1h.id), (4, cls.alarm_24h.id)],
            'attendee_ids': [(0, 0, {'partner_id': cls.partner_phone_3.id})],
        })

        cls.event_24h = cls.env['calendar.event'].create({
            'name': 'Event in 24h',
            'start': now + timedelta(hours=24),
            'stop': now + timedelta(hours=25),
            'alarm_ids': [(4, cls.alarm_1h.id), (4, cls.alarm_24h.id)],
            'attendee_ids': [(0, 0, {'partner_id': cls.partner_phone_2.id})],
        })

        cls.sms_template_1h = cls.env['sms.template'].create({
            'name': 'Calendar Alarm SMS Template',
            'body': 'Reminder: Your event is starting in 1 hour!',
            'model_id': cls.env['ir.model']._get('calendar.event').id,
        })

        cls.alarm_1h.sms_template_id = cls.sms_template_1h.id

        cls.sms_template_24h = cls.env['sms.template'].create({
            'name': 'Calendar Alarm SMS Template',
            'body': 'Reminder: Your event is starting in 24 hour!',
            'model_id': cls.env['ir.model']._get('calendar.event').id,
        })
        cls.alarm_24h.sms_template_id = cls.sms_template_24h.id

    def test_attendees_with_number(self):
        """Test if only partners with sanitized number are returned."""
        attendees = self.env['calendar.event'].create({
            'name': "Boostrap vs Foundation",
            'start': datetime(2022, 1, 1, 11, 11),
            'stop': datetime(2022, 2, 2, 22, 22),
            'partner_ids': [(6, 0, [self.partner_phone.id, self.partner_no_phone.id])],
        })._sms_get_default_partners()
        self.assertEqual(len(attendees), 1, "There should be only one partner retrieved")

    def test_send_reminder_match_both_events(self):
        """
        Test that only the necessary SMS messages are sent,
         with each SMS template correctly matching its corresponding alarm duration and the event.
        """
        with self.mockSMSGateway():
            lastcall = fields.Datetime.now() - timedelta(hours=1)
            self.env['calendar.alarm_manager'].with_context(lastcall=lastcall)._send_reminder()

        self.assertEqual(len(self._sms), 3)
        self.assertSMS(self.partner_phone, self.partner_phone.phone_sanitized, 'sent',
                        content=self.sms_template_1h.body)
        self.assertSMS(self.partner_phone_2, self.partner_phone_2.phone_sanitized, 'sent',
                        content=self.sms_template_24h.body)
