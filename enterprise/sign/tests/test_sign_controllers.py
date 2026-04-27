# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json
from unittest.mock import patch
from freezegun import freeze_time

from odoo.http import Request
from .sign_request_common import SignRequestCommon
from odoo.addons.base.tests.common import HttpCaseWithUserDemo
from odoo.addons.sign.controllers.main import Sign
from odoo.exceptions import AccessError, ValidationError
from odoo.addons.website.tools import MockRequest
from odoo.tests import tagged
from odoo.tools import formataddr

class TestSignControllerCommon(SignRequestCommon, HttpCaseWithUserDemo):
    def setUp(self):
        super().setUp()
        self.SignController = Sign()

    def _json_url_open(self, url, data, **kwargs):
        data = {
            "id": 0,
            "jsonrpc": "2.0",
            "method": "call",
            "params": data,
        }
        headers = {
            "Content-Type": "application/json",
            **kwargs.get('headers', {})
        }
        return self.url_open(url, data=json.dumps(data).encode(), headers=headers)


@tagged('post_install', '-at_install')
class TestSignController(TestSignControllerCommon):
    # test float auto_field display
    def test_sign_controller_float(self):
        sign_request = self.create_sign_request_no_item(signer=self.partner_1, cc_partners=self.partner_4)
        text_type = self.env['sign.item.type'].search([('name', '=', 'Text')])
        # the partner_latitude expects 7 zeros of decimal precision
        text_type.auto_field = 'partner_latitude'
        token_a = self.env["sign.request.item"].search([('sign_request_id', '=', sign_request.id)]).access_token
        with MockRequest(sign_request.env):
            values = self.SignController.get_document_qweb_context(sign_request.id, token=token_a)
            sign_type = list(filter(lambda sign_type: sign_type["name"] == "Text", values["sign_item_types"]))[0]
            latitude = sign_type["auto_value"]
            self.assertEqual(latitude, 0)

    # test auto_field with wrong partner field
    def test_sign_controller_dummy_fields(self):
        text_type = self.env['sign.item.type'].search([('name', '=', 'Text')])
        # we set a dummy field that raises an error
        with self.assertRaises(ValidationError):
            text_type.auto_field = 'this_is_not_a_partner_field'

        # we set a field the demo user does not have access and must not be able to set as auto_field
        self.patch(type(self.env['res.partner']).function, 'groups', 'base.group_system')
        with self.assertRaises(AccessError):
            text_type.with_user(self.user_demo).auto_field = 'function'

    # test auto_field with multiple sub steps
    def test_sign_controller_multi_step_auto_field(self):
        self.partner_1.company_id = self.env.ref('base.main_company')
        self.partner_1.company_id.country_id = self.env.ref('base.be').id
        sign_request = self.create_sign_request_no_item(signer=self.partner_1, cc_partners=self.partner_4)
        text_type = self.env['sign.item.type'].search([('name', '=', 'Text')])
        text_type.auto_field = 'company_id.country_id.name'
        token_a = self.env["sign.request.item"].search([('sign_request_id', '=', sign_request.id)]).access_token
        with MockRequest(sign_request.env):
            values = self.SignController.get_document_qweb_context(sign_request.id, token=token_a)
            sign_type = list(filter(lambda sign_type: sign_type["name"] == "Text", values["sign_item_types"]))[0]
            country = sign_type["auto_value"]
            self.assertEqual(country, "Belgium")

    def test_sign_request_requires_auth_when_credits_are_available(self):
        sign_request = self.create_sign_request_1_role_sms_auth(self.partner_1, self.env['res.partner'])
        sign_request_item = sign_request.request_item_ids[0]

        self.assertFalse(sign_request_item.signed_without_extra_auth)
        self.assertEqual(sign_request_item.role_id.auth_method, 'sms')

        sign_vals = self.create_sign_values(sign_request.template_id.sign_item_ids, sign_request_item.role_id.id)
        with patch('odoo.addons.iap.models.iap_account.IapAccount.get_credits', lambda self, x: 10):
            response = self._json_url_open(
                '/sign/sign/%d/%s' % (sign_request.id, sign_request_item.access_token),
                data={'signature': sign_vals}
            ).json()['result']

            self.assertFalse(response.get('success'))
            self.assertTrue(sign_request_item.state, 'sent')
            self.assertFalse(sign_request_item.signed_without_extra_auth)

    def test_sign_request_allows_no_auth_when_credits_are_not_available(self):
        sign_request = self.create_sign_request_1_role_sms_auth(self.partner_1, self.env['res.partner'])
        sign_request_item = sign_request.request_item_ids[0]

        self.assertFalse(sign_request_item.signed_without_extra_auth)
        self.assertEqual(sign_request_item.role_id.auth_method, 'sms')

        sign_vals = self.create_sign_values(sign_request.template_id.sign_item_ids, sign_request_item.role_id.id)
        with patch('odoo.addons.iap.models.iap_account.IapAccount.get_credits', lambda self, x: 0):
            response = self._json_url_open(
                '/sign/sign/%d/%s' % (sign_request.id, sign_request_item.access_token),
                data={'signature': sign_vals}
            ).json()['result']

            self.assertTrue(response.get('success'))
            self.assertTrue(sign_request_item.state, 'completed')
            self.assertTrue(sign_request.state, 'done')
            self.assertTrue(sign_request_item.signed_without_extra_auth)

    def test_sign_from_mail_no_expiry_params(self):
        sign_request = self.create_sign_request_1_role(self.partner_1, self.env['res.partner'])
        url = '/sign/document/mail/%s/%s' % (sign_request.id, sign_request.request_item_ids[0].access_token)
        response = self.url_open(url)
        self.assertEqual(response.status_code, 404)
        self.assertTrue('The signature request might have been deleted or modified.' in response.text)

    def test_sign_from_mail_link_not_expired(self):
        with freeze_time('2020-01-01'):
            sign_request = self.create_sign_request_1_role(self.partner_1, self.env['res.partner'])
            sign_request_item_id = sign_request.request_item_ids[0]
            timestamp = sign_request_item_id._generate_expiry_link_timestamp()
            expiry_hash = sign_request_item_id._generate_expiry_signature(sign_request_item_id.id, timestamp)

            url = '/sign/document/mail/%(sign_request_id)s/%(access_token)s?timestamp=%(timestamp)s&exp=%(exp)s' % {
                'sign_request_id': sign_request.id,
                'access_token': sign_request.request_item_ids[0].access_token,
                'timestamp': timestamp,
                'exp': expiry_hash
            }
            response = self.url_open(url)
            self.assertEqual(response.status_code, 200)
            self.assertTrue('/sign/document/%s/%s' % (sign_request.id, sign_request_item_id.access_token) in response.url)

    def test_sign_from_mail_with_expired_link(self):
        with freeze_time('2020-01-01'):
            sign_request = self.create_sign_request_1_role(self.partner_1, self.env['res.partner'])
            sign_request_item_id = sign_request.request_item_ids[0]
            timestamp = sign_request_item_id._generate_expiry_link_timestamp()
            expiry_hash = sign_request_item_id._generate_expiry_signature(sign_request_item_id.id, timestamp)

        with freeze_time('2020-01-04'):
            url = '/sign/document/mail/%(sign_request_id)s/%(access_token)s?timestamp=%(timestamp)s&exp=%(exp)s' % {
                'sign_request_id': sign_request.id,
                'access_token': sign_request.request_item_ids[0].access_token,
                'timestamp': timestamp,
                'exp': expiry_hash
            }
            response = self.url_open(url)
            self.assertEqual(response.status_code, 403)
            self.assertTrue('This link has expired' in response.text)

    def test_shared_sign_request_without_expiry_params(self):
        sign_request = self.create_sign_request_1_role(self.partner_1, self.env['res.partner'])
        sign_request.state = 'shared'
        sign_request_item_id = sign_request.request_item_ids[0]
        url = '/sign/document/mail/%s/%s' % (sign_request.id, sign_request_item_id.access_token)
        response = self.url_open(url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue('/sign/document/%s/%s' % (sign_request.id, sign_request_item_id.access_token) in response.url)

    def test_sign_from_resend_expired_link(self):
        with freeze_time('2020-01-01'):
            sign_request = self.create_sign_request_1_role(self.partner_1, self.env['res.partner'])
            sign_request_item_id = sign_request.request_item_ids[0]
            timestamp = sign_request_item_id._generate_expiry_link_timestamp()
            expiry_hash = sign_request_item_id._generate_expiry_signature(sign_request_item_id.id, timestamp)

            url = '/sign/document/mail/%(sign_request_id)s/%(access_token)s?timestamp=%(timestamp)s&exp=%(exp)s' % {
                'sign_request_id': sign_request.id,
                'access_token': sign_request.request_item_ids[0].access_token,
                'timestamp': timestamp,
                'exp': expiry_hash
            }
            response = self.url_open(url)
            self.assertEqual(response.status_code, 200)
            self.assertTrue('/sign/document/%s/%s' % (sign_request.id, sign_request_item_id.access_token) in response.url)

            sign_request_item = {sign_request_item.role_id: sign_request_item for sign_request_item in sign_request.request_item_ids}
            sign_request_item_customer = sign_request_item[self.role_customer]

            sign_request_item_customer.sudo()._edit_and_sign(self.single_role_customer_sign_values)
            mail = self.env['mail.mail'].search([('email_to', '=', formataddr((self.partner_1.name, self.partner_1.email)))])
            self.assertEqual(len(mail.ids), 2)

        with freeze_time('2020-01-04'):
            self.start_tour(url, 'sign_resend_expired_link_tour', login='demo')

    def test_cancel_request_as_public_user(self):
        """
        Test that a public user can cancel a sign request and that a cancellation log is recorded on the partner_id.
        """
        sign_request = self.create_sign_request_1_role(self.partner_1, self.env['res.partner'])
        sign_request_item = sign_request.request_item_ids[0]

        url = '/sign/sign_confirm_cancel/%(item_id)s' % {
            'item_id': sign_request_item.id,
        }

        # Set the environment user as the public user
        self.env.user = self.public_user

        # Send a request to cancel the sign request item
        self.authenticate(None, None)
        post_data = {
            'access_token': sign_request_item.access_token,
            'csrf_token': Request.csrf_token(self),
        }
        response = self.url_open(url, data=post_data)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(sign_request.state, 'canceled', "Sign request state should be 'canceled'")
        self.assertEqual(sign_request_item.state, 'canceled', "Sign request item state should be 'canceled'")

        sign_cancel_log = self.env['sign.log'].search([
            ('sign_request_id', '=', sign_request.id),
            ('action', '=', 'cancel')
        ])

        self.assertTrue(sign_cancel_log, "A sign cancel log should be created")
        self.assertEqual(sign_cancel_log.request_state, 'canceled',
                         "Log request state should be 'canceled'")
        self.assertEqual(sign_cancel_log.partner_id, self.partner_1,
                         "Log partner_id should match partner_1")
        self.assertEqual(sign_cancel_log.sign_request_item_id.id, sign_request_item.id,
                         "Log should reference the correct request item")
