import json
import time

from uuid import uuid4
from xmlrpc.client import Fault

from passlib.totp import TOTP

from odoo import http, _
from odoo.exceptions import AccessDenied
from odoo.service import common as auth, model
from odoo.tests import tagged, HttpCase, get_db_name

from ..controllers.home import Home

@tagged('post_install', '-at_install')
class TestTOTP(HttpCase):
    def setUp(self):
        super().setUp()

        self.totp = None
        # might be possible to do client-side using `crypto.subtle` instead of
        # this horror show, but requires working on 64b integers, & BigInt is
        # significantly less well supported than crypto
        def totp_hook(self_hook, secret=None):
            if self.totp is None:
                self.totp = TOTP(secret)
            if secret:
                return self.totp.generate().token
            else:
                # on check, take advantage of window because previous token has been
                # "burned" so we can't generate the same, but tour is so fast
                # we're pretty certainly within the same 30s
                return self.totp.generate(time.time() + 30).token
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
        uid = self.env.ref('base.user_demo').id
        with self.assertRaisesRegex(Fault, r'Access Denied'):
            self.xmlrpc_object.execute_kw(
                get_db_name(), uid, 'demo',
                'res.users', 'read', [uid, ['login']]
            )

        # 3. Check 2FA is required and disable it
        self.start_tour('/', 'totp_login_enabled', login=None)

        # 4. Finally, check that 2FA is in fact disabled
        self.start_tour('/', 'totp_login_disabled', login=None)

        # 5. Check that rpc is now re-allowed
        uid = self.xmlrpc_common.authenticate(get_db_name(), 'demo', 'demo', {})
        self.assertEqual(uid, self.env.ref('base.user_demo').id)
        [r] = self.xmlrpc_object.execute_kw(
            get_db_name(), uid, 'demo',
            'res.users', 'read', [uid, ['login']]
        )
        self.assertEqual(r['login'], 'demo')


    def test_totp_administration(self):
        self.start_tour('/web', 'totp_tour_setup', login='demo')
        self.start_tour('/web', 'totp_admin_disables', login='admin')
        self.start_tour('/', 'totp_login_disabled', login=None)

    def _build_payload(self, params={}):
        """
        Helper to properly build jsonrpc payload
        """
        return {
            'jsonrpc': '2.0',
            'method': 'call',
            'id': str(uuid4()),
            'params': params,
        }

    def test_totp_mobile_login(self):
        headers = {
            'Content-Type': 'application/json',
        }
        # 1. Enable 2FA
        self.start_tour('/web', 'totp_tour_setup', login='demo')
        self.url_open('/web/session/logout')

        # 2. query login
        payload = self._build_payload({
            'db': get_db_name(),
            'login': 'demo',
            'password': 'demo',
            'context': {},
        })
        response = self.url_open('/web/session/authenticate', data=json.dumps(payload), headers=headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['result']['uid'], None)

        # 3. query totp_token empty
        payload = self._build_payload({
            'totp_token': ''
        })
        response = self.url_open('/web/session/authenticate/totp', data=json.dumps(payload), headers=headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['result']['error'], _("Invalid authentication code format."))

        # 4. query totp_token wrong digits
        payload = self._build_payload({
            'totp_token': '123'
        })
        response = self.url_open('/web/session/authenticate/totp', data=json.dumps(payload), headers=headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['result']['error'], _("Verification failed, please double-check the 6-digit code"))

        # 5. query totp_token right digits
        payload = self._build_payload({
            'totp_token': self.totp.generate().token
        })
        response = self.url_open('/web/session/authenticate/totp', data=json.dumps(payload), headers=headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['result']['uid'], self.env.ref('base.user_demo').id)
