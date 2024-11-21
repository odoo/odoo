# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from unittest.mock import patch
from odoo.exceptions import UserError
from odoo.addons.mail.models.mail_mail import MailDeliveryException
from odoo.tests.common import HttpCase
from werkzeug.urls import url_parse


class TestResetPassword(HttpCase):

    @classmethod
    def setUpClass(cls):
        super(TestResetPassword, cls).setUpClass()
        cls.test_user = cls.env['res.users'].create({
            'login': 'test',
            'name': 'The King',
            'email': 'noop@example.com',
        })

    def test_reset_password(self):
        """
            Test that first signup link and password reset link are different to accomodate for the different behaviour
            on first signup if a password is already set user is redirected to login page when accessing that link again
            'signup_email' is used in the web controller (web_auth_reset_password) to detect this behaviour
        """

        self.assertEqual(self.test_user.email, url_parse(self.test_user.with_context(create_user=True).partner_id._get_signup_url()).decode_query()["signup_email"], "query must contain 'signup_email'")

        # Invalidate signup_url to skip signup process
        self.env.invalidate_all()
        self.test_user.action_reset_password()

        self.assertNotIn("signup_email", url_parse(self.test_user.partner_id._get_signup_url()).decode_query(), "query should not contain 'signup_email'")

    @patch('odoo.addons.mail.models.mail_mail.MailMail.send')
    def test_reset_password_mail_server_error(self, mock_send):
        """
        Test that action_reset_password() method raises UserError and _action_reset_password() method raises MailDeliveryException.

        action_reset_password() method attempts to reset the user's password by executing the private method _action_reset_password().
        If any errors occur during the password reset process, a UserError exception is raised with the following behavior:

        - If a MailDeliveryException is caught and the exception's second argument is a ConnectionRefusedError,
        a UserError is raised with the message "Could not contact the mail server, please check your outgoing email server configuration".
        This indicates that the error is related to the mail server and the user should verify their email server settings.

        - If a MailDeliveryException is caught but the exception's second argument is not a ConnectionRefusedError,
        a UserError is raised with the message "There was an error when trying to deliver your Email, please check your configuration".
        This indicates that there was an error during the email delivery process, and the user should review their email configuration.

        Note: The _action_reset_password() method, marked as private with the underscore prefix, performs the actual password reset logic
        and the original MailDeliveryException occurs from this method.
        """

        mock_send.side_effect = MailDeliveryException(
            "Unable to connect to SMTP Server",
            ConnectionRefusedError("111, 'Connection refused'"),
        )
        with self.assertRaises(UserError) as cm1:
            self.test_user.action_reset_password()

        self.assertEqual(
            str(cm1.exception),
            "Could not contact the mail server, please check your outgoing email server configuration",
        )

        mock_send.side_effect = MailDeliveryException(
            "Unable to connect to SMTP Server",
            ValueError("[Errno -2] Name or service not known"),
        )
        with self.assertRaises(UserError) as cm2:
            self.test_user.action_reset_password()

        self.assertEqual(
            str(cm2.exception),
            "There was an error when trying to deliver your Email, please check your configuration",
        )

        # To check private method _action_reset_password() raises MailDeliveryException when there is no valid smtp server
        with self.assertRaises(MailDeliveryException):
            self.test_user._action_reset_password()
