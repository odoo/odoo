# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.addons.base.tests.common import MockSmtplibCase
from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger


class TestIrMailServer(TransactionCase, MockSmtplibCase):

    def setUp(self):
        self._init_mail_servers()

    def _build_email(self, mail_from, return_path=None):
        return self.env['ir.mail_server'].build_email(
            email_from=mail_from,
            email_to='dest@example-é.com',
            subject='subject', body='body',
            headers={'Return-Path': return_path} if return_path else None
        )

    def test_match_from_filter(self):
        """Test the from_filter field on the "ir.mail_server"."""
        match_from_filter = self.env['ir.mail_server']._match_from_filter

        # Should match
        tests = [
            ('admin@mail.example.com', 'mail.example.com'),
            ('admin@mail.example.com', 'mail.EXAMPLE.com'),
            ('admin@mail.example.com', 'admin@mail.example.com'),
            ('admin@mail.example.com', False),
            ('"fake@test.com" <admin@mail.example.com>', 'mail.example.com'),
            ('"fake@test.com" <ADMIN@mail.example.com>', 'mail.example.com'),
        ]
        for email, from_filter in tests:
            self.assertTrue(match_from_filter(email, from_filter))

        # Should not match
        tests = [
            ('admin@mail.example.com', 'test@mail.example.com'),
            ('admin@mail.example.com', 'test.com'),
            ('admin@mail.example.com', 'mail.éxample.com'),
            ('admin@mmail.example.com', 'mail.example.com'),
            ('admin@mail.example.com', 'mmail.example.com'),
            ('"admin@mail.example.com" <fake@test.com>', 'mail.example.com'),
        ]
        for email, from_filter in tests:
            self.assertFalse(match_from_filter(email, from_filter))

    @mute_logger('odoo.models.unlink')
    def test_mail_server_priorities(self):
        """Test if we choose the right mail server to send an email.

        Priorities are
        1. Forced mail server (e.g.: in mass mailing)
            - If the "from_filter" of the mail server match the notification email
              use the notifications email in the "From header"
            - Otherwise spoof the "From" (because we force the mail server but we don't
              know which email use to send it)
        2. A mail server for which the "from_filter" match the "From" header
        3. A mail server for which the "from_filter" match the domain of the "From" header
        4. The mail server used for notifications
        5. A mail server without "from_filter" (and so spoof the "From" header because we
           do not know for which email address it can be used)
        """
        # sanity checks
        self.assertTrue(self.env['ir.mail_server']._get_default_from_address(), 'Notifications email must be set for testing')
        self.assertTrue(self.env['ir.mail_server']._get_default_bounce_address(), 'Bounce email must be set for testing')

        mail_server, mail_from = self.env['ir.mail_server']._find_mail_server(email_from='specific_user@test.com')
        self.assertEqual(mail_server, self.server_user)
        self.assertEqual(mail_from, 'specific_user@test.com')

        mail_server, mail_from = self.env['ir.mail_server']._find_mail_server(email_from='"Name name@strange.name" <specific_user@test.com>')
        self.assertEqual(mail_server, self.server_user, 'Must extract email from full name')
        self.assertEqual(mail_from, '"Name name@strange.name" <specific_user@test.com>', 'Must keep the given mail from')

        # Should not be case sensitive
        mail_server, mail_from = self.env['ir.mail_server']._find_mail_server(email_from='specific_user@test.com')
        self.assertEqual(mail_server, self.server_user, 'Mail from is case insensitive')
        self.assertEqual(mail_from, 'specific_user@test.com', 'Should not change the mail from')

        mail_server, mail_from = self.env['ir.mail_server']._find_mail_server(email_from='unknown_email@test.com')
        self.assertEqual(mail_server, self.server_domain)
        self.assertEqual(mail_from, 'unknown_email@test.com')

        # Cover a different condition that the "email case insensitive" test
        mail_server, mail_from = self.env['ir.mail_server']._find_mail_server(email_from='unknown_email@TEST.COM')
        self.assertEqual(mail_server, self.server_domain, 'Domain is case insensitive')
        self.assertEqual(mail_from, 'unknown_email@TEST.COM', 'Domain is case insensitive')

        mail_server, mail_from = self.env['ir.mail_server']._find_mail_server(email_from='"Test" <test@unknown_domain.com>')
        self.assertEqual(mail_server, self.server_notification, 'Should take the notification email')
        self.assertEqual(mail_from, 'notifications@test.com')

        # remove the notifications email to simulate a mis-configured Odoo database
        # so we do not have the choice, we have to spoof the FROM
        # (otherwise we can not send the email)
        self.env['ir.config_parameter'].sudo().set_param('mail.catchall.domain', False)
        with mute_logger('odoo.addons.base.models.ir_mail_server'):
            mail_server, mail_from = self.env['ir.mail_server']._find_mail_server(email_from='test@unknown_domain.com')
            self.assertEqual(mail_server.from_filter, False, 'No notifications email set, must be forced to spoof the FROM')
            self.assertEqual(mail_from, 'test@unknown_domain.com')

    @mute_logger('odoo.models.unlink')
    def test_mail_server_send_email(self):
        IrMailServer = self.env['ir.mail_server']
        default_bounce_adress = self.env['ir.mail_server']._get_default_bounce_address()

        # A mail server is configured for the email
        with self.mock_smtplib_connection():
            message = self._build_email(mail_from='specific_user@test.com')
            IrMailServer.send_email(message)

        self.assertEqual(len(self.emails), 1)

        self.assert_email_sent_smtp(
            smtp_from='specific_user@test.com',
            message_from='specific_user@test.com',
            from_filter='specific_user@test.com',
        )

        # No mail server are configured for the email address,
        # so it will use the notifications email instead and encapsulate the old email
        with self.mock_smtplib_connection():
            message = self._build_email(mail_from='"Name" <test@unknown_domain.com>')
            IrMailServer.send_email(message)

        self.assertEqual(len(self.emails), 1)

        self.assert_email_sent_smtp(
            smtp_from='notifications@test.com',
            message_from='"Name (test@unknown_domain.com)" <notifications@test.com>',
            from_filter='notifications@test.com',
        )

        # Same situation, but the original email has no name part
        with self.mock_smtplib_connection():
            message = self._build_email(mail_from='test@unknown_domain.com')
            IrMailServer.send_email(message)

        self.assertEqual(len(self.emails), 1)

        self.assert_email_sent_smtp(
            smtp_from='notifications@test.com',
            message_from='"test@unknown_domain.com" <notifications@test.com>',
            from_filter='notifications@test.com',
        )

        # A mail server is configured for the entire domain name, so we can use the bounce
        # email address because the mail server supports it
        with self.mock_smtplib_connection():
            message = self._build_email(mail_from='unknown_name@test.com')
            IrMailServer.send_email(message)

        self.assertEqual(len(self.emails), 1)

        self.assert_email_sent_smtp(
            smtp_from=default_bounce_adress,
            message_from='unknown_name@test.com',
            from_filter='test.com',
        )

        # remove the notification server
        # so <notifications@test.com> will use the <test.com> mail server
        self.server_notification.unlink()

        # The mail server configured for the notifications email has been removed
        # but we can still use the mail server configured for test.com
        # and so we will be able to use the bounce address
        # because we use the mail server for "test.com"
        with self.mock_smtplib_connection():
            message = self._build_email(mail_from='"Name" <test@unknown_domain.com>')
            IrMailServer.send_email(message)

        self.assertEqual(len(self.emails), 1)

        self.assert_email_sent_smtp(
            smtp_from=default_bounce_adress,
            message_from='"Name (test@unknown_domain.com)" <notifications@test.com>',
            from_filter='test.com',
        )

        # Test that the mail from / recipient envelop are encoded using IDNA
        self.env['ir.config_parameter'].sudo().set_param('mail.catchall.domain', 'ééééééé.com')
        with self.mock_smtplib_connection():
            message = self._build_email(mail_from='test@ééééééé.com')
            IrMailServer.send_email(message)

        self.assertEqual(len(self.emails), 1)

        self.assert_email_sent_smtp(
            smtp_from='bounce@xn--9caaaaaaa.com',
            smtp_to_list=['dest@xn--example--i1a.com'],
            message_from='test@=?utf-8?b?w6nDqcOpw6nDqcOpw6k=?=.com',
            from_filter=False,
        )

    @mute_logger('odoo.models.unlink')
    def test_mail_server_send_email_smtp_session(self):
        """Test all the cases when we provide the SMTP session.

        The results must be the same as passing directly the parameter to "send_email".
        """
        IrMailServer = self.env['ir.mail_server']
        default_bounce_adress = self.env['ir.mail_server']._get_default_bounce_address()

        # A mail server is configured for the email
        with self.mock_smtplib_connection():
            smtp_session = IrMailServer.connect(smtp_from='specific_user@test.com')
            message = self._build_email(mail_from='specific_user@test.com')
            IrMailServer.send_email(message, smtp_session=smtp_session)

        self.connect_mocked.assert_called_once()
        self.assert_email_sent_smtp(
            smtp_from='specific_user@test.com',
            message_from='specific_user@test.com',
            from_filter='specific_user@test.com',
        )

        # No mail server are configured for the email address,
        # so it will use the notifications email instead and encapsulate the old email
        with self.mock_smtplib_connection():
            smtp_session = IrMailServer.connect(smtp_from='"Name" <test@unknown_domain.com>')
            message = self._build_email(mail_from='"Name" <test@unknown_domain.com>')
            IrMailServer.send_email(message, smtp_session=smtp_session)

        self.connect_mocked.assert_called_once()
        self.assert_email_sent_smtp(
            smtp_from='notifications@test.com',
            message_from='"Name (test@unknown_domain.com)" <notifications@test.com>',
            from_filter='notifications@test.com',
        )

        # A mail server is configured for the entire domain name, so we can use the bounce
        # email address because the mail server supports it
        with self.mock_smtplib_connection():
            smtp_session = IrMailServer.connect(smtp_from='unknown_name@test.com')
            message = self._build_email(mail_from='unknown_name@test.com')
            IrMailServer.send_email(message, smtp_session=smtp_session)

        self.connect_mocked.assert_called_once()
        self.assert_email_sent_smtp(
            smtp_from=default_bounce_adress,
            message_from='unknown_name@test.com',
            from_filter='test.com',
        )

        # remove the notification server
        # so <notifications@test.com> will use the <test.com> mail server
        self.server_notification.unlink()

        # The mail server configured for the notifications email has been removed
        # but we can still use the mail server configured for test.com
        with self.mock_smtplib_connection():
            smtp_session = IrMailServer.connect(smtp_from='"Name" <test@unknown_domain.com>')
            message = self._build_email(mail_from='"Name" <test@unknown_domain.com>')
            IrMailServer.send_email(message, smtp_session=smtp_session)

        self.connect_mocked.assert_called_once()
        self.assert_email_sent_smtp(
            smtp_from=default_bounce_adress,
            message_from='"Name (test@unknown_domain.com)" <notifications@test.com>',
            from_filter='test.com',
        )

    @mute_logger('odoo.models.unlink')
    @patch.dict("odoo.tools.config.options", {"from_filter": "test.com"})
    def test_mail_server_binary_arguments_domain(self):
        """Test the configuration provided in the odoo-bin arguments.

        This config is used when no mail server exists.
        """
        IrMailServer = self.env['ir.mail_server']
        default_bounce_adress = self.env['ir.mail_server']._get_default_bounce_address()

        # Remove all mail server so we will use the odoo-bin arguments
        self.env['ir.mail_server'].search([]).unlink()
        self.assertFalse(self.env['ir.mail_server'].search([]))

        # Use an email in the domain of the "from_filter"
        with self.mock_smtplib_connection():
            message = self._build_email(mail_from='specific_user@test.com')
            IrMailServer.send_email(message)

        self.connect_mocked.assert_called_once()
        self.assert_email_sent_smtp(
            smtp_from=default_bounce_adress,
            message_from='specific_user@test.com',
            from_filter='test.com',
        )

        # Test if the domain name is normalized before comparison
        with self.mock_smtplib_connection():
            message = self._build_email(mail_from='specific_user@test.com')
            IrMailServer.send_email(message)

        self.connect_mocked.assert_called_once()
        self.assert_email_sent_smtp(
            smtp_from=default_bounce_adress,
            message_from='specific_user@test.com',
            from_filter='test.com',
        )

        # Use an email outside of the domain of the "from_filter"
        # So we will use the notifications email in the headers and the bounce address
        # in the envelop because the "from_filter" allows to use the entire domain
        with self.mock_smtplib_connection():
            message = self._build_email(mail_from='test@unknown_domain.com')
            IrMailServer.send_email(message)

        self.connect_mocked.assert_called_once()
        self.assert_email_sent_smtp(
            smtp_from=default_bounce_adress,
            message_from='"test@unknown_domain.com" <notifications@test.com>',
            from_filter='test.com',
        )

    @mute_logger('odoo.models.unlink')
    @patch.dict("odoo.tools.config.options", {"from_filter": "test.com"})
    def test_mail_server_binary_arguments_domain_smtp_session(self):
        """Test the configuration provided in the odoo-bin arguments.

        This config is used when no mail server exists.
        Use a pre-configured SMTP session.
        """
        IrMailServer = self.env['ir.mail_server']
        default_bounce_adress = self.env['ir.mail_server']._get_default_bounce_address()

        # Remove all mail server so we will use the odoo-bin arguments
        self.env['ir.mail_server'].search([]).unlink()
        self.assertFalse(self.env['ir.mail_server'].search([]))

        # Use an email in the domain of the "from_filter"
        with self.mock_smtplib_connection():
            smtp_session = IrMailServer.connect(smtp_from='specific_user@test.com')
            message = self._build_email(mail_from='specific_user@test.com')
            IrMailServer.send_email(message, smtp_session=smtp_session)

        self.connect_mocked.assert_called_once()
        self.assert_email_sent_smtp(
            smtp_from=default_bounce_adress,
            message_from='specific_user@test.com',
            from_filter='test.com',
        )

        # Use an email outside of the domain of the "from_filter"
        # So we will use the notifications email in the headers and the bounce address
        # in the envelop because the "from_filter" allows to use the entire domain
        with self.mock_smtplib_connection():
            smtp_session = IrMailServer.connect(smtp_from='test@unknown_domain.com')
            message = self._build_email(mail_from='test@unknown_domain.com')
            IrMailServer.send_email(message, smtp_session=smtp_session)

        self.connect_mocked.assert_called_once()
        self.assert_email_sent_smtp(
            smtp_from=default_bounce_adress,
            message_from='"test@unknown_domain.com" <notifications@test.com>',
            from_filter='test.com',
        )
