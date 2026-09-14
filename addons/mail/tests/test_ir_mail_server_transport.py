import base64
import email.message
import email.policy
import smtplib
import ssl
from collections import Counter
from unittest.mock import patch

import psycopg.errors

from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.tools import config, mute_logger

from odoo.addons.mail.models.ir_mail_server import (
    MailDeliveryError,
    OutgoingEmailError,
)
from odoo.addons.mail.tests.common import MockSmtplibCase


def _generate_self_signed_cert(common_name="smtp.example.com"):
    import datetime

    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)])
    now = datetime.datetime.now(datetime.UTC)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1))
        .not_valid_after(now + datetime.timedelta(days=3650))
        .add_extension(
            x509.SubjectAlternativeName([x509.DNSName(common_name)]), critical=False
        )
        .sign(key, hashes.SHA256())
    )
    cert_pem = cert.public_bytes(serialization.Encoding.PEM)
    key_pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption(),
    )
    return cert_pem, key_pem


class _FakeSMTP:
    def __init__(self):
        self.messages = []
        self.from_filter = "example.com"

    def sendmail(
        self,
        smtp_from,
        smtp_to_list,
        message_str,
        mail_options=(),
        rcpt_options=(),
    ):
        self.messages.append(message_str)

    def send_message(
        self, message, smtp_from, smtp_to_list, mail_options=(), rcpt_options=()
    ):
        self.messages.append(message.as_string())


_HTML_BODIES = """Two realistic HTML bodies, as MIME round-trip inputs.

Copied out of the sanitiser's fixture corpus, which moved to the libs suite
that owns it. Importing them from there would have this addon reach past an
`odoo.libs` area, which `tooling/architecture/libs_facade_check.py` forbids
-- and rightly: what this test needs is *some* realistic HTML, not that
corpus. The expected plaintext in the test is what pins the choice."""

MISC_HTML_SOURCE = """
<font size="2" style="color: rgb(31, 31, 31); font-family: monospace; font-variant: normal; line-height: normal; ">test1</font>
<div style="color: rgb(31, 31, 31); font-family: monospace; font-variant: normal; line-height: normal; font-size: 12px; font-style: normal; ">
<b>test2</b></div><div style="color: rgb(31, 31, 31); font-family: monospace; font-variant: normal; line-height: normal; font-size: 12px; ">
<i>test3</i></div><div style="color: rgb(31, 31, 31); font-family: monospace; font-variant: normal; line-height: normal; font-size: 12px; ">
<u>test4</u></div><div style="color: rgb(31, 31, 31); font-family: monospace; font-variant: normal; line-height: normal; font-size: 12px; ">
<strike>test5</strike></div><div style="color: rgb(31, 31, 31); font-family: monospace; font-variant: normal; line-height: normal; ">
<font size="5">test6</font></div><div><ul><li><font color="#1f1f1f" face="monospace" size="2">test7</font></li><li>
<font color="#1f1f1f" face="monospace" size="2">test8</font></li></ul><div><ol><li><font color="#1f1f1f" face="monospace" size="2">test9</font>
</li><li><font color="#1f1f1f" face="monospace" size="2">test10</font></li></ol></div></div>
<blockquote style="margin: 0 0 0 40px; border: none; padding: 0px;"><div><div><div><font color="#1f1f1f" face="monospace" size="2">
test11</font></div></div></div></blockquote><blockquote style="margin: 0 0 0 40px; border: none; padding: 0px;">
<blockquote style="margin: 0 0 0 40px; border: none; padding: 0px;"><div><font color="#1f1f1f" face="monospace" size="2">
test12</font></div><div><font color="#1f1f1f" face="monospace" size="2"><br></font></div></blockquote></blockquote>
<font color="#1f1f1f" face="monospace" size="2"><a href="http://google.com">google</a></font>
<a href="javascript:alert('malicious code')">test link</a>
"""

