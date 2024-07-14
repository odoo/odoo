# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
import json
from unittest.mock import patch
from hashlib import sha256

from odoo import Command
from odoo.tests import tagged
from odoo.exceptions import ValidationError

from odoo.addons.sign.tests.test_sign_controllers import TestSignControllerCommon

@tagged('post_install', '-at_install')
class SignItsmeCommon(TestSignControllerCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        itsme_auth_role = cls.env['sign.item.role'].create({
            'name': 'Itsme Role',
            'auth_method': 'itsme'
        })

        cls.template_itsme = cls.env['sign.template'].create({
            'name': 'template_itsme_test',
            'attachment_id': cls.attachment.id,
        })
        cls.env['sign.item'].create([
            {
                'type_id': cls.env.ref('sign.sign_item_type_text').id,
                'required': True,
                'responsible_id': itsme_auth_role.id,
                'page': 1,
                'posX': 0.273,
                'posY': 0.158,
                'template_id': cls.template_itsme.id,
                'width': 0.150,
                'height': 0.015,
            }
        ])

        cls.sign_request_itsme = cls.env['sign.request'].create({
            'template_id': cls.template_itsme.id,
            'reference': cls.template_itsme.display_name,
            'request_item_ids': [Command.create({
                'partner_id': cls.partner_1.id,
                'role_id': itsme_auth_role.id,
            })],
        })

    def create_sign_request_1_role_itsme_auth(self, customer, cc_partners):
        role = self.env.ref('sign.sign_item_role_customer')
        role.auth_method = 'itsme'
        return self.create_sign_request_1_role(customer, cc_partners)

    def test_sign_itsme_with_token_is_successful(self):
        sign_request_item = self.sign_request_itsme.request_item_ids[0]
        self.assertEqual(sign_request_item.state, 'sent')
        vals = self.create_sign_values(self.sign_request_itsme.template_id.sign_item_ids, sign_request_item.role_id.id)
        sign_request_item._sign(vals, validation_required=True)
        self.assertEqual(sign_request_item.state, 'sent')
        sign_request_item.write({
            'itsme_validation_hash': 'abc',
            'itsme_signer_name': self.partner_1.name
        })
        sign_request_item._post_fill_request_item()
        self.assertEqual(sign_request_item.state, 'completed')
        self.assertEqual(self.sign_request_itsme.state, 'signed')

    def test_sign_itsme_without_token_raises_error(self):
        sign_request_item = self.sign_request_itsme.request_item_ids[0]
        self.assertEqual(sign_request_item.state, 'sent')
        vals = self.create_sign_values(self.sign_request_itsme.template_id.sign_item_ids, sign_request_item.role_id.id)
        sign_request_item._sign(vals, validation_required=True)
        self.assertEqual(sign_request_item.state, 'sent')
        with self.assertRaises(ValidationError):
            sign_request_item._post_fill_request_item()
        self.assertEqual(sign_request_item.state, 'sent')
        self.assertEqual(self.sign_request_itsme.state, 'sent')

    def test_sign_itsme_API(self):
        sign_request_item = self.sign_request_itsme.request_item_ids[0]
        sign_vals = self.create_sign_values(self.sign_request_itsme.template_id.sign_item_ids, sign_request_item.role_id.id)
        with patch('odoo.addons.iap.models.iap_account.IapAccount.get_credits', lambda self, x: 10):
            with patch('odoo.addons.sign_itsme.controllers.main.jsonrpc', lambda url, params: {'success': True, 'url': url}):
                response = self._json_url_open(
                    '/sign/sign/%d/%s' % (self.sign_request_itsme.id, sign_request_item.access_token),
                    data={'signature': sign_vals},
                    headers={"Referer": 'abc'}
                ).json()['result']

                self.assertTrue(response.get('success'))
                self.assertTrue(len(sign_request_item.sign_item_value_ids), 1)
                self.assertTrue(sign_request_item.state, 'sent')

        vals = {
            "name": "John Doe",
            "birthdate": "1999-01-21"
        }

        computed_hash_from_values = sha256(json.dumps(vals, sort_keys=True, ensure_ascii=True, indent=None).encode('utf-8')).hexdigest()
        response = self._json_url_open(
            '/itsme_sign/itsme_successful',
            data={
                "itsme_state": "%s.%s" % (self.sign_request_itsme.id, sign_request_item.access_token),
                **vals,
                "itsme_hash": computed_hash_from_values
            }
        ).json()['result']

        self.assertTrue(response.get("success"))
        self.assertEqual(sign_request_item.state, 'completed')
        self.assertEqual(self.sign_request_itsme.state, 'signed')
        self.assertEqual(sign_request_item.itsme_validation_hash, computed_hash_from_values)
        self.assertEqual(sign_request_item.itsme_signer_name, vals['name'])
        self.assertEqual(sign_request_item.itsme_signer_birthdate, datetime.date(1999, 1, 21))

    def test_wrong_hash(self):
        sign_request_item = self.sign_request_itsme.request_item_ids[0]
        vals = self.create_sign_values(self.sign_request_itsme.template_id.sign_item_ids, sign_request_item.role_id.id)
        sign_request_item._sign(vals, validation_required=True)

        vals = {
            "name": "John Doe",
            "birthdate": "1999-01-21"
        }

        computed_hash_from_values = sha256(json.dumps(
            {
                "name": "John Deer",
                "birthdate": "1999-01-21"
            },
            sort_keys=True, ensure_ascii=True, indent=None).encode('utf-8')
        ).hexdigest()

        response = self._json_url_open(
            '/itsme_sign/itsme_successful',
            data={
                "itsme_state": "%s.%s" % (self.sign_request_itsme.id, sign_request_item.access_token),
                **vals,
                "itsme_hash": computed_hash_from_values
            }
        ).json()['result']

        self.assertFalse(response.get("success"))
        self.assertEqual(sign_request_item.state, 'sent')
        self.assertEqual(self.sign_request_itsme.state, 'sent')
        self.assertFalse(sign_request_item.itsme_validation_hash)
        self.assertFalse(sign_request_item.itsme_signer_name)
        self.assertFalse(sign_request_item.itsme_signer_birthdate)

    def test_sign_itsme_request_requires_auth_when_credits_are_available(self):
        sign_request = self.create_sign_request_1_role_itsme_auth(self.partner_1, self.env['res.partner'])
        sign_request_item = sign_request.request_item_ids[0]

        self.assertFalse(sign_request_item.signed_without_extra_auth)
        self.assertEqual(sign_request_item.role_id.auth_method, 'itsme')

        sign_vals = self.create_sign_values(sign_request.template_id.sign_item_ids, sign_request_item.role_id.id)
        with patch('odoo.addons.sign_itsme.controllers.main.jsonrpc', lambda url, params: {'success': True, 'url': url}):
            with patch('odoo.addons.iap.models.iap_account.IapAccount.get_credits', lambda self, x: 10):
                response = self._json_url_open(
                    '/sign/sign/%d/%s' % (sign_request.id, sign_request_item.access_token),
                    data={'signature': sign_vals},
                    headers={"Referer": 'abc'}
                ).json()['result']

                self.assertTrue(response.get('success'))
                self.assertTrue(sign_request_item.state, 'sent')
                self.assertFalse(sign_request_item.signed_without_extra_auth)

    def test_sign_itsme_request_allows_no_auth_when_credits_are_not_available(self):
        sign_request = self.create_sign_request_1_role_itsme_auth(self.partner_1, self.env['res.partner'])
        sign_request_item = sign_request.request_item_ids[0]

        self.assertFalse(sign_request_item.signed_without_extra_auth)
        self.assertEqual(sign_request_item.role_id.auth_method, 'itsme')

        sign_vals = self.create_sign_values(sign_request.template_id.sign_item_ids, sign_request_item.role_id.id)
        with patch('odoo.addons.iap.models.iap_account.IapAccount.get_credits', lambda self, service: 0):
            response = self._json_url_open(
                '/sign/sign/%d/%s' % (sign_request.id, sign_request_item.access_token),
                data={'signature': sign_vals},
                headers={"Referer": 'abc'}
            ).json()['result']

            self.assertTrue(response.get('success'))
            self.assertTrue(sign_request_item.state, 'completed')
            self.assertTrue(sign_request.state, 'done')
            self.assertTrue(sign_request_item.signed_without_extra_auth)
