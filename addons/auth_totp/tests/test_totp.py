import logging
import json
import time
from xmlrpc.client import Fault

from passlib.totp import TOTP

from odoo import http
from odoo.tests import tagged, get_db_name, new_test_user, HttpCase
from odoo.tools import mute_logger

from odoo.addons.auth_totp.models.totp import TOTP as auth_TOTP

from ..controllers.home import Home

_logger = logging.getLogger(__name__)


class TestTOTPMixin:
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_test = new_test_user(
            cls.env, 'test_user', password='test_user', tz='UTC',
        )

        ml = mute_logger('odoo.addons.rpc.controllers.xmlrpc')
        ml.__enter__()  # noqa: PLC2801
        cls.addClassCleanup(ml.__exit__)

    def install_totphook(self):
        baseline_time = time.time()
        last_offset = 0
        totp = None

        # might be possible to do client-side using `crypto.subtle` instead of
        # this horror show, but requires working on 64b integers, & BigInt is
        # significantly less well supported than crypto
        def totp_hook(self, secret=None, offset=0):
            nonlocal totp, last_offset
            last_offset = offset * 30
            if totp is None:
                totp = TOTP(secret)

            # generate the token for the given time offset
            # we can't generate the same token twice, but tour is so fast
            # we're pretty certainly within the same 30s
            token = totp.generate(baseline_time + last_offset).token
            _logger.info("TOTP secret:%s offset:%s token:%s", secret, offset, token)
            return token
        # because not preprocessed by ControllerType metaclass
        totp_hook.routing_type = 'json'
        self.env.registry.clear_cache('routing')
        # patch Home to add test endpoint
        Home.totp_hook = http.route('/totphook', type='jsonrpc', auth='none')(totp_hook)

        def totp_match(self, code, t=None, **kwargs):
            # Allow going beyond the 30s window
            return origin_match(self, code, t=baseline_time + last_offset, **kwargs)

        origin_match = auth_TOTP.match
        auth_TOTP.match = totp_match

        # remove endpoint and destroy routing map
        @self.addCleanup
        def _cleanup():
            del Home.totp_hook
            auth_TOTP.match = origin_match
            self.env.registry.clear_cache('routing')


@tagged('post_install', '-at_install')
class TestTOTP(TestTOTPMixin, HttpCase):

    def setUp(self):
        super().setUp()
        self.install_totphook()

    def test_totp(self):
        # 1. Enable 2FA
        self.start_tour('/odoo', 'totp_tour_setup', login='test_user')

        # 2. Verify that RPC is blocked because 2FA is on.
        self.assertFalse(
            self.xmlrpc_common.authenticate(get_db_name(), 'test_user', 'test_user', {}),
            "Should not have returned a uid"
        )
        self.assertFalse(
            self.xmlrpc_common.authenticate(get_db_name(), 'test_user', 'test_user', {'interactive': True}),
            'Trying to fake the auth type should not work'
        )
        uid = self.user_test.id
        with self.assertRaisesRegex(Fault, r'Access Denied'), mute_logger("odoo.http"):
            self.xmlrpc_object.execute_kw(
                get_db_name(), uid, 'test_user',
                'res.users', 'read', [uid, ['login']]
            )

        # 3. Check 2FA is required
        with self.assertLogs("odoo.addons.auth_totp.models.res_users", "WARNING") as cm:
            self.start_tour('/', 'totp_login_enabled', login=None)

        self.assertEqual(len(cm.output), 1)
        self.assertIn("2FA check: REUSE", cm.output[0])

        # 4. Check 2FA is not requested on saved device and disable it
        self.start_tour('/', 'totp_login_device', login=None)

        # 5. Finally, check that 2FA is in fact disabled
        self.start_tour('/', 'totp_login_disabled', login=None)

        # 6. Check that rpc is now re-allowed
        uid = self.xmlrpc_common.authenticate(get_db_name(), 'test_user', 'test_user', {})
        self.assertEqual(uid, self.user_test.id)
        [r] = self.xmlrpc_object.execute_kw(
            get_db_name(), uid, 'test_user',
            'res.users', 'read', [uid, ['login']]
        )
        self.assertEqual(r['login'], 'test_user')

    def test_totp_administration(self):
        self.start_tour('/web', 'totp_tour_setup', login='test_user')
        # If not enabled (like in demo data), landing on res.config will try
        # to disable module_sale_quotation_builder and raise an issue
        group_order_template = self.env.ref('sale_management.group_sale_order_template', raise_if_not_found=False)
        if group_order_template:
            self.env.ref('base.group_user').write({"implied_ids": [(4, group_order_template.id)]})
        self.start_tour('/odoo', 'totp_admin_disables', login='admin')
        self.start_tour('/', 'totp_login_disabled', login=None)

    @mute_logger('odoo.http')
    def test_totp_authenticate(self):
        """
        Ensure we don't leak the session info from an half-logged-in
        user.
        """
        self.start_tour('/odoo', 'totp_tour_setup', login='test_user')
        self.url_open('/web/session/logout')

        headers = {
            "Content-Type": "application/json",
        }

        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "id": 0,
            "params": {
                "db": get_db_name(),
                "login": "test_user",
                "password": "test_user",
            },
        }
        response = self.url_open("/web/session/authenticate", data=json.dumps(payload), headers=headers)
        data = response.json()
        self.assertEqual(data['result']['uid'], None)