QUOTE_THUNDERBIRD_HTML = """<html>
  <head>
    <meta content="text/html; charset=utf-8" http-equiv="Content-Type">
  </head>
  <body text="#000000" bgcolor="#FFFFFF">
    <div class="moz-cite-prefix">On 01/05/2016 10:24 AM, Raoul
      Poilvache wrote:<br>
    </div>
    <blockquote
cite="mid:CAP76m_WWFH2KVrbjOxbaozvkmbzZYLWJnQ0n0sy9XpGaCWRf1g@mail.gmail.com"
      type="cite">
      <div dir="ltr"><b><i>Test reply. The suite.</i></b><br clear="all">
        <div><br>
        </div>
        -- <br>
        <div class="gmail_signature">Raoul Poilvache</div>
      </div>
    </blockquote>
    Top cool !!!<br>
    <br>
    <pre class="moz-signature" cols="72">--
Raoul Poilvache
</pre>
  </body>
</html>"""


@tagged("mail_server")
class EmailConfigCase(TransactionCase):
    @config.patch(email_from="settings@example.com")
    def test_default_email_from(self):
        message = self.env["ir.mail_server"]._prepare_email__(
            False,
            "recipient@example.com",
            "Subject",
            "The body of an email",
        )
        self.assertEqual(message["From"], "settings@example.com")

    def test_build_email_missing_from_raises_coded_error(self):
        IrMailServer = self.env["ir.mail_server"]
        with config.patch(email_from=False):
            with self.assertRaises(OutgoingEmailError) as capture:
                IrMailServer._prepare_email__(
                    False, "recipient@example.com", "Subject", "Body"
                )
        self.assertEqual(capture.exception.code, IrMailServer.NO_FOUND_FROM)

    def test_build_email_attachment_malformed_mimetype(self):
        message = self.env["ir.mail_server"]._prepare_email__(
            "sender@example.com",
            "recipient@example.com",
            "Subject",
            "Body",
            attachments=[("weird.bin", b"data", "application/pdf/x")],
        )
        attachments = [
            part
            for part in message.walk()
            if part.get_content_disposition() == "attachment"
        ]
        self.assertEqual(len(attachments), 1)
        self.assertEqual(attachments[0].get_filename(), "weird.bin")

    def test_build_email_headers_override_standard_headers(self):
        IrMailServer = self.env["ir.mail_server"]
        for header, override in [
            ("Subject", "Overridden Subject"),
            ("Reply-To", "boss@example.com"),
            ("From", "override@example.com"),
            ("Message-Id", "<pinned@example.com>"),
        ]:
            message = IrMailServer._prepare_email__(
                "sender@example.com",
                "recipient@example.com",
                "Original Subject",
                "Body",
                reply_to="orig-reply@example.com",
                headers={header: override},
            )
            self.assertEqual(
                message.get_all(header),
                [override],
                f"{header} from headers must replace, exactly once",
            )

    def test_build_email_rejects_header_injection(self):
        IrMailServer = self.env["ir.mail_server"]

        with self.assertRaises(ValueError):
            IrMailServer._prepare_email__(
                "sender@example.com",
                "recipient@example.com",
                "Subject\r\nBcc: attacker@example.com",
                "Body",
            )

        with self.assertRaises(ValueError):
            IrMailServer._prepare_email__(
                "sender@example.com",
                "recipient@example.com",
                "Subject",
                "Body",
                headers={"X-Custom": "value\r\nBcc: attacker@example.com"},
            )

        with self.assertRaises(ValueError):
            IrMailServer._prepare_email__(
                "sender@example.com",
                "recipient@example.com",
                "Subject",
                "Body",
                headers={"X-Foo\r\nBcc: attacker@example.com": "v"},
            )


