import json
from unittest.mock import patch
from urllib.parse import urlencode

from odoo.tests import HttpCase
from odoo.tools import hash_sign


class TestAuthOAuthSignup(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.implicit, cls.pkce = cls.env['auth.oauth.provider'].create([{
            'name': flow,
            'body': flow,
            'flow': flow,
            'enabled': True,
            'client_id': 'odoo-client',
            'auth_endpoint': f'https://{flow}.example.com/authorize',
            'token_endpoint': f'https://{flow}.example.com/token',
            'validation_endpoint': f'https://{flow}.example.com/userinfo',
        } for flow in ('implicit', 'pkce')])

    def test_oauth_signup_does_not_clear_caches(self):
        from odoo.orm.environments import Transaction  # noqa: PLC0415

        self.env['ir.config_parameter'].sudo().set_str('auth_signup.invitation_scope', 'b2c')
        provider = self.env.ref('auth_oauth.provider_openerp')
        validation = {
            'user_id': 'cache_oauth_uid',
            'email': 'cache_oauth@example.com',
            'name': 'cache oauth',
        }

        self.authenticate(None, None)
        self.opener.cookies['tz'] = 'Europe/Brussels'
        params = {
            'access_token': 'cache_oauth_token',
            'state': json.dumps({'d': self.env.cr.dbname, 'p': provider.id}),
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
