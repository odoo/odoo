# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import UserError
from odoo.tests import HttpCase

class TestSpamPasswordReset(HttpCase):

    def setUp(self):
        super(TestSpamPasswordReset, self).setUp()
        res_config = self.env['res.config.settings']
        self.default_values = res_config.default_get(list(res_config.fields_get()))

    def _activate_free_signup(self):
        self.default_values.update({'auth_signup_uninvited': 'b2c'})

    def _get_free_signup_url(self):
        return '/web/signup'

    def test_password_reset_spam(self):
        """
        Check if a new user can spam the password reset
        """

        # Create a new user (automatically sends a password reset)
        new_user = self.env['res.users'].create({
            'login': 'test',
            'name': 'toto',
            'email': 'toto@example.com',
        })

        # Check if the user can ask for two more password resets after the one sent at its creation
        new_user.action_reset_password()
        new_user.action_reset_password()
        # Check if the user is limited at the fourth password reset
        with self.assertRaises(UserError):
            new_user.action_reset_password()
