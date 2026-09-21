# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json
from urllib.parse import parse_qs, unquote_plus, urlsplit

from lxml import html

from odoo.tests import HttpCase, tagged
from odoo.tools import verify_hash_signed


@tagged('post_install', '-at_install')
class TestLoginWith(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Provider = cls.env['auth.oauth.provider']
        # only the providers of the test are listed on the login page
        Provider.search([]).enabled = False
        cls.pkce_provider = Provider.create({
            'name': 'PKCE Provider',
            'flow': 'pkce',
            'client_id': 'pkce-client',
            'client_secret': 'pkce-secret',
            'auth_endpoint': 'https://idp.example.com/authorize',
            'token_endpoint': 'https://idp.example.com/token',
            'validation_endpoint': 'https://idp.example.com/userinfo',
            'body': 'Sign in with PKCE',
            'enabled': True,
        })
        cls.implicit_provider = cls.env.ref('auth_oauth.provider_openerp')
        cls.implicit_provider.enabled = True

    def _login_with(self, provider_ref, **params):
        response = self.url_open(
            '/web/login-with/%s' % provider_ref, params=params, allow_redirects=False,
        )
        self.assertEqual(response.status_code, 303)
        return response

    def _authorize_params(self, response, endpoint):
        location = urlsplit(response.headers['Location'])
        self.assertEqual('%s://%s%s' % (location.scheme, location.netloc, location.path), endpoint)
        params = {key: values[0] for key, values in parse_qs(location.query).items()}
        params['state'] = json.loads(params['state'])
        return params

    def _assert_unavailable(self, provider_ref):
        response = self._login_with(provider_ref)
        self.assertEqual(
            urlsplit(response.headers['Location']).path + '?' + urlsplit(response.headers['Location']).query,
            '/web/login?oauth_error=provider_unavailable',
        )

    def test_login_page_links(self):
        """The login page only links to /web/login-with, it issues no
        authorization request."""
        response = self.url_open('/web/login')
        self.assertEqual(response.status_code, 200)
        self.assertIn('href="/web/login-with/%s"' % self.pkce_provider.id, response.text)
        self.assertIn('href="/web/login-with/%s"' % self.implicit_provider.id, response.text)
        self.assertNotIn(self.pkce_provider.auth_endpoint, response.text)
        self.assertNotIn(self.implicit_provider.auth_endpoint, response.text)
        self.assertNotIn('code_challenge', response.text)

    def test_login_page_links_forward_params(self):
        response = self.url_open('/web/login', params={'redirect': '/odoo/action-42', 'token': 'abc'})
        hrefs = html.fromstring(response.text).xpath(
            '//a[starts-with(@href, "/web/login-with/%s?")]/@href' % self.pkce_provider.id,
        )
        self.assertEqual(len(hrefs), 1)
        self.assertEqual(
            parse_qs(urlsplit(hrefs[0]).query),
            {'redirect': ['/odoo/action-42'], 'token': ['abc']},
        )

    def test_login_with_pkce(self):
        """A visitor without any session gets an authorization request bound to
        the session the callback will come back with."""
        self.assertFalse(self.opener.cookies.get('session_id'))
        response = self._login_with(self.pkce_provider.id, redirect='/odoo/action-42', token='abc')
        sid = self.opener.cookies.get('session_id')
        self.assertTrue(sid, "the session the request is bound to must reach the browser")

        params = self._authorize_params(response, self.pkce_provider.auth_endpoint)
        self.assertEqual(params['response_type'], 'code')
        self.assertEqual(params['client_id'], 'pkce-client')
        self.assertEqual(params['code_challenge_method'], 'S256')
        self.assertNotIn('pkce-secret', response.headers['Location'])

        state = params['state']
        self.assertEqual(state['p'], self.pkce_provider.id)
        self.assertEqual(state['d'], self.env.cr.dbname)
        self.assertEqual(state['t'], 'abc')
        self.assertTrue(unquote_plus(state['r']).endswith('/odoo/action-42'))

        nonce, signed_state = verify_hash_signed(self.env(su=True), 'auth_oauth_pkce_state', state['n'])
        self.assertEqual(signed_state, {key: value for key, value in state.items() if key != 'n'})
        code_verifier = self.pkce_provider._get_code_verifier(sid, nonce)
        self.assertEqual(params['code_challenge'], self.pkce_provider._get_code_challenge(code_verifier))

        # the session id does not change before the callback
        self.url_open('/web/login')
        self.assertEqual(self.opener.cookies.get('session_id'), sid)

    def test_login_with_implicit(self):
        response = self._login_with(self.implicit_provider.id)
        params = self._authorize_params(response, self.implicit_provider.auth_endpoint)
        self.assertEqual(params['response_type'], 'token')
        self.assertEqual(params['state']['p'], self.implicit_provider.id)
        self.assertNotIn('n', params['state'])
        self.assertNotIn('code_challenge', params)

    def test_login_with_xmlid(self):
        response = self._login_with('auth_oauth.provider_openerp')
        params = self._authorize_params(response, self.implicit_provider.auth_endpoint)
        self.assertEqual(params['state']['p'], self.implicit_provider.id)

        self.env['ir.model.data'].create({
            'module': '__test__',
            'name': 'pkce_provider',
            'model': 'auth.oauth.provider',
            'res_id': self.pkce_provider.id,
        })
        response = self._login_with('__test__.pkce_provider')
        params = self._authorize_params(response, self.pkce_provider.auth_endpoint)
        self.assertEqual(params['state']['p'], self.pkce_provider.id)

    def test_login_with_unavailable(self):
        self._assert_unavailable(self.pkce_provider.id + 1000)    # no such provider
        self._assert_unavailable('auth_oauth.provider_google')    # not enabled
        self._assert_unavailable('auth_oauth.no_such_provider')   # no such xmlid
        self._assert_unavailable('base.user_admin')               # not a provider
        self._assert_unavailable('not-an-xmlid')
        self.pkce_provider.enabled = False
        self._assert_unavailable(self.pkce_provider.id)

    def test_login_page_unavailable_error(self):
        response = self.url_open('/web/login?oauth_error=provider_unavailable')
        self.assertIn('This login method is not available.', response.text)