@tagged("mail_server")
class TestIrMailServer(TransactionCase, MockSmtplibCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["ir.config_parameter"].sudo().set_param(
            "mail.default.from_filter", False
        )
        cls._init_mail_servers()

    def test_assert_base_values(self):
        self.assertFalse(self.env["ir.mail_server"]._get_default_bounce_address())
        self.assertFalse(self.env["ir.mail_server"]._get_default_from_address())

    def test_send_email_delivery_failure_reason_is_readable(self):
        IrMailServer = self.env["ir.mail_server"]
        message = self._build_email("admin@example.com")

        class _RaisingSession:
            from_filter = False
            smtp_from = False
            _host = "smtp.probe.example.com"

            def send_message(self, *args, **kwargs):
                raise smtplib.SMTPDataError(554, b"5.7.1 rejected")

        with (
            patch.object(type(IrMailServer), "_disable_send", lambda _: False),
            mute_logger("odoo.addons.mail.models.ir_mail_server"),
            self.assertRaises(MailDeliveryError) as capture,
        ):
            IrMailServer.send_email(message, smtp_session=_RaisingSession())

        rendered = str(capture.exception)
        self.assertNotIn("('", rendered)
        self.assertNotIn("', '", rendered)
        self.assertIn("smtp.probe.example.com", rendered)
        self.assertIn("SMTPDataError", rendered)

    def test_find_mail_server_parses_each_from_filter_once(self):
        IrMailServer = self.env["ir.mail_server"]
        servers = IrMailServer.create(
            [
                {
                    "name": f"probe{i}",
                    "smtp_host": f"host{i}.example.com",
                    "smtp_encryption": "none",
                    "smtp_authentication": "login",
                    "from_filter": f"probe{i}.example.com",
                }
                for i in range(5)
            ]
        )

        seen = []
        original = type(IrMailServer)._parse_from_filter

        def counting(self, from_filter):
            seen.append(from_filter)
            return original(self, from_filter)

        with patch.object(type(IrMailServer), "_parse_from_filter", counting):
            IrMailServer.sudo()._get_mail_server(
                "nobody@nomatch.example.org", mail_servers=servers
            )

        repeats = {ff: n for ff, n in Counter(seen).items() if n > 1}
        self.assertFalse(repeats, f"from_filter re-parsed: {repeats}")

    def test_bpo_34424_35805(self):
        fake_smtp = _FakeSMTP()
        msg = email.message.EmailMessage(policy=email.policy.SMTP)
        msg["From"] = '"Joé Doe" <joe@example.com>'
        msg["To"] = '"Joé Doe" <joe@example.com>'

        msg["Message-Id"] = (
            "<929227342217024.1596730490.324691772460938-example-30661-some.reference@test-123.example.com>"
        )
        msg["References"] = (
            "<345227342212345.1596730777.324691772483620-example-30453-other.reference@test-123.example.com>"
        )

        msg_on_the_wire = self._send_email(msg, fake_smtp)
        self.assertEqual(
            msg_on_the_wire,
            "From: =?utf-8?q?Jo=C3=A9?= Doe <joe@example.com>\r\n"
            "To: =?utf-8?q?Jo=C3=A9?= Doe <joe@example.com>\r\n"
            "Message-Id: <929227342217024.1596730490.324691772460938-example-30661-some.reference@test-123.example.com>\r\n"
            "References: <345227342212345.1596730777.324691772483620-example-30453-other.reference@test-123.example.com>\r\n"
            "\r\n",
        )

    def test_content_alternative_correct_order(self):
        fake_smtp = _FakeSMTP()
        msg = self._build_email(
            "test@example.com", body="<p>Hello world</p>", subtype="html"
        )
        msg_on_the_wire = self._send_email(msg, fake_smtp)

        self.assertGreater(
            msg_on_the_wire.index("text/html"),
            msg_on_the_wire.index("text/plain"),
            "The html part should be preferred (=appear after) to the text part",
        )
        self.assertEqual(
            msg_on_the_wire.count("==============="),
            2 + 2,
            "There should be 2 parts: one text and one html",
        )
        self.assertEqual(
            msg_on_the_wire.count("MIME-Version: 1.0"),
            3,
            "There should be 3 headers MIME-Version: one on the enveloppe, one on the html part, one on the text part",
        )

    def test_content_mail_body(self):
        bodies = [
            "content",
            "<p>content</p>",
            '<head><meta content="text/html; charset=utf-8" http-equiv="Content-Type"></head><body><p>content</p></body>',
            MISC_HTML_SOURCE,
            QUOTE_THUNDERBIRD_HTML,
        ]
        expected_list = [
            "content",
            "content",
            "content",
            "test1\n*test2*\ntest3\ntest4\ntest5\ntest6   test7\ntest8    test9\ntest10\ntest11\ntest12\ngoogle [1]\ntest link [2]\n\n\n[1] http://google.com\n[2] javascript:alert('malicious code')",
            "On 01/05/2016 10:24 AM, Raoul\nPoilvache wrote:\n\n* Test reply. The suite. *\n\n--\nRaoul Poilvache\n\nTop cool !!!\n\n--\nRaoul Poilvache",
        ]
        for body, expected in zip(bodies, expected_list, strict=False):
            message = self.env["ir.mail_server"]._prepare_email__(
                "john.doe@from.example.com",
                "destinataire@to.example.com",
                body=body,
                subject="Subject",
                subtype="html",
            )
            body_alternative = None
            for part in message.walk():
                if part.get_content_maintype() == "multipart":
                    continue
                if part.get_content_type() == "text/plain":
                    if not part.get_payload():
                        continue
                    body_alternative = part.get_content().rstrip("\n")
            self.assertEqual(body_alternative, expected)

    @mute_logger("odoo.db")
    def test_mail_server_auth_cert_requires_tls(self):
        with self.assertRaises(psycopg.errors.CheckViolation):
            self.env["ir.mail_server"].create(
                {
                    "name": "test",
                    "smtp_host": "smtp_host",
                    "smtp_encryption": "none",
                    "smtp_authentication": "certificate",
                }
            )

    def test_mail_server_match_from_filter(self):
        tests = [
            ("admin@mail.example.com", "mail.example.com"),
            ("admin@mail.example.com", "mail.EXAMPLE.com"),
            ("admin@mail.example.com", "admin@mail.example.com"),
            ("admin@mail.example.com", False),
            (
                '"fake@test.mycompany.com" <admin@mail.example.com>',
                "mail.example.com",
            ),
            (
                '"fake@test.mycompany.com" <ADMIN@mail.example.com>',
                "mail.example.com",
            ),
            (
                '"fake@test.mycompany.com" <ADMIN@mail.example.com>',
                "test.mycompany.com, mail.example.com, test2.com",
            ),
        ]
        for email_addr, from_filter in tests:
            self.assertTrue(
                self.env["ir.mail_server"]._match_from_filter(email_addr, from_filter)
            )

        tests = [
            ("admin@mail.example.com", "test@mail.example.com"),
            ("admin@mail.example.com", "test.mycompany.com"),
            ("admin@mail.example.com", "mail.éxample.com"),
            ("admin@mmail.example.com", "mail.example.com"),
            ("admin@mail.example.com", "mmail.example.com"),
            (
                '"admin@mail.example.com" <fake@test.mycompany.com>',
                "mail.example.com",
            ),
            (
                '"fake@test.mycompany.com" <ADMIN@mail.example.com>',
                "test.mycompany.com, wrong.mail.example.com, test3.com",
            ),
        ]
        for email_addr, from_filter in tests:
            self.assertFalse(
                self.env["ir.mail_server"]._match_from_filter(email_addr, from_filter)
            )

    @mute_logger("odoo.models.unlink")
    def test_mail_server_priorities(self):
        for email_from, (expected_mail_server, expected_email_from) in zip(
            [
                "specific_user@test.mycompany.com",
                "unknown_email@test.mycompany.com",
                '"Test" <test@unknown_domain.com>',
            ],
            [
                (self.mail_server_user, "specific_user@test.mycompany.com"),
                (self.mail_server_domain, "unknown_email@test.mycompany.com"),
                (self.mail_server_default, '"Test" <test@unknown_domain.com>'),
            ],
            strict=False,
        ):
            with self.subTest(email_from=email_from):
                mail_server, mail_from = self.env["ir.mail_server"]._get_mail_server(
                    email_from=email_from
                )
                self.assertEqual(mail_server, expected_mail_server)
                self.assertEqual(mail_from, expected_email_from)

    @mute_logger("odoo.models.unlink")
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
                    "test@unknown_domain.com",
                    '"Name" <test@unknown_domain.com>',
                    self.mail_server_default,
                ),
                (
                    "test@unknown_domain.com",
                    "test@unknown_domain.com",
                    self.mail_server_default,
                ),
                (
                    "unknown_name@test.mycompany.com",
                    '"Name" <unknown_name@test.mycompany.com>',
                    self.mail_server_domain,
                ),
            ],
            strict=False,
        ):
            for provide_smtp in [False, True]:
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
                smtp_from="test@unknown_domain.com",
                message_from='"Name" <test@unknown_domain.com>',
                from_filter=False,
            )

    @mute_logger("odoo.models.unlink", "odoo.addons.mail.models.ir_mail_server")
    def test_mail_server_send_email_context_force(self):
        context_server = self.env["ir.mail_server"].create(
            {
                "from_filter": "context.example.com",
                "name": "context",
                "smtp_host": "test",
            }
        )
        IrMailServer = self.env["ir.mail_server"].with_context(
            domain_notifications_email="notification@context.example.com",
            domain_bounce_address="bounce@context.example.com",
        )
        with self.mock_smtplib_connection():
            mail_server, smtp_from = IrMailServer._get_mail_server(
                email_from='"Name" <test@unknown_domain.com>'
            )
            self.assertEqual(mail_server, context_server)
            self.assertEqual(smtp_from, "notification@context.example.com")
            smtp_session = IrMailServer._connect__(smtp_from=smtp_from)
            message = self._build_email(mail_from='"Name" <test@unknown_domain.com>')
            IrMailServer.send_email(message, smtp_session=smtp_session)

        self.assertEqual(len(self.emails), 1)
        self.assertSMTPEmailsSent(
            smtp_from="bounce@context.example.com",
            message_from='"Name" <notification@context.example.com>',
            from_filter=context_server.from_filter,
        )

        self.env["ir.mail_server"].search([]).from_filter = "random.domain"
        with self.mock_smtplib_connection():
            message = self._build_email(mail_from="specific_user@test.com")
            IrMailServer.with_context(
                domain_notifications_email="test@custom_domain.com"
            ).send_email(message)

        self.connect_mocked.assert_called_once()
        self.assertSMTPEmailsSent(
            smtp_from="test@custom_domain.com",
            message_from='"specific_user" <test@custom_domain.com>',
            from_filter="random.domain",
        )

    @mute_logger("odoo.models.unlink")
    def test_mail_server_send_email_IDNA(self):
        with self.mock_smtplib_connection():
            message = self._build_email(mail_from="test@ééééééé.com")
            self.env["ir.mail_server"].send_email(message)

        self.assertEqual(len(self.emails), 1)
        self.assertSMTPEmailsSent(
            smtp_from="test@xn--9caaaaaaa.com",
            smtp_to_list=["dest@xn--example--i1a.com"],
            message_from="test@=?utf-8?b?w6nDqcOpw6nDqcOpw6k=?=.com",
            from_filter=False,
        )

    @mute_logger("odoo.models.unlink", "odoo.addons.mail.models.ir_mail_server")
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
                (
                    "specific_user@test.mycompany.com",
                    "specific_user@test.mycompany.com",
                ),
                (
                    "specific_user@test.mycompany.com",
                    '"Formatted Name" <specific_user@test.mycompany.com>',
                ),
                (
                    "specific_user@test.MYCOMPANY.com",
                    '"Formatted Name" <specific_user@test.MYCOMPANY.com>',
                ),
                (
                    "SPECIFIC_USER@test.mycompany.com",
                    '"Formatted Name" <SPECIFIC_USER@test.mycompany.com>',
                ),
                ("test@unknown_domain.com", "test@unknown_domain.com"),
                (
                    "test@unknown_domain.com",
                    '"Formatted Name" <test@unknown_domain.com>',
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

    @mute_logger("odoo.models.unlink")
    @config.patch(from_filter="fake.com", smtp_server="cli_example.com")
    def test_mail_server_config_cli(self):
        IrMailServer = self.env["ir.mail_server"]
        self.env["ir.config_parameter"].sudo().set_param(
            "mail.default.from_filter", "fake.com"
        )

        server_other = IrMailServer.create(
            [
                {
                    "name": "Server No From Filter",
                    "smtp_host": "smtp_host",
                    "smtp_encryption": "none",
                    "smtp_authentication": "cli",
                    "from_filter": "dummy@example.com, cli_example.com, dummy2@example.com",
                }
            ]
        )

        for mail_from, (
            expected_smtp_from,
            expected_msg_from,
            expected_mail_server,
        ) in zip(
            [
                "test@cli_example.com",
                "specific_user@test.mycompany.com",
            ],
            [
                ("test@cli_example.com", "test@cli_example.com", server_other),
                (
                    "specific_user@test.mycompany.com",
                    "specific_user@test.mycompany.com",
                    self.mail_server_user,
                ),
            ],
            strict=False,
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
        IrMailServer = self.env["ir.mail_server"]

        eml_content = b"From: user@example.com\nTo: user2@example.com\nSubject: Test Email\n\nThis is a test email."
        attachments = [("test.eml", eml_content, "message/rfc822")]

        message = IrMailServer._prepare_email__(
            email_from="john.doe@from.example.com",
            email_to="destinataire@to.example.com",
            subject="Subject with .eml attachment",
            body="This email contains a .eml attachment.",
            attachments=attachments,
        )

        acceptable_encodings = {"7bit", "8bit", "binary"}
        found_rfc822_part = False

        for part in message.iter_attachments():
            if part.get_content_type() == "message/rfc822":
                found_rfc822_part = True
                encoding = part.get("Content-Transfer-Encoding", "7bit").lower()

                self.assertIn(
                    encoding,
                    acceptable_encodings,
                    f"RFC violation: message/rfc822 attachment has Content-Transfer-Encoding '{encoding}'. "
                    f"Only 7bit, 8bit, or binary encoding is permitted per RFC 2046 Section 5.2.1.",
                )

        self.assertTrue(
            found_rfc822_part,
            "No message/rfc822 attachment found in the built email",
        )

    def test_eml_message_serialization_with_non_ascii(self):
        IrMailServer = self.env["ir.mail_server"]

        eml_content = "From: user@example.com\nTo: user2@example.com\nSubject: Test\n\nBody with é"
        attachments = [("test.eml", eml_content.encode(), "message/rfc822")]

        message = IrMailServer._prepare_email__(
            email_from="john.doe@from.example.com",
            email_to="destinataire@to.example.com",
            subject="Serialization test",
            body="This email contains a .eml attachment.",
            attachments=attachments,
        )

        try:
            serialized = message.as_string().encode("utf-8")
        except UnicodeEncodeError as e:
            msg = "Email with non-ASCII .eml attachment could not be serialized"
            raise AssertionError(msg) from e

        self.assertIsInstance(serialized, bytes)


@tagged("mail_server")
class TestSslContexts(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.cert_pem, cls.key_pem = _generate_self_signed_cert("smtp.example.com")
        _, cls.mismatched_key_pem = _generate_self_signed_cert("smtp.example.com")

    def _make_cert_server(self, encryption, key_pem=None):
        return self.env["ir.mail_server"].create(
            {
                "name": f"cert-{encryption}",
                "smtp_host": "smtp.example.com",
                "smtp_authentication": "certificate",
                "smtp_encryption": encryption,
                "smtp_ssl_certificate": base64.b64encode(self.cert_pem),
                "smtp_ssl_private_key": base64.b64encode(key_pem or self.key_pem),
            }
        )

    def test_ssl_context_for_encryption_modes(self):
        IrMailServer = self.env["ir.mail_server"]
        for encryption in ("ssl_strict", "starttls_strict"):
            ctx = IrMailServer._prepare_ssl_context_for_encryption(encryption)
            self.assertTrue(ctx.check_hostname, encryption)
            self.assertEqual(ctx.verify_mode, ssl.CERT_REQUIRED, encryption)
        for encryption in ("ssl", "starttls"):
            ctx = IrMailServer._prepare_ssl_context_for_encryption(encryption)
            self.assertFalse(ctx.check_hostname, encryption)
            self.assertEqual(ctx.verify_mode, ssl.CERT_NONE, encryption)

    def test_ssl_context_from_cert_files(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            cert_path = Path(tmp) / "cert.pem"
            key_path = Path(tmp) / "key.pem"
            cert_path.write_bytes(self.cert_pem)
            key_path.write_bytes(self.key_pem)
            ctx = self.env["ir.mail_server"]._prepare_ssl_context_from_cert_files(
                str(cert_path), str(key_path)
            )
            self.assertEqual(type(ctx).__name__, "PyOpenSSLContext")

    def test_ssl_context_from_cert_files_strict_verifies_peer(self):
        import tempfile
        from pathlib import Path

        from OpenSSL.SSL import VERIFY_FAIL_IF_NO_PEER_CERT, VERIFY_NONE, VERIFY_PEER

        IrMailServer = self.env["ir.mail_server"]
        with tempfile.TemporaryDirectory() as tmp:
            cert_path = Path(tmp) / "cert.pem"
            key_path = Path(tmp) / "key.pem"
            cert_path.write_bytes(self.cert_pem)
            key_path.write_bytes(self.key_pem)
            for encryption in ("ssl_strict", "starttls_strict"):
                ctx = IrMailServer._prepare_ssl_context_from_cert_files(
                    str(cert_path), str(key_path), encryption, "smtp.example.com"
                )
                self.assertEqual(
                    ctx._ctx.get_verify_mode(),
                    VERIFY_PEER | VERIFY_FAIL_IF_NO_PEER_CERT,
                    encryption,
                )
            for encryption in (None, "none", "ssl", "starttls"):
                ctx = IrMailServer._prepare_ssl_context_from_cert_files(
                    str(cert_path), str(key_path), encryption, "smtp.example.com"
                )
                self.assertEqual(ctx._ctx.get_verify_mode(), VERIFY_NONE, encryption)

    def test_connect_cert_files_strict_encryption_verifies(self):
        import tempfile
        from pathlib import Path

        from OpenSSL.SSL import VERIFY_FAIL_IF_NO_PEER_CERT, VERIFY_PEER

        with tempfile.TemporaryDirectory() as tmp:
            cert_path = Path(tmp) / "cert.pem"
            key_path = Path(tmp) / "key.pem"
            cert_path.write_bytes(self.cert_pem)
            key_path.write_bytes(self.key_pem)
            captured = self._capture_connect_context(
                smtp_server="smtp.example.com",
                smtp_port=465,
                smtp_ssl="ssl_strict",
                smtp_ssl_certificate_filename=str(cert_path),
                smtp_ssl_private_key_filename=str(key_path),
            )
            ctx = captured["ssl"]
            self.assertEqual(type(ctx).__name__, "PyOpenSSLContext")
            self.assertEqual(
                ctx._ctx.get_verify_mode(),
                VERIFY_PEER | VERIFY_FAIL_IF_NO_PEER_CERT,
            )

    def test_ssl_context_from_certificate_builds_for_all_variants(self):
        for encryption in ("starttls", "starttls_strict", "ssl", "ssl_strict"):
            server = self._make_cert_server(encryption)
            ctx = server._prepare_ssl_context_from_certificate()
            self.assertEqual(type(ctx).__name__, "PyOpenSSLContext", encryption)

    def test_ssl_context_from_certificate_key_mismatch_raises_usererror(self):
        with self.assertRaises(UserError):
            self._make_cert_server("starttls_strict", key_pem=self.mismatched_key_pem)

    def _capture_connect_context(self, **config_values):
        captured = {}

        class _FakeConn:
            def __init__(self, *a, **kw):
                captured["ssl"] = kw.get("context")

            def set_debuglevel(self, *a):
                pass

            def starttls(self, context=None):
                captured["starttls"] = context

            def ehlo_or_helo_if_needed(self):
                pass

        IrMailServer = self.env["ir.mail_server"]
        with (
            patch.object(type(IrMailServer), "_disable_send", lambda _: False),
            patch("smtplib.SMTP_SSL", _FakeConn),
            patch("smtplib.SMTP", _FakeConn),
            config.patch(**config_values),
        ):
            transport = IrMailServer._prepare_smtp_transport()
            IrMailServer._open_smtp_connection(transport, None)
        return captured

    def test_connect_raw_param_strict_encryption_verifies(self):
        captured = self._capture_connect_context(
            smtp_server="smtp.example.test", smtp_port=465, smtp_ssl="ssl_strict"
        )
        ctx = captured["ssl"]
        self.assertIsNotNone(ctx, "ssl_strict must not connect with context=None")
        self.assertTrue(ctx.check_hostname)
        self.assertEqual(ctx.verify_mode, ssl.CERT_REQUIRED)

        captured = self._capture_connect_context(
            smtp_server="smtp.example.test", smtp_port=587, smtp_ssl="starttls_strict"
        )
        ctx = captured["starttls"]
        self.assertIsNotNone(ctx, "starttls_strict must not STARTTLS with context=None")
        self.assertTrue(ctx.check_hostname)
        self.assertEqual(ctx.verify_mode, ssl.CERT_REQUIRED)

    def test_connect_raw_param_lax_encryption_unchanged(self):
        captured = self._capture_connect_context(
            smtp_server="smtp.example.test", smtp_port=465, smtp_ssl="ssl"
        )
        ctx = captured["ssl"]
        self.assertFalse(ctx.check_hostname)
        self.assertEqual(ctx.verify_mode, ssl.CERT_NONE)

    def test_connect_bare_smtp_ssl_flag_is_verified_starttls(self):
        captured = self._capture_connect_context(
            smtp_server="smtp.example.test", smtp_port=587, smtp_ssl=True
        )
        self.assertIsNone(captured["ssl"], "True must not select implicit TLS")
        ctx = captured["starttls"]
        self.assertTrue(ctx.check_hostname)
        self.assertEqual(ctx.verify_mode, ssl.CERT_REQUIRED)

    def test_cli_encryption_follows_the_smtp_ssl_option(self):
        IrMailServer = self.env["ir.mail_server"].browse()
        for smtp_ssl, expected in (
            (False, None),
            (True, "starttls_strict"),
            ("starttls", "starttls"),
            ("starttls_strict", "starttls_strict"),
            ("ssl", "ssl"),
            ("ssl_strict", "ssl_strict"),
        ):
            with self.subTest(smtp_ssl=smtp_ssl), config.patch(smtp_ssl=smtp_ssl):
                transport = IrMailServer._prepare_smtp_transport()
                self.assertEqual(transport.encryption, expected)
                self.assertEqual(transport.ssl_context is None, expected is None)

    def test_smtp_ssl_option_parses_modes_and_booleans(self):
        self.assertIs(config.parse("smtp_ssl", "True"), True)
        self.assertIs(config.parse("smtp_ssl", "false"), False)
        self.assertIs(config.parse("smtp_ssl", "none"), False)
        for mode in ("starttls_strict", "starttls", "ssl_strict", "ssl"):
            self.assertEqual(config.parse("smtp_ssl", mode), mode)
        with self.assertRaisesRegex(Exception, "invalid value: 'tls'"):
            config.parse("smtp_ssl", "tls")


class TestResolveTransport(TransactionCase):
    def test_resolve_from_record(self):
        IrMailServer = self.env["ir.mail_server"]
        server = IrMailServer.create(
            {
                "name": "rec",
                "smtp_host": "mail.record.test",
                "smtp_port": 2525,
                "smtp_user": "u@record.test",
                "smtp_pass": "secret",
                "smtp_encryption": "starttls_strict",
                "smtp_authentication": "login",
                "from_filter": "record.test",
            }
        )
        t = server._prepare_smtp_transport()
        self.assertEqual(t.server, "mail.record.test")
        self.assertEqual(t.port, 2525)
        self.assertEqual(t.user, "u@record.test")
        self.assertEqual(t.password, "secret")
        self.assertEqual(t.encryption, "starttls_strict")
        self.assertEqual(t.from_filter, "record.test")
        self.assertEqual(t.login_server, server)
        self.assertTrue(t.ssl_context.check_hostname)

    def test_resolve_cli_auth_record_ignores_record_transport(self):
        IrMailServer = self.env["ir.mail_server"]
        server = IrMailServer.create(
            {
                "name": "cli",
                "smtp_host": "ignored.test",
                "smtp_port": 9999,
                "smtp_authentication": "cli",
                "from_filter": "cli.test",
            }
        )
        with config.patch(smtp_server="cli.host", smtp_port=25):
            t = server._prepare_smtp_transport()
        self.assertEqual(
            t.server, "cli.host", "record host must be ignored for cli auth"
        )
        self.assertEqual(t.from_filter, "cli.test", "record from_filter is still used")
        self.assertEqual(t.login_server, server)

    def test_session_context_roundtrip(self):
        from odoo.addons.mail.models.ir_mail_server import _SmtpSessionContext

        IrMailServer = self.env["ir.mail_server"]

        class _BareSession:
            pass

        conn = _BareSession()
        with mute_logger("odoo.addons.mail.models.ir_mail_server"):
            self.assertEqual(
                IrMailServer._read_session_context(conn),
                _SmtpSessionContext(from_filter=False, smtp_from=False),
                "a session this model never opened enforces nothing, loudly",
            )
        IrMailServer._stash_session_context(
            conn,
            _SmtpSessionContext(from_filter="example.com", smtp_from="a@example.com"),
        )
        ctx = IrMailServer._read_session_context(conn)
        self.assertEqual(ctx.from_filter, "example.com")
        self.assertEqual(ctx.smtp_from, "a@example.com")
        self.assertFalse(
            hasattr(conn, "from_filter"),
            "the session object itself is left untouched",
        )
