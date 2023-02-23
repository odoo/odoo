# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests.common import HttpCase
from werkzeug.urls import url_parse


class TestResetPassword(HttpCase):

    def test_reset_password(self):
        """
            Test that first signup link and password reset link are different to accomodate for the different behaviour
            on first signup if a password is already set user is redirected to login page when accessing that link again
            'signup_email' is used in the web controller (web_auth_reset_password) to detect this behaviour
        """
        test_user = self.env['res.users'].create({
            'login': 'test',
            'name': 'The King',
            'email': 'noop@example.com',
        })

        self.assertEqual(test_user.email, url_parse(test_user.with_context(create_user=True).signup_url).decode_query()["signup_email"], "query must contain 'signup_email'")

        # Invalidate signup_url to skip signup process
        self.env.invalidate_all()
        test_user.action_reset_password()

        self.assertNotIn("signup_email", url_parse(test_user.signup_url).decode_query(), "query should not contain 'signup_email'")
