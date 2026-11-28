import json
from unittest.mock import Mock, patch
from urllib.parse import parse_qs, unquote_plus, urlencode, urlsplit

from lxml import html

from odoo.exceptions import AccessDenied, ValidationError
from odoo.tests import HttpCase
from odoo.tools import hash_sign, verify_hash_signed


class TestAuthOAuthSignup(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Provider = cls.env['auth.oauth.provider']
        # only the providers of the tests are listed on the login page
        Provider.search([]).enabled = False
        cls.odoo = cls.env.ref('auth_oauth.provider_openerp')
        cls.odoo.enabled = True
        cls.implicit, cls.pkce = Provider.create([{
            'name': flow,
            'body': flow,
            'flow': flow,
            'enabled': True,
            'client_id': 'odoo-client',
            'client_auth_method': 'client_secret_post',
            'client_secret': 'odoo-secret',
            'auth_endpoint': f'https://{flow}.example.com/authorize',
            'token_endpoint': f'https://{flow}.example.com/token',
            'validation_endpoint': f'https://{flow}.example.com/userinfo',
        } for flow in ('implicit', 'pkce')])

    def test_oauth_signup_does_not_clear_caches(self):
        from odoo.orm.environments import Transaction  # noqa: PLC0415

        self.env['ir.config_parameter'].sudo().set_str('auth_signup.invitation_scope', 'b2c')
        validation = {
            'user_id': 'cache_oauth_uid',
            'email': 'cache_oauth@example.com',
            'name': 'cache oauth',
        }

        self.authenticate(None, None)
        self.opener.cookies['tz'] = 'Europe/Brussels'
        params = {
            'access_token': 'cache_oauth_token',
            'state': json.dumps({'d': self.env.cr.dbname, 'p': self.odoo.id}),
        }

        with (
            patch.object(self.registry['res.users'], '_auth_oauth_rpc', return_value=validation),
            patch.object(Transaction, 'invalidate_ormcache') as invalidate_ormcache,
        ):
            self.url_open(f'/auth_oauth/signin?{urlencode(params)}', allow_redirects=False)

        new_user = self.env['res.users'].search([('oauth_uid', '=', 'cache_oauth_uid')])
        self.assertTrue(new_user)
        self.assertEqual(new_user.tz, 'Europe/Brussels')
        self.assertTrue(new_user.login_date)
        invalidate_ormcache.assert_not_called()

    def test_client_authentication(self):
        """The token request authenticates the way the provider is configured
        for, and never falls back to an unauthenticated one.
        """
        cases = [
            # (method, expected basic auth, expected client_secret in the body)
            ('none', None, None),
            ('client_secret_basic', ('odoo-client', 'odoo-secret'), None),
            ('client_secret_post', None, 'odoo-secret'),
        ]
        response = Mock(ok=True, status_code=200)
        response.json.return_value = {'access_token': 'tok'}
        for method, auth, body_secret in cases:
            with self.subTest(method=method), patch('requests.post', return_value=response) as post:
                self.pkce.client_auth_method = method
                self.pkce._exchange_code_for_token('code', 'verifier', 'https://odoo/cb')
                self.assertEqual(post.call_args.kwargs['auth'], auth)
                self.assertEqual(post.call_args.kwargs['data'].get('client_secret'), body_secret)

        # a secret based method requires a secret...
        with self.assertRaises(ValidationError):
            self.pkce.client_secret = False
        # ...including once neutralization cleared it, bypassing the constraint
        self.env.cr.execute("UPDATE auth_oauth_provider SET client_secret = NULL WHERE id = %s", [self.pkce.id])
        self.pkce.invalidate_recordset(['client_secret'])
        with patch('requests.post') as post, self.assertRaises(AccessDenied), \
             self.assertLogs('odoo.addons.auth_oauth.models.auth_oauth', 'WARNING'):
            self.pkce._exchange_code_for_token('code', 'verifier', 'https://odoo/cb')
        post.assert_not_called()

    # ------------------------------------------------------------------
    # /web/login-with: the authorization request is only issued when the
    # user picks a provider
    # ------------------------------------------------------------------

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
        self.assertIn('href="/web/login-with/%s"' % self.pkce.id, response.text)
        self.assertIn('href="/web/login-with/%s"' % self.implicit.id, response.text)
        self.assertNotIn(self.pkce.auth_endpoint, response.text)
        self.assertNotIn(self.implicit.auth_endpoint, response.text)
        self.assertNotIn('code_challenge', response.text)

    def test_login_page_links_forward_params(self):
        response = self.url_open('/web/login', params={'redirect': '/odoo/action-42', 'token': 'abc'})
        hrefs = html.fromstring(response.text).xpath(
            '//a[starts-with(@href, "/web/login-with/%s?")]/@href' % self.pkce.id,
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
        response = self._login_with(self.pkce.id, redirect='/odoo/action-42', token='abc')
        sid = self.opener.cookies.get('session_id')
        self.assertTrue(sid, "the session the request is bound to must reach the browser")

        params = self._authorize_params(response, self.pkce.auth_endpoint)
        self.assertEqual(params['response_type'], 'code')
        self.assertEqual(params['client_id'], 'odoo-client')
        self.assertEqual(params['code_challenge_method'], 'S256')
        self.assertNotIn('odoo-secret', response.headers['Location'])

        state = params['state']
        self.assertEqual(state['p'], self.pkce.id)
        self.assertEqual(state['d'], self.env.cr.dbname)
        self.assertEqual(state['t'], 'abc')
        self.assertTrue(unquote_plus(state['r']).endswith('/odoo/action-42'))

        nonce, signed_state = verify_hash_signed(self.env(su=True), 'auth_oauth_pkce_state', state['n'])
        self.assertEqual(signed_state, {key: value for key, value in state.items() if key != 'n'})
        code_verifier = self.pkce._get_code_verifier(sid, nonce)
        self.assertEqual(params['code_challenge'], self.pkce._get_code_challenge(code_verifier))

        # the session id does not change before the callback
        self.url_open('/web/login')
        self.assertEqual(self.opener.cookies.get('session_id'), sid)

    def test_login_with_implicit(self):
        response = self._login_with(self.implicit.id)
        params = self._authorize_params(response, self.implicit.auth_endpoint)
        self.assertEqual(params['response_type'], 'token')
        self.assertEqual(params['state']['p'], self.implicit.id)
        self.assertNotIn('n', params['state'])
        self.assertNotIn('code_challenge', params)

    def test_login_with_xmlid(self):
        response = self._login_with('auth_oauth.provider_openerp')
        params = self._authorize_params(response, self.odoo.auth_endpoint)
        self.assertEqual(params['state']['p'], self.odoo.id)

        self.env['ir.model.data'].create({
            'module': '__test__',
            'name': 'pkce_provider',
            'model': 'auth.oauth.provider',
            'res_id': self.pkce.id,
        })
        response = self._login_with('__test__.pkce_provider')
        params = self._authorize_params(response, self.pkce.auth_endpoint)
        self.assertEqual(params['state']['p'], self.pkce.id)

    def test_login_with_unavailable(self):
        self._assert_unavailable(self.pkce.id + 1000)             # no such provider
        self._assert_unavailable('auth_oauth.provider_google')    # not enabled
        self._assert_unavailable('auth_oauth.no_such_provider')   # no such xmlid
        self._assert_unavailable('base.user_admin')               # not a provider
        self._assert_unavailable('not-an-xmlid')
        self.pkce.enabled = False
        self._assert_unavailable(self.pkce.id)

    def test_login_page_unavailable_error(self):
        response = self.url_open('/web/login?oauth_error=provider_unavailable')
        self.assertIn('This login method is not available.', response.text)

    # ------------------------------------------------------------------
    # Mix-up attack (RFC 9700 §4.4): the callback only acts upon a response
    # of the provider named by the state, which the iss parameter of RFC 9207
    # identifies when the provider sends one. Same check for both flows.
    # ------------------------------------------------------------------

    def _trusted(self, provider, **params):
        """Hit the callback with a response the state of which names
        ``provider``, and tell whether it was acted upon: the code exchanged
        (pkce) or the access token sent to the userinfo endpoint (implicit).
        """
        state = {'d': self.env.cr.dbname, 'p': provider.id}
        if provider.flow == 'pkce':
            state['n'] = hash_sign(self.env, 'auth_oauth_pkce_state', ['nonce', state])
            params['code'] = 'the-code'
        else:
            params['access_token'] = 'tok'
        params['state'] = json.dumps(state)
        with patch.object(self.registry['auth.oauth.provider'], '_exchange_code_for_token', return_value={'access_token': 'tok'}) as exchange, \
             patch.object(self.registry['res.users'], '_auth_oauth_validate', return_value={'user_id': 'subject'}) as validate:
            self.url_open('/auth_oauth/signin?' + urlencode(params), allow_redirects=False)
        return exchange.called or validate.called

    def test_issuer_configured(self):
        """A provider known to send ``iss`` must send it on every response,
        matching the configured issuer (RFC 9207 §2.4).
        """
        for provider in (self.implicit, self.pkce):
            with self.subTest(flow=provider.flow):
                provider.issuer = f'https://{provider.flow}.example.com'
                self.assertTrue(self._trusted(provider, iss=provider.issuer))
                # mix-up: the state names this provider, the response comes from another one
                self.assertFalse(self._trusted(provider, iss='https://other.example.com'))
                # a response without iss is not its own
                self.assertFalse(self._trusted(provider))
                # plain string comparison, no normalization
                self.assertFalse(self._trusted(provider, iss=provider.issuer + '/'))

    def test_issuer_not_configured(self):
        """Without a configured issuer, a response need not carry ``iss``, but
        one that does must come from the origin of the authorization endpoint.
        """
        for provider in (self.implicit, self.pkce):
            with self.subTest(flow=provider.flow):
                origin = f'https://{provider.flow}.example.com'
                self.assertTrue(self._trusted(provider))
                self.assertTrue(self._trusted(provider, iss=origin))
                # issuers may carry a path (a tenant, a realm)
                self.assertTrue(self._trusted(provider, iss=origin + '/realms/main'))
                # mix-up: the state names this provider, the response comes from another one
                self.assertFalse(self._trusted(provider, iss='https://other.example.com'))
                # same host, not the same origin
                self.assertFalse(self._trusted(provider, iss=origin.replace('https', 'http')))
                self.assertFalse(self._trusted(provider, iss='not an issuer'))
