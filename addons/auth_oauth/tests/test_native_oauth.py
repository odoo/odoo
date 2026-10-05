import base64
import hashlib
import json
from datetime import timedelta
from urllib.parse import parse_qs, urlencode, urlsplit

from lxml import html

from odoo import http
from odoo.tests import HttpCase, get_db_name, new_test_user, tagged
from odoo.tools import mute_logger
from odoo.tools.misc import hash_sign

from ..controllers.main import NATIVE_CODE_SCOPE

FLOW = '0123456789abcdef0123456789abcdef'
VERIFIER = 'v' * 64
CHALLENGE = base64.urlsafe_b64encode(hashlib.sha256(VERIFIER.encode()).digest()).decode().rstrip('=')


@tagged('post_install', '-at_install')
class TestNativeOAuth(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.provider = cls.env['auth.oauth.provider'].create({
            'name': 'Test provider',
            'body': 'Log in with the test provider',
            'enabled': True,
            'client_id': 'test',
            'auth_endpoint': 'https://provider.example/auth',
            'validation_endpoint': 'https://provider.example/userinfo',
        })
        cls.env['ir.config_parameter'].set_param('auth_signup.invitation_scope', 'b2b')
        cls.user = new_test_user(cls.env, 'oauth_user')
        cls.user.write({'oauth_provider_id': cls.provider.id, 'oauth_uid': 'sub-1'})

    def setUp(self):
        super().setUp()
        validations = {
            'good-token': {'sub': 'sub-1'},
            'unknown-user-token': {'sub': 'sub-unknown'},
        }

        def _auth_oauth_rpc(users, endpoint, access_token):
            return validations.get(access_token, {'error': 'invalid_token'})

        self.patch(self.registry['res.users'], '_auth_oauth_rpc', _auth_oauth_rpc)

    def _signin(self, access_token='good-token', **native):
        state = {'d': get_db_name(), 'p': self.provider.id, **native}
        query = {'access_token': access_token, 'state': json.dumps(state)}
        return self.url_open(f'/auth_oauth/signin?{urlencode(query)}', allow_redirects=False)

    def _native_params(self, url):
        location = urlsplit(url)
        self.assertEqual((location.scheme, location.path), ('com.odoo.mobile', f'/oauth/{FLOW}'))
        return {k: v[0] for k, v in parse_qs(location.query).items()}

    def _native_signin(self):
        """Sign in up to the confirmation page and follow its link."""
        response = self._signin(nc=CHALLENGE, nf=FLOW)
        self.assertEqual(response.status_code, 200)
        [link] = html.fromstring(response.text).xpath("//a[contains(@class, 'o_auth_oauth_native_confirm')]")
        return self._native_params(link.get('href'))

    def _exchange(self, data, headers=None):
        return self.url_open('/auth_oauth/native/exchange', data=data, headers=headers, allow_redirects=False)

    def _session_uid(self):
        sid = self.opener.cookies.get('session_id')
        return sid and http.root.session_store.get(sid).uid

    def test_signin_without_native_state(self):
        response = self._signin()
        self.assertEqual(response.status_code, 303)
        self.assertEqual(urlsplit(response.headers['Location']).path, '/odoo')
        self.assertEqual(self._session_uid(), self.user.id)

    def test_signin_ignores_malformed_native_state(self):
        for native in [
            {'nc': CHALLENGE},
            {'nf': FLOW},
            {'nc': CHALLENGE, 'nf': FLOW.upper()},
            {'nc': CHALLENGE, 'nf': FLOW + '0'},
            {'nc': CHALLENGE[:-1], 'nf': FLOW},
            {'nc': CHALLENGE[:-1] + '=', 'nf': FLOW},
            {'nc': {'x': 1}, 'nf': FLOW},
            {'nc': CHALLENGE, 'nf': 1},
        ]:
            with self.subTest(native=native):
                self.opener.cookies.clear()
                response = self._signin(**native)
                self.assertEqual(response.status_code, 303)
                self.assertEqual(urlsplit(response.headers['Location']).path, '/odoo')
                self.assertEqual(self._session_uid(), self.user.id)

    def test_native_signin_does_not_log_the_browser_in(self):
        params = self._native_signin()
        self.assertEqual(params['db'], get_db_name())
        self.assertTrue(params['code'])
        self.assertFalse(self._session_uid())

    def test_native_signin_waits_for_the_user(self):
        response = self._signin(nc=CHALLENGE, nf=FLOW)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('Location', response.headers)
        self.assertIn(self.user.login, response.text)
        self.assertEqual(response.headers['X-Frame-Options'], 'DENY')
        self.assertEqual(response.headers['Content-Security-Policy'], "frame-ancestors 'none'")
        self.assertEqual(response.headers['Cache-Control'], 'no-store')

    @mute_logger('odoo.addons.auth_oauth.controllers.main')
    def test_native_signin_errors(self):
        for access_token, error in [('unknown-user-token', '3'), ('bad-token', '2')]:
            with self.subTest(access_token=access_token):
                response = self._signin(access_token, nc=CHALLENGE, nf=FLOW)
                self.assertEqual(response.status_code, 303)
                self.assertEqual(self._native_params(response.headers['Location']), {'error': error})
                self.assertFalse(self._session_uid())

    def test_exchange(self):
        params = self._native_signin()
        response = self._exchange(
            {**params, 'verifier': VERIFIER},
            headers={'Origin': 'null', 'Sec-Fetch-Site': 'none'},
        )
        self.assertEqual(response.status_code, 303)
        self.assertEqual(urlsplit(response.headers['Location']).path, '/odoo')
        self.assertEqual(self._session_uid(), self.user.id)

    def test_exchange_same_origin(self):
        params = self._native_signin()
        response = self._exchange(
            {**params, 'verifier': VERIFIER},
            headers={'Origin': self.base_url(), 'Sec-Fetch-Site': 'same-origin'},
        )
        self.assertEqual(response.status_code, 303)
        self.assertEqual(self._session_uid(), self.user.id)

    def test_exchange_wrong_verifier(self):
        params = self._native_signin()
        response = self._exchange({**params, 'verifier': 'w' * 64})
        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers['Location'], '/web/login?oauth_error=3')
        self.assertFalse(self._session_uid())

    def test_exchange_expired_code(self):
        self._signin()  # stores the provider token on the user
        self.opener.cookies.clear()
        code = hash_sign(
            self.env(su=True), NATIVE_CODE_SCOPE,
            {'login': self.user.login, 'challenge': CHALLENGE, 'redirect': '/odoo'},
            expiration=timedelta(seconds=-1),
        )
        response = self._exchange({'db': get_db_name(), 'code': code, 'verifier': VERIFIER})
        self.assertEqual(response.headers['Location'], '/web/login?oauth_error=3')
        self.assertFalse(self._session_uid())

    def test_exchange_malformed_code(self):
        response = self._exchange({'db': get_db_name(), 'code': 'not-a-code', 'verifier': VERIFIER})
        self.assertEqual(response.headers['Location'], '/web/login?oauth_error=3')

    def test_exchange_missing_params(self):
        params = {'db': get_db_name(), 'code': 'code', 'verifier': VERIFIER}
        for missing in params:
            with self.subTest(missing=missing):
                response = self._exchange({**params, missing: ''})
                self.assertEqual(response.status_code, 400)

    def test_exchange_rejects_cross_site(self):
        params = self._native_signin()
        for headers in [
            {'Sec-Fetch-Site': 'cross-site'},
            {'Sec-Fetch-Site': 'same-site'},
            {'Origin': 'null', 'Sec-Fetch-Site': 'cross-site'},
            {'Origin': 'https://attacker.example'},
        ]:
            with self.subTest(headers=headers):
                response = self._exchange({**params, 'verifier': VERIFIER}, headers=headers)
                self.assertEqual(response.status_code, 400)
                self.assertFalse(self._session_uid())
