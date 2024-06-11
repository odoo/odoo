# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo.addons.sms.tests.common import SMSCommon
from odoo.tests import tagged


@tagged('sms')
class TestCalendarSms(SMSCommon):

    @classmethod
    def setUpClass(cls):
        super(TestCalendarSms, cls).setUpClass()

        cls.partner_phone = cls.env['res.partner'].create({
            'name': 'Partner With Phone Number',
            'phone': '0477777777',
            'country_id': cls.env.ref('base.be').id,
        })
        cls.partner_no_phone = cls.env['res.partner'].create({
            'name': 'Partner With No Phone Number',
            'country_id': cls.env.ref('base.be').id,
        })
        cls.event = cls.env['calendar.event'].create({
            'alarm_ids': [(0, 0, {
                'alarm_type': 'sms',
                'name': 'SMS Reminder',
            })],
            'name': "Boostrap vs Foundation",
            'partner_ids': [(6, 0, [cls.partner_phone.id, cls.partner_no_phone.id])],
            'start': datetime(2022, 1, 1, 11, 11),
            'stop': datetime(2022, 2, 2, 22, 22),
        })

    def test_attendees_with_number(self):
        """Test if only partners with sanitized number are returned."""
        with self.mockSMSGateway():
            self.event._do_sms_reminder(self.event.alarm_ids)
        self.assertEqual(len(self._sms), 1, "There should be only one partner retrieved")
