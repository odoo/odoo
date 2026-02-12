# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from contextlib import contextmanager
from unittest.mock import patch

import odoo
from odoo import http
from odoo.addons.base.tests.common import HttpCaseWithUserPortal, HttpCaseWithUserDemo
from odoo.exceptions import AccessError, UserError

from datetime import datetime, timedelta
from odoo.tools import mute_logger

class TestAuthSignupFlow(HttpCaseWithUserPortal, HttpCaseWithUserDemo):

    def setUp(self):
        super(TestAuthSignupFlow, self).setUp()
        res_config = self.env['res.config.settings']
        self.default_values = res_config.default_get(list(res_config.fields_get()))

    def _activate_free_signup(self):
        self.default_values.update({'auth_signup_uninvited': 'b2c'})

    def _get_free_signup_url(self):
        return '/web/signup'

    @contextmanager
    def patch_captcha_signup(self):
        def _verify_request_recaptcha_token(self, captcha):
            if captcha != 'signup':
                raise UserError("CAPTCHA test")
        with patch.object(self.env.registry['ir.http'], '_verify_request_recaptcha_token', _verify_request_recaptcha_token):
            yield

    def test_confirmation_mail_free_signup(self):
        """
        Check if a new user is informed by email when he is registered
        """

        # Activate free signup
        self._activate_free_signup()

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

        # Override unlink to not delete the email if the send works.
        with patch.object(odoo.addons.mail.models.mail_mail.MailMail, 'unlink', lambda self: None), self.patch_captcha_signup():
            # Call the controller
            url_free_signup = self._get_free_signup_url()
            response = self.url_open(url_free_signup, data=payload)
            self.assertIn('/web/login_successful?account_created=True', response.url)
            # Check if an email is sent to the new userw
            new_user = self.env['res.users'].search([('name', '=', name)])
            self.assertTrue(new_user)
            mail = self.env['mail.message'].search([('message_type', '=', 'email_outgoing'), ('model', '=', 'res.users'), ('res_id', '=', new_user.id)], limit=1)
            self.assertTrue(mail, "The new user must be informed of his registration")

    def test_compute_signup_url(self):
        user = self.user_demo
        user.group_ids -= self.env.ref('base.group_partner_manager')

        partner = self.partner_portal
        partner.signup_prepare()

        with self.assertRaises(AccessError):
            partner.with_user(user.id)._get_signup_url()

    def test_copy_multiple_users(self):
        users = self.env['res.users'].create([
            {'login': 'testuser1', 'name': 'Test User 1', 'email': 'test1@odoo.com'},
            {'login': 'testuser2', 'name': 'Test User 2', 'email': 'test2@odoo.com'},
        ])
        initial_user_count = self.env['res.users'].search_count([])
        users.copy()
        self.assertEqual(
            self.env['res.users'].search_count([]),
            initial_user_count + len(users)
        )

    def test_notify_unregistered(self):
        users = self.env['res.users'].create([
            {'login': 'testuser1', 'name': 'Test User 1', 'email': 'test1@odoo.com'},
            {'login': 'testuser2', 'name': 'Test User 2', 'email': 'test2@odoo.com'},
        ])
        for u in users:
            u.create_date = datetime.now() - timedelta(days=5, minutes=10)
        with self.registry.cursor() as cr:
            users.with_env(users.env(cr=cr)).send_unregistered_user_reminder(after_days=5, batch_size=100)

    @mute_logger('odoo.sql_db', 'odoo.addons.auth_signup.controllers.main')
    def test_signup_with_similar_user(self):
        self._activate_free_signup()

        def web_signup(url, data, login):
            self.authenticate(None, None)
            data.update({'login': login, 'csrf_token': http.Request.csrf_token(self)})
            res = self.url_open(url, data=data)
            self.logout()
            return res.content

        # Values from login form
        payload = {
            'name': 'user',
            'password': 'mypassword',
            'confirm_password': 'mypassword',
        }

        url_free_signup = self._get_free_signup_url()

        # Signup a first time with a unique login
        res = web_signup(url_free_signup, payload, 'Unique@Example.com')
        self.assertIn(b'You are logged in.', res)
        # Make sure the created user has login in lowercase
        self.assertEqual(len(self.env['res.users'].search([('login', '=', 'unique@example.com')])), 1)

        # Try to signup with similar logins (case insensitive)
        similar_logins = ['Unique@example.com', 'UNIQUE@example.com', '  unique@Example.com  ']
        for login in similar_logins:
            with self.subTest(login=login):
                res = web_signup(url_free_signup, payload, login)
                self.assertIn(b'Another user is already registered using this email address.', res)
