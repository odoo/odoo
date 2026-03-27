import logging

from datetime import datetime, timedelta
from xmlrpc.client import Fault

from odoo.tests import get_db_name, tagged, HttpCase
from odoo.tools import mute_logger

from odoo.addons.auth_totp.tests.test_totp import TestTOTPMixin

_logger = logging.getLogger(__name__)


@tagged('post_install', '-at_install')
class TestTOTPMailEnforce(TestTOTPMixin, HttpCase):

    def test_totp_rpc_api_keys_only(self):
        db = get_db_name()
        login, password = self.user_test.login, self.user_test.login
        uid = self.xmlrpc_common.authenticate(db, password, login, {})

        # Without TOTP by mail, xmlrpc using password is expected
        [result] = self.xmlrpc_object.execute_kw(db, uid, password, 'res.users', 'read', [uid, ['login']])
        self.assertEqual(result['login'], login)

        # Enable enforcing TOTP by mail
        self.env['res.config.settings'].create({
            'auth_totp_enforce': True,
            'auth_totp_policy': 'all_required'
        }).execute()

        # With TOTP by mail, xmlrpc using password is not expected
        with (
            self.assertRaisesRegex(Fault, r'Access Denied'),
            self.assertLogs(logger='odoo.addons.base.models.res_users') as log_catcher,
            mute_logger("odoo.http")
        ):
            self.xmlrpc_object.execute_kw(db, uid, password, 'res.users', 'read', [uid, ['login']])
        self.assertIn("Invalid API key or password-based authentication", log_catcher.output[0])

        # Create an API key for the user
        api_key = self.env['res.users.apikeys'].with_user(self.user_test)._generate(
            None, 'Foo', datetime.now() + timedelta(days=1)
        )

        # With TOTP by mail, xmlrpc using an API key is expected
        [result] = self.xmlrpc_object.execute_kw(db, uid, api_key, 'res.users', 'read', [uid, ['login']])
        self.assertEqual(result['login'], login)
