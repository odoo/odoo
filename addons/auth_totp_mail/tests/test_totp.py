# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from datetime import datetime, timedelta

from odoo.tests import HttpCase, get_db_name, tagged

from odoo.addons.auth_totp.tests.test_totp import TestTOTPMixin

_logger = logging.getLogger(__name__)


@tagged('post_install', '-at_install')
class TestTOTPMail(TestTOTPMixin, HttpCase):

    def test_totp_rpc_api_keys_only(self):
        db = get_db_name()
        login, password = self.user_test.login, self.user_test.login

        # Without TOTP by mail, xmlrpc using password is expected
        result = self.make_jsonrpc_request('/web/session/authenticate', params={
            'db': db,
            'login': login,
            'password': password,
        })
        self.assertEqual(result['uid'], self.user_test.id)

        # Enable enforcing TOTP by mail
        self.env['res.config.settings'].create({
            'auth_totp_enforce': True,
            'auth_totp_policy': 'all_required',
        }).execute()

        # With TOTP by mail, xmlrpc using password is not expected
        result = self.make_jsonrpc_request('/web/session/authenticate', params={
            'db': db,
            'login': login,
            'password': password,
        })
        self.assertFalse(result.get('uid'))

        # Create an API key for the user
        api_key = self.env['res.users.apikeys'].with_user(self.user_test)._generate(
            None, 'Foo', datetime.now() + timedelta(days=1),
        )

        # With TOTP by mail, xmlrpc using an API key is expected
        result = self.url_open('/json/2/res.users/context_get', json={'ids': []}, headers={
            'X-Odoo-Database': db,
            'Authorization': f'Bearer {api_key}',
        }).raise_for_status().json()
        self.assertEqual(result['uid'], self.user_test.id)


@tagged('post_install', '-at_install')
class TestTOTPInvite(TestTOTPMixin, HttpCase):

    def test_totp_administration(self):
        # If not enabled (like in demo data), landing on res.config will try
        # to disable module_sale_quotation_builder and raise an issue
        group_order_template = self.env.ref('sale_management.group_sale_order_template', raise_if_not_found=False)
        if group_order_template:
            self.env.ref('base.group_user').write({"implied_ids": [(4, group_order_template.id)]})
        self.install_totphook()
        self.start_tour('/odoo', 'totp_admin_invite', login='admin')
        self.start_tour('/odoo', 'totp_admin_self_invite', login='admin')
