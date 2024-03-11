import logging
import json
import time
from xmlrpc.client import Fault

from passlib.totp import TOTP

from odoo import http
from odoo.addons.base.tests.common import HttpCaseWithUserDemo
from odoo.exceptions import AccessDenied
from odoo.service import common as auth, model
from odoo.tests import tagged, get_db_name, loaded_demo_data
from odoo.tools import mute_logger

from ..controllers.home import Home

_logger = logging.getLogger(__name__)


@tagged('post_install', '-at_install')
class TestTOTP(HttpCaseWithUserDemo):
    def setUp(self):
        super().setUp()
        totp = None
        # might be possible to do client-side using `crypto.subtle` instead of
        # this horror show, but requires working on 64b integers, & BigInt is
        # significantly less well supported than crypto
        def totp_hook(self, secret=None):
            nonlocal totp
            if totp is None:
                totp = TOTP(secret)
            if secret:
                return totp.generate().token
            else:
                # on check, take advantage of window because previous token has been
                # "burned" so we can't generate the same, but tour is so fast
                # we're pretty certainly within the same 30s
                return totp.generate(time.time() + 30).token
        # because not preprocessed by ControllerType metaclass
        totp_hook.routing_type = 'json'
        self.env['ir.http']._clear_routing_map()
        # patch Home to add test endpoint
        Home.totp_hook = http.route('/totphook', type='json', auth='none')(totp_hook)
        # remove endpoint and destroy routing map
        @self.addCleanup
        def _cleanup():
            del Home.totp_hook
            self.env['ir.http']._clear_routing_map()

    def test_totp(self):
        # TODO: Make this work if no demo data + hr installed
        if not loaded_demo_data(self.env):
            _logger.warning("This test relies on demo data. To be rewritten independently of demo data for accurate and reliable results.")
            return
        # 1. Enable 2FA
        self.start_tour('/web', 'totp_tour_setup', login='demo')

        # 2. Verify that RPC is blocked because 2FA is on.
        self.assertFalse(
            self.xmlrpc_common.authenticate(get_db_name(), 'demo', 'demo', {}),
            "Should not have returned a uid"
        )
        self.assertFalse(
            self.xmlrpc_common.authenticate(get_db_name(), 'demo', 'demo', {'interactive': True}),
            'Trying to fake the auth type should not work'
        )
        uid = self.user_demo.id
        with self.assertRaisesRegex(Fault, r'Access Denied'):
            self.xmlrpc_object.execute_kw(
                get_db_name(), uid, 'demo',
                'res.users', 'read', [uid, ['login']]
            )

        # 3. Check 2FA is required
        self.start_tour('/', 'totp_login_enabled', login=None)

        # 4. Check 2FA is not requested on saved device and disable it
        self.start_tour('/', 'totp_login_device', login=None)

        # 5. Finally, check that 2FA is in fact disabled
        self.start_tour('/', 'totp_login_disabled', login=None)

        # 6. Check that rpc is now re-allowed
        uid = self.xmlrpc_common.authenticate(get_db_name(), 'demo', 'demo', {})
        self.assertEqual(uid, self.user_demo.id)
        [r] = self.xmlrpc_object.execute_kw(
            get_db_name(), uid, 'demo',
            'res.users', 'read', [uid, ['login']]
        )
        self.assertEqual(r['login'], 'demo')


    def test_totp_administration(self):
        # TODO: Make this work if no demo data + hr installed
        if not loaded_demo_data(self.env):
            _logger.warning("This test relies on demo data. To be rewritten independently of demo data for accurate and reliable results.")
            return
        self.start_tour('/web', 'totp_tour_setup', login='demo')
        self.start_tour('/web', 'totp_admin_disables', login='admin')
        self.start_tour('/', 'totp_login_disabled', login=None)

    @mute_logger('odoo.http')
    def test_totp_authenticate(self):
        """
        Ensure we don't leak the session info from an half-logged-in
        user.
        """
        # TODO: Make this work if no demo data + hr installed
        if not loaded_demo_data(self.env):
            _logger.warning("This test relies on demo data. To be rewritten independently of demo data for accurate and reliable results.")
            return

        self.start_tour('/web', 'totp_tour_setup', login='demo')
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
                "login": "demo",
                "password": "demo",
                "context": {},
            },
        }
        response = self.url_open("/web/session/authenticate", data=json.dumps(payload), headers=headers)
        data = response.json()
        self.assertEqual(data['result']['uid'], None)
