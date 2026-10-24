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
        self.env['mail.mail'].search([]).sudo().unlink()
        with (
            patch.object(self.env.registry['mail.mail'], 'unlink', lambda m: None),
        ):
            response = self.url_open('/web/signup', data=payload)
            new_user = self.env['res.users'].search([('name', '=', name)])
            self.assertTrue(new_user)
            self.assertEqual(response.status_code, 200, "Signup request should succeed with a 200")
            mails = self.env['mail.mail'].search([])
            expected_subjects = {
                'Your two-factor authentication code',
                'New Connection to your Account',
                f'Welcome to {self.env.company.name}!',
            }
            subjects = mails.mapped('subject')
            # Ensure no mail is duplicated
            self.assertEqual(set(subjects), expected_subjects)
            self.assertEqual(len(subjects), len(expected_subjects))

    def test_password_reset_with_2fa_enforced(self):
        user = self.user_demo

        self.authenticate(None, None)
        csrf_token = http.Request.csrf_token(self)

        payload = {
            'login': user.login,
            'name': user.name,
            'password': 'mypassword',
            'confirm_password': 'mypassword',
            'csrf_token': csrf_token,
        }
        user.partner_id.signup_prepare(signup_type="reset")
        url = user.partner_id._get_signup_url()
        self.env['mail.mail'].search([]).sudo().unlink()
        with (
            patch.object(self.env.registry['mail.mail'], 'unlink', lambda m: None),
        ):
            response = self.url_open(url, data=payload)
            self.assertEqual(response.status_code, 200, "Password reset should succeed with a 200")
            mails = self.env['mail.mail'].search([])
            expected_subjects = {
                'Your two-factor authentication code',
                'New Connection to your Account',
                'Security Update: Password Changed',
            }
            subjects = mails.mapped('subject')
            # Ensure no mail is duplicated
            self.assertEqual(set(subjects), expected_subjects)
            self.assertEqual(len(subjects), len(expected_subjects))
