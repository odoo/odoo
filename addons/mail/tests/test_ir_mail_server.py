# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.addons.mail.tests.common import MailCommon
from odoo.tests import tagged, users
from odoo.tools import config, mute_logger


@tagged('mail_server')
class TestIrMailServer(MailCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.default_bounce_address = f'{cls.alias_bounce}@{cls.alias_domain}'
        cls.default_from_address = f'{cls.default_from}@{cls.alias_domain}'

    def test_alter_smtp_to_list(self):
        """ Check smtp_to_list alteration. Reminder: Message is the envelope,
        SMTP is the actual sending. """
        IrMailServer = self.env['ir.mail_server']
        mail_from = 'specific_user@test.mycompany.com'

        for mail_server, mail_values, smtp_to_lst, msg_to_lst, msg_cc_lst in [
            (
                IrMailServer,
                {'email_to': '"Customer" <customer@test.example.com>'},
                ['customer@test.example.com'],
                ['"Customer" <customer@test.example.com>'],
                [],
            ),
            # 'send_validated_to' context key: restrict SMTP To actual recipients
            # but do not rewrite Msg['To'], aka envelope (main usage is to cleanup
            # addresses found by extract_rfc2822_addresses anyway)
            (
                IrMailServer.with_context(send_validated_to=['another@test.example.com', 'customer@test.example.com']),
                {'email_to': ['"Customer" <customer@test.example.com>', 'user2@test.mycompany.com']},
                ['customer@test.example.com'],
                ['"Customer" <customer@test.example.com>', 'user2@test.mycompany.com'],
                [],
            ),
            # 'send_smtp_skip_to' context key: block list of SMTP recipients
            (
                IrMailServer.with_context(send_smtp_skip_to=['skip@test.example.com', 'other@test.example.com', 'wrong', 'skip.2@test.example.com']),
                {
                    'email_to': ['"Customer" <customer@test.example.com>', '"Skip Me" <skip@test.example.com>',
                                 '"User" <user@test.mycompany.com>', 'user2@test.mycompany.com', '"Skip Me 2" <skip.2@test.example.com>'],
                },
                ['customer@test.example.com', 'user@test.mycompany.com', 'user2@test.mycompany.com'],
                ['"Customer" <customer@test.example.com>', '"Skip Me" <skip@test.example.com>',
                 '"User" <user@test.mycompany.com>', 'user2@test.mycompany.com', '"Skip Me 2" <skip.2@test.example.com>'],
                {},
            ),
            # 'X-Forge-To' header: force envelope Msg['To'] (not SMTP recipients)
            # used notably for mailing lists
            (
                IrMailServer,
                {
                    'email_to': ['"Customer" <customer@test.example.com>', 'user2@test.mycompany.com'],
                    'headers': {'X-Forge-To': 'mailing@some.domain'}
                },
                ['customer@test.example.com', 'user2@test.mycompany.com'],
                ['mailing@some.domain'],
                [],
            ),
            # 'X-Msg-To-Add' header: add in Msg['To'] without impacting SMTP To, e.g.
            # displaying more recipients than actually mailed
            (
                IrMailServer,
                {
                    'email_to': ['"Customer" <customer@test.example.com>', 'user2@test.mycompany.com'],
                    'headers': {'X-Msg-To-Add': '"Other" <other.customer@test.example.com>'}
                },
                ['customer@test.example.com', 'user2@test.mycompany.com'],
                ['"Customer" <customer@test.example.com>', 'user2@test.mycompany.com', '"Other" <other.customer@test.example.com>'],
                {},
            ),
        ]:
            with self.subTest(mail_values=mail_values, smtp_to_lst=smtp_to_lst):
                with self.mock_smtplib_connection():
                    smtp_session = mail_server.connect(smtp_from=mail_from)
                    message = self._build_email(mail_from=mail_from, **mail_values)
                    mail_server.send_email(message, smtp_session=smtp_session)

                self.assertEqual(len(self.emails), 1)
                self.assertSMTPEmailsSent(
                    message_from=mail_from,
                    smtp_from=mail_from,
                    smtp_to_list=smtp_to_lst,
                    msg_cc_lst=msg_cc_lst,
                    msg_to_lst=msg_to_lst,
                )

    def test_assert_base_values(self):
        self.assertEqual(
            self.env['ir.mail_server']._get_default_bounce_address(),
            self.default_bounce_address)
        self.assertEqual(
            self.env['ir.mail_server']._get_default_from_address(),
            self.default_from_address)

    @patch.dict(config.options, {"email_from": "settings@example.com"})
    def test_default_email_from(self, *args):
        """ Check that default_from parameter of alias domain respected. """
        for (default_from, domain_name), expected_from in zip(
            [
                ('icp', 'test.mycompany.com'),
                (False, 'test.mycompany.com'),
                (False, False),
            ], [
                "icp@test.mycompany.com",
                "settings@example.com",
                "settings@example.com",
            ],
        ):
            with self.subTest(default_from=default_from, domain_name=domain_name):
                if domain_name:
                    self.mail_alias_domain.name = domain_name
                    self.mail_alias_domain.default_from = default_from
                    self.env.company.alias_domain_id = self.mail_alias_domain
                else:
                    self.env.company.alias_domain_id = False
                message = self.env["ir.mail_server"].build_email(
                    False, "recipient@example.com", "Subject",
                    "The body of an email",
                )
                self.assertEqual(message["From"], expected_from)

    @mute_logger('odoo.models.unlink')
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
                (self.default_bounce_address, 'specific_user@test.mycompany.com'),
                (self.default_bounce_address, '"Formatted Name" <specific_user@test.mycompany.com>'),
                (self.default_bounce_address, '"Formatted Name" <specific_user@test.MYCOMPANY.com>'),
                (self.default_bounce_address, '"Formatted Name" <SPECIFIC_USER@test.mycompany.com>'),
                # outside "from_filter" domain: we will use notifications emails in the
                # headers, and bounce address in the envelope because the "from_filter"
                # allows to use the entire domain
                (self.default_bounce_address, f'"test" <{self.default_from}@{self.alias_domain}>'),
                (self.default_bounce_address, f'"Formatted Name" <{self.default_from}@{self.alias_domain}>'),
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

    @users('admin')
    def test_mail_server_get_test_email_from(self):
        """ Test the email used to test the mail server connection. Check
        from_filter parsing / alias_domain.default_from support. """
        test_server = self.env['ir.mail_server'].create({
            'from_filter': 'example_2.com, example_3.com',
            'name': 'Test Server',
            'smtp_host': 'smtp_host',
            'smtp_encryption': 'none',
        })

        # check default.from / filter matching
        for (default_from, from_filter), expected_test_email in zip(
            [
                ('notifications', 'dummy.com, full_email@example_2.com, dummy2.com'),
                ('notifications', self.mail_alias_domain.name),
                ('notifications', f'{self.mail_alias_domain.name}, example_2.com'),
                # default relies on "odoo"
                (False, self.mail_alias_domain.name),
                # fallback on user email if no from_filter
                ('notifications', ' '),
                ('notifications', ','),
                ('notifications', False),
                (False, False),
            ], [
                'full_email@example_2.com',
                f'notifications@{self.mail_alias_domain.name}',
                f'notifications@{self.mail_alias_domain.name}',
                f'odoo@{self.mail_alias_domain.name}',
                self.env.user.email,
                self.env.user.email,
                self.env.user.email,
                self.env.user.email,
            ],
        ):
            with self.subTest(default_from=default_from, from_filter=from_filter):
                self.mail_alias_domain.default_from = default_from
                test_server.from_filter = from_filter
                email_from = test_server._get_test_email_from()
                self.assertEqual(email_from, expected_test_email)

    @mute_logger('odoo.models.unlink')
    def test_mail_server_priorities(self):
        """ Test if we choose the right mail server to send an email.
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
        # this mail server can now be used for a specific email address and 2 domain names
        self.mail_server_user.from_filter = "domain1.com, specific_user@test.mycompany.com, domain2.com"

        for email_from, (expected_mail_server, expected_email_from) in zip(
            [
                # matches user-specific server
                'specific_user@test.mycompany.com',
                # matches user-specific server (with formatting') -> should extract
                # email from full name, must keep the given email_from
                '"Name name@strange.name" <specific_user@test.mycompany.com>',
                # case check
                'SPECIFIC_USER@test.mycompany.com',
                'specific_user@test.MYCOMPANY.com',
                # matches domain-based server: domain is case insensitive
                'unknown_email@test.mycompany.com',
                'unknown_email@TEST.MYCOMPANY.COM',
                '"Unknown" <unknown_email@test.mycompany.com>',
                # fallback on notification email
                '"Test" <test@unknown_domain.com>',
                # fallback when email_from is False, should default to notification email
                False,
                # mail_server_user multiple from_filter check: can be used for a
                # specific email and 2 domain names -> check other domains in filter
                '"Example" <test@domain2.com>',
                '"Example" <test@domain1.com>',
            ], [
                (self.mail_server_user, 'specific_user@test.mycompany.com'),
                (self.mail_server_user, '"Name name@strange.name" <specific_user@test.mycompany.com>'),
                (self.mail_server_user, 'SPECIFIC_USER@test.mycompany.com'),
                (self.mail_server_user, 'specific_user@test.MYCOMPANY.com'),
                (self.mail_server_domain, 'unknown_email@test.mycompany.com'),
                (self.mail_server_domain, 'unknown_email@TEST.MYCOMPANY.COM'),
                (self.mail_server_domain, '"Unknown" <unknown_email@test.mycompany.com>'),
                (self.mail_server_notification, f'{self.default_from}@test.mycompany.com'),
                (self.mail_server_notification, f'{self.default_from}@test.mycompany.com'),
                # mail_server_user multiple from_filter check
                (self.mail_server_user, '"Example" <test@domain2.com>'),
                (self.mail_server_user, '"Example" <test@domain1.com>'),
            ],
        ):
            with self.subTest(email_from=email_from):
                mail_server, mail_from = self.env['ir.mail_server']._find_mail_server(email_from=email_from)
                self.assertEqual(mail_server, expected_mail_server)
                self.assertEqual(mail_from, expected_email_from)

    @mute_logger('odoo.models.unlink', 'odoo.addons.base.models.ir_mail_server')
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
                (f'{self.default_from}@{self.alias_domain}', f'"Name" <{self.default_from}@{self.alias_domain}>', self.mail_server_notification),
                # same situation, but the original email has no name part
                (f'{self.default_from}@{self.alias_domain}', f'"test" <{self.default_from}@{self.alias_domain}>', self.mail_server_notification),
                # A mail server is configured for the entire domain name, so we can use the bounce
                # email address because the mail server supports it
                (self.default_bounce_address, '"Name" <unknown_name@test.mycompany.com>', self.mail_server_domain),
            ],
        ):
            # test with and without providing an SMTP session, which should not impact test
            for provide_smtp in [True, False]:
                with self.subTest(mail_from=mail_from):
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
                smtp_from=self.default_bounce_address,
                message_from=f'"Name" <{self.default_from}@{self.alias_domain}>',
                mail_server=self.mail_server_domain,
            )

        # miss-configured database, no mail servers from filter
        # match the user / notification email
        self.env['ir.mail_server'].search([]).from_filter = "random.domain"
        self.mail_alias_domain.default_from = 'test'
        self.mail_alias_domain.name = 'custom_domain.com'
        with self.mock_smtplib_connection():
            message = self._build_email(mail_from='specific_user@test.com')
            IrMailServer.send_email(message)

        self.connect_mocked.assert_called_once()
        self.assertSMTPEmailsSent(
            smtp_from='test@custom_domain.com',
            message_from='"specific_user" <test@custom_domain.com>',
            from_filter='random.domain',
        )
