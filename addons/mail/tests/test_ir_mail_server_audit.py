import base64
import contextlib
import datetime
import email.policy
import gc
import inspect
import logging
import re
import smtplib
import ssl
import tempfile
import weakref
from email.message import EmailMessage
from pathlib import Path
from unittest.mock import patch

import psycopg
from urllib3.util.ssl_match_hostname import CertificateError

from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.service.model import call_kw, get_public_method
from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.tools import config, email_domain_extract, email_normalize, mute_logger

from odoo.addons.mail.models.ir_mail_server import (
    IMPLICIT_TLS_ENCRYPTIONS,
    STARTTLS_ENCRYPTIONS,
    VERIFIED_ENCRYPTIONS,
    MailDeliveryError,
    OutgoingEmailError,
    _check_hostname_callback,
    _log_smtp_debug,
    _SmtpSessionContext,
)

_IR_MAIL_SERVER_LOGGER = "odoo.addons.mail.models.ir_mail_server"


@tagged("post_install", "-at_install")
class TestMailServerArchiveAndHeaders(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.IrMailServer = cls.env["ir.mail_server"]
        cls.server_b, cls.server_a, cls.server_c = cls.IrMailServer.create(
            [
                {
                    "name": "Bravo Server",
                    "smtp_host": "smtp_host",
                    "smtp_encryption": "none",
                    "from_filter": "bravo.example.com",
                },
                {
                    "name": "Alpha Server",
                    "smtp_host": "smtp_host",
                    "smtp_encryption": "none",
                    "from_filter": "alpha.example.com",
                },
                {
                    "name": "Charlie Server",
                    "smtp_host": "smtp_host",
                    "smtp_encryption": "none",
                    "from_filter": "charlie.example.com",
                },
            ]
        )

    def test_smtp_connection_test_disabled_send_raises_clean_error(self):
        self.assertTrue(self.IrMailServer._disable_send())
        with self.assertRaises(UserError) as ctx:
            self.server_a.test_smtp_connection()
        self.assertIn("outgoing emails are disabled", str(ctx.exception))

    def test_archive_unused_server_succeeds(self):
        self.assertEqual(self.IrMailServer._get_active_usages(), {})
        self.server_a.active = True
        self.server_a.write({"active": False})
        self.assertFalse(self.server_a.active)

    @mute_logger(_IR_MAIL_SERVER_LOGGER)
    def test_archive_ignores_usages_of_servers_not_being_archived(self):
        usages = {self.server_c.id: ["Charlie usage"]}
        with patch.object(
            type(self.IrMailServer),
            "_get_active_usages",
            lambda self: usages,
        ):
            self.server_a.write({"active": False})
        self.assertFalse(self.server_a.active)

    @mute_logger(_IR_MAIL_SERVER_LOGGER)
    def test_archive_single_server_message_stays_singular(self):
        usages = {
            self.server_a.id: ["Alpha usage"],
            self.server_b.id: ["Bravo usage"],
        }
        with patch.object(
            type(self.IrMailServer),
            "_get_active_usages",
            lambda self: usages,
        ):
            with self.assertRaises(UserError) as ctx:
                self.server_a.write({"active": False})
        message = str(ctx.exception)
        self.assertIn("You cannot archive this Outgoing Mail Server", message)
        self.assertNotIn("Bravo", message)
        self.assertNotIn("(Dedicated Outgoing Mail Server)", message)

    def test_archive_non_active_write_skips_usage_check(self):
        usages = {self.server_a.id: ["Some usage"]}
        with patch.object(
            type(self.IrMailServer),
            "_get_active_usages",
            lambda self: usages,
        ):
            self.server_a.write({"name": "Alpha Renamed"})
        self.assertEqual(self.server_a.name, "Alpha Renamed")
        self.assertTrue(self.server_a.active)

    @mute_logger(_IR_MAIL_SERVER_LOGGER)
    def test_archive_single_used_server_message(self):
        usages = {self.server_a.id: ["Used by alias catchall"]}
        with patch.object(
            type(self.IrMailServer),
            "_get_active_usages",
            lambda self: usages,
        ):
            with self.assertRaises(UserError) as ctx:
                self.server_a.write({"active": False})
        message = str(ctx.exception)
        self.assertIn("You cannot archive this Outgoing Mail Server", message)
        self.assertIn("Alpha Server", message)
        self.assertIn("- Used by alias catchall", message)
        self.assertNotIn("(Dedicated Outgoing Mail Server)", message)
        self.assertTrue(self.server_a.active)

    @mute_logger(_IR_MAIL_SERVER_LOGGER)
    def test_archive_multiple_used_servers_message_and_ordering(self):
        servers = self.server_b | self.server_a | self.server_c
        usages = {
            self.server_a.id: ["Alpha usage"],
            self.server_b.id: ["Bravo usage"],
            self.server_c.id: ["Charlie usage"],
        }
        with patch.object(
            type(self.IrMailServer),
            "_get_active_usages",
            lambda self: usages,
        ):
            with self.assertRaises(UserError) as ctx:
                servers.write({"active": False})
        message = str(ctx.exception)
        self.assertIn("You cannot archive these Outgoing Mail Servers", message)
        self.assertIn("Alpha Server (Dedicated Outgoing Mail Server):", message)
        self.assertIn("Bravo Server (Dedicated Outgoing Mail Server):", message)
        self.assertIn("Charlie Server (Dedicated Outgoing Mail Server):", message)
        self.assertLess(message.index("Alpha Server"), message.index("Bravo Server"))
        self.assertLess(message.index("Bravo Server"), message.index("Charlie Server"))
        self.assertLess(message.index("Alpha usage"), message.index("Bravo usage"))
        self.assertLess(message.index("Bravo usage"), message.index("Charlie usage"))
        self.assertTrue(all(servers.mapped("active")))

    def _make_message(self):
        message = EmailMessage(policy=email.policy.SMTP)
        message["From"] = "sender@example.com"
        message["Subject"] = "Subject"
        return message

    def test_alter_message_x_msg_to_add_empty_to(self):
        message = self._make_message()
        message["X-Msg-To-Add"] = "added@example.com"
        self.IrMailServer._alter_message__(message, "sender@example.com")
        self.assertEqual(message["To"], "added@example.com")
        self.assertIsNone(message["X-Msg-To-Add"])

    def test_alter_message_x_msg_to_add_dedupes_against_existing_to(self):
        message = self._make_message()
        message["To"] = "keep@example.com"
        message["X-Msg-To-Add"] = "keep@example.com, extra@example.com"
        self.IrMailServer._alter_message__(message, "sender@example.com")
        self.assertEqual(message["To"], "keep@example.com, extra@example.com")

    def test_alter_message_x_msg_to_add_dedupes_within_the_header(self):
        message = self._make_message()
        message["To"] = "keep@example.com"
        message["X-Msg-To-Add"] = (
            "bob@example.com, Bob <bob@example.com>, extra@example.com"
        )
        self.IrMailServer._alter_message__(message, "sender@example.com")
        self.assertEqual(
            message["To"], "keep@example.com, bob@example.com, extra@example.com"
        )

    def test_alter_message_x_forge_to_overrides_and_scrubs_headers(self):
        message = self._make_message()
        message["To"] = "original@example.com"
        message["Bcc"] = "hidden@example.com"
        message["X-Forge-To"] = "forged@example.com"
        message["X-Msg-To-Add"] = "ignored@example.com"
        self.IrMailServer._alter_message__(message, "sender@example.com")
        self.assertEqual(message["To"], "forged@example.com")
        self.assertIsNone(message["Bcc"])
        self.assertIsNone(message["X-Forge-To"])
        self.assertIsNone(message["X-Msg-To-Add"])
        self.assertEqual(message["From"], "sender@example.com")


class _FailingSMTPSession:
    from_filter = False
    smtp_from = False

    def send_message(self, message, smtp_from, smtp_to_list):
        raise smtplib.SMTPDataError(554, b"5.7.1 rejected")


@tagged("post_install", "-at_install")
class TestMailServerSendFailureObservability(TransactionCase):
    def _make_message(self):
        message = EmailMessage(policy=email.policy.SMTP)
        message["From"] = "sender@example.com"
        message["To"] = "recipient@example.com"
        message["Subject"] = "Subject"
        return message

    def test_send_email_failure_warns_and_chains(self):
        IrMailServer = self.env["ir.mail_server"]
        with (
            patch.object(
                type(IrMailServer), "_disable_send", classmethod(lambda cls: False)
            ),
            self.assertLogs(_IR_MAIL_SERVER_LOGGER, level="WARNING") as capture,
            self.assertRaises(MailDeliveryError) as ctx,
        ):
            IrMailServer.send_email(
                self._make_message(), smtp_session=_FailingSMTPSession()
            )

        self.assertIsInstance(ctx.exception.__cause__, smtplib.SMTPDataError)
        rendered = str(ctx.exception)
        self.assertTrue(rendered.startswith("Mail Delivery Failed\n"))
        self.assertIn("Mail delivery failed via SMTP server 'unknown'", rendered)
        self.assertIn("SMTPDataError", rendered)
        record = next(
            r for r in capture.records if "Mail delivery failed" in r.getMessage()
        )
        self.assertEqual(record.levelno, logging.WARNING)
        self.assertIsNotNone(record.exc_info)


@tagged("post_install", "-at_install")
class TestMailServerOnchangeEncryption(TransactionCase):
    def _new_server(self, encryption, port):
        return self.env["ir.mail_server"].new(
            {
                "name": "Onchange Server",
                "smtp_host": "smtp_host",
                "smtp_encryption": encryption,
                "smtp_port": port,
            }
        )

    def test_default_port_follows_encryption(self):
        server = self._new_server("none", 25)
        server.smtp_encryption = "ssl"
        server._onchange_smtp_encryption()
        self.assertEqual(server.smtp_port, 465)
        server.smtp_encryption = "none"
        server._onchange_smtp_encryption()
        self.assertEqual(server.smtp_port, 25)
        server.smtp_encryption = "ssl_strict"
        server._onchange_smtp_encryption()
        self.assertEqual(server.smtp_port, 465)
        server.smtp_encryption = "starttls_strict"
        server._onchange_smtp_encryption()
        self.assertEqual(server.smtp_port, 25)

    def test_custom_port_survives_toggle(self):
        server = self._new_server("none", 2525)
        server.smtp_encryption = "ssl"
        server._onchange_smtp_encryption()
        self.assertEqual(server.smtp_port, 2525)
        server.smtp_encryption = "starttls"
        server._onchange_smtp_encryption()
        self.assertEqual(server.smtp_port, 2525)

    def test_starttls_submission_port_survives_ssl_toggle(self):
        server = self._new_server("starttls", 587)
        server.smtp_encryption = "ssl_strict"
        server._onchange_smtp_encryption()
        self.assertEqual(server.smtp_port, 587)
        server.smtp_encryption = "starttls"
        server._onchange_smtp_encryption()
        self.assertEqual(server.smtp_port, 587)


@tagged("post_install", "-at_install")
class TestSmtpRecipientList(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.IrMailServer = cls.env["ir.mail_server"]

    def _message(self, to=None, cc=None, bcc=None):
        message = EmailMessage(policy=email.policy.SMTP)
        message["From"] = "sender@example.com"
        for header, value in (("To", to), ("Cc", cc), ("Bcc", bcc)):
            if value:
                message[header] = value
        return message

    def test_recipient_repeated_across_headers_is_sent_once(self):
        message = self._message(
            to="dup@example.com, only_to@example.com",
            cc="dup@example.com",
            bcc="dup@example.com, only_bcc@example.com",
        )
        self.assertEqual(
            self.IrMailServer._prepare_smtp_to_list(message, None),
            ["dup@example.com", "only_to@example.com", "only_bcc@example.com"],
        )

    def test_recipient_dedup_is_case_insensitive(self):
        message = self._message(to="Dup@Example.COM", cc="dup@example.com")
        self.assertEqual(
            self.IrMailServer._prepare_smtp_to_list(message, None),
            ["Dup@Example.COM"],
        )

    def test_recipient_order_is_to_then_cc_then_bcc(self):
        message = self._message(
            to="a@example.com", cc="b@example.com", bcc="c@example.com"
        )
        self.assertEqual(
            self.IrMailServer._prepare_smtp_to_list(message, None),
            ["a@example.com", "b@example.com", "c@example.com"],
        )

    def test_validated_to_accepts_normalized_match(self):
        message = self._message(to='"Alice B" <Alice@Example.COM>')
        self.assertEqual(
            self.IrMailServer.with_context(
                send_validated_to=["alice@example.com"]
            )._prepare_smtp_to_list(message, None),
            ["Alice@Example.COM"],
        )

    def test_validated_to_still_filters_unvetted_addresses(self):
        message = self._message(to="alice@example.com, mallory@example.com")
        self.assertEqual(
            self.IrMailServer.with_context(
                send_validated_to=["alice@example.com"]
            )._prepare_smtp_to_list(message, None),
            ["alice@example.com"],
        )

    def test_skip_list_still_blocks_recipients(self):
        message = self._message(to="bad@example.com, good@example.com")
        self.assertEqual(
            self.IrMailServer.with_context(
                send_smtp_skip_to=["bad@example.com"]
            )._prepare_smtp_to_list(message, None),
            ["good@example.com"],
        )


@tagged("post_install", "-at_install")
class TestAlterMessageWireFormat(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.IrMailServer = cls.env["ir.mail_server"]

    def _to_line(self, message):
        return next(
            (
                line
                for line in message.as_string().splitlines()
                if line.startswith("To:")
            ),
            None,
        )

    def _message(self, to, x_msg_to_add):
        message = EmailMessage(policy=email.policy.SMTP)
        message["From"] = "sender@example.com"
        message["Subject"] = "Subject"
        if to:
            message["To"] = to
        message["X-Msg-To-Add"] = x_msg_to_add
        return message

    def test_no_original_to_emits_no_leading_comma(self):
        message = self._message(None, "added@example.com")
        self.IrMailServer._alter_message__(message, "sender@example.com")
        self.assertEqual(self._to_line(message), "To: added@example.com")

    def test_fully_redundant_addition_emits_no_trailing_comma(self):
        message = self._message("keep@example.com", "keep@example.com")
        self.IrMailServer._alter_message__(message, "sender@example.com")
        self.assertEqual(self._to_line(message), "To: keep@example.com")

    def test_genuine_addition_is_appended(self):
        message = self._message("keep@example.com", "extra@example.com")
        self.IrMailServer._alter_message__(message, "sender@example.com")
        self.assertEqual(
            self._to_line(message), "To: keep@example.com, extra@example.com"
        )


@tagged("post_install", "-at_install")
class TestEnvelopeOnlyHeaders(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.IrMailServer = cls.env["ir.mail_server"]

    def _message(self):
        message = EmailMessage(policy=email.policy.SMTP)
        message["From"] = "sender@example.com"
        message["To"] = "rcpt@example.com"
        message["Bcc"] = "hidden@example.com"
        message["Return-Path"] = "bounce@example.com"
        message["Subject"] = "Subject"
        return message

    def test_return_path_feeds_the_envelope_then_is_stripped(self):
        message = self._message()
        smtp_from, smtp_to_list, message = self.IrMailServer._prepare_email_message__(
            message, None
        )
        self.assertEqual(
            smtp_from,
            "bounce@example.com",
            "Return-Path still selects the envelope sender",
        )
        self.assertIn("hidden@example.com", smtp_to_list)
        self.assertIsNone(message["Return-Path"])
        self.assertIsNone(message["Bcc"])
        self.assertNotIn("Return-Path", message.as_string())

    def test_alter_message_strips_return_path(self):
        message = self._message()
        self.IrMailServer._alter_message__(message, "sender@example.com")
        self.assertIsNone(message["Return-Path"])

    def test_falsy_header_value_emits_no_header(self):
        message = self.IrMailServer._prepare_email__(
            email_from="sender@example.com",
            email_to="rcpt@example.com",
            subject="Subject",
            body="body",
            headers={
                "X-Unset": False,
                "X-None": None,
                "X-Empty": "",
                "X-Zero": 0,
                "X-Kept": "value",
                "X-Kept-Numeric": "0",
            },
        )
        wire = message.as_string()
        for header in ("X-Unset", "X-None", "X-Empty", "X-Zero"):
            self.assertIsNone(message[header])
            self.assertNotIn(f"{header}:", wire)
        self.assertIn("X-Kept: value", wire)
        self.assertIn("X-Kept-Numeric: 0", wire)


@tagged("post_install", "-at_install")
class TestFromFilterIndex(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.IrMailServer = cls.env["ir.mail_server"]

    def test_index_splits_addresses_from_domains(self):
        index = self.IrMailServer._from_filter_index(
            " Notify@Example.COM , Example.NET ,, "
        )
        self.assertEqual(index.emails, ("notify@example.com",))
        self.assertEqual(index.domains, ("example.net",))
        self.assertFalse(index.unrestricted)

    def test_separator_only_filter_is_unrestricted(self):
        for from_filter in (" , ", ",,", "   ", "", False):
            with self.subTest(from_filter=from_filter):
                self.assertTrue(
                    self.IrMailServer._from_filter_index(from_filter).unrestricted
                )
                self.assertTrue(
                    self.IrMailServer._match_from_filter(
                        "anyone@example.com", from_filter
                    )
                )

    def test_unparseable_part_restricts_without_matching(self):
        index = self.IrMailServer._from_filter_index("@@@, example.com")
        self.assertEqual(index.emails, ())
        self.assertEqual(index.domains, ("example.com",))
        self.assertEqual(index.unparsed, ("@@@",))

        junk = self.IrMailServer._from_filter_index("@@@")
        self.assertFalse(junk.unrestricted, "junk must not authorize every sender")
        self.assertFalse(self.IrMailServer._match_from_filter("not an email", "@@@"))
        self.assertFalse(
            self.IrMailServer._match_from_filter("real@example.com", "@@@")
        )

    def test_match_from_filter_address_and_domain(self):
        from_filter = "notify@example.com, other.com"
        for sender, expected in (
            ("Notify@Example.com", True),
            ("someone@other.com", True),
            ("someone@example.com", False),
            ("notify@third.com", False),
            (False, False),
        ):
            with self.subTest(sender=sender):
                self.assertIs(
                    self.IrMailServer._match_from_filter(sender, from_filter), expected
                )

    def test_find_mail_server_treats_separator_only_filter_as_unrestricted(self):
        servers = self.IrMailServer.create(
            [
                {
                    "name": "restricted",
                    "smtp_host": "smtp_host",
                    "sequence": 10,
                    "from_filter": "restricted.example.com",
                },
                {
                    "name": "junk filter",
                    "smtp_host": "smtp_host",
                    "sequence": 20,
                    "from_filter": " , ",
                },
            ]
        )
        found, _email_from = self.IrMailServer.sudo()._get_mail_server(
            "someone@elsewhere.example.com", servers
        )
        self.assertEqual(
            found,
            servers[1],
            "the unrestricted server is picked through the regular fallback",
        )


@tagged("post_install", "-at_install")
class TestTransportAndSizeLimits(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.IrMailServer = cls.env["ir.mail_server"]

    def test_cli_authentication_still_honours_smtp_debug(self):
        server = self.IrMailServer.create(
            {
                "name": "cli",
                "smtp_host": "ignored",
                "smtp_authentication": "cli",
                "smtp_debug": True,
                "from_filter": "example.com",
            }
        )
        transport = server._prepare_smtp_transport()
        self.assertTrue(transport.debug)
        self.assertEqual(transport.from_filter, "example.com")

    def test_max_email_size_survives_a_non_numeric_parameter(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "base.default_max_email_size", "ten"
        )
        with self.assertLogs("odoo.addons.base.models.ir_config_parameter", "WARNING"):
            self.assertEqual(self.IrMailServer._get_max_email_size(), 10.0)

    def test_max_email_size_prefers_the_server_value(self):
        server = self.IrMailServer.create(
            {"name": "sized", "smtp_host": "smtp_host", "max_email_size": 42.5}
        )
        self.assertEqual(server._get_max_email_size(), 42.5)


class _Session:
    def __init__(self, features):
        if features is not None:
            self.esmtp_features = features


@tagged("post_install", "-at_install")
class TestSmtputf8Envelope(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.IrMailServer = cls.env["ir.mail_server"]

    def _message(self, email_from="sender@example.com", email_to="rcpt@example.com"):
        message = EmailMessage(policy=email.policy.SMTP)
        message["From"] = email_from
        message["To"] = email_to
        message["Subject"] = "Subject"
        return message

    def test_session_capability_detection(self):
        self.assertTrue(
            self.IrMailServer._is_smtputf8_supported(_Session({"smtputf8": ""})),
        )
        self.assertFalse(
            self.IrMailServer._is_smtputf8_supported(_Session({"size": "10"})),
        )
        self.assertFalse(
            self.IrMailServer._is_smtputf8_supported(_Session({})),
            "a server that spoke EHLO without SMTPUTF8 cannot carry unicode",
        )
        for unknown in (None, _Session(None)):
            self.assertTrue(
                self.IrMailServer._is_smtputf8_supported(unknown),
                "no feature map (test mode / double): assume capable",
            )

    def test_non_ascii_sender_is_a_permanent_from_failure(self):
        message = self._message(email_from="jos\xe9@example.com")
        with self.assertRaises(OutgoingEmailError) as ctx:
            self.IrMailServer._prepare_email_message__(message, _Session({}))
        self.assertEqual(ctx.exception.code, self.IrMailServer.NO_VALID_FROM)
        self.assertIn("SMTPUTF8", str(ctx.exception))

    def test_non_ascii_recipient_is_a_permanent_recipient_failure(self):
        message = self._message(email_to="r\xe9cipient@example.com")
        with self.assertRaises(OutgoingEmailError) as ctx:
            self.IrMailServer._prepare_email_message__(message, _Session({}))
        self.assertEqual(ctx.exception.code, self.IrMailServer.NO_VALID_RECIPIENT)

    def test_non_ascii_allowed_when_the_server_advertises_smtputf8(self):
        message = self._message(
            email_from="jos\xe9@example.com", email_to="r\xe9cipient@example.com"
        )
        smtp_from, smtp_to_list, _msg = self.IrMailServer._prepare_email_message__(
            message, _Session({"smtputf8": ""})
        )
        self.assertEqual(smtp_from, "jos\xe9@example.com")
        self.assertEqual(smtp_to_list, ["r\xe9cipient@example.com"])

    def test_ascii_envelope_is_untouched_on_a_plain_server(self):
        message = self._message()
        smtp_from, smtp_to_list, _msg = self.IrMailServer._prepare_email_message__(
            message, _Session({})
        )
        self.assertEqual(smtp_from, "sender@example.com")
        self.assertEqual(smtp_to_list, ["rcpt@example.com"])


@tagged("post_install", "-at_install")
class TestSmtpTimeout(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.IrMailServer = cls.env["ir.mail_server"]

    def test_timeout_comes_from_the_configuration(self):
        with config.patch(smtp_timeout=12):
            self.assertEqual(self.IrMailServer._get_smtp_timeout(), 12)

    def test_zero_disables_the_timeout(self):
        with config.patch(smtp_timeout=0):
            self.assertIsNone(
                self.IrMailServer._get_smtp_timeout(),
                "0 means block indefinitely, not 'time out immediately'",
            )

    def test_transport_carries_the_timeout_from_both_config_sources(self):
        server = self.IrMailServer.create(
            {"name": "timeout", "smtp_host": "smtp_host", "smtp_encryption": "none"}
        )
        with config.patch(smtp_timeout=7, smtp_server="smtp_host"):
            self.assertEqual(server._prepare_smtp_transport().timeout, 7)
            self.assertEqual(
                self.IrMailServer.browse()._prepare_smtp_transport().timeout, 7
            )


@tagged("post_install", "-at_install")
class TestCertificateLoadErrors(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.IrMailServer = cls.env["ir.mail_server"]

    def test_invalid_stored_certificate_raises_user_error(self):
        with self.assertRaises(UserError) as ctx:
            self.IrMailServer.create(
                {
                    "name": "bad-cert",
                    "smtp_host": "smtp.example.com",
                    "smtp_authentication": "certificate",
                    "smtp_encryption": "starttls_strict",
                    "smtp_ssl_certificate": base64.b64encode(b"not a certificate"),
                    "smtp_ssl_private_key": base64.b64encode(b"not a key"),
                }
            )
        self.assertIn("not a valid file", str(ctx.exception))

    def test_invalid_certificate_files_raise_user_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            cert_path = Path(tmp) / "cert.pem"
            key_path = Path(tmp) / "key.pem"
            cert_path.write_bytes(b"not a certificate")
            key_path.write_bytes(b"not a key")
            with self.assertRaises(UserError) as ctx:
                self.IrMailServer._prepare_ssl_context_from_cert_files(
                    str(cert_path), str(key_path), "starttls_strict", "smtp.example.com"
                )
        self.assertIn("not a valid file", str(ctx.exception))

    def test_non_base64_certificate_field_raises_user_error(self):
        with self.assertRaises(UserError):
            self.IrMailServer.create(
                {
                    "name": "corrupt-cert",
                    "smtp_host": "smtp.example.com",
                    "smtp_authentication": "certificate",
                    "smtp_encryption": "starttls",
                    "smtp_ssl_certificate": b"!!!not base64!!!",
                    "smtp_ssl_private_key": b"!!!not base64!!!",
                }
            )


def _self_signed(common_name, issuer_key=None, issuer_name=None, ca=False):
    import datetime

    from cryptography import x509
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)])
    now = datetime.datetime.now(datetime.UTC)
    builder = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer_name or subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1))
        .not_valid_after(now + datetime.timedelta(days=365))
    )
    if ca:
        builder = builder.add_extension(
            x509.BasicConstraints(ca=True, path_length=None), critical=True
        )
    return builder.sign(issuer_key or key, hashes.SHA256()), key


@tagged("post_install", "-at_install")
class TestCertificateChain(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from cryptography.hazmat.primitives import serialization

        cls.IrMailServer = cls.env["ir.mail_server"]
        ca_cert, ca_key = _self_signed("Intermediate CA", ca=True)
        leaf_cert, leaf_key = _self_signed(
            "smtp.example.com", issuer_key=ca_key, issuer_name=ca_cert.subject
        )
        cls.leaf_pem = leaf_cert.public_bytes(serialization.Encoding.PEM)
        cls.chain_pem = cls.leaf_pem + ca_cert.public_bytes(serialization.Encoding.PEM)
        cls.key_pem = leaf_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption(),
        )

    def _server(self, cert_pem):
        return self.IrMailServer.create(
            {
                "name": "chain",
                "smtp_host": "smtp.example.com",
                "smtp_authentication": "certificate",
                "smtp_encryption": "starttls_strict",
                "smtp_ssl_certificate": base64.b64encode(cert_pem),
                "smtp_ssl_private_key": base64.b64encode(self.key_pem),
            }
        )

    def _loaded_chain(self, cert_pem):
        loaded = []
        real_context = self.IrMailServer._prepare_client_ssl_context

        def capturing(encryption, smtp_server):
            context = real_context(encryption, smtp_server)
            openssl_context = context._ctx
            use_certificate = openssl_context.use_certificate
            add_extra = openssl_context.add_extra_chain_cert

            def track_leaf(cert):
                loaded.append(cert)
                return use_certificate(cert)

            def track_intermediate(cert):
                loaded.append(cert)
                return add_extra(cert)

            openssl_context.use_certificate = track_leaf
            openssl_context.add_extra_chain_cert = track_intermediate
            return context

        with patch.object(
            type(self.IrMailServer),
            "_prepare_client_ssl_context",
            staticmethod(capturing),
        ):
            self._server(cert_pem)._prepare_ssl_context_from_certificate()
        return [cert.subject.rfc4514_string() for cert in loaded]

    def test_full_chain_is_presented(self):
        self.assertEqual(
            self._loaded_chain(self.chain_pem),
            ["CN=smtp.example.com", "CN=Intermediate CA"],
            "the intermediate must be added to the chain, not dropped",
        )

    def test_leaf_only_certificate_still_works(self):
        self.assertEqual(self._loaded_chain(self.leaf_pem), ["CN=smtp.example.com"])


@tagged("post_install", "-at_install")
class TestPrepareEmailMessageIsNonDestructive(TransactionCase):
    class _Session:
        from_filter = False
        smtp_from = False
        esmtp_features = {"smtputf8": ""}

        def __init__(self):
            self.sent = []

        def send_message(self, message, smtp_from, smtp_to_list):
            self.sent.append((smtp_from, smtp_to_list))

    def _message(self):
        return self.env["ir.mail_server"]._prepare_email__(
            "sender@example.com",
            "to@example.com",
            "Subject",
            "Body",
            email_bcc=["bcc@example.com"],
            headers={"Return-Path": "bounce@example.com"},
        )

    def test_prepare_leaves_the_caller_message_intact(self):
        IrMailServer = self.env["ir.mail_server"]
        message = self._message()
        smtp_from, smtp_to, prepared = IrMailServer._prepare_email_message__(
            message, self._Session()
        )

        self.assertEqual(message["Bcc"], "bcc@example.com")
        self.assertEqual(message["Return-Path"], "bounce@example.com")
        self.assertIsNot(prepared, message)
        self.assertIsNone(prepared["Bcc"], "the wire copy must not carry Bcc")
        self.assertIsNone(prepared["Return-Path"])
        self.assertEqual(smtp_from, "bounce@example.com")
        self.assertEqual(smtp_to, ["to@example.com", "bcc@example.com"])

    def test_preparing_twice_is_idempotent(self):
        IrMailServer = self.env["ir.mail_server"]
        message = self._message()
        first = IrMailServer._prepare_email_message__(message, self._Session())[:2]
        second = IrMailServer._prepare_email_message__(message, self._Session())[:2]
        self.assertEqual(first, second, "a retry must resolve the same envelope")

    def test_send_email_does_not_consume_the_caller_message(self):
        IrMailServer = self.env["ir.mail_server"]
        message = self._message()
        session = self._Session()
        with patch.object(type(IrMailServer), "_disable_send", lambda _: False):
            IrMailServer.send_email(message, smtp_session=session)
            IrMailServer.send_email(message, smtp_session=session)
        self.assertEqual(
            session.sent[0], session.sent[1], "resending must reach the same envelope"
        )
        self.assertEqual(message["Bcc"], "bcc@example.com")


@tagged("post_install", "-at_install")
class TestFindMailServerOrdering(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.IrMailServer = cls.env["ir.mail_server"]
        cls.IrMailServer.sudo().search([]).unlink()
        cls.servers = cls.IrMailServer.create(
            [
                {
                    "name": f"tie-{index}",
                    "smtp_host": f"{index}.example.com",
                    "smtp_encryption": "none",
                    "from_filter": "shared.example.com",
                }
                for index in range(4)
            ]
        )

    def test_equal_sequence_resolves_by_id(self):
        self.assertEqual(
            self.servers.mapped("sequence"), [10] * 4, "same priority by default"
        )
        expected = self.servers[0]
        for _attempt in range(2):
            server, _from = self.IrMailServer.sudo()._get_mail_server(
                "someone@shared.example.com"
            )
            self.assertEqual(server, expected)
            self.env.cr.execute(
                "UPDATE ir_mail_server SET name = name || '.' WHERE id = %s",
                (self.servers[0].id,),
            )
            self.env.invalidate_all()

    def test_sequence_still_wins_over_id(self):
        self.servers[-1].sequence = 1
        self.assertEqual(
            self.IrMailServer.sudo()._get_mail_server("someone@shared.example.com")[0],
            self.servers[-1],
        )


@tagged("post_install", "-at_install")
class TestMailServerDeletionGuard(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.IrMailServer = cls.env["ir.mail_server"]
        cls.server = cls.IrMailServer.create(
            {
                "name": "Used Server",
                "smtp_host": "smtp_host",
                "smtp_encryption": "none",
            }
        )

    def test_unused_server_can_be_deleted(self):
        self.assertTrue(self.server.unlink())

    @mute_logger(_IR_MAIL_SERVER_LOGGER, "odoo.models.unlink")
    def test_used_server_cannot_be_deleted(self):
        usages = {self.server.id: ["Used by a mail template"]}
        with patch.object(
            type(self.IrMailServer), "_get_active_usages", lambda self: usages
        ):
            with self.assertRaises(UserError) as ctx:
                self.server.unlink()
        message = str(ctx.exception)
        self.assertIn("You cannot delete this Outgoing Mail Server", message)
        self.assertIn("Used Server", message)
        self.assertIn("- Used by a mail template", message)
        self.assertTrue(self.server.exists())


@tagged("post_install", "-at_install")
class TestConnectionTestErrorClassification(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.IrMailServer = cls.env["ir.mail_server"]
        cls.server = cls.IrMailServer.create(
            {"name": "probe", "smtp_host": "smtp_host", "smtp_encryption": "none"}
        )

    def _message_for(self, exc):
        with self.assertNoLogs(_IR_MAIL_SERVER_LOGGER, logging.WARNING):
            return str(
                self.IrMailServer._prepare_connection_test_error(exc, self.server)
            )

    def test_connection_refused_is_reported_as_a_reachability_problem(self):
        message = self._message_for(ConnectionRefusedError(111, "Connection refused"))
        self.assertIn("Check the port number", message)
        self.assertIn("Connection refused", message)

    def test_network_unreachable_is_reported_without_a_traceback(self):
        message = self._message_for(OSError(101, "Network is unreachable"))
        self.assertIn("Check the server address", message)
        self.assertIn("Network is unreachable", message)

    def test_more_specific_handlers_still_win_over_oserror(self):
        self.assertIn(
            "Server replied with following exception",
            self._message_for(smtplib.SMTPResponseException(550, "nope")),
        )
        self.assertIn(
            "An option is not supported by the server",
            self._message_for(smtplib.SMTPNotSupportedError("no STARTTLS")),
        )
        self.assertIn(
            "An SSL exception occurred",
            self._message_for(ssl.SSLError("handshake failure")),
        )
        self.assertIn(
            "No response received",
            self._message_for(TimeoutError("timed out")),
        )


@tagged("post_install", "-at_install")
class TestSmtpDebugGoesThroughTheLogger(TransactionCase):
    def test_debug_transcript_is_logged(self):
        with self.assertLogs(_IR_MAIL_SERVER_LOGGER, logging.DEBUG) as captured:
            _log_smtp_debug("send:", "'EHLO odoo\\r\\n'")
        self.assertIn("EHLO odoo", captured.output[0])

    def test_open_connection_redirects_smtplib_debug(self):
        IrMailServer = self.env["ir.mail_server"]
        captured = {}

        class _FakeConn:
            def __init__(self, *args, **kwargs):
                pass

            def set_debuglevel(self, level):
                captured["level"] = level
                captured["print_debug"] = self._print_debug

            def _print_debug(self, *args):
                raise AssertionError("smtplib's stderr printer must be replaced")

            def ehlo_or_helo_if_needed(self):
                pass

        server = IrMailServer.create(
            {"name": "cli", "smtp_authentication": "cli", "smtp_debug": True}
        )
        with (
            patch.object(type(IrMailServer), "_disable_send", lambda _: False),
            patch("smtplib.SMTP", _FakeConn),
            config.patch(smtp_server="smtp.example.com"),
        ):
            transport = server._prepare_smtp_transport()
            IrMailServer._open_smtp_connection(transport, None)

        self.assertTrue(captured["level"])
        self.assertIs(captured["print_debug"], _log_smtp_debug)


@tagged("post_install", "-at_install")
class TestCertificateChainOnTheWire(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from cryptography.hazmat.primitives import serialization

        cls.IrMailServer = cls.env["ir.mail_server"]
        cls.pem = serialization.Encoding.PEM
        root, root_key = _self_signed("Chain Root", ca=True)
        inter, inter_key = _self_signed(
            "Chain Intermediate", issuer_key=root_key, issuer_name=root.subject, ca=True
        )
        leaf, leaf_key = _self_signed(
            "client.example.com", issuer_key=inter_key, issuer_name=inter.subject
        )
        server_cert, server_key = _self_signed(
            "localhost", issuer_key=root_key, issuer_name=root.subject
        )
        cls.leaf_pem = leaf.public_bytes(cls.pem)
        cls.chain_pem = cls.leaf_pem + inter.public_bytes(cls.pem)
        cls.key_pem = leaf_key.private_bytes(
            cls.pem,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption(),
        )
        cls.root_pem = root.public_bytes(cls.pem)
        cls.server_pem = server_cert.public_bytes(cls.pem) + server_key.private_bytes(
            cls.pem,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption(),
        )

    def _handshake(self, cert_pem):
        import socket
        import threading

        with tempfile.TemporaryDirectory() as tmp:
            root_path = Path(tmp) / "root.pem"
            server_path = Path(tmp) / "server.pem"
            root_path.write_bytes(self.root_pem)
            server_path.write_bytes(self.server_pem)

            server_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            server_context.load_cert_chain(str(server_path))
            server_context.load_verify_locations(str(root_path))
            server_context.verify_mode = ssl.CERT_REQUIRED

            listener = socket.socket()
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            listener.bind(("127.0.0.1", 0))
            listener.listen(1)
            verdict = {}

            def serve():
                try:
                    raw, _ = listener.accept()
                    raw.settimeout(10)
                    tls = server_context.wrap_socket(raw, server_side=True)
                    verdict["chain"] = len(tls.get_verified_chain() or ())
                    tls.close()
                except ssl.SSLError as exc:
                    verdict["error"] = type(exc).__name__

            thread = threading.Thread(target=serve, daemon=True)
            thread.start()
            try:
                server = self.IrMailServer.create(
                    {
                        "name": "wire",
                        "smtp_host": "localhost",
                        "smtp_authentication": "certificate",
                        "smtp_encryption": "starttls",
                        "smtp_ssl_certificate": base64.b64encode(cert_pem),
                        "smtp_ssl_private_key": base64.b64encode(self.key_pem),
                    }
                )
                context = server._prepare_ssl_context_from_certificate()
                context.verify_mode = ssl.CERT_NONE
                plain = socket.create_connection(listener.getsockname(), timeout=10)
                with contextlib.suppress(OSError):
                    context.wrap_socket(plain, server_hostname="localhost").close()
            finally:
                thread.join(timeout=10)
                listener.close()
            return verdict

    def test_intermediate_reaches_the_peer(self):
        self.assertEqual(
            self._handshake(self.chain_pem).get("chain"),
            3,
            "the peer must verify leaf -> intermediate -> root",
        )

    def test_leaf_alone_cannot_be_verified(self):
        self.assertEqual(
            self._handshake(self.leaf_pem).get("error"),
            "SSLCertVerificationError",
            "without the intermediate the peer cannot build a trust path",
        )


@tagged("post_install", "-at_install")
class TestDetachedCopyIsolation(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.IrMailServer = cls.env["ir.mail_server"]

    def _multipart(self):
        return self.IrMailServer._prepare_email__(
            "a@example.com",
            "to@example.com",
            "Sub",
            "<p>Body</p>",
            subtype="html",
            message_id="<pinned@example.com>",
            attachments=[("f.txt", b"data", "text/plain")],
        )

    def test_setting_a_header_on_the_copy_does_not_reach_the_original(self):
        original = self._multipart()
        detached = self.IrMailServer._copy_message_detached(original)
        detached["X-Injected"] = "value"
        self.assertIsNone(original["X-Injected"])

    def test_attaching_to_the_copy_does_not_reach_the_original(self):
        original = self._multipart()
        parts_before = len(original.get_payload())
        detached = self.IrMailServer._copy_message_detached(original)
        extra = EmailMessage(policy=email.policy.SMTP)
        extra.set_content("added by an override")
        detached.attach(extra)
        self.assertEqual(len(original.get_payload()), parts_before)
        self.assertEqual(len(detached.get_payload()), parts_before + 1)

    def test_parts_are_shared_not_cloned(self):
        original = self._multipart()
        detached = self.IrMailServer._copy_message_detached(original)
        self.assertIs(detached.get_payload(1), original.get_payload(1))

    def test_prepared_message_is_byte_identical_to_in_place_preparation(self):

        class _Session:
            from_filter = False
            smtp_from = False
            esmtp_features = {"smtputf8": ""}

        in_place = self._multipart()
        self.IrMailServer._alter_message__(in_place, in_place["From"])

        copied = self._multipart()
        _from, _to, prepared = self.IrMailServer._prepare_email_message__(
            copied, _Session()
        )

        boundary = re.compile(rb"===============\d+==")
        self.assertEqual(
            boundary.sub(b"B", in_place.as_bytes()),
            boundary.sub(b"B", prepared.as_bytes()),
        )


@tagged("post_install", "-at_install")
class TestConnectionErrorDispatchMatrix(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.IrMailServer = cls.env["ir.mail_server"]
        cls.server = cls.IrMailServer.create(
            {"name": "probe", "smtp_host": "smtp_host", "smtp_encryption": "none"}
        )

    def test_every_handler_is_reachable(self):
        import socket

        import idna
        from urllib3.util.ssl_match_hostname import CertificateError

        cases = [
            (idna.IDNAError("bad host"), "Invalid server name"),
            (TimeoutError("timed out"), "No response received"),
            (socket.gaierror(-2, "Name or service not known"), "No response received"),
            (
                ConnectionRefusedError(111, "refused"),
                "Could not establish a connection",
            ),
            (ConnectionResetError(104, "reset"), "Could not establish a connection"),
            (
                smtplib.SMTPServerDisconnected("gone"),
                "closed the connection unexpectedly",
            ),
            (smtplib.SMTPResponseException(550, "no"), "Server replied with following"),
            (
                smtplib.SMTPAuthenticationError(535, b"bad"),
                "Server replied with following",
            ),
            (smtplib.SMTPNotSupportedError("nope"), "option is not supported"),
            (smtplib.SMTPException("generic"), "An SMTP exception occurred"),
            (CertificateError("hostname mismatch"), "CertificateError"),
            (ssl.SSLCertVerificationError("verify"), "An SSL exception occurred"),
            (ssl.SSLError("handshake"), "An SSL exception occurred"),
            (OSError(101, "Network is unreachable"), "connection to the server failed"),
        ]
        for exc, expected in cases:
            with self.subTest(exception=type(exc).__name__):
                with self.assertNoLogs(_IR_MAIL_SERVER_LOGGER, logging.WARNING):
                    message = str(
                        self.IrMailServer._prepare_connection_test_error(
                            exc, self.server
                        )
                    )
                self.assertIn(expected, message)

    @mute_logger(_IR_MAIL_SERVER_LOGGER)
    def test_unclassified_error_still_falls_through_with_a_warning(self):
        message = str(
            self.IrMailServer._prepare_connection_test_error(
                ValueError("boom"), self.server
            )
        )
        self.assertIn("Connection Test Failed", message)


@tagged("post_install", "-at_install")
class TestNotificationsEmailNormalization(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.IrMailServer = cls.env["ir.mail_server"]
        cls.IrMailServer.search([]).unlink()
        cls.decoy = cls.IrMailServer.create(
            {
                "name": "decoy",
                "smtp_host": "decoy.example.com",
                "sequence": 1,
                "from_filter": "unrelated.example.com",
            }
        )
        cls.notifier = cls.IrMailServer.create(
            {
                "name": "notifier",
                "smtp_host": "notifier.example.com",
                "sequence": 2,
                "from_filter": "notifications@example.com",
            }
        )

    def _find(self, notifications_email):
        return self.IrMailServer.with_context(
            domain_notifications_email=notifications_email
        )._get_mail_server("stranger@nowhere.example.com")

    def test_uppercase_domain_selects_the_notifications_server(self):
        server, email_from = self._find("notifications@Example.COM")
        self.assertEqual(server, self.notifier)
        self.assertEqual(email_from, "notifications@example.com")

    def test_uppercase_domain_does_not_fall_back_past_an_open_server(self):
        self.IrMailServer.create(
            {"name": "open", "smtp_host": "open.example.com", "sequence": 5}
        )
        server, _email_from = self._find("notifications@Example.COM")
        self.assertEqual(server, self.notifier)

    def test_formatted_address_selects_the_notifications_server(self):
        server, email_from = self._find('"Notif" <notifications@example.com>')
        self.assertEqual(server, self.notifier)
        self.assertEqual(email_from, "notifications@example.com")

    def test_uppercase_domain_matches_a_domain_filter(self):
        self.notifier.from_filter = "example.com"
        server, email_from = self._find("notifications@Example.COM")
        self.assertEqual(server, self.notifier)
        self.assertEqual(email_from, "notifications@example.com")

    def test_already_normalized_address_is_unaffected(self):
        server, email_from = self._find("notifications@example.com")
        self.assertEqual(server, self.notifier)
        self.assertEqual(email_from, "notifications@example.com")

    def test_matching_a_server_logs_no_fallback_warning(self):
        for notifications_email in (
            "notifications@Example.COM",
            '"Notif" <notifications@example.com>',
            "notifications@example.com",
        ):
            with self.subTest(notifications_email=notifications_email):
                with self.assertNoLogs(_IR_MAIL_SERVER_LOGGER, logging.WARNING):
                    self._find(notifications_email)


@tagged("post_install", "-at_install")
class TestTestEmailFromSelection(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.IrMailServer = cls.env["ir.mail_server"]

    def _server(self, from_filter):
        return self.IrMailServer.create(
            {
                "name": "tested",
                "smtp_host": "smtp.example.com",
                "from_filter": from_filter,
            }
        )

    def test_an_unparseable_part_can_no_longer_be_stored(self):
        for from_filter in ("@@@", "@@@, example.com"):
            with (
                self.subTest(from_filter=from_filter),
                self.assertRaises(ValidationError),
                self.env.cr.savepoint(),
            ):
                self._server(from_filter)

    def test_the_reader_still_tolerates_junk_it_is_handed(self):
        self.env.user.email = "admin@example.com"
        index = self.IrMailServer._from_filter_index("@@@")
        self.assertEqual(index.sender(), None)
        self.assertEqual(index.domain(), None)
        self.assertEqual(
            self.IrMailServer._from_filter_index("@@@, example.com").domain(),
            "example.com",
        )

    def test_formatted_filter_entry_yields_a_bare_address(self):
        self.assertEqual(
            self._server('"Bob" <bob@example.com>')._get_test_email_from(),
            "bob@example.com",
        )

    def test_first_usable_address_wins(self):
        self.assertEqual(
            self._server("b@example.com, a@example.com")._get_test_email_from(),
            "b@example.com",
        )

    def test_domain_only_filter_builds_a_sender_in_that_domain(self):
        self._assert_sender_in_domain(self._server("example.com"), "example.com")

    def _assert_sender_in_domain(self, server, domain):
        email_from = server._get_test_email_from()
        normalized = email_normalize(email_from)
        self.assertTrue(normalized, f"{email_from!r} is not a usable sender")
        self.assertEqual(email_domain_extract(normalized), domain)


@tagged("post_install", "-at_install")
class TestCertificateMaterialValidatedOnWrite(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from cryptography.hazmat.primitives import serialization

        cls.IrMailServer = cls.env["ir.mail_server"]
        cert, key = _self_signed("smtp.example.com")
        _, other_key = _self_signed("other.example.com")
        cls.cert_pem = cert.public_bytes(serialization.Encoding.PEM)
        cls.key_pem = key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption(),
        )
        cls.other_key_pem = other_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption(),
        )

    def _create(self, cert_pem, key_pem):
        return self.IrMailServer.create(
            {
                "name": "cert",
                "smtp_host": "smtp.example.com",
                "smtp_authentication": "certificate",
                "smtp_encryption": "starttls_strict",
                "smtp_ssl_certificate": base64.b64encode(cert_pem),
                "smtp_ssl_private_key": base64.b64encode(key_pem),
            }
        )

    def test_matching_pair_is_accepted(self):
        self.assertTrue(self._create(self.cert_pem, self.key_pem))

    def test_key_from_another_certificate_is_rejected(self):
        with self.assertRaises(UserError):
            self._create(self.cert_pem, self.other_key_pem)

    def test_garbage_certificate_is_rejected(self):
        with self.assertRaises(UserError):
            self._create(b"not a certificate", self.key_pem)

    def test_garbage_key_is_rejected(self):
        with self.assertRaises(UserError):
            self._create(self.cert_pem, b"not a key")

    def test_swapping_in_a_bad_key_later_is_rejected(self):
        server = self._create(self.cert_pem, self.key_pem)
        with self.assertRaises(UserError):
            server.smtp_ssl_private_key = base64.b64encode(self.other_key_pem)

    def test_material_is_ignored_while_authentication_is_not_certificate(self):
        self.assertTrue(
            self.IrMailServer.create(
                {
                    "name": "login",
                    "smtp_host": "smtp.example.com",
                    "smtp_authentication": "login",
                    "smtp_ssl_certificate": base64.b64encode(b"leftover"),
                    "smtp_ssl_private_key": base64.b64encode(b"leftover"),
                }
            )
        )


@tagged("post_install", "-at_install")
class TestSmtpHeloName(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.IrMailServer = cls.env["ir.mail_server"]

    def test_unset_option_defers_to_smtplib(self):
        with config.patch(smtp_helo_name=""):
            self.assertIsNone(self.IrMailServer._get_smtp_local_hostname())

    def test_configured_name_is_returned(self):
        with config.patch(smtp_helo_name="mail.example.com"):
            self.assertEqual(
                self.IrMailServer._get_smtp_local_hostname(), "mail.example.com"
            )

    def test_connection_announces_the_configured_name(self):
        announced = {}

        class FakeSMTP:
            esmtp_features = {}

            def __init__(self, host, port, timeout=None, local_hostname=None, **kw):
                announced["local_hostname"] = local_hostname

            def set_debuglevel(self, level):
                pass

            def ehlo_or_helo_if_needed(self):
                pass

        transport = self.IrMailServer.create(
            {"name": "helo", "smtp_host": "smtp.example.com"}
        )._prepare_smtp_transport()
        with (
            config.patch(smtp_helo_name="mail.example.com"),
            patch.object(smtplib, "SMTP", FakeSMTP),
        ):
            self.IrMailServer._open_smtp_connection(transport, "from@example.com")
        self.assertEqual(announced["local_hostname"], "mail.example.com")


@tagged("post_install", "-at_install")
class TestRemoteCallSurface(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.reader = cls.env["res.users"].create(
            {
                "name": "Mail Server Reader",
                "login": "mail_server_reader",
                "group_ids": [(6, 0, [cls.env.ref("base.group_user").id])],
            }
        )
        cls.env["ir.model.access"].create(
            {
                "name": "ir_mail_server read for the audit",
                "model_id": cls.env["ir.model"]._get_id("ir.mail_server"),
                "group_id": cls.env.ref("base.group_user").id,
                "perm_read": True,
                "perm_write": False,
                "perm_create": False,
                "perm_unlink": False,
            }
        )
        cls.env.registry.clear_cache()
        cls.server = cls.env["ir.mail_server"].create(
            {"name": "acl", "smtp_host": "smtp.example.com"}
        )

    def test_reader_really_has_read_but_not_write(self):
        as_reader = self.env["ir.mail_server"].with_user(self.reader)
        self.assertTrue(as_reader.has_access("read"))
        self.assertFalse(as_reader.has_access("write"))

    def test_send_email_is_not_rpc_callable(self):
        with self.assertRaises(AccessError):
            call_kw(
                self.env["ir.mail_server"].with_user(self.reader),
                "send_email",
                [{"From": "attacker@example.com"}],
                {"mail_server_id": self.server.id},
            )

    def test_connection_test_requires_write_access(self):
        with self.assertRaises(AccessError):
            call_kw(
                self.server.with_user(self.reader),
                "test_smtp_connection",
                [[self.server.id]],
                {},
            )

    def test_ui_buttons_stay_rpc_callable_for_an_administrator(self):
        for name in ("test_smtp_connection", "action_update_max_email_size"):
            with self.subTest(method=name):
                self.assertTrue(get_public_method(self.env["ir.mail_server"], name))


@tagged("post_install", "-at_install")
class TestSessionAdvertisedSizeLimit(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.IrMailServer = cls.env["ir.mail_server"]
        cls.server = cls.IrMailServer.create(
            {"name": "sized", "smtp_host": "smtp.example.com", "max_email_size": 25.0}
        )

    def _session(self, size):
        class _Session:
            esmtp_features = {} if size is None else {"size": size}

        return _Session()

    def test_a_tighter_server_limit_wins(self):
        self.assertEqual(
            self.server._get_max_email_size(self._session(str(10 * 1024**2))), 10.0
        )

    def test_a_looser_server_limit_does_not_override_the_policy(self):
        self.assertEqual(
            self.server._get_max_email_size(self._session(str(50 * 1024**2))), 25.0
        )

    def test_no_session_keeps_the_configured_value(self):
        self.assertEqual(self.server._get_max_email_size(), 25.0)

    def test_size_advertised_without_a_value_is_not_a_zero_limit(self):
        self.assertEqual(self.server._get_max_email_size(self._session("")), 25.0)

    def test_a_server_not_advertising_size_keeps_the_configured_value(self):
        self.assertEqual(self.server._get_max_email_size(self._session(None)), 25.0)

    def test_a_garbage_size_is_ignored(self):
        self.assertEqual(self.server._get_max_email_size(self._session("lots")), 25.0)

    def test_the_parameter_fallback_is_capped_too(self):
        unsized = self.IrMailServer.create(
            {"name": "unsized", "smtp_host": "smtp.example.com"}
        )
        self.env["ir.config_parameter"].sudo().set_param(
            "base.default_max_email_size", "30"
        )
        self.assertEqual(
            unsized._get_max_email_size(self._session(str(2 * 1024**2))), 2.0
        )
        self.assertEqual(unsized._get_max_email_size(), 30.0)


@tagged("post_install", "-at_install")
class TestResolvedServerIsNotResolvedTwice(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.IrMailServer = cls.env["ir.mail_server"]
        cls.IrMailServer.search([]).unlink()
        cls.IrMailServer.create(
            {"name": "catch-all", "smtp_host": "catchall.example.com"}
        )

    @contextlib.contextmanager
    def _capture(self):
        captured = {}

        class _FakeConn:
            esmtp_features = {}

            def __init__(self, *args, **kwargs):
                pass

            def set_debuglevel(self, level):
                pass

            def ehlo_or_helo_if_needed(self):
                pass

        with (
            config.patch(smtp_server="cli.example.com"),
            patch.object(smtplib, "SMTP", _FakeConn),
            patch.object(
                type(self.IrMailServer),
                "_disable_send",
                classmethod(lambda cls: False),
            ),
        ):
            yield captured

    def _connect(self, **kwargs):
        with self._capture():
            session = self.IrMailServer._connect__(
                smtp_from="notifications@example.com", **kwargs
            )
        return self.IrMailServer._read_session_context(session)

    def test_resolving_is_skipped_when_the_caller_already_resolved(self):
        calls = []
        real = type(self.IrMailServer)._get_mail_server

        def counting(self, *args, **kwargs):
            calls.append(1)
            return real(self, *args, **kwargs)

        with patch.object(type(self.IrMailServer), "_get_mail_server", counting):
            self._connect(resolve_server=False)
            self.assertEqual(calls, [], "the batch's verdict was second-guessed")
            self._connect()
            self.assertEqual(len(calls), 1, "the default must still resolve")

    def test_the_session_context_is_the_same_either_way(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "mail.default.from_filter", "example.com"
        )
        self.assertEqual(
            self._connect(resolve_server=False),
            self.IrMailServer._read_session_context(
                self._fake_cli_session_context_reference()
            ),
        )

    def _fake_cli_session_context_reference(self):
        with self._capture():
            transport = self.IrMailServer._prepare_smtp_transport()
            return self.IrMailServer._open_smtp_connection(
                transport, "notifications@example.com"
            )

    def test_a_forced_server_is_still_validated(self):
        archived = self.IrMailServer.create(
            {"name": "gone", "smtp_host": "gone.example.com", "active": False}
        )
        with self._capture(), self.assertRaises(UserError):
            self.IrMailServer._connect__(
                mail_server_id=archived.id,
                smtp_from="a@example.com",
                resolve_server=False,
            )

    def test_a_session_only_sends_through_the_server_it_was_opened_for(self):
        opened_for = self.IrMailServer.search([], limit=1)
        other = self.IrMailServer.create(
            {"name": "other", "smtp_host": "other.example.com"}
        )
        with self._capture():
            session = self.IrMailServer._connect__(
                mail_server_id=opened_for.id,
                smtp_from="a@example.com",
                resolve_server=False,
            )
        self.assertEqual(
            self.IrMailServer._read_session_context(session).mail_server_id,
            opened_for.id,
        )
        message = self.IrMailServer._prepare_email__(
            "a@example.com", "b@example.com", "subject", "body"
        )
        self.IrMailServer._check_session_mail_server(session, opened_for.id)
        with self.assertRaises(ValueError):
            self.IrMailServer.send_email(
                message, mail_server_id=other.id, smtp_session=session
            )
        with self._capture():
            cli_session = self.IrMailServer._connect__(
                smtp_from="a@example.com", resolve_server=False
            )
        with self.assertRaises(ValueError):
            self.IrMailServer.send_email(
                message, mail_server_id=opened_for.id, smtp_session=cli_session
            )


@tagged("post_install", "-at_install")
class TestVerifyHostnameCallback(TransactionCase):
    @staticmethod
    def _certificate(common_name, san_dns_names=()):
        from cryptography import x509
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import ec
        from cryptography.x509.oid import NameOID
        from OpenSSL.crypto import X509

        key = ec.generate_private_key(ec.SECP256R1())
        name = x509.Name(
            [x509.NameAttribute(NameOID.COMMON_NAME, common_name)],
        )
        builder = (
            x509.CertificateBuilder()
            .subject_name(name)
            .issuer_name(name)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.datetime(2020, 1, 1))
            .not_valid_after(datetime.datetime(2050, 1, 1))
        )
        if san_dns_names:
            builder = builder.add_extension(
                x509.SubjectAlternativeName(
                    [x509.DNSName(dns) for dns in san_dns_names]
                ),
                critical=False,
            )
        return X509.from_cryptography(builder.sign(key, hashes.SHA256()))

    def _verify(self, certificate, hostname, err_depth=0):
        return _check_hostname_callback(
            None, certificate, 0, err_depth, 0, hostname=hostname
        )

    def test_san_match_is_accepted(self):
        certificate = self._certificate("irrelevant", ["smtp.example.com"])
        self.assertTrue(self._verify(certificate, "smtp.example.com"))

    def test_san_mismatch_is_refused(self):
        certificate = self._certificate("irrelevant", ["other.example.com"])
        with self.assertRaises(CertificateError):
            self._verify(certificate, "smtp.example.com")

    def test_common_name_alone_is_not_a_match(self):
        certificate = self._certificate("smtp.example.com")
        with self.assertRaises(CertificateError):
            self._verify(certificate, "smtp.example.com")

    def test_a_wildcard_san_still_matches(self):
        certificate = self._certificate("irrelevant", ["*.example.com"])
        self.assertTrue(self._verify(certificate, "smtp.example.com"))

    def test_only_the_leaf_is_matched(self):
        certificate = self._certificate("Some CA", ["ca.example.com"])
        self.assertTrue(self._verify(certificate, "smtp.example.com", err_depth=1))

    def test_a_failed_openssl_check_is_refused_before_any_matching(self):
        certificate = self._certificate("irrelevant", ["smtp.example.com"])
        self.assertFalse(
            _check_hostname_callback(
                None, certificate, 10, 0, 0, hostname="smtp.example.com"
            )
        )


@tagged("post_install", "-at_install")
class TestMailServerFieldConstraints(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.IrMailServer = cls.env["ir.mail_server"]

    def test_a_login_server_cannot_be_saved_without_a_host(self):
        with (
            self.assertRaises(psycopg.errors.IntegrityError),
            mute_logger("odoo.db.cursor"),
        ):
            self.IrMailServer.create({"name": "hostless"})

    def test_an_archived_server_may_keep_an_empty_host(self):
        server = self.IrMailServer.create({"name": "h", "smtp_host": "h"})
        server.action_archive()
        server.smtp_host = False
        self.assertFalse(server.smtp_host)

    def test_but_it_cannot_be_brought_back_without_one(self):
        server = self.IrMailServer.create({"name": "h", "smtp_host": "h"})
        server.action_archive()
        server.smtp_host = False
        with (
            self.assertRaises(psycopg.errors.IntegrityError),
            mute_logger("odoo.db.cursor"),
        ):
            server.action_unarchive()

    def test_a_cli_server_still_needs_no_host(self):
        server = self.IrMailServer.create({"name": "cli", "smtp_authentication": "cli"})
        self.assertFalse(server.smtp_host)

    def test_an_out_of_range_port_is_refused(self):
        for port in (0, -1, 65536, 99999):
            with (
                self.subTest(port=port),
                self.assertRaises(psycopg.errors.IntegrityError),
                mute_logger("odoo.db.cursor"),
                self.env.cr.savepoint(),
            ):
                self.IrMailServer.create(
                    {"name": f"p{port}", "smtp_host": "h", "smtp_port": port}
                )

    def test_a_negative_max_email_size_is_refused(self):
        with (
            self.assertRaises(psycopg.errors.IntegrityError),
            mute_logger("odoo.db.cursor"),
        ):
            self.IrMailServer.create(
                {"name": "neg", "smtp_host": "h", "max_email_size": -0.5}
            )

    def test_zero_max_email_size_still_means_use_the_default(self):
        server = self.IrMailServer.create({"name": "z", "smtp_host": "h"})
        self.assertEqual(server.max_email_size, 0.0)
        self.assertEqual(server._get_max_email_size(), 10.0)

    def test_a_from_filter_entry_that_is_neither_address_nor_domain_is_refused(self):
        for from_filter in (
            "odoo.com;example.com",
            "not a domain",
            "@@@",
            "example.com, bad@@entry",
            "*.example.com",
        ):
            with (
                self.subTest(from_filter=from_filter),
                self.assertRaises(ValidationError) as ctx,
                self.env.cr.savepoint(),
            ):
                self.IrMailServer.create(
                    {"name": "f", "smtp_host": "h", "from_filter": from_filter}
                )
            self.assertIn("not a valid entry", str(ctx.exception))

    def test_the_error_names_the_offending_entry(self):
        with self.assertRaises(ValidationError) as ctx:
            self.IrMailServer.create(
                {
                    "name": "f",
                    "smtp_host": "h",
                    "from_filter": "example.com, odoo.com;other.com",
                }
            )
        self.assertIn("'odoo.com;other.com'", str(ctx.exception))
        self.assertNotIn("'example.com'", str(ctx.exception))

    def test_good_from_filters_are_still_accepted(self):
        for from_filter in (
            "",
            "example.com",
            "notify@example.com",
            " Notify@Example.COM , Example.NET ,, ",
            "sub.domain.example.co.uk",
            "café.fr",
        ):
            with self.subTest(from_filter=from_filter), self.env.cr.savepoint():
                self.IrMailServer.create(
                    {"name": "f", "smtp_host": "h", "from_filter": from_filter}
                )

    def test_a_missing_certificate_is_a_validation_error(self):
        with self.assertRaises(ValidationError):
            self.IrMailServer.create(
                {
                    "name": "c",
                    "smtp_host": "h",
                    "smtp_encryption": "ssl",
                    "smtp_authentication": "certificate",
                }
            )

    def test_unloadable_certificate_material_is_a_validation_error(self):
        with self.assertRaises(ValidationError):
            self.IrMailServer.create(
                {
                    "name": "c",
                    "smtp_host": "h",
                    "smtp_encryption": "ssl",
                    "smtp_authentication": "certificate",
                    "smtp_ssl_certificate": base64.b64encode(b"junk"),
                    "smtp_ssl_private_key": base64.b64encode(b"junk"),
                }
            )


@tagged("post_install", "-at_install")
class TestFromFilterIndexIsHonest(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.IrMailServer = cls.env["ir.mail_server"]

    def test_the_index_keeps_declaration_order(self):
        index = self.IrMailServer._from_filter_index(
            "b@example.com, a@example.com, zz.example, aa.example"
        )
        self.assertEqual(index.emails, ("b@example.com", "a@example.com"))
        self.assertEqual(index.domains, ("zz.example", "aa.example"))
        self.assertEqual(index.sender(), "b@example.com")
        self.assertEqual(index.domain(), "zz.example")

    def test_the_index_deduplicates(self):
        index = self.IrMailServer._from_filter_index(
            "A@example.com, a@example.com, Example.NET, example.net"
        )
        self.assertEqual(index.emails, ("a@example.com",))
        self.assertEqual(index.domains, ("example.net",))

    def test_junk_is_recorded_verbatim_so_the_constraint_can_name_it(self):
        index = self.IrMailServer._from_filter_index("@@@, example.com, not a domain")
        self.assertEqual(index.emails, ())
        self.assertEqual(index.domains, ("example.com",))
        self.assertEqual(index.unparsed, ("@@@", "not a domain"))
        self.assertFalse(index.unrestricted)

    def test_a_domain_shaped_like_a_domain_is_a_domain(self):
        for part in ("example.com", "a.b.c.example", "xn--caf-dma.fr", "café.fr"):
            with self.subTest(part=part):
                self.assertEqual(
                    self.IrMailServer._from_filter_index(part).domains, (part.lower(),)
                )

    def test_matches_normalizes_its_own_argument(self):
        index = self.IrMailServer._from_filter_index("notify@example.com, other.com")
        for candidate in (
            "notify@example.com",
            "Notify@Example.com",
            '"N" <notify@example.com>',
            "someone@OTHER.com",
        ):
            with self.subTest(candidate=candidate):
                self.assertTrue(index.matches(candidate))
        self.assertFalse(index.matches("someone@example.com"))
        self.assertFalse(index.matches(False))

    def test_from_filter_readers_agree_with_the_index(self):
        server = self.IrMailServer.create(
            {
                "name": "s",
                "smtp_host": "h",
                "from_filter": "notify@example.com, example.net",
            }
        )
        self.assertEqual(server._from_filter_sender(), "notify@example.com")
        self.assertEqual(server._from_filter_domain(), "example.net")


@tagged("post_install", "-at_install")
class TestSmtpUsernameEncoding(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.IrMailServer = cls.env["ir.mail_server"]

    def test_an_ascii_username_is_passed_through_untouched(self):
        for user in (
            "plainuser",
            "user@example.com",
            "USER@Example.COM",
            "a.b-c@sub.example.co.uk",
            "user@",
            "user@my_host.local",
            "user@[192.168.0.1]",
            "user@a..b",
        ):
            with self.subTest(user=user):
                self.assertEqual(self.IrMailServer._encode_smtp_user(user), user)

    def test_a_non_ascii_domain_is_punycoded(self):
        self.assertEqual(
            self.IrMailServer._encode_smtp_user("user@café.fr"),
            "user@xn--caf-dma.fr",
        )

    def test_a_non_ascii_domain_that_idna_refuses_falls_back_to_the_literal(self):
        with mute_logger(_IR_MAIL_SERVER_LOGGER):
            self.assertEqual(
                self.IrMailServer._encode_smtp_user("user@café..fr"), "user@café..fr"
            )

    def test_a_refused_username_is_reported_not_raised(self):
        with self.assertLogs(_IR_MAIL_SERVER_LOGGER, "WARNING") as logs:
            self.IrMailServer._encode_smtp_user("user@café..fr")
        self.assertIn("not a valid IDN", logs.output[0])


@tagged("post_install", "-at_install")
class TestOutgoingEmailErrorCodes(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.IrMailServer = cls.env["ir.mail_server"]

    def test_codes_are_opaque_identifiers(self):
        for code in (
            self.IrMailServer.NO_VALID_RECIPIENT,
            self.IrMailServer.NO_FOUND_FROM,
            self.IrMailServer.NO_FOUND_SMTP_FROM,
            self.IrMailServer.NO_VALID_FROM,
        ):
            with self.subTest(code=code):
                self.assertRegex(code, r"^[a-z_]+$")

    def test_every_code_resolves_to_a_message(self):
        for code in (
            self.IrMailServer.NO_VALID_RECIPIENT,
            self.IrMailServer.NO_FOUND_FROM,
            self.IrMailServer.NO_FOUND_SMTP_FROM,
            self.IrMailServer.NO_VALID_FROM,
        ):
            with self.subTest(code=code):
                message = self.IrMailServer._get_outgoing_email_message(code)
                self.assertNotEqual(message, code)
                self.assertGreater(len(message), len(code))

    def test_the_message_never_leaks_into_the_code(self):
        message = self.IrMailServer._get_outgoing_email_message(
            self.IrMailServer.NO_VALID_RECIPIENT
        )
        error = OutgoingEmailError(message, self.IrMailServer.NO_VALID_RECIPIENT)
        self.assertEqual(error.code, self.IrMailServer.NO_VALID_RECIPIENT)
        self.assertEqual(str(error), message)
        self.assertNotEqual(error.code, str(error))

    def test_a_missing_sender_raises_the_right_code(self):
        with (
            config.patch(email_from=False),
            self.assertRaises(OutgoingEmailError) as ctx,
        ):
            self.IrMailServer._prepare_email__(None, "d@example.com", "s", "b")
        self.assertEqual(ctx.exception.code, self.IrMailServer.NO_FOUND_FROM)

    def test_no_recipient_raises_the_right_code(self):
        message = self.IrMailServer._prepare_email__("a@example.com", [], "s", "b")
        with self.assertRaises(OutgoingEmailError) as ctx:
            self.IrMailServer._prepare_email_message__(message, None)
        self.assertEqual(ctx.exception.code, self.IrMailServer.NO_VALID_RECIPIENT)

    def test_an_empty_recipient_emits_no_to_header_at_all(self):
        message = self.IrMailServer._prepare_email__("a@example.com", [], "s", "b")
        self.assertIsNone(message["To"])
        self.assertFalse(
            [
                line
                for line in message.as_string().splitlines()
                if line.startswith("To:")
            ]
        )


@tagged("post_install", "-at_install")
class TestEnvelopeSenderExtraction(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.IrMailServer = cls.env["ir.mail_server"]

    def test_a_display_name_holding_an_address_does_not_win(self):
        self.assertEqual(
            self.IrMailServer._get_envelope_sender('"user@gmail.com" <notif@odoo.com>'),
            "notif@odoo.com",
        )

    def test_a_multi_mailbox_header_uses_the_first_mailbox(self):
        self.assertEqual(
            self.IrMailServer._get_envelope_sender("a@example.com, c@example.net"),
            "a@example.com",
        )

    def test_a_plain_address_is_itself(self):
        self.assertEqual(
            self.IrMailServer._get_envelope_sender("a@example.com"), "a@example.com"
        )

    def test_nothing_parseable_yields_nothing(self):
        self.assertIsNone(self.IrMailServer._get_envelope_sender("not an address"))

    def test_the_envelope_follows_the_first_mailbox_end_to_end(self):
        message = self.IrMailServer._prepare_email__(
            "a@example.com, c@example.net", "d@example.com", "s", "b"
        )
        smtp_from, _to, _msg = self.IrMailServer._prepare_email_message__(message, None)
        self.assertEqual(smtp_from, "a@example.com")


@tagged("post_install", "-at_install")
class TestSessionContextRegistry(TransactionCase):
    class _Foreign:
        esmtp_features = {"smtputf8": ""}

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.IrMailServer = cls.env["ir.mail_server"]

    def test_a_stashed_session_reads_back(self):
        session = self._Foreign()
        self.IrMailServer._stash_session_context(
            session, _SmtpSessionContext(from_filter="example.com", smtp_from="a@b.com")
        )
        context = self.IrMailServer._read_session_context(session)
        self.assertEqual(context.from_filter, "example.com")
        self.assertEqual(context.smtp_from, "a@b.com")

    def test_no_session_is_not_a_foreign_session(self):
        with self.assertNoLogs(_IR_MAIL_SERVER_LOGGER, "WARNING"):
            self.assertEqual(
                self.IrMailServer._read_session_context(None), _SmtpSessionContext()
            )

    def test_a_session_this_model_never_opened_is_reported(self):
        with self.assertLogs(_IR_MAIL_SERVER_LOGGER, "WARNING") as logs:
            context = self.IrMailServer._read_session_context(self._Foreign())
        self.assertEqual(context, _SmtpSessionContext())
        self.assertIn("did not open", logs.output[0])

    def test_the_registry_does_not_pin_sessions_in_memory(self):
        session = self._Foreign()
        self.IrMailServer._stash_session_context(session, _SmtpSessionContext())
        reference = weakref.ref(session)
        del session
        gc.collect()
        self.assertIsNone(reference(), "a finished session must be collectable")


@tagged("post_install", "-at_install")
class TestEncryptionPolicyIsOneDecision(TransactionCase):
    EXPECTED = {
        "none": (False, False, False),
        "starttls": (False, True, False),
        "starttls_strict": (False, True, True),
        "ssl": (True, False, False),
        "ssl_strict": (True, False, True),
    }

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.IrMailServer = cls.env["ir.mail_server"]

    def test_every_selection_value_is_classified(self):
        declared = {
            value
            for value, _label in self.IrMailServer._fields[
                "smtp_encryption"
            ]._description_selection(self.env)
        }
        self.assertEqual(
            declared - set(self.EXPECTED),
            set(),
            "a new encryption mode must say which transport it opens and whether "
            "it verifies the peer",
        )

    def test_the_matrix(self):
        for encryption, (implicit, starttls, verified) in self.EXPECTED.items():
            with self.subTest(encryption=encryption):
                self.assertIs(encryption in IMPLICIT_TLS_ENCRYPTIONS, implicit)
                self.assertIs(encryption in STARTTLS_ENCRYPTIONS, starttls)
                self.assertIs(encryption in VERIFIED_ENCRYPTIONS, verified)

    def test_starttls_and_implicit_tls_never_overlap(self):
        self.assertEqual(IMPLICIT_TLS_ENCRYPTIONS & STARTTLS_ENCRYPTIONS, frozenset())

    def test_verified_is_a_subset_of_the_encrypted_modes(self):
        self.assertLessEqual(
            VERIFIED_ENCRYPTIONS, IMPLICIT_TLS_ENCRYPTIONS | STARTTLS_ENCRYPTIONS
        )

    def test_both_context_builders_agree_on_every_mode(self):
        for encryption, (_i, _s, verified) in self.EXPECTED.items():
            with self.subTest(encryption=encryption):
                stdlib = self.IrMailServer._prepare_ssl_context_for_encryption(
                    encryption
                )
                pyopenssl = self.IrMailServer._prepare_client_ssl_context(
                    encryption, "smtp.example.com"
                )
                self.assertIs(
                    stdlib.verify_mode != ssl.CERT_NONE,
                    verified,
                    "stdlib path disagrees with the policy",
                )
                self.assertIs(
                    pyopenssl.verify_mode != ssl.CERT_NONE,
                    verified,
                    "PyOpenSSL path disagrees with the policy",
                )

    def test_a_lax_mode_never_verifies_on_either_path(self):
        for encryption in set(self.EXPECTED) - VERIFIED_ENCRYPTIONS:
            with self.subTest(encryption=encryption):
                self.assertFalse(
                    self.IrMailServer._prepare_ssl_context_for_encryption(
                        encryption
                    ).check_hostname
                )
                self.assertEqual(
                    self.IrMailServer._prepare_client_ssl_context(
                        encryption, "h"
                    ).verify_mode,
                    ssl.CERT_NONE,
                )

    def test_the_certificate_path_is_deliberately_san_only(self):
        source = inspect.getsource(_check_hostname_callback)
        self.assertIn("get_subj_alt_name", source)
        self.assertNotIn("commonName", source)
