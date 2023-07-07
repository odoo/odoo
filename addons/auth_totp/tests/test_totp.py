import base64
import json
import logging
import os
import time
import threading
from xmlrpc.client import Fault

from passlib.totp import TOTP

from odoo import http
from odoo.tests import tagged, HttpCase, get_db_name
from odoo.tools import mute_logger

from ..controllers.home import Home

_logger = logging.getLogger(__name__)

@tagged('post_install', '-at_install')
class TestTOTP(HttpCase):
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

        # 3. Check 2FA is required
        self.start_tour('/', 'totp_login_enabled', login=None)

        # 4. Check 2FA is not requested on saved device and disable it
        self.start_tour('/', 'totp_login_device', login=None)

        # 5. Finally, check that 2FA is in fact disabled
        self.start_tour('/', 'totp_login_disabled', login=None)

        # 6. Check that rpc is now re-allowed
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

    @mute_logger('odoo.http')
    def test_totp_authenticate(self):
        """
        Ensure we don't leak the session info from an half-logged-in
        user.
        """

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
            },
        }
        response = self.url_open("/web/session/authenticate", data=json.dumps(payload), headers=headers)
        data = response.json()
        self.assertEqual(data['result']['uid'], None)


@tagged('-at_install', 'post_install')
class TestTOTPConcurrent(HttpCase):
    def test_totp_concurrent_session_expired(self):
        ct_json = {'Content-Type': 'application/json'}
        jsonrpc = {
            'jsonrpc': '2.0',
            'method': 'call',
            'id': 0,
        }
        session = self.authenticate('demo', 'demo')
        session['identity-check-last'] = time.time()  # needed by check_identity
        http.root.session_store.save(session)


        # Setup
        #
        # Both requests get the same session then /web/session/check
        # waits for /web/dataset/call_kw to finish
        barrier = threading.Barrier(2)
        event = threading.Event()

        _post_init = http.Request._post_init
        def sync_post_init(self):
            _post_init(self)
            _logger.info("%s %s", self.httprequest.path, "waits at barrier")
            barrier.wait(timeout=1)
            _logger.info("%s %s", self.httprequest.path, "resumes from barrier")
            if self.httprequest.path == '/web/session/check':
                _logger.info("%s %s", self.httprequest.path, "waits at event")
                event.wait(timeout=1)
                _logger.info("%s %s", self.httprequest.path, "resume from event")
        self.patch(http.Request, '_post_init', sync_post_init)

        _totp_try_setting = self.env.registry['res.users']._totp_try_setting
        def signal_totp_try_setting(*args, **kwargs):
            res = _totp_try_setting(*args, **kwargs)
            _logger.info("%s %s", http.request.httprequest.path, "sets event")
            event.set()
            return res
        self.patch(self.env.registry['res.users'], '_totp_try_setting', signal_totp_try_setting)


        # Test case
        #
        # Start both requests in their own thread so that the two run
        # in parallel
        check_session_res = None
        def check_session():
            nonlocal check_session_res
            check_session_res = self.url_open('/web/session/check', data=json.dumps(jsonrpc), headers=ct_json)

        totp_enable_res = None
        def totp_enable():
            nonlocal totp_enable_res
            secret = base64.b32encode(os.urandom(20)).decode()
            code = TOTP(secret).generate().token
            auto_totp_wizard = self.env['auth_totp.wizard'].create([{
                'user_id': session.uid,
                'secret': secret,
                'code': code,
            }])
            totp_enable_res = self.url_open(
                '/web/dataset/call_kw',
                data=json.dumps(jsonrpc | {'params': {
                    'model': 'auth_totp.wizard',
                    'method': 'enable',
                    'args': [auto_totp_wizard.id],
                    'kwargs': {},
                }}),
                headers=ct_json,
            )
            check_session_thread.join()

        totp_enable_thread = threading.Thread(target=totp_enable)
        check_session_thread = threading.Thread(target=check_session)
        totp_enable_thread.start()
        check_session_thread.start()
        totp_enable_thread.join()
        check_session_thread.join()

        # Assertion
        #
        # Both request should succeed, the /web/session/check one
        # shouldn't fail because of an expired session
        check_session_res.raise_for_status()
        if error := check_session_res.json().get('error'):
            self.fail('\n' + error['data']['debug'])

        totp_enable_res.raise_for_status()
        if error := totp_enable_res.json().get('error'):
            self.fail('\n' + error['data']['debug'])
