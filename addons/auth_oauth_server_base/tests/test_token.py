from unittest.mock import patch

from odoo.tests import HttpCase, tagged

from odoo.addons.auth_oauth_server_base.controllers.oauth_server_controller_base import OauthServerControllerBase

CLIENT_REDIRECT_URI = 'https://client.example.com/callback'


@tagged('post_install', '-at_install')
class TestToken(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.resource = cls.env['oauth.resource'].create({
            'name': 'testrs', 'label': 'Test Resource', 'access_token_scope': 'testrs',
        })

    def test_oauth_token_requires_client_credentials(self):
        client_data = self.env['oauth.client']._register_client(
            resource=self.resource, client_name='Test Client',
            redirect_uris=[CLIENT_REDIRECT_URI], client_type='confidential',
        )

        token_result = {
            'access_token': 'access_token', 'refresh_token': 'refresh_token',
            'token_type': 'Bearer', 'expires_in': 600, 'scope': 'testrs',
        }
        with patch.object(OauthServerControllerBase, '_redeem_authorization_code', return_value=token_result):
            response = self.url_open('/oauth/token', data={
                'grant_type': 'authorization_code', 'code': 'authorization_code',
                'client_id': client_data['client_id'], 'client_secret': 'wrong-secret',
                'redirect_uri': CLIENT_REDIRECT_URI, 'code_verifier': 'code_verifier',
            })
            self.assertEqual(response.status_code, 401, response.text)
            self.assertEqual(response.json()['error'], 'invalid_client')
            self.assertEqual(response.json()['error_description'], "Invalid client credentials")

            response = self.url_open('/oauth/token', data={
                'grant_type': 'authorization_code', 'code': 'authorization_code',
                'client_id': client_data['client_id'], 'client_secret': client_data['client_secret'],
                'redirect_uri': CLIENT_REDIRECT_URI, 'code_verifier': 'code_verifier',
            })
            self.assertEqual(response.json(), token_result)
