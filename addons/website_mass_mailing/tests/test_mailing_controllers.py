# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo.tests.common import HttpCase, tagged


@tagged('-at_install', 'post_install')
class TestMassMailingSubscribeController(HttpCase):

    def _subscribe(self, mailing_list):
        payload = {'params': {
            'list_id': mailing_list.id,
            'value': 'joe@example.com',
            'subscription_type': 'email',
        }}
        response = self.url_open(
            '/website_mass_mailing/subscribe',
            data=json.dumps(payload),
            headers={'Content-Type': 'application/json'},
        )
        return response.json().get('result', {'toast_type': 'error'})

    def test_private_list_requires_internal_user(self):
        private_list = self.env['mailing.list'].create({'name': 'Private', 'is_public': False})

        self._subscribe(private_list)
        self.assertFalse(private_list.contact_ids)

        self.authenticate('admin', 'admin')
        self.assertEqual(self._subscribe(private_list)['toast_type'], 'success')
        self.assertTrue(private_list.contact_ids)

    def test_public_list_accepts_public_user(self):
        public_list = self.env['mailing.list'].create({'name': 'Public', 'is_public': True})
        self.assertEqual(self._subscribe(public_list)['toast_type'], 'success')
