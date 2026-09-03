from unittest.mock import patch

from odoo.tests import HttpCase, tagged

from odoo.addons.auth_oauth_server_base.controllers.oauth_server_controller_base import OauthServerControllerBase

CLIENT_REDIRECT_URI = 'https://client.example.com/callback'


@tagged('post_install', '-at_install')
class TestRevoke(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.resource = cls.env['oauth.resource'].create({
            'name': 'testrs', 'label': 'Test Resource', 'access_token_scope': 'testrs',
        })

    def test_revoke_with_unknown_client_is_rejected(self):
        public_client = self.env['oauth.client']._register_client(
            resource=self.resource, client_name='Test Client',
            redirect_uris=[CLIENT_REDIRECT_URI], client_type='public',
        )
        confidential_client = self.env['oauth.client']._register_client(
            resource=self.resource, client_name='Test Client',
            redirect_uris=[CLIENT_REDIRECT_URI], client_type='confidential',
        )

        with patch.object(OauthServerControllerBase, '_handle_revoke_request') as mock_handle_revoke:
            response = self.url_open('/oauth/revoke', data={
                'token': 'some-token', 'client_id': 'unknown_client_id',
            })
            self.assertEqual(response.status_code, 401, response.text)
            self.assertEqual(response.json()['error'], 'invalid_client')
            self.assertEqual(response.json()['error_description'], "Invalid client credentials")
            mock_handle_revoke.assert_not_called()

            response = self.url_open('/oauth/revoke', data={
                'token': 'some-token', 'client_id': public_client['client_id'],
            })
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json(), {})
            mock_handle_revoke.assert_called_once()
            mock_handle_revoke.reset_mock()

            response = self.url_open('/oauth/revoke', data={
                'token': 'some-token', 'client_id': confidential_client['client_id'],
            })
            self.assertEqual(response.status_code, 401, response.text)
            self.assertEqual(response.json()['error'], 'invalid_client')
            self.assertEqual(response.json()['error_description'], "Invalid client credentials")
            mock_handle_revoke.assert_not_called()

            response = self.url_open('/oauth/revoke', data={
                'token': 'some-token', 'client_id': confidential_client['client_id'],
                'client_secret': confidential_client['client_secret'],
            })
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json(), {})
            mock_handle_revoke.assert_called_once()
