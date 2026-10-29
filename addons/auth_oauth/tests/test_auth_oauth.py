import json
from unittest.mock import patch
from urllib.parse import urlencode

from odoo.tests import HttpCase


class TestAuthOAuthSignup(HttpCase):

    def test_oauth_signup_does_not_clear_caches(self):
        self.env['ir.config_parameter'].sudo().set_param('auth_signup.invitation_scope', 'b2c')
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
            patch.object(self.env.registry, 'clear_cache', wraps=self.env.registry.clear_cache) as clear_cache
        ):
            self.url_open(f'/auth_oauth/signin?{urlencode(params)}', allow_redirects=False)

        new_user = self.env['res.users'].search([('oauth_uid', '=', 'cache_oauth_uid')])
        self.assertTrue(new_user)
        self.assertEqual(new_user.tz, 'Europe/Brussels')
        self.assertTrue(new_user.login_date)
        clear_cache.assert_not_called()
