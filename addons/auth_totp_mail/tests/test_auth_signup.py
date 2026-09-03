# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch
from odoo.addons.base.tests.common import HttpCaseWithUserDemo, HttpCaseWithUserPortal

from odoo import http
from odoo.tests.common import tagged


@tagged('post_install', '-at_install')
class TestAuthSignupFlowWith2faEnforced(HttpCaseWithUserPortal, HttpCaseWithUserDemo):

    def setUp(self):
        super().setUp()
        self.env['res.config.settings'].create(
            {
                # Activate free signup
                'auth_signup_uninvited': 'b2c',
                # Enforce 2FA for all users
                'auth_totp_enforce': True,
                'auth_totp_policy': 'all_required',
            }
        ).execute()

    def test_signup_with_2fa_enforced(self):
        """
        Check that registration cleanly succeeds with 2FA enabled and enforced
        """
        # ensure the company has an email, otherwise the test fails in no_demo
        # because there's no source address
        self.env.company.email = "mycompany@example.com"

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

    def test_alert_new_device_lang(self):
        self.env['res.lang']._activate_lang('fr_BE')
        user = self.user_demo
        user.lang = 'fr_BE'

        view = self.env.ref('mail.account_security_alert')
        # Disable inherited template to avoid error
        inherit_views = self.env['ir.ui.view'].search([
            ('inherit_id', '=', view.id),
        ])
        inherit_views.active = False
        view.with_context(lang='en_US').arch = '<div>mail in EN</div>'
        view.update_field_translations('arch_db', {
           'fr_BE': {
                'mail in EN': 'email en FR',
            }
        })

        self.authenticate(None, None)
        csrf_token = http.Request.csrf_token(self)
        payload = {
            'login': 'demo',
            'password': 'demo',
            'csrf_token': csrf_token,
        }
        self.env['mail.mail'].search([]).sudo().unlink()
        with (
            patch.object(self.env.registry['mail.mail'], 'unlink', lambda m: None),
            patch.object(self.env.registry['res.users'], '_mfa_type', lambda u: 'totp'),
        ):
            res = self.url_open('/web/login', data=payload)
            self.assertEqual(res.status_code, 200)
            mail = self.env['mail.mail'].search([], limit=1)
            self.assertIn('<div>email en FR</div>', mail.body_html)
