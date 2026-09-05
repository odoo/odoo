from unittest.mock import patch

from odoo.tests import HttpCase, tagged

OAUTH_BASE_URL = 'https://oauth.example.com'


@tagged('post_install', '-at_install')
class TestOauthServerMetadata(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.resource = cls.env['oauth.resource'].create({
            'name': 'testrs', 'label': 'Test Resource', 'access_token_scope': 'testrs',
        })

    def test_protected_resource_metadata(self):
        with patch(
            'odoo.addons.auth_oauth_server_base.controllers.oauth_server_controller_base.oauth_base_url',
            return_value=OAUTH_BASE_URL
        ):
            response = self.url_open('/.well-known/oauth-protected-resource/testrs')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), {
                'resource': f'{OAUTH_BASE_URL}/testrs',
                'authorization_servers': [f'{OAUTH_BASE_URL}/oauth/testrs'],
            })

    def test_authorization_server_metadata(self):
        with patch(
            'odoo.addons.auth_oauth_server_base.controllers.oauth_server_controller_base.oauth_base_url',
            return_value=OAUTH_BASE_URL
        ):
            response = self.url_open('/.well-known/oauth-authorization-server/oauth/testrs')
            self.assertEqual(response.status_code, 200)

            expected_metadata = {
                'issuer': f'{OAUTH_BASE_URL}/oauth/testrs',
                'authorization_endpoint': f'{OAUTH_BASE_URL}/oauth/authorize',
                'token_endpoint': f'{OAUTH_BASE_URL}/oauth/token',
                'revocation_endpoint': f'{OAUTH_BASE_URL}/oauth/revoke',
                'response_types_supported': ['code'],
                'grant_types_supported': ['authorization_code', 'refresh_token'],
                'code_challenge_methods_supported': ['S256'],
                'token_endpoint_auth_methods_supported': ['none', 'client_secret_basic', 'client_secret_post'],
                'scopes_supported': ['testrs'],
            }
            self.assertEqual({key: response.json().get(key) for key in expected_metadata}, expected_metadata)

    def test_metadata_of_an_unknown_resource_is_not_served(self):
        response = self.url_open('/.well-known/oauth-protected-resource/unknown-resource')
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()['error'], 'invalid_resource')
        self.assertEqual(response.json()['error_description'], "OAuth resource unknown-resource isn't available")
