# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import email.message
import email.policy

from unittest.mock import patch

from odoo import tools
from odoo.addons.base.tests import test_mail_examples
from odoo.addons.base.tests.common import MockSmtplibCase
from odoo.tests import tagged, users
from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger
from odoo.tools import config


class _FakeSMTP:
    """SMTP stub"""
    def __init__(self):
        self.messages = []
        self.from_filter = 'example.com'

    # Python 3 before 3.7.4
    def sendmail(self, smtp_from, smtp_to_list, message_str,
                 mail_options=(), rcpt_options=()):
        self.messages.append(message_str)

    # Python 3.7.4+
    def send_message(self, message, smtp_from, smtp_to_list,
                     mail_options=(), rcpt_options=()):
        self.messages.append(message.as_string())


@tagged('mail_server')
class EmailConfigCase(TransactionCase):

    @patch.dict(config.options, {"email_from": "settings@example.com"})
    def test_default_email_from(self):
        """ Email from setting is respected and comes from configuration. """
        message = self.env["ir.mail_server"].build_email(
            False, "recipient@example.com", "Subject",
            "The body of an email",
        )
        self.assertEqual(message["From"], "settings@example.com")


@tagged('mail_server')
class TestIrMailServer(TransactionCase, MockSmtplibCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['ir.config_parameter'].sudo().set_param('mail.default.from_filter', False)
        cls._init_mail_servers()

    def test_assert_base_values(self):
        self.assertFalse(self.env['ir.mail_server']._get_default_bounce_address())
        self.assertFalse(self.env['ir.mail_server']._get_default_from_address())

    def test_bpo_34424_35805(self):
        """Ensure all email sent are bpo-34424 and bpo-35805 free"""
        fake_smtp = _FakeSMTP()
        msg = email.message.EmailMessage(policy=email.policy.SMTP)
        msg['From'] = '"Joé Doe" <joe@example.com>'
        msg['To'] = '"Joé Doe" <joe@example.com>'

        # Message-Id & References fields longer than 77 chars (bpo-35805)
        msg['Message-Id'] = '<929227342217024.1596730490.324691772460938-example-30661-some.reference@test-123.example.com>'
        msg['References'] = '<345227342212345.1596730777.324691772483620-example-30453-other.reference@test-123.example.com>'

        msg_on_the_wire = self._send_email(msg, fake_smtp)
        self.assertEqual(msg_on_the_wire,
            'From: =?utf-8?q?Jo=C3=A9?= Doe <joe@example.com>\r\n'
            'To: =?utf-8?q?Jo=C3=A9?= Doe <joe@example.com>\r\n'
            'Message-Id: <929227342217024.1596730490.324691772460938-example-30661-some.reference@test-123.example.com>\r\n'
            'References: <345227342212345.1596730777.324691772483620-example-30453-other.reference@test-123.example.com>\r\n'
            '\r\n'
        )

    def test_content_alternative_correct_order(self):
        """
        RFC-1521 7.2.3. The Multipart/alternative subtype
        > the alternatives appear in an order of increasing faithfulness
        > to the original content. In general, the best choice is the
        > LAST part of a type supported by the recipient system's local
        > environment.

        Also, the MIME-Version header should be present in BOTH the
        enveloppe AND the parts
        """
        fake_smtp = _FakeSMTP()
        msg = self._build_email("test@example.com", body='<p>Hello world</p>', subtype='html')
        msg_on_the_wire = self._send_email(msg, fake_smtp)

        self.assertGreater(msg_on_the_wire.index('text/html'), msg_on_the_wire.index('text/plain'),
            "The html part should be preferred (=appear after) to the text part")
        self.assertEqual(msg_on_the_wire.count('==============='), 2 + 2, # +2 for the header and the footer
            "There should be 2 parts: one text and one html")
        self.assertEqual(msg_on_the_wire.count('MIME-Version: 1.0'), 3,
            "There should be 3 headers MIME-Version: one on the enveloppe, "
            "one on the html part, one on the text part")

    def test_content_mail_body(self):
        bodies = [
            'content',
            '<p>content</p>',
            '<head><meta content="text/html; charset=utf-8" http-equiv="Content-Type"></head><body><p>content</p></body>',
            test_mail_examples.MISC_HTML_SOURCE,
            test_mail_examples.QUOTE_THUNDERBIRD_HTML,
        ]
        expected_list = [
            'content',
            'content',
            'content',
            "test1\n*test2*\ntest3\ntest4\ntest5\ntest6   test7\ntest8    test9\ntest10\ntest11\ntest12\ngoogle [1]\ntest link [2]\n\n\n[1] http://google.com\n[2] javascript:alert('malicious code')",
            'On 01/05/2016 10:24 AM, Raoul\nPoilvache wrote:\n\n* Test reply. The suite. *\n\n--\nRaoul Poilvache\n\nTop cool !!!\n\n--\nRaoul Poilvache',
        ]
        for body, expected in zip(bodies, expected_list):
            message = self.env['ir.mail_server'].build_email(
                'john.doe@from.example.com',
                'destinataire@to.example.com',
                body=body,
                subject='Subject',
                subtype='html',
            )
            body_alternative = False
            for part in message.walk():
                if part.get_content_maintype() == 'multipart':
                    continue  # skip container
                if part.get_content_type() == 'text/plain':
                    if not part.get_payload():
                        continue
                    body_alternative = tools.ustr(part.get_content())
                    # remove ending new lines as it just adds noise
                    body_alternative = body_alternative.strip('\n')
            self.assertEqual(body_alternative, expected)

    @users('admin')
    def test_mail_server_get_test_email_from(self):
        """ Test the email used to test the mail server connection. Check
        from_filter parsing / default fallback value. """
        test_server = self.env['ir.mail_server'].create({
            'from_filter': 'example_2.com, example_3.com',
            'name': 'Test Server',
            'smtp_host': 'smtp_host',
            'smtp_encryption': 'none',
        })
        for from_filter, expected_test_email in zip(
            [
                'example_2.com, example_3.com',
                'dummy.com, full_email@example_2.com, dummy2.com',
                # fallback on user's email
                ' ',
                ',',
                False,
            ], [
                'noreply@example_2.com',
                'full_email@example_2.com',
                self.env.user.email,
                self.env.user.email,
                self.env.user.email,
            ],
        ):
            with self.subTest(from_filter=from_filter):
                test_server.from_filter = from_filter
                email_from = test_server._get_test_email_from()
                self.assertEqual(email_from, expected_test_email)

    def test_mail_server_match_from_filter(self):
        """ Test the from_filter field on the "ir.mail_server". """
        # Should match
        tests = [
            ('admin@mail.example.com', 'mail.example.com'),
            ('admin@mail.example.com', 'mail.EXAMPLE.com'),
            ('admin@mail.example.com', 'admin@mail.example.com'),
            ('admin@mail.example.com', False),
            ('"fake@test.mycompany.com" <admin@mail.example.com>', 'mail.example.com'),
            ('"fake@test.mycompany.com" <ADMIN@mail.example.com>', 'mail.example.com'),
            ('"fake@test.mycompany.com" <ADMIN@mail.example.com>', 'test.mycompany.com, mail.example.com, test2.com'),
        ]
        for email, from_filter in tests:
            self.assertTrue(self.env['ir.mail_server']._match_from_filter(email, from_filter))

        # Should not match
        tests = [
            ('admin@mail.example.com', 'test@mail.example.com'),
            ('admin@mail.example.com', 'test.mycompany.com'),
            ('admin@mail.example.com', 'mail.éxample.com'),
            ('admin@mmail.example.com', 'mail.example.com'),
            ('admin@mail.example.com', 'mmail.example.com'),
            ('"admin@mail.example.com" <fake@test.mycompany.com>', 'mail.example.com'),
            ('"fake@test.mycompany.com" <ADMIN@mail.example.com>', 'test.mycompany.com, wrong.mail.example.com, test3.com'),
        ]
        for email, from_filter in tests:
            self.assertFalse(self.env['ir.mail_server']._match_from_filter(email, from_filter))

    @mute_logger('odoo.models.unlink')
    def test_mail_server_priorities(self):
        """ Test if we choose the right mail server to send an email. Simulates
        simple Odoo DB so we have to spoof the FROM otherwise we cannot send
        any email. """
        for email_from, (expected_mail_server, expected_email_from) in zip(
            [
                'specific_user@test.mycompany.com',
                'unknown_email@test.mycompany.com',
                # no notification set, must be forced to spoof the FROM
                '"Test" <test@unknown_domain.com>',
            ], [
                (self.mail_server_user, 'specific_user@test.mycompany.com'),
                (self.mail_server_domain, 'unknown_email@test.mycompany.com'),
                (self.mail_server_default, '"Test" <test@unknown_domain.com>'),
            ],
        ):
            with self.subTest(email_from=email_from):
                mail_server, mail_from = self.env['ir.mail_server']._find_mail_server(email_from=email_from)
                self.assertEqual(mail_server, expected_mail_server)
                self.assertEqual(mail_from, expected_email_from)

    @mute_logger('odoo.models.unlink')
    def test_mail_server_send_email(self):
        """ Test main 'send_email' usage: check mail_server choice based on from
        filters, encapsulation, spoofing. """
        IrMailServer = self.env['ir.mail_server']

        for mail_from, (expected_smtp_from, expected_msg_from, expected_mail_server) in zip(
            [
                'specific_user@test.mycompany.com',
                '"Name" <test@unknown_domain.com>',
                'test@unknown_domain.com',
                '"Name" <unknown_name@test.mycompany.com>'
            ], [
                # A mail server is configured for the email
                ('specific_user@test.mycompany.com', 'specific_user@test.mycompany.com', self.mail_server_user),
                # No mail server are configured for the email address, so it will use the
                # notifications email instead and encapsulate the old email
                ('test@unknown_domain.com', '"Name" <test@unknown_domain.com>', self.mail_server_default),
                # same situation, but the original email has no name part
                ('test@unknown_domain.com', 'test@unknown_domain.com', self.mail_server_default),
                # A mail server is configured for the entire domain name, so we can use the bounce
                # email address because the mail server supports it
                ('unknown_name@test.mycompany.com', '"Name" <unknown_name@test.mycompany.com>', self.mail_server_domain),
            ]
        ):
            # test with and without providing an SMTP session, which should not impact test
            for provide_smtp in [False, True]:
                with self.subTest(mail_from=mail_from, provide_smtp=provide_smtp):
                    with self.mock_smtplib_connection():
                        if provide_smtp:
                            smtp_session = IrMailServer.connect(smtp_from=mail_from)
                            message = self._build_email(mail_from=mail_from)
                            IrMailServer.send_email(message, smtp_session=smtp_session)
                        else:
                            message = self._build_email(mail_from=mail_from)
                            IrMailServer.send_email(message)

                    self.connect_mocked.assert_called_once()
                    self.assertEqual(len(self.emails), 1)
                    self.assertSMTPEmailsSent(
                        smtp_from=expected_smtp_from,
                        message_from=expected_msg_from,
                        mail_server=expected_mail_server,
                    )

        # remove the notification server
        # so <notifications.test@test.mycompany.com> will use the <test.mycompany.com> mail server
        # The mail server configured for the notifications email has been removed
        # but we can still use the mail server configured for test.mycompany.com
        # and so we will be able to use the bounce address
        # because we use the mail server for "test.mycompany.com"
        self.mail_server_notification.unlink()
        for provide_smtp in [False, True]:
            with self.mock_smtplib_connection():
                if provide_smtp:
                    smtp_session = IrMailServer.connect(smtp_from='"Name" <test@unknown_domain.com>')
                    message = self._build_email(mail_from='"Name" <test@unknown_domain.com>')
                    IrMailServer.send_email(message, smtp_session=smtp_session)
                else:
                    message = self._build_email(mail_from='"Name" <test@unknown_domain.com>')
                    IrMailServer.send_email(message)

            self.connect_mocked.assert_called_once()
            self.assertEqual(len(self.emails), 1)
            self.assertSMTPEmailsSent(
                smtp_from='test@unknown_domain.com',
                message_from='"Name" <test@unknown_domain.com>',
                from_filter=False,
            )

    @mute_logger('odoo.models.unlink', 'odoo.addons.base.models.ir_mail_server')
    def test_mail_server_send_email_context_force(self):
        """ Allow to force notifications_email / bounce_address from context
        to allow higher-level apps to send values until end of mail stack
        without hacking too much models. """
        # custom notification / bounce email from context
        context_server = self.env['ir.mail_server'].create({
            'from_filter': 'context.example.com',
            'name': 'context',
            'smtp_host': 'test',
        })
        IrMailServer = self.env["ir.mail_server"].with_context(
            domain_notifications_email="notification@context.example.com",
            domain_bounce_address="bounce@context.example.com",
        )
        with self.mock_smtplib_connection():
            mail_server, smtp_from = IrMailServer._find_mail_server(email_from='"Name" <test@unknown_domain.com>')
            self.assertEqual(mail_server, context_server)
            self.assertEqual(smtp_from, "notification@context.example.com")
            smtp_session = IrMailServer.connect(smtp_from=smtp_from)
            message = self._build_email(mail_from='"Name" <test@unknown_domain.com>')
            IrMailServer.send_email(message, smtp_session=smtp_session)

        self.assertEqual(len(self.emails), 1)
        self.assertSMTPEmailsSent(
            smtp_from="bounce@context.example.com",
            message_from='"Name" <notification@context.example.com>',
            from_filter=context_server.from_filter,
        )

        # miss-configured database, no mail servers from filter
        # match the user / notification email
        self.env['ir.mail_server'].search([]).from_filter = "random.domain"
        with self.mock_smtplib_connection():
            message = self._build_email(mail_from='specific_user@test.com')
            IrMailServer.with_context(domain_notifications_email='test@custom_domain.com').send_email(message)

        self.connect_mocked.assert_called_once()
        self.assertSMTPEmailsSent(
            smtp_from='test@custom_domain.com',
            message_from='"specific_user" <test@custom_domain.com>',
            from_filter='random.domain',
        )

    @mute_logger('odoo.models.unlink')
    def test_mail_server_send_email_IDNA(self):
        """ Test that the mail from / recipient envelop are encoded using IDNA """
        with self.mock_smtplib_connection():
            message = self._build_email(mail_from='test@ééééééé.com')
            self.env['ir.mail_server'].send_email(message)

        self.assertEqual(len(self.emails), 1)
        self.assertSMTPEmailsSent(
            smtp_from='test@xn--9caaaaaaa.com',
            smtp_to_list=['dest@xn--example--i1a.com'],
            message_from='test@=?utf-8?b?w6nDqcOpw6nDqcOpw6k=?=.com',
            from_filter=False,
        )

    @mute_logger('odoo.models.unlink', 'odoo.addons.base.models.ir_mail_server')
    @patch.dict(config.options, {
        "from_filter": "dummy@example.com, test.mycompany.com, dummy2@example.com",
        "smtp_server": "example.com",
    })
    def test_mail_server_config_bin(self):
        """ Test the configuration provided in the odoo-bin arguments. This config
        is used when no mail server exists. Test with and without giving a
        pre-configured SMTP session, should not impact results.

        Also check "mail.default.from_filter" parameter usage that should overwrite
        odoo-bin argument "--from-filter".
        """
        IrMailServer = self.env['ir.mail_server']

        # Remove all mail server so we will use the odoo-bin arguments
        IrMailServer.search([]).unlink()
        self.assertFalse(IrMailServer.search([]))

        for mail_from, (expected_smtp_from, expected_msg_from) in zip(
            [
                # inside "from_filter" domain
                'specific_user@test.mycompany.com',
                '"Formatted Name" <specific_user@test.mycompany.com>',
                '"Formatted Name" <specific_user@test.MYCOMPANY.com>',
                '"Formatted Name" <SPECIFIC_USER@test.mycompany.com>',
                # outside "from_filter" domain
                'test@unknown_domain.com',
                '"Formatted Name" <test@unknown_domain.com>',
            ], [
                # inside "from_filter" domain: no rewriting
                ('specific_user@test.mycompany.com', 'specific_user@test.mycompany.com'),
                ('specific_user@test.mycompany.com', '"Formatted Name" <specific_user@test.mycompany.com>'),
                ('specific_user@test.MYCOMPANY.com', '"Formatted Name" <specific_user@test.MYCOMPANY.com>'),
                ('SPECIFIC_USER@test.mycompany.com', '"Formatted Name" <SPECIFIC_USER@test.mycompany.com>'),
                # outside "from_filter" domain: spoofing, as fallback email can be found
                ('test@unknown_domain.com', 'test@unknown_domain.com'),
                ('test@unknown_domain.com', '"Formatted Name" <test@unknown_domain.com>'),
            ]
        ):
            for provide_smtp in [False, True]:  # providing smtp session should ont impact test
                with self.subTest(mail_from=mail_from, provide_smtp=provide_smtp):
                    with self.mock_smtplib_connection():
                        if provide_smtp:
                            smtp_session = IrMailServer.connect(smtp_from=mail_from)
                            message = self._build_email(mail_from=mail_from)
                            IrMailServer.send_email(message, smtp_session=smtp_session)
                        else:
                            message = self._build_email(mail_from=mail_from)
                            IrMailServer.send_email(message)

                    self.connect_mocked.assert_called_once()
                    self.assertEqual(len(self.emails), 1)
                    self.assertSMTPEmailsSent(
                        smtp_from=expected_smtp_from,
                        message_from=expected_msg_from,
                        from_filter="dummy@example.com, test.mycompany.com, dummy2@example.com",
                    )

        # for from_filter in ICP, overwrite the one from odoo-bin
        self.env['ir.config_parameter'].sudo().set_param('mail.default.from_filter', 'icp.example.com')

        # Use an email in the domain of the config parameter "mail.default.from_filter"
        with self.mock_smtplib_connection():
            message = self._build_email(mail_from='specific_user@icp.example.com')
            IrMailServer.send_email(message)

        self.assertSMTPEmailsSent(
            smtp_from='specific_user@icp.example.com',
            message_from='specific_user@icp.example.com',
            from_filter='icp.example.com',
        )

    @mute_logger('odoo.models.unlink')
    @patch.dict(config.options, {'from_filter': 'fake.com', 'smtp_server': 'cli_example.com'})
    def test_mail_server_config_cli(self):
        """ Test the mail server configuration when the "smtp_authentication" is
        "cli". It should take the configuration from the odoo-bin argument. The
        "from_filter" of the mail server should overwrite the one set in the CLI
        arguments.
        """
        IrMailServer = self.env['ir.mail_server']
        # should be ignored by the mail server
        self.env['ir.config_parameter'].sudo().set_param('mail.default.from_filter', 'fake.com')

        server_other = IrMailServer.create([{
            'name': 'Server No From Filter',
            'smtp_host': 'smtp_host',
            'smtp_encryption': 'none',
            'smtp_authentication': 'cli',
            'from_filter': 'dummy@example.com, cli_example.com, dummy2@example.com',
        }])

        for mail_from, (expected_smtp_from, expected_msg_from, expected_mail_server) in zip(
            [
                # check that the CLI server take the configuration in the odoo-bin argument
                # except the from_filter which is taken on the mail server
                'test@cli_example.com',
                # other mail servers still work
                'specific_user@test.mycompany.com',
            ], [
                ('test@cli_example.com', 'test@cli_example.com', server_other),
                ('specific_user@test.mycompany.com', 'specific_user@test.mycompany.com', self.mail_server_user),
            ],
        ):
            with self.subTest(mail_from=mail_from):
                with self.mock_smtplib_connection():
                    message = self._build_email(mail_from=mail_from)
                    IrMailServer.send_email(message)

                self.assertSMTPEmailsSent(
                    smtp_from=expected_smtp_from,
                    message_from=expected_msg_from,
                    mail_server=expected_mail_server,
                )

    def test_eml_attachment_encoding(self):
        """Test that message/rfc822 attachments are encoded using 7bit, 8bit, or binary encoding."""
        IrMailServer = self.env['ir.mail_server']

        # Create a sample .eml file content
        eml_content = b"From: user@example.com\nTo: user2@example.com\nSubject: Test Email\n\nThis is a test email."
        attachments = [('test.eml', eml_content, 'message/rfc822')]

        # Build the email with the .eml attachment
        message = IrMailServer.build_email(
            email_from='john.doe@from.example.com',
            email_to='destinataire@to.example.com',
            subject='Subject with .eml attachment',
            body='This email contains a .eml attachment.',
            attachments=attachments,
        )

        # Verify that the attachment is correctly encoded
        acceptable_encodings = {'7bit', '8bit', 'binary'}
        for part in message.iter_attachments():
            if part.get_content_type() == 'message/rfc822':
                self.assertIn(
                    part.get('Content-Transfer-Encoding'),
                    acceptable_encodings,
                    "The message/rfc822 attachment should be encoded using 7bit, 8bit, or binary encoding.",
                )
