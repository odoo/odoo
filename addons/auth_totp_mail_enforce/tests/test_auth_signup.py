# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.addons.base.tests.common import HttpCaseWithUserDemo, HttpCaseWithUserPortal
from odoo.tests import tagged


@tagged('post_install', '-at_install', 'assets_bundle')
class TestAuthSignupFlow(HttpCaseWithUserPortal, HttpCaseWithUserDemo):

    def setUp(self):
        super().setUp()
        res_config = self.env['res.config.settings']
        self.default_values = res_config.default_get(list(res_config.fields_get()))

    def _activate_free_signup(self):
        self.default_values.update({'auth_signup_uninvited': 'b2c'})

    def _enforce_2fa(self):
        self.default_values.update({'auth_totp.policy': 'all_required'})

    def test_signup_with_2fa_enforced(self):
        """
        Check that registration cleanly succeeds with 2FA enabled and enforced
        """

        self._activate_free_signup()
        self._enforce_2fa()

        # Get csrf_token
        self.authenticate(None, None)
        csrf_token = http.Request.csrf_token(self)

        # Values from login form
        name = 'toto'
        payload = {
            'login': 'toto@example.com',
            'name': name,
            'password': 'mypassword',
            'confirm_password': 'mypassword',
            'csrf_token': csrf_token,
        }
        response = self.url_open('/web/signup', data=payload)
        new_user = self.env['res.users'].search([('name', '=', name)])
        self.assertTrue(new_user)
        self.assertEqual(response.status_code, 200, "Signup request should succeed with a 200")
