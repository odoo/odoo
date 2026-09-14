from contextlib import contextmanager
from datetime import datetime, timedelta
from itertools import batched

from odoo.exceptions import UserError
from odoo.tests import tagged, users
from odoo.tools import config, mute_logger

from odoo.addons.mail.tests.common import MailCommon


@tagged("mail_server")
class TestIrMailServer(MailCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.default_bounce_address = f"{cls.alias_bounce}@{cls.alias_domain}"
        cls.default_from_address = f"{cls.default_from}@{cls.alias_domain}"

    def test_alter_smtp_to_list(self):
        IrMailServer = self.env["ir.mail_server"]
        mail_from = "specific_user@test.mycompany.com"

        for mail_server, mail_values, smtp_to_lst, msg_to_lst, msg_cc_lst in [
            (
                IrMailServer,
                {"email_to": '"Customer" <customer@test.example.com>'},
                ["customer@test.example.com"],
                ['"Customer" <customer@test.example.com>'],
                [],
            ),
            (
                IrMailServer.with_context(
                    send_validated_to=[
                        "another@test.example.com",
                        "customer@test.example.com",
                    ]
                ),
                {
                    "email_to": [
                        '"Customer" <customer@test.example.com>',
                        "user2@test.mycompany.com",
                    ]
                },
                ["customer@test.example.com"],
                ['"Customer" <customer@test.example.com>', "user2@test.mycompany.com"],
                [],
            ),
            (
                IrMailServer.with_context(
                    send_smtp_skip_to=[
                        "skip@test.example.com",
                        "other@test.example.com",
                        "wrong",
                        "skip.2@test.example.com",
                    ]
                ),
                {
                    "email_to": [
                        '"Customer" <customer@test.example.com>',
                        '"Skip Me" <skip@test.example.com>',
                        '"User" <user@test.mycompany.com>',
                        "user2@test.mycompany.com",
                        '"Skip Me 2" <skip.2@test.example.com>',
                    ],
                },
                [
                    "customer@test.example.com",
                    "user@test.mycompany.com",
                    "user2@test.mycompany.com",
                ],
                [
                    '"Customer" <customer@test.example.com>',
                    '"Skip Me" <skip@test.example.com>',
                    '"User" <user@test.mycompany.com>',
                    "user2@test.mycompany.com",
                    '"Skip Me 2" <skip.2@test.example.com>',
                ],
                {},
            ),
            (
                IrMailServer,
                {
                    "email_to": [
                        '"Customer" <customer@test.example.com>',
                        "user2@test.mycompany.com",
                    ],
                    "headers": {"X-Forge-To": "mailing@some.domain"},
                },
                ["customer@test.example.com", "user2@test.mycompany.com"],
                ["mailing@some.domain"],
                [],
            ),
            (
                IrMailServer,
                {
                    "email_to": [
                        '"Customer" <customer@test.example.com>',
                        "user2@test.mycompany.com",
                    ],
                    "headers": {
                        "X-Msg-To-Add": '"Other" <other.customer@test.example.com>'
                    },
                },
                ["customer@test.example.com", "user2@test.mycompany.com"],
                [
                    '"Customer" <customer@test.example.com>',
                    "user2@test.mycompany.com",
                    '"Other" <other.customer@test.example.com>',
                ],
                {},
            ),
        ]:
            with self.subTest(mail_values=mail_values, smtp_to_lst=smtp_to_lst):
                with self.mock_smtplib_connection():
                    smtp_session = mail_server._connect__(smtp_from=mail_from)
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
            self.env["ir.mail_server"]._get_default_bounce_address(),
            self.default_bounce_address,
        )
        self.assertEqual(
            self.env["ir.mail_server"]._get_default_from_address(),
            self.default_from_address,
        )

    @config.patch(email_from="settings@example.com")
    def test_default_email_from(self, *args):
        for (default_from, domain_name), expected_from in zip(
            [
                ("icp", "test.mycompany.com"),
                (False, "test.mycompany.com"),
                (False, False),
            ],
            [
                "icp@test.mycompany.com",
                "settings@example.com",
                "settings@example.com",
            ],
            strict=False,
        ):
            with self.subTest(default_from=default_from, domain_name=domain_name):
                if domain_name:
                    self.mail_alias_domain.name = domain_name
                    self.mail_alias_domain.default_from = default_from
                    self.env.company.alias_domain_id = self.mail_alias_domain
                else:
                    self.env.company.alias_domain_id = False
                message = self.env["ir.mail_server"]._prepare_email__(
                    False,
                    "recipient@example.com",
                    "Subject",
                    "The body of an email",
                )
                self.assertEqual(message["From"], expected_from)

    @mute_logger("odoo.models.unlink")
    @config.patch(
        from_filter="dummy@example.com, test.mycompany.com, dummy2@example.com",
        smtp_server="example.com",
    )
    def test_mail_server_config_bin(self):
        IrMailServer = self.env["ir.mail_server"]

        IrMailServer.search([]).unlink()
        self.assertFalse(IrMailServer.search([]))

        for mail_from, (expected_smtp_from, expected_msg_from) in zip(
            [
                "specific_user@test.mycompany.com",
                '"Formatted Name" <specific_user@test.mycompany.com>',
                '"Formatted Name" <specific_user@test.MYCOMPANY.com>',
                '"Formatted Name" <SPECIFIC_USER@test.mycompany.com>',
                "test@unknown_domain.com",
                '"Formatted Name" <test@unknown_domain.com>',
            ],
            [
                (self.default_bounce_address, "specific_user@test.mycompany.com"),
                (
                    self.default_bounce_address,
                    '"Formatted Name" <specific_user@test.mycompany.com>',
                ),
                (
                    self.default_bounce_address,
                    '"Formatted Name" <specific_user@test.MYCOMPANY.com>',
                ),
                (
                    self.default_bounce_address,
                    '"Formatted Name" <SPECIFIC_USER@test.mycompany.com>',
                ),
                (
                    self.default_bounce_address,
                    f'"test" <{self.default_from}@{self.alias_domain}>',
                ),
                (
                    self.default_bounce_address,
                    f'"Formatted Name" <{self.default_from}@{self.alias_domain}>',
                ),
            ],
            strict=False,
        ):
            for provide_smtp in [
                False,
                True,
            ]:
                with self.subTest(mail_from=mail_from, provide_smtp=provide_smtp):
                    with self.mock_smtplib_connection():
                        if provide_smtp:
                            smtp_session = IrMailServer._connect__(smtp_from=mail_from)
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

        self.env["ir.config_parameter"].sudo().set_param(
            "mail.default.from_filter", "icp.example.com"
        )

        with self.mock_smtplib_connection():
            message = self._build_email(mail_from="specific_user@icp.example.com")
            IrMailServer.send_email(message)

        self.assertSMTPEmailsSent(
            smtp_from="specific_user@icp.example.com",
            message_from="specific_user@icp.example.com",
            from_filter="icp.example.com",
        )

    @users("admin")
    def test_mail_server_get_test_email_from(self):
        test_server = self.env["ir.mail_server"].create(
            {
                "from_filter": "example_2.com, example_3.com",
                "name": "Test Server",
                "smtp_host": "smtp_host",
                "smtp_encryption": "none",
            }
        )

        for (default_from, from_filter), expected_test_email in zip(
            [
                ("notifications", "dummy.com, full_email@example_2.com, dummy2.com"),
                ("notifications", self.mail_alias_domain.name),
                ("notifications", f"{self.mail_alias_domain.name}, example_2.com"),
                (False, self.mail_alias_domain.name),
                ("notifications", " "),
                ("notifications", ","),
                ("notifications", False),
                (False, False),
            ],
            [
                "full_email@example_2.com",
                f"notifications@{self.mail_alias_domain.name}",
                f"notifications@{self.mail_alias_domain.name}",
                f"odoo@{self.mail_alias_domain.name}",
                self.env.user.email,
                self.env.user.email,
                self.env.user.email,
                self.env.user.email,
            ],
            strict=False,
        ):
            with self.subTest(default_from=default_from, from_filter=from_filter):
                self.mail_alias_domain.default_from = default_from
                test_server.from_filter = from_filter
                email_from = test_server._get_test_email_from()
                self.assertEqual(email_from, expected_test_email)

    @mute_logger("odoo.models.unlink")
    def test_mail_server_priorities(self):
        self.mail_server_user.from_filter = (
            "domain1.com, specific_user@test.mycompany.com, domain2.com"
        )

        for email_from, (expected_mail_server, expected_email_from) in zip(
            [
                "specific_user@test.mycompany.com",
                '"Name name@strange.name" <specific_user@test.mycompany.com>',
                "SPECIFIC_USER@test.mycompany.com",
                "specific_user@test.MYCOMPANY.com",
                "unknown_email@test.mycompany.com",
                "unknown_email@TEST.MYCOMPANY.COM",
                '"Unknown" <unknown_email@test.mycompany.com>',
                '"Test" <test@unknown_domain.com>',
                False,
                '"Example" <test@domain2.com>',
                '"Example" <test@domain1.com>',
            ],
            [
                (self.mail_server_user, "specific_user@test.mycompany.com"),
                (
                    self.mail_server_user,
                    '"Name name@strange.name" <specific_user@test.mycompany.com>',
                ),
                (self.mail_server_user, "SPECIFIC_USER@test.mycompany.com"),
                (self.mail_server_user, "specific_user@test.MYCOMPANY.com"),
                (self.mail_server_domain, "unknown_email@test.mycompany.com"),
                (self.mail_server_domain, "unknown_email@TEST.MYCOMPANY.COM"),
                (
                    self.mail_server_domain,
                    '"Unknown" <unknown_email@test.mycompany.com>',
                ),
                (
                    self.mail_server_notification,
                    f"{self.default_from}@test.mycompany.com",
                ),
                (
                    self.mail_server_notification,
                    f"{self.default_from}@test.mycompany.com",
                ),
                (self.mail_server_user, '"Example" <test@domain2.com>'),
                (self.mail_server_user, '"Example" <test@domain1.com>'),
            ],
            strict=False,
        ):
            with self.subTest(email_from=email_from):
                mail_server, mail_from = self.env["ir.mail_server"]._get_mail_server(
                    email_from=email_from
                )
                self.assertEqual(mail_server, expected_mail_server)
                self.assertEqual(mail_from, expected_email_from)

    @mute_logger("odoo.models.unlink", "odoo.addons.mail.models.ir_mail_server")
    def test_mail_server_send_email(self):
        IrMailServer = self.env["ir.mail_server"]

        for mail_from, (
            expected_smtp_from,
            expected_msg_from,
            expected_mail_server,
        ) in zip(
            [
                "specific_user@test.mycompany.com",
                '"Name" <test@unknown_domain.com>',
                "test@unknown_domain.com",
                '"Name" <unknown_name@test.mycompany.com>',
            ],
            [
                (
                    "specific_user@test.mycompany.com",
                    "specific_user@test.mycompany.com",
                    self.mail_server_user,
                ),
                (
                    f"{self.default_from}@{self.alias_domain}",
                    f'"Name" <{self.default_from}@{self.alias_domain}>',
                    self.mail_server_notification,
                ),
                (
                    f"{self.default_from}@{self.alias_domain}",
                    f'"test" <{self.default_from}@{self.alias_domain}>',
                    self.mail_server_notification,
                ),
                (
                    self.default_bounce_address,
                    '"Name" <unknown_name@test.mycompany.com>',
                    self.mail_server_domain,
                ),
            ],
            strict=False,
        ):
            for provide_smtp in [True, False]:
                with self.subTest(mail_from=mail_from):
                    with self.mock_smtplib_connection():
                        if provide_smtp:
                            smtp_session = IrMailServer._connect__(smtp_from=mail_from)
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

        self.mail_server_notification.unlink()
        for provide_smtp in [False, True]:
            with self.mock_smtplib_connection():
                if provide_smtp:
                    smtp_session = IrMailServer._connect__(
                        smtp_from='"Name" <test@unknown_domain.com>'
                    )
                    message = self._build_email(
                        mail_from='"Name" <test@unknown_domain.com>'
                    )
                    IrMailServer.send_email(message, smtp_session=smtp_session)
                else:
                    message = self._build_email(
                        mail_from='"Name" <test@unknown_domain.com>'
                    )
                    IrMailServer.send_email(message)
            self.connect_mocked.assert_called_once()
            self.assertEqual(len(self.emails), 1)
            self.assertSMTPEmailsSent(
                smtp_from=self.default_bounce_address,
                message_from=f'"Name" <{self.default_from}@{self.alias_domain}>',
                mail_server=self.mail_server_domain,
            )

        self.env["ir.mail_server"].search([]).from_filter = "random.domain"
        self.mail_alias_domain.default_from = "test"
        self.mail_alias_domain.name = "custom-domain.com"
        with self.mock_smtplib_connection():
            message = self._build_email(mail_from="specific_user@test.com")
            IrMailServer.send_email(message)

        self.connect_mocked.assert_called_once()
        self.assertSMTPEmailsSent(
            smtp_from="test@custom-domain.com",
            message_from='"specific_user" <test@custom-domain.com>',
            from_filter="random.domain",
        )


