# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.api import SUPERUSER_ID
from odoo.tests import HttpCase, new_test_user, tagged


@tagged('post_install', '-at_install')
class TestAuthOauthSessions(HttpCase):

    def test_oauth_login_from_new_device_keeps_other_sessions_alive(self):
        provider = self.env['auth.oauth.provider'].create({
            'name': 'Test Provider',
            'auth_endpoint': 'https://example.com/auth',
            'validation_endpoint': 'https://example.com/validate',
            'body': 'Login with Test Provider',
        })
        new_test_user(
            self.env, login='oauth_user', password='test_babar',
            oauth_provider_id=provider.id,
            oauth_uid='external-uid-1',
            oauth_access_token='token-from-device-a',
        )

        self.authenticate('oauth_user', 'test_babar')
        self.assertTrue(self.url_open('/web').url.endswith('/web'))

        # Simulates a second device logging in via OAuth.
        validation = {'user_id': 'external-uid-1'}
        params = {'access_token': 'token-from-device-b'}
        login = self.env['res.users'].with_user(SUPERUSER_ID)._auth_oauth_signin(
            provider.id, validation, params,
        )
        self.assertEqual(login, 'oauth_user')
        self.env.flush_all()

        self.assertTrue(
            self.url_open('/web').url.endswith('/web'),
            "OAuth login from a new device must not invalidate other sessions",
        )
