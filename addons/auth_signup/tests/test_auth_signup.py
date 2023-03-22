# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

import odoo
from odoo.tests import HttpCase
from odoo import http
from odoo.exceptions import AccessError

class TestAuthSignupFlow(HttpCase):

    def setUp(self):
        super(TestAuthSignupFlow, self).setUp()
        res_config = self.env['res.config.settings']
        self.default_values = res_config.default_get(list(res_config.fields_get()))

    def _activate_free_signup(self):
        self.default_values.update({'auth_signup_uninvited': 'b2c'})

    def _activate_confirmation_mail_on_signup(self):
        self.default_values.update({'auth_signup_confirmation_mail':'True'})

    def _get_free_signup_url(self):
        return '/web/signup'

    def test_confirmation_mail_free_signup(self):
        """
        Check if a new user is informed by email when he is registered
        """

        # Activate free signup
        self._activate_free_signup()

        # Activate confirmation mail on signup
        self._activate_confirmation_mail_on_signup()

        # Get csrf_token
        self.authenticate(None, None)
        csrf_token = http.Request.csrf_token(self)

        # Values from login form
        name = 'toto'
        address = 'toto@example.com'
        payload = {
            'login': address,
            'name': name,
            'password': 'mypassword',
            'confirm_password': 'mypassword',
            'csrf_token': csrf_token,
        }

        # Override unlink to not delete the email if the send works.
        with patch.object(odoo.addons.mail.models.mail_mail.MailMail, 'unlink', lambda self: None):
            # Call the controller
            url_free_signup = self._get_free_signup_url()
            self.url_open(url_free_signup, data=payload)
            # Check if a res_users_signup is created and gets his confirmation mail
            new_user = self.env['res.users.signup'].search([('name', '=', name)])
            self.assertTrue(new_user)
            mail = self.env['mail.message'].search([('message_type', '=', 'email'), ('subject', '=', 'Your confirmation token for registration')], limit=1)
            if not mail:
                mail = self.env['mail.mail'].search([('email_to', '=', address)], limit=1)
            self.assertTrue(mail, "The new user must receive the confirmation token")
            # Check that the email contains the token
            body = mail['body_html']
            self.assertNotEqual(body.find("?token="), -1, "The mail must contain the token")
            # Confirm the creation of the res_user with the informations of the res_users_signup and check it
            new_user.confirm_account()
            final_user = self.env['res.users'].search([('name', '=', name)])
            self.assertTrue(final_user)
            # Check that res_users_signup has no entry for the test user anymore (unlink worked)
            new_user = self.env['res.users.signup'].search([('name', '=', name)])
            self.assertFalse(new_user)

    def test_compute_signup_url(self):
        user = self.env.ref('base.user_demo')
        user.groups_id -= self.env.ref('base.group_partner_manager')

        partner = self.env.ref('base.partner_demo_portal')
        partner.signup_prepare()

        with self.assertRaises(AccessError):
            partner.with_user(user.id).signup_url
