# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json
from unittest.mock import Mock, patch
from urllib.parse import parse_qs, urlencode, urlsplit

from lxml import html

from odoo.exceptions import AccessDenied
from odoo.tests import HttpCase, TransactionCase, tagged


def _token_response(status, payload):
    """Fake ``requests.Response`` of the token endpoint."""
    response = Mock(ok=status < 400, status_code=status)
    response.json.return_value = payload
    return response


class TestPkceProvider(TransactionCase):
    """PKCE building blocks of the provider model, no HTTP request involved:
    verifier/challenge derivation and the code for token exchange, with the
    token endpoint mocked.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.provider = cls.env['auth.oauth.provider'].create({
            'name': 'PKCE IdP',
            'flow': 'pkce',
            'client_id': 'odoo-client',
            'auth_endpoint': 'https://idp.example.com/authorize',
            'token_endpoint': 'https://idp.example.com/token',
            'validation_endpoint': 'https://idp.example.com/userinfo',
            'body': 'Log in with PKCE IdP',
        })

    def test_code_challenge(self):
        """The S256 challenge is BASE64URL(SHA256(verifier)) without padding,
        checked against the worked example of RFC 7636 appendix B so that any
        provider following the RFC accepts it.
        """
        self.assertEqual(
            self.provider._get_code_challenge('dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk'),
            'E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM',
        )

    def test_code_verifier(self):
        """Nothing is stored server side: the callback derives the verifier
        again from the session and the nonce. It must therefore be stable for
        the same inputs, and change with either of them so that another
        session (or another authorization request) never ends up with it.
        """
        verifier = self.provider._get_code_verifier('sid', 'nonce')
        # RFC 7636 §4.1: 43 to 128 characters
        self.assertTrue(43 <= len(verifier) <= 128)
        # derived again on the callback: same inputs, same verifier
        self.assertEqual(verifier, self.provider._get_code_verifier('sid', 'nonce'))
        # bound to the session and to the authorization request
        self.assertNotEqual(verifier, self.provider._get_code_verifier('other-sid', 'nonce'))
        self.assertNotEqual(verifier, self.provider._get_code_verifier('sid', 'other-nonce'))

    def test_exchange_client_secret(self):
        """The token request carries the client secret the way the provider
        is configured for, and the client id and code verifier in any case.
        """
        # (client_secret_method, client_secret, expected basic auth, expected client_secret in the body)
        cases = [
            # public client: no secret sent at all
            ('post', False, None, None),
            # confidential client, secret in the request body
            ('post', 'shh', None, 'shh'),
            # confidential client, secret in an HTTP Basic header only
            ('basic', 'shh', ('odoo-client', 'shh'), None),
        ]
        for method, secret, expected_auth, expected_body_secret in cases:
            with self.subTest(method=method, secret=secret):
                self.provider.write({'client_secret_method': method, 'client_secret': secret})
                response = _token_response(200, {'access_token': 'tok'})
                with patch('requests.post', return_value=response) as post:
                    token = self.provider._exchange_code_for_token('code', 'verifier', 'https://odoo/cb')
                self.assertEqual(token['access_token'], 'tok')
                kwargs = post.call_args.kwargs
                self.assertEqual(kwargs['auth'], expected_auth)
                # RFC 7636 §4.5 / §4.3: always part of the body, secret or not
                self.assertEqual(kwargs['data']['code_verifier'], 'verifier')
                self.assertEqual(kwargs['data']['client_id'], 'odoo-client')
                self.assertEqual(kwargs['data'].get('client_secret'), expected_body_secret)

    def test_exchange_refused(self):
        """Any token response that does not hand over an access token turns
        into an AccessDenied, which the callback maps to a login error rather
        than a crash.
        """
        responses = [
            # regular refusal, e.g. a code replayed or a verifier mismatch
            _token_response(400, {'error': 'invalid_grant'}),
            # some providers report errors with a 200
            _token_response(200, {'error': 'invalid_grant'}),
            # success status, but no access token
            _token_response(200, {'token_type': 'Bearer'}),
            # valid JSON that is not an object
            _token_response(200, ['not', 'a', 'dict']),
        ]
        for response in responses:
            with self.subTest(payload=response.json.return_value), \
                 patch('requests.post', return_value=response), \
                 self.assertRaises(AccessDenied):
                self.provider._exchange_code_for_token('code', 'verifier', 'https://odoo/cb')


@tagged('post_install', '-at_install')
class TestPkceSignin(HttpCase):
    """End to end PKCE flow through the real routes: the authorization link of
    the login page, then the provider callback on ``/auth_oauth/signin``. Only
    the calls to the provider (token and userinfo endpoints) are mocked.

    Both legs go through the same browser session, which the code verifier is
    bound to.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.provider = cls.env['auth.oauth.provider'].create({
            'name': 'PKCE IdP',
            'flow': 'pkce',
            'enabled': True,
            'client_id': 'odoo-client',
            'auth_endpoint': 'https://idp.example.com/authorize',
            'token_endpoint': 'https://idp.example.com/token',
            'validation_endpoint': 'https://idp.example.com/userinfo',
            'body': 'Log in with PKCE IdP',
        })
        # already linked to the provider, so that the callback signs it in
        # instead of signing a new user up
        cls.user = cls.env['res.users'].create({
            'name': 'PKCE User',
            'login': 'pkce_user',
            'oauth_provider_id': cls.provider.id,
            'oauth_uid': 'pkce-subject',
        })

    def _authorization_params(self):
        """Load the login page and return the query of the provider's link."""
        response = self.url_open('/web/login')
        self.assertEqual(response.status_code, 200)
        links = [
            href for href in html.fromstring(response.content).xpath('//a/@href')
            if href.startswith(self.provider.auth_endpoint)
        ]
        self.assertEqual(len(links), 1)
        return {key: value[0] for key, value in parse_qs(urlsplit(links[0]).query).items()}

    def _callback(self, **params):
        """Hit the callback as the provider would redirect the browser to it,
        with a provider that accepts any code and identifies the user above.
        Return the response and the mocked token exchange.
        """
        Provider = self.registry['auth.oauth.provider']
        Users = self.registry['res.users']
        with patch.object(Provider, '_exchange_code_for_token', return_value={'access_token': 'tok'}) as exchange, \
             patch.object(Users, '_auth_oauth_validate', return_value={'user_id': 'pkce-subject'}):
            response = self.url_open('/auth_oauth/signin?' + urlencode(params), allow_redirects=False)
        return response, exchange

    def test_authorization_link(self):
        """The login page sends the user to the provider with an
        authorization code request, rather than an implicit one.
        """
        params = self._authorization_params()
        # code flow, not response_type=token
        self.assertEqual(params['response_type'], 'code')
        # S256 only: "plain" would leak the verifier in the browser history
        self.assertEqual(params['code_challenge_method'], 'S256')
        self.assertEqual(params['client_id'], 'odoo-client')
        self.assertIn('code_challenge', params)
        state = json.loads(params['state'])
        self.assertEqual(state['p'], self.provider.id)
        # the signed nonce the verifier is derived from on the callback
        self.assertIn('n', state)

    def test_signin(self):
        """Happy path: the callback trades the code for an access token and
        signs the user in with it.
        """
        params = self._authorization_params()
        response, exchange = self._callback(code='the-code', state=params['state'])
        # redirected into the app, not back to the login page with an error
        self.assertEqual(response.status_code, 303)
        self.assertNotIn('oauth_error', response.headers['Location'])

        # the verifier sent to the token endpoint matches the challenge
        # sent along the authorization request: this is what a real
        # provider checks before handing over the token
        code, code_verifier, redirect_uri = exchange.call_args.args
        self.assertEqual(code, 'the-code')
        self.assertEqual(self.provider._get_code_challenge(code_verifier), params['code_challenge'])
        # RFC 6749 §4.1.3: same redirect uri on both requests
        self.assertEqual(redirect_uri, params['redirect_uri'])
        # the rest of the sign in is the implicit flow one, fed with the
        # access token obtained from the exchange
        self.assertEqual(self.user.oauth_access_token, 'tok')

    def test_signin_rejected(self):
        """Callbacks that may not be trusted, or that carry no code, send the
        user back to the login page with an error, without ever reaching the
        token endpoint.
        """
        params = self._authorization_params()
        state = json.loads(params['state'])
        # genuine signature, but in a state it was not issued for (here an
        # open redirect attempt)
        tampered = dict(state, r='https%3A%2F%2Fevil.example.com')
        # a state forged without the signature, e.g. built by an attacker
        unsigned = {key: value for key, value in state.items() if key != 'n'}
        cases = {
            'tampered state': {'code': 'the-code', 'state': json.dumps(tampered)},
            'unsigned state': {'code': 'the-code', 'state': json.dumps(unsigned)},
            'no code': {'state': params['state']},
            # the user declined the consent screen of the provider
            'user refused': {'error': 'access_denied', 'state': params['state']},
        }
        for case, callback_params in cases.items():
            with self.subTest(case):
                response, exchange = self._callback(**callback_params)
                self.assertEqual(response.status_code, 303)
                self.assertIn('oauth_error=2', response.headers['Location'])
                exchange.assert_not_called()
