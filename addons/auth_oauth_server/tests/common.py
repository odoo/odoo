import json
from urllib.parse import parse_qs, urlsplit

from odoo.tests import HttpCase, new_test_user

from odoo.addons.auth_oauth_server_base.utils.oauth_utils import challenge_from_verifier

REDIRECT_URI = 'https://client.example.com/callback'


class OauthServerCommon(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.resource = cls.env['oauth.resource'].create({
            'name': 'testrs',
            'label': 'Test Resource',
            'access_token_scope': 'testrs',
            'allowed_group_ids': [cls.env.ref('base.group_user').id],
        })
        cls.internal_user = new_test_user(cls.env, login='internal_user', groups='base.group_user')
        cls.portal_user = new_test_user(cls.env, login='portal_user', groups='base.group_portal')

    def _register_client(self, redirect_uris=(REDIRECT_URI,), resource='testrs', auth_method='client_secret_post'):
        params = {
            'client_name': 'Test Client',
            'redirect_uris': list(redirect_uris),
        }
        if auth_method:
            params['token_endpoint_auth_method'] = auth_method
        response = self.url_open(
            f'/oauth/register/{resource}',
            data=json.dumps(params),
            headers={'Content-Type': 'application/json'}
        )
        return response.json()

    def _authorize(self, allow_redirects=True, **params_overrides):
        params = {
            'redirect_uri': REDIRECT_URI,
            'response_type': 'code',
            'code_challenge': challenge_from_verifier(self._get_verifier()),
            'code_challenge_method': 'S256',
            'state': 'xyz',
            **params_overrides,
        }
        if not params.get('client_id'):
            params['client_id'] = self._register_client()['client_id']
        return self.url_open('/oauth/authorize', params=params, allow_redirects=allow_redirects)

    def _submit_consent(self, **params_overrides):
        params = {
            'redirect_uri': REDIRECT_URI,
            'response_type': 'code',
            'code_challenge': challenge_from_verifier(self._get_verifier()),
            'code_challenge_method': 'S256',
            'state': 'xyz',
            'allow': 'true',
            'csrf_token': self.csrf_token(),
            **params_overrides,
        }
        if not params.get('client_id'):
            params['client_id'] = self._register_client()['client_id']
        return self.url_open('/oauth/authorize/submit_consent', data=params, allow_redirects=False)

    def _generate_auth_code(self, **params_overrides):
        consent_response = self._submit_consent(**params_overrides)
        location = consent_response.headers['Location']
        return parse_qs(urlsplit(location).query)['code'][0]

    def _generate_access_token(self, code, client_id=None, client_secret=None, headers=None, **params_overrides):
        params = {
            'redirect_uri': REDIRECT_URI,
            'code_verifier': self._get_verifier(),
            'code': code,
            'grant_type': 'authorization_code',
            **params_overrides,
        }
        if client_id:
            params['client_id'] = client_id
        if client_secret:
            params['client_secret'] = client_secret

        return self.url_open('/oauth/token', data=params, headers=headers)

    def _redeem_refresh_token(self, refresh_token, client_id, client_secret):
        return self.url_open(
            '/oauth/token',
            data={
                'grant_type': 'refresh_token',
                'refresh_token': refresh_token,
                'client_id': client_id,
                'client_secret': client_secret,
            }
        )

    def _revoke(self, token, client_id, client_secret):
        return self.url_open(
            '/oauth/revoke',
            data={
                'token': token,
                'client_id': client_id,
                'client_secret': client_secret,
            }
        )

    def _get_verifier(self):
        return 'a' * 64