@tagged("mail_server")
class TestPersonalServer(MailCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_1, cls.user_2 = cls.user_employee, cls.user_employee_c2
        cls.mail_server_1, cls.mail_server_2 = cls.env["ir.mail_server"].create(
            [
                {
                    "name": "test",
                    "owner_user_id": user.id,
                    "from_filter": user.email,
                    "smtp_user": user.email,
                    "smtp_host": f"test_{i}@example.com",
                }
                for i, user in enumerate((cls.user_1, cls.user_2))
            ]
        )

    @contextmanager
    def assert_mail_sent_then_scheduled(
        self, mails, to_process_count, sent_count, send_datetime
    ):
        TEST_LIMIT = 5
        outgoing = mails.filtered(
            lambda m: (
                m.state == "outgoing"
                and (not m.scheduled_date or m.scheduled_date <= send_datetime)
            )
        ).sorted(lambda m: (m.create_date, m.id))

        self.assertEqual(len(outgoing), to_process_count)

        yield

        sent = outgoing.filtered(lambda m: m.state == "sent")
        self.assertEqual(
            sent, outgoing[: len(sent)], "Should send in priority old mails"
        )
        unsent = outgoing - sent
        self.assertEqual(len(sent), sent_count)

        scheduled_dates = sorted(unsent.mapped("scheduled_date"))
        scheduled_dates = list(batched(scheduled_dates, TEST_LIMIT, strict=False))

        for i, to_check in enumerate(scheduled_dates, start=1):
            self.assertEqual(
                set(to_check), {send_datetime.replace(second=0) + timedelta(minutes=i)}
            )

    @mute_logger("odoo.models.unlink", "odoo.addons.mail.models.ir_mail_server")
    @config.patch(from_filter="cli@example.com", smtp_server="example.com")
    def test_personal_mail_server(self):
        IrMailServer = self.env["ir.mail_server"]
        self.env["ir.mail_server"].search([]).from_filter = "random.domain"

        (self.env["ir.mail_server"].search([]) - self.mail_server_user).unlink()
        self.mail_server_user.write(
            {
                "from_filter": "user@test.mycompany.com",
                "owner_user_id": False,
            }
        )
        with self.mock_smtplib_connection():
            message = self._build_email(
                mail_from="notifications.test@test.mycompany.com"
            )
            IrMailServer.send_email(message)

        self.connect_mocked.assert_called_once()
        self.assertSMTPEmailsSent(
            smtp_from="notifications.test@test.mycompany.com",
            message_from="notifications.test@test.mycompany.com",
            from_filter="user@test.mycompany.com",
        )

        self.mail_server_user.write(
            {
                "from_filter": "user@test.mycompany.com",
                "owner_user_id": self.env.user.id,
            }
        )
        with self.mock_smtplib_connection():
            message = self._build_email(
                mail_from="notifications.test@test.mycompany.com"
            )
            IrMailServer.send_email(message)

        self.connect_mocked.assert_called_once()
        self.assertSMTPEmailsSent(
            smtp_from="notifications.test@test.mycompany.com",
            message_from="notifications.test@test.mycompany.com",
            from_filter="cli@example.com",
        )

        with self.mock_smtplib_connection(), self.assertRaises(UserError):
            message = self._build_email(mail_from="test@test.mycompany.com")
            IrMailServer.send_email(message, mail_server_id=self.mail_server_user.id)
        self.assertFalse(self.emails)

    def test_personal_mail_server_copy(self):
        self.assertFalse(self.mail_server_1.copy().owner_user_id)

    def test_personal_mail_server_from_filter_is_matched_normalized(self):
        owner_email = self.user_1.email
        for stored in (owner_email, owner_email.upper(), f"  {owner_email} "):
            with self.subTest(from_filter=stored):
                self.mail_server_1.from_filter = stored
                self.mail_server_1._check_forced_mail_server(True, owner_email)
                self.user_1.invalidate_recordset(["outgoing_mail_server_id"])
                self.assertEqual(
                    self.user_1.outgoing_mail_server_id,
                    self.mail_server_1,
                    "the owner must still be using the server the sender accepts",
                )

    def test_personal_mail_server_still_rejects_other_senders(self):
        domain = self.user_1.email.split("@")[1]
        for smtp_from, from_filter in (
            (f"someone.else@{domain}", self.user_1.email),
            (self.user_1.email, domain),
        ):
            with self.subTest(smtp_from=smtp_from, from_filter=from_filter):
                self.mail_server_1.from_filter = from_filter
                with self.assertRaises(UserError):
                    self.mail_server_1._check_forced_mail_server(True, smtp_from)

    @mute_logger("odoo.models.unlink")
    def test_personal_mail_server_limit(self):
        TEST_LIMIT = 5
        self.env["ir.config_parameter"].set_param(
            "mail.server.personal.limit.minutes", str(TEST_LIMIT)
        )
        user_1, user_2 = self.user_1, self.user_2
        mail_server_1, mail_server_2 = self.mail_server_1, self.mail_server_2

        with self.mock_datetime_and_now("2025-01-01 20:02:23"):
            mails_user_1 = (
                self.env["mail.mail"]
                .with_user(user_1)
                .sudo()
                .create(
                    [
                        {
                            "state": "outgoing",
                            "email_to": "target@test.com",
                            "email_from": user_1.email,
                        }
                        for i in range(22)
                    ]
                )
            )
            mails_user_2 = (
                self.env["mail.mail"]
                .with_user(user_2)
                .sudo()
                .create(
                    [
                        {
                            "state": "outgoing",
                            "email_to": "target@test.com",
                            "email_from": user_2.email,
                        }
                        for i in range(17)
                    ]
                )
            )
            mails_other = self.env["mail.mail"].create(
                [
                    {
                        "state": "outgoing",
                        "email_to": "target@test.com",
                        "email_from": user_1.email,
                    }
                    for i in range(25)
                ]
            )

        mails = mails_other + mails_user_1 + mails_user_2

        self.assertEqual(mail_server_1.owner_limit_count, 0)
        self.assertFalse(mail_server_1.owner_limit_time)

        DATE_SEND_1 = datetime(2025, 1, 1, 20, 5, 23)
        with (
            self.mock_smtplib_connection(),
            self.mock_datetime_and_now(DATE_SEND_1),
            self.assert_mail_sent_then_scheduled(
                mails_user_1, len(mails_user_1), 5, DATE_SEND_1
            ),
            self.assert_mail_sent_then_scheduled(
                mails_user_2, len(mails_user_2), 5, DATE_SEND_1
            ),
        ):
            mails.send()

        for personal_server in (mail_server_1, mail_server_2):
            self.assertEqual(personal_server.owner_limit_count, TEST_LIMIT)
            self.assertEqual(
                personal_server.owner_limit_time, DATE_SEND_1.replace(second=0)
            )

        self.assertEqual(
            self.connect_mocked.call_count, 3, "Called once for each mail server"
        )

        self.assertEqual(set(mails_other.mapped("state")), {"sent"})

        with self.mock_datetime_and_now("2025-01-01 20:04:23"):
            new_mails_user_1 = (
                self.env["mail.mail"]
                .with_user(user_1)
                .sudo()
                .create(
                    [
                        {
                            "state": "outgoing",
                            "email_to": "target@test.com",
                            "email_from": user_1.email,
                        }
                        for i in range(12)
                    ]
                )
            )
        mails_user_1 |= new_mails_user_1

        DATE_SEND_2 = datetime(2025, 1, 1, 20, 5, 23)
        with (
            self.mock_smtplib_connection(),
            self.mock_datetime_and_now(DATE_SEND_2),
            self.assert_mail_sent_then_scheduled(new_mails_user_1, 12, 0, DATE_SEND_2),
        ):
            new_mails_user_1.send()

        self.assertEqual(mail_server_1.owner_limit_count, TEST_LIMIT)
        self.assertEqual(mail_server_1.owner_limit_time, DATE_SEND_2.replace(second=0))

        DATE_SEND_3 = datetime(2025, 1, 1, 20, 6, 23)
        processed = (mails_user_1 | new_mails_user_1).filtered(
            lambda m: not m.scheduled_date or m.scheduled_date <= DATE_SEND_3
        )
        with (
            self.mock_smtplib_connection(),
            self.mock_datetime_and_now(DATE_SEND_3),
            self.assert_mail_sent_then_scheduled(processed, 10, 5, DATE_SEND_3),
        ):
            self.env["mail.mail"].process_email_queue()

        self.assertEqual(mail_server_1.owner_limit_count, TEST_LIMIT)
        self.assertEqual(mail_server_1.owner_limit_time, DATE_SEND_3.replace(second=0))

        DATE_SEND_5 = datetime(2025, 1, 1, 20, 7, 23)
        with (
            self.mock_smtplib_connection(),
            self.mock_datetime_and_now(DATE_SEND_5),
            self.assert_mail_sent_then_scheduled(mails_user_1, 15, 5, DATE_SEND_5),
        ):
            self.env["mail.mail"].process_email_queue()

        self.assertEqual(mail_server_1.owner_limit_count, TEST_LIMIT)
        self.assertEqual(mail_server_1.owner_limit_time, DATE_SEND_5.replace(second=0))

        DATE_SEND_6 = datetime(2025, 1, 1, 20, 25, 23)
        with (
            self.mock_smtplib_connection(),
            self.mock_datetime_and_now(DATE_SEND_6),
            self.assert_mail_sent_then_scheduled(mails_user_1, 19, 5, DATE_SEND_6),
        ):
            self.env["mail.mail"].process_email_queue()

        self.assertEqual(mail_server_1.owner_limit_count, TEST_LIMIT)
        self.assertEqual(mail_server_1.owner_limit_time, DATE_SEND_6.replace(second=0))

        for i in range(2):
            DATE_SEND_7 = datetime(2025, 1, 1, 20, 26 + i, 23)
            with (
                self.mock_smtplib_connection(),
                self.mock_datetime_and_now(DATE_SEND_7),
            ):
                self.env["mail.mail"].process_email_queue()
            self.assertEqual(mail_server_1.owner_limit_count, TEST_LIMIT)
            self.assertEqual(
                mail_server_1.owner_limit_time, DATE_SEND_7.replace(second=0)
            )

        DATE_SEND_8 = datetime(2025, 1, 1, 20, 28, 23)
        with self.mock_smtplib_connection(), self.mock_datetime_and_now(DATE_SEND_8):
            self.env["mail.mail"].process_email_queue()
        self.assertEqual(mail_server_1.owner_limit_count, 4)
        self.assertEqual(mail_server_1.owner_limit_time, DATE_SEND_8.replace(second=0))

        new_mails_user_1 = (
            self.env["mail.mail"]
            .with_user(user_1)
            .sudo()
            .create(
                [
                    {
                        "state": "outgoing",
                        "email_to": "target@test.com",
                        "email_from": user_1.email,
                    }
                    for i in range(TEST_LIMIT)
                ]
            )
        )
        DATE_SEND_9 = datetime(2025, 1, 1, 20, 28, 23)
        with (
            self.mock_smtplib_connection(),
            self.mock_datetime_and_now(DATE_SEND_9),
            self.assert_mail_sent_then_scheduled(
                new_mails_user_1, len(new_mails_user_1), 1, DATE_SEND_9
            ),
        ):
            self.env["mail.mail"].process_email_queue()
        self.assertEqual(mail_server_1.owner_limit_count, TEST_LIMIT)
        self.assertEqual(mail_server_1.owner_limit_time, DATE_SEND_9.replace(second=0))

    @mute_logger("odoo.models.unlink")
    def test_personal_mail_server_limit_many_recipient(self):
        TEST_LIMIT = 5
        self.env["ir.config_parameter"].set_param(
            "mail.server.personal.limit.minutes", str(TEST_LIMIT)
        )

        partners = self.env["res.partner"].create(
            [
                {"name": f"Partner {i}", "email": f"partner_{i}@test.com"}
                for i in range(16)
            ]
        )
        with self.mock_datetime_and_now("2025-01-01 20:30:23"):
            email_to = '"Named To1" <to.1@test.com>, "Named To2" <to.1@test.com>'
            mail = (
                self.env["mail.mail"]
                .with_user(self.user_employee)
                .sudo()
                .create(
                    {
                        "email_from": self.user_employee.email,
                        "email_cc": '"Named Cc1" <cc.1@test.com>, "Named Cc2" <cc.2@test.com>',
                        "email_to": email_to,
                        "headers": {"test": "test header"},
                        "recipient_ids": partners.ids,
                        "state": "outgoing",
                    }
                )
            )

        with (
            self.mock_smtplib_connection(),
            self.mock_datetime_and_now("2025-01-01 20:31:23"),
        ):
            self.env["mail.mail"].process_email_queue()

        self.assertEqual(self.mail_server_1.owner_limit_count, TEST_LIMIT)
        mails = self.env["mail.mail"].search(
            [("mail_message_id", "=", mail.mail_message_id.id)],
            order="create_date DESC, id DESC",
        )
        self.assertEqual(len(mails), 2)

        self.assertEqual(mails.mapped("email_to"), [email_to, False])

        self.assertEqual(mails.mapped("headers"), [{"test": "test header"}] * 2)

        self.assertEqual(mails.mapped("state"), ["sent", "outgoing"])
        outgoing = mails.filtered(lambda m: m.state == "outgoing")
        self.assertEqual(len(outgoing), 1)
        self.assertFalse(outgoing.email_to)
        self.assertEqual(outgoing.state, "outgoing")
        self.assertEqual(outgoing.create_uid, self.user_employee)
        self.assertEqual(len(outgoing.recipient_ids), 16 - (TEST_LIMIT - 1))

        with (
            self.mock_smtplib_connection(),
            self.mock_datetime_and_now("2025-01-01 20:31:33"),
        ):
            self.env["mail.mail"].process_email_queue()
        self.assertEqual(self.mail_server_1.owner_limit_count, TEST_LIMIT)
        mails = self.env["mail.mail"].search(
            [("mail_message_id", "=", mail.mail_message_id.id)]
        )
        self.assertEqual(len(mails), 2)
        self.assertEqual(outgoing.state, "outgoing")
        self.assertEqual(outgoing.create_uid, self.user_employee)
        self.assertEqual(len(outgoing.recipient_ids), 16 - (TEST_LIMIT - 1))

        with (
            self.mock_smtplib_connection(),
            self.mock_datetime_and_now("2025-01-01 20:32:27"),
        ):
            self.env["mail.mail"].process_email_queue()
        self.assertEqual(self.mail_server_1.owner_limit_count, TEST_LIMIT)
        mails = self.env["mail.mail"].search(
            [("mail_message_id", "=", mail.mail_message_id.id)]
        )
        self.assertEqual(sorted(mails.mapped("state")), ["outgoing", "sent", "sent"])
        outgoing = mails.filtered(lambda m: m.state == "outgoing")
        self.assertEqual(len(outgoing), 1)
        self.assertFalse(outgoing.email_to)
        self.assertEqual(outgoing.state, "outgoing")
        self.assertEqual(outgoing.create_uid, self.user_employee)
        self.assertEqual(
            len(outgoing.recipient_ids), 16 - (TEST_LIMIT - 1) - TEST_LIMIT
        )

        with self.mock_datetime_and_now("2025-01-01 20:32:29"):
            other_mail = (
                self.env["mail.mail"]
                .with_user(self.user_employee)
                .sudo()
                .create(
                    {
                        "email_from": self.user_employee.email,
                        "email_to": "target@test.com",
                        "headers": {"test": "test header"},
                        "recipient_ids": partners[:7].ids,
                        "state": "outgoing",
                    }
                )
            )

        with (
            self.mock_smtplib_connection(),
            self.mock_datetime_and_now("2025-01-01 20:37:29"),
        ):
            self.env["mail.mail"].process_email_queue()
        self.assertEqual(self.mail_server_1.owner_limit_count, TEST_LIMIT)
        self.assertEqual(other_mail.state, "outgoing")
        mails = self.env["mail.mail"].search(
            [
                (
                    "mail_message_id",
                    "in",
                    (mail.mail_message_id.id, other_mail.mail_message_id.id),
                )
            ],
            order="create_date DESC, id DESC",
        )
        self.assertEqual(
            sorted(mails.mapped("state")),
            ["outgoing", "outgoing", "sent", "sent", "sent"],
        )
        outgoing_1 = mails[-1]
        self.assertFalse(outgoing_1.email_to)
        self.assertEqual(outgoing_1.state, "outgoing")
        self.assertEqual(outgoing_1.create_uid, self.user_employee)
        self.assertEqual(
            len(outgoing_1.recipient_ids), 16 - (TEST_LIMIT - 1) - 2 * TEST_LIMIT
        )

        outgoing_2 = mails[1]
        self.assertEqual(outgoing_2.email_to, "target@test.com")
        self.assertEqual(outgoing_2.state, "outgoing")
        self.assertEqual(outgoing_2.create_uid, self.user_employee)
        self.assertEqual(len(outgoing_2.recipient_ids), 7)

        with (
            self.mock_smtplib_connection(),
            self.mock_datetime_and_now("2025-01-01 20:39:29"),
        ):
            self.env["mail.mail"].process_email_queue()
        self.assertEqual(self.mail_server_1.owner_limit_count, TEST_LIMIT)
        mails = self.env["mail.mail"].search(
            [
                (
                    "mail_message_id",
                    "in",
                    (mail.mail_message_id.id, other_mail.mail_message_id.id),
                )
            ]
        )
        self.assertEqual(
            sorted(mails.mapped("state")),
            ["outgoing", "sent", "sent", "sent", "sent", "sent"],
        )

        outgoing = mails.filtered(lambda m: m.state == "outgoing")
        self.assertEqual(len(outgoing), 1)
        self.assertFalse(outgoing.email_to)
        self.assertEqual(outgoing.state, "outgoing")
        self.assertEqual(outgoing.create_uid, self.user_employee)
        self.assertEqual(len(outgoing.recipient_ids), 7 - 2)

        with (
            self.mock_smtplib_connection(),
            self.mock_datetime_and_now("2025-01-01 20:42:29"),
        ):
            self.env["mail.mail"].process_email_queue()
        self.assertEqual(self.mail_server_1.owner_limit_count, 5)
        mails = self.env["mail.mail"].search(
            [
                (
                    "mail_message_id",
                    "in",
                    (mail.mail_message_id.id, other_mail.mail_message_id.id),
                )
            ]
        )
        self.assertEqual(set(mails.mapped("state")), {"sent"})


@tagged("mail_server")
class TestMailServerUsageGuard(MailCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.IrMailServer = cls.env["ir.mail_server"]

    def _server_with_template(self, template_active):
        server = self.IrMailServer.create({"name": "used", "smtp_host": "h"})
        template = self.env["mail.template"].create(
            {
                "name": "t",
                "model_id": self.env.ref("base.model_res_partner").id,
                "mail_server_id": server.id,
                "active": template_active,
            }
        )
        return server, template

    def test_an_active_template_blocks_archiving(self):
        server, _template = self._server_with_template(True)
        with self.assertRaises(UserError) as ctx:
            server.action_archive()
        self.assertIn("still used", str(ctx.exception))

    def test_an_archived_template_blocks_archiving_too(self):
        server, template = self._server_with_template(False)
        with self.assertRaises(UserError) as ctx:
            server.action_archive()
        self.assertIn("archived Email Template", str(ctx.exception))
        self.assertIn(template.display_name, str(ctx.exception))

    def test_an_archived_template_blocks_deletion_too(self):
        server, _template = self._server_with_template(False)
        with self.assertRaises(UserError):
            server.unlink()

    def test_an_archived_reference_is_labelled_as_archived(self):
        server = self.IrMailServer.create({"name": "used", "smtp_host": "h"})
        live = self.env["mail.template"].create(
            {
                "name": "live",
                "model_id": self.env.ref("base.model_res_partner").id,
                "mail_server_id": server.id,
            }
        )
        dead = self.env["mail.template"].create(
            {
                "name": "dead",
                "model_id": self.env.ref("base.model_res_partner").id,
                "mail_server_id": server.id,
                "active": False,
            }
        )
        usages = server._get_active_usages()[server.id]
        self.assertIn(f"{live.display_name} (Email Template)", usages)
        self.assertIn(f"{dead.display_name} (archived Email Template)", usages)

    def test_a_server_nothing_references_is_still_free(self):
        server = self.IrMailServer.create({"name": "unused", "smtp_host": "h"})
        server.action_archive()
        self.assertFalse(server.active)
        server.unlink()
