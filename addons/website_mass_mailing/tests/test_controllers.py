# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
from unittest.mock import patch

import odoo
import odoo.tests


@odoo.tests.common.tagged('post_install', '-at_install')
class TestSnippets(odoo.tests.HttpCase):

    def test_subscribe_no_list(self):
        """Ensure subscription to removed/merged lists result in standalone contacts."""
        email = 'test@test.lan'
        list_id = 12823
        self.assertFalse(self.env['mailing.list'].browse(list_id).exists(), 'Test assumption failed, list is not expected to exist')

        with patch('odoo.addons.google_recaptcha.models.ir_http.Http._verify_request_recaptcha_token', new=lambda self, token: True):
            self.url_open('/website_mass_mailing/subscribe',
                              data=json.dumps({'params': {'list_id': list_id, 'subscription_type': 'email', 'value': email}}).encode(),
                              headers={"Content-Type": "application/json"})

        new_contact = self.env['mailing.contact'].search([('email', '=', email)])
        self.assertTrue(new_contact, 'New contact should be created')
        self.assertFalse(new_contact.list_ids, 'Contact should not be in any list')

        self.assertEqual(len(new_contact.message_ids), 2, 'Should be a creation message and a message saying the contact was created for a non-existing list')
        self.assertIn('This contact subscribed to a removed or merged mailing list', new_contact.message_ids[0].body)

        # subscribe again
        with patch('odoo.addons.google_recaptcha.models.ir_http.Http._verify_request_recaptcha_token', new=lambda self, token: True):
            self.url_open('/website_mass_mailing/subscribe',
                              data=json.dumps({'params': {'list_id': list_id, 'subscription_type': 'email', 'value': email}}).encode(),
                              headers={"Content-Type": "application/json"})

        self.assertEqual(len(new_contact.message_ids), 3, 'Should log attempt to subscribe even if the contact exists')
        self.assertIn('This contact subscribed to a removed or merged mailing list.', new_contact.message_ids[0].body)
