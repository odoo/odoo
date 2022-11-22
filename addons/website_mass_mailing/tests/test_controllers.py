# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests


@odoo.tests.common.tagged('post_install', '-at_install')
class TestSnippets(odoo.tests.HttpCase):

    def test_subscribe_no_list(self):
        """Ensure subscription to removed/merged lists result in standalone contacts."""
        email_formatted = '"Ea-Nasir, Dilmun Goods" eanasir@urcopper.example.com'
        email = "eanasir@urcopper.example.com"

        new_mailing_list = self.env['mailing.list'].create({'name': 'test_subscribe_no_list'})
        list_id = new_mailing_list.id
        new_mailing_list.unlink()

        self.assertFalse(self.env['mailing.list'].browse(list_id).exists(), 'Test assumption failed, list is not expected to exist')

        self.make_jsonrpc_request(
            '/website_mass_mailing/subscribe',
            {'list_id': list_id, 'subscription_type': 'email', 'value': email_formatted},
        )

        new_contact = self.env['mailing.contact'].search([('email', '=', email)])
        self.assertTrue(new_contact, 'New contact should be created')
        self.assertFalse(new_contact.list_ids, 'Contact should not be in any list')

        # subscribe again
        self.make_jsonrpc_request(
            '/website_mass_mailing/subscribe',
            {'list_id': list_id, 'subscription_type': 'email', 'value': email_formatted},
        )

        self.assertFalse(new_contact.list_ids, 'Contact should not be in any list')
