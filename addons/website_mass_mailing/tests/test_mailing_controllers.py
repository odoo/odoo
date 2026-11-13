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

    def _is_subscriber(self, mailing_list):
        payload = {'params': {
            'list_id': mailing_list.id,
            'subscription_type': 'email',
        }}
        response = self.url_open(
            '/website_mass_mailing/is_subscriber',
            data=json.dumps(payload),
            headers={'Content-Type': 'application/json'},
        )
        return response.json()['result']

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

    def test_is_subscriber_hidden_list_can_subscribe(self):
        hidden_list = self.env['mailing.list'].create({'name': 'Internal Mailing List', 'is_public': False})

        self.assertFalse(self._is_subscriber(hidden_list)['can_subscribe'])
        self.authenticate('admin', 'admin')
        self.assertTrue(self._is_subscriber(hidden_list)['can_subscribe'])
