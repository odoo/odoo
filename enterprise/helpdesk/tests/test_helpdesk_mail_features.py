# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.helpdesk.tests.common import HelpdeskCommon
from odoo.tests import users
from odoo.tools import formataddr


class TestHelpdeskMailFeatures(HelpdeskCommon):

    @users('hm')
    def test_suggested_recipients_auto_creation(self):
        """Check default creates value for auto creation of recipient (customer)."""
        partner_name = 'Jérémy Dawson'
        partner_phone = '+33 1990b01010'
        email = 'jdawson@example.com'
        formatted_email = formataddr((partner_name, email))
        ticket = self.env['helpdesk.ticket'].create({
            'name': 'How do I renew my subscription at the discounted price?',
            'partner_phone': partner_phone,
            'partner_name': partner_name,
        })
        ticket.partner_email = formatted_email
        data = ticket._message_get_suggested_recipients()[0]
        create_vals = data.get('create_values')
        self.assertFalse(data.get('persona_id'))
        self.assertEqual(data.get('email'), formatted_email)
        self.assertEqual(data.get('lang'), None)
        self.assertEqual(data.get('reason'), 'Customer Email')
        self.assertEqual(create_vals, ticket._get_customer_information().get(email, {}))
        self.assertEqual(create_vals['name'], partner_name)
        self.assertEqual(create_vals['phone'], partner_phone)

        # check that the creation of the contact won't fail due to bad values
        _partner = self.env['res.partner'].create(create_vals)
