# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo.tests.common import SingleTransactionCase


class TestCalendarSms(SingleTransactionCase):

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

    def test_attendees_with_number(self):
        """Test if only partners with sanitized number are returned."""
        attendees = self.env['calendar.event'].create({
            'name': "Boostrap vs Foundation",
            'start': datetime(2022, 1, 1, 11, 11),
            'stop': datetime(2022, 2, 2, 22, 22),
            'partner_ids': [(6, 0, [self.partner_phone.id, self.partner_no_phone.id])],
        })._sms_get_default_partners()
        self.assertEqual(len(attendees), 1, "There should be only one partner retrieved")
