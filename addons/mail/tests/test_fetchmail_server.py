import contextlib
import datetime
import shutil
import ssl
import tempfile
from pathlib import Path
from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests import TransactionCase, mute_logger

from .incoming_mail_servers import FakeMailServer
from odoo.addons.mail.models.fetchmail_server import (
    MAIL_SERVER_DEACTIVATE_TIME,
    SERVER_TEARDOWN_BUDGET,
)
from odoo.addons.mail.tests.common import FakedDialCase
from odoo.addons.mail.tools import incoming_mail

RAW_MESSAGE = (
    b"From: sender@example.com\r\n"
    b"To: catchall@example.com\r\n"
    b"Subject: probe\r\n"
    b"Message-Id: <probe-%d@example.com>\r\n"
    b"Date: Mon, 18 Aug 2026 10:00:00 +0000\r\n"
    b"\r\n"
    b"body line one\r\n"
    b".dot-stuffed line\r\n"
)


def _message(index: int) -> bytes:
    return RAW_MESSAGE % index


class MockedConnection:
    def __init__(self, messages=None, fail_ack=False, announces=None):
        self.mock_messages = dict(messages or {})
        self.fail_ack = fail_ack
        self.announces = announces
        self.acknowledged = []
        self.disconnected = False

    def count_unread_messages(self):
        if self.announces is not None:
            return self.announces
        return len(self.mock_messages)

    def get_unread_messages(self):
        yield from list(self.mock_messages.items())

    def mark_message_handled(self, num):
        if self.fail_ack:
            raise OSError("STORE failed")
        self.acknowledged.append(num)
        self.mock_messages.pop(num, None)

    def disconnect(self):
        self.disconnected = True


class FetchmailCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["fetchmail.server"].search([]).action_archive()

    @contextlib.contextmanager
    def _polling_cursor(self, **context):
        with self.enter_registry_test_mode(), self.registry.cursor() as cr:
            yield self.env(cr=cr, context=dict(self.env.context, **context))

    def _server(self, **values):
        return self.env["fetchmail.server"].create(
            {
                "name": "test server",
                "server_type": "imap",
                "server": "mail.example.com",
                "port": 993,
                "user": "u",
                "password": "p",
                "state": "done",
                **values,
            }
        )


class TestIncomingMailTransport(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._certificate = cls._create_self_signed_certificate()

    @classmethod
    def _create_self_signed_certificate(cls):
        from cryptography import x509
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.x509.oid import NameOID

        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        subject = x509.Name(
            [x509.NameAttribute(NameOID.COMMON_NAME, "not-your-mail-server.invalid")]
        )
        now = datetime.datetime.now(datetime.UTC)
        certificate = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(subject)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - datetime.timedelta(days=1))
            .not_valid_after(now + datetime.timedelta(days=1))
            .sign(key, hashes.SHA256())
        )
        directory = Path(tempfile.mkdtemp(prefix="odoo-fetchmail-cert-"))
        cert_path, key_path = directory / "cert.pem", directory / "key.pem"
        cert_path.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
        key_path.write_bytes(
            key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )
        cls.addClassCleanup(shutil.rmtree, directory, ignore_errors=True)
        return str(cert_path), str(key_path)

    def test_ssl_strict_rejects_an_unvalidated_certificate(self):
        for protocol in ("imap", "pop"):
            with (
                self.subTest(protocol=protocol),
                FakeMailServer(protocol, certificate=self._certificate) as server,
            ):
                with self.assertRaises(ssl.SSLCertVerificationError):
                    incoming_mail.connect(
                        protocol, "127.0.0.1", server.port, "ssl_strict"
                    )
                self.assertEqual(
                    server.mailbox.credentials,
                    {},
                    "nothing may be sent to a server that failed validation",
                )

    def test_ssl_without_validation_still_connects(self):
        with FakeMailServer("pop", certificate=self._certificate) as server:
            connection = incoming_mail.connect("pop", "127.0.0.1", server.port, "ssl")
            connection.disconnect()

    def test_ssl_context_per_scheme(self):
        for scheme, verify, check_hostname in [
            ("none", None, None),
            ("ssl", ssl.CERT_NONE, False),
            ("starttls", ssl.CERT_NONE, False),
            ("ssl_strict", ssl.CERT_REQUIRED, True),
            ("starttls_strict", ssl.CERT_REQUIRED, True),
        ]:
            with self.subTest(scheme=scheme):
                context = incoming_mail.ssl_context_for_encryption(scheme)
                if verify is None:
                    self.assertIsNone(context, "cleartext must not build a context")
                    continue
                self.assertEqual(context.verify_mode, verify)
                self.assertEqual(context.check_hostname, check_hostname)

    def test_unknown_protocol_is_named(self):
        with self.assertRaises(ValueError):
            incoming_mail.connect("local", "127.0.0.1", 0, "none")

    def test_pop3_returns_the_message_byte_for_byte(self):
        raw = _message(1)
        with FakeMailServer("pop", [(1, raw, [])]) as server:
            connection = incoming_mail.connect("pop", "127.0.0.1", server.port, "none")
            connection.user("u")
            connection.pass_("p")
            self.assertEqual(connection.count_unread_messages(), 1)
            fetched = list(connection.get_unread_messages())
            connection.disconnect()
        self.assertEqual(
            fetched[0][1],
            raw.rstrip(b"\r\n"),
            "CRLF terminators and dot-unstuffing must survive the round trip",
        )
        self.assertTrue(server.mailbox.quit_received)

    def test_pop3_does_not_issue_a_pointless_list(self):
        with FakeMailServer("pop", [(1, _message(1), [])]) as server:
            connection = incoming_mail.connect("pop", "127.0.0.1", server.port, "none")
            connection.count_unread_messages()
            connection.disconnect()
        self.assertNotIn("LIST", server.mailbox.log)

    def test_pop3_acknowledges_by_deleting(self):
        with FakeMailServer("pop", [(1, _message(1), []), (2, _message(2), [])]) as srv:
            connection = incoming_mail.connect("pop", "127.0.0.1", srv.port, "none")
            connection.count_unread_messages()
            for num, _raw in connection.get_unread_messages():
                connection.mark_message_handled(num)
            connection.disconnect()
        self.assertEqual(srv.mailbox.deleted, {1, 2})

    def test_imap_fetches_oldest_first_and_leaves_them_unread(self):
        messages = [
            (101, _message(1), []),
            (102, _message(2), []),
            (103, _message(3), ["\\Seen"]),
        ]
        with FakeMailServer("imap", messages) as server:
            connection = incoming_mail.connect("imap", "127.0.0.1", server.port, "none")
            connection.login("u", "p")
            self.assertEqual(
                connection.count_unread_messages(), 2, "the \\Seen one is not unread"
            )
            fetched = [num for num, _raw in connection.get_unread_messages()]
            self.assertEqual(
                fetched, [b"101", b"102"], "oldest first, addressed by UID"
            )
            self.assertEqual(
                server.mailbox.flags()[101],
                [],
                "a fetched-but-unacknowledged message must stay unread",
            )
            connection.mark_message_handled(b"101")
            self.assertEqual(server.mailbox.flags()[101], ["\\Seen"])
            connection.disconnect()

    def test_imap_survives_a_concurrent_expunge(self):
        messages = [
            (101, _message(1), []),
            (102, _message(2), []),
            (103, _message(3), []),
        ]
        with FakeMailServer("imap", messages) as server:
            connection = incoming_mail.connect("imap", "127.0.0.1", server.port, "none")
            connection.login("u", "p")
            connection.count_unread_messages()
            stream = connection.get_unread_messages()
            num, _raw = next(stream)

            server.mailbox.expunge_uid(101)

            connection.mark_message_handled(num)
            connection.disconnect()
        self.assertEqual(
            server.mailbox.flags(),
            {102: [], 103: []},
            "acknowledging uid 101 must not touch any surviving message",
        )

    def test_imap_disconnect_does_not_expunge(self):
        messages = [(101, _message(1), []), (102, _message(2), ["\\Deleted"])]
        with FakeMailServer("imap", messages) as server:
            connection = incoming_mail.connect("imap", "127.0.0.1", server.port, "none")
            connection.login("u", "p")
            connection.count_unread_messages()
            connection.disconnect()
        self.assertEqual(server.mailbox.uids, [101, 102])
        self.assertEqual(server.mailbox.expunged, [])
        self.assertIn("UNSELECT", " ".join(server.mailbox.log))
        self.assertNotIn("CLOSE", " ".join(server.mailbox.log))

    def test_imap_logs_out_even_when_unselect_fails(self):
        with FakeMailServer("imap", [(101, _message(1), [])]) as server:
            connection = incoming_mail.connect("imap", "127.0.0.1", server.port, "none")
            connection.login("u", "p")
            connection.count_unread_messages()
            with (
                patch.object(type(connection), "unselect", side_effect=OSError("boom")),
                self.assertRaises(OSError),
            ):
                connection.disconnect()
        self.assertIn("LOGOUT", " ".join(server.mailbox.log))

    def test_a_fetch_with_no_literal_is_not_a_message(self):
        messages = [(101, _message(1), []), (102, _message(2), [])]
        with FakeMailServer("imap", messages) as server:
            server.mailbox.literal_less.add(101)
            connection = incoming_mail.connect("imap", "127.0.0.1", server.port, "none")
            connection.login("u", "p")
            self.assertEqual(connection.count_unread_messages(), 2)
            fetched = list(connection.get_unread_messages())
            connection.disconnect()
        self.assertEqual(
            fetched,
            [(b"102", _message(2))],
            "the literal-less answer must be skipped, not handed on as a body",
        )

    def test_peek_returns_the_message_without_marking_it_read(self):
        messages = [(101, _message(1), []), (102, _message(2), ["\\Seen"])]
        with FakeMailServer("imap", messages) as server:
            connection = incoming_mail.connect("imap", "127.0.0.1", server.port, "none")
            connection.login("u", "p")
            connection.select()
            for uid in (b"101", b"102"):
                typ, data = connection.uid("FETCH", uid, "(BODY.PEEK[])")
                self.assertEqual(typ, "OK")
                self.assertEqual(data[0][1], _message(1 if uid == b"101" else 2))
            connection.logout()
        self.assertEqual(
            server.mailbox.flags(),
            {101: [], 102: ["\\Seen"]},
            "peeking must leave every flag exactly as it found it",
        )

    def test_get_unread_uses_peek_and_never_toggles_seen(self):
        messages = [(101, _message(1), [])]
        with FakeMailServer("imap", messages) as server:
            connection = incoming_mail.connect("imap", "127.0.0.1", server.port, "none")
            connection.login("u", "p")
            self.assertEqual(connection.count_unread_messages(), 1)
            fetched = list(connection.get_unread_messages())
            log = " ".join(server.mailbox.log)
            connection.disconnect()
        self.assertEqual(fetched, [(b"101", _message(1))])
        self.assertIn(
            "BODY.PEEK", log, "the unread fetch must peek, not implicitly mark \\Seen"
        )
        self.assertNotIn(
            "-FLAGS",
            log,
            "peeking needs no flag to be toggled back off, so no window can leave "
            "the mail seen-but-unhandled",
        )

    def test_get_unread_before_select_is_named(self):
        for protocol in ("imap", "pop"):
            with self.subTest(protocol=protocol), FakeMailServer(protocol) as server:
                connection = incoming_mail.connect(
                    protocol, "127.0.0.1", server.port, "none"
                )
                with self.assertRaises(incoming_mail.NotSelectedError):
                    next(connection.get_unread_messages())


class TestFetchmailConfiguration(FetchmailCommon):
    def test_encryption_drives_the_default_port(self):
        for server_type, encryption, port in [
            ("imap", "none", 143),
            ("imap", "starttls_strict", 143),
            ("imap", "ssl_strict", 993),
            ("pop", "none", 110),
            ("pop", "ssl", 995),
            ("local", "none", 0),
        ]:
            with self.subTest(server_type=server_type, encryption=encryption):
                self.assertEqual(
                    incoming_mail.default_port(server_type, encryption), port
                )

    def test_encryption_is_an_onchange_trigger(self):
        triggers = self.env["fetchmail.server"]._onchange_methods
        self.assertTrue(triggers.get("server_type"))
        self.assertTrue(
            triggers.get("encryption"),
            "encryption must trigger the onchange whatever addons are installed",
        )

    def test_ticking_encryption_moves_the_port(self):
        Server = self.env["fetchmail.server"]
        spec = {name: {} for name in ("server_type", "encryption", "port")}
        result = Server.onchange(
            {"server_type": "pop", "encryption": "none", "port": 0},
            ["server_type"],
            spec,
        )
        self.assertEqual(result["value"]["port"], 110)
        result = Server.onchange(
            {"server_type": "pop", "encryption": "ssl_strict", "port": 110},
            ["encryption"],
            spec,
        )
        self.assertEqual(result["value"]["port"], 995)

    def test_configuration_is_filled_without_a_form(self):
        server = self._server(name="local one", server_type="local")
        self.assertIn("odoo-mailgate.py", server.configuration)
        self.assertIn(self.env.cr.dbname, server.configuration)
        self.assertIn(
            "--password-file",
            server.configuration,
            "the copy-paste line is where an operator learns the safer form; an "
            "option only the script's --help mentions is one nobody uses",
        )
        self.assertIn("--retry-status", server.configuration)
        self.assertFalse(
            self._server(name="imap one").configuration,
            "a remote server has no mailgate command line",
        )

    def test_server_type_info_follows_server_type(self):
        server = self._server(name="local two", server_type="local")
        self.assertTrue(server.server_type_info)
        server.server_type = "imap"
        self.assertFalse(server.server_type_info)

    def test_credentials_are_group_restricted(self):
        for field in ("user", "password"):
            self.assertEqual(
                self.env["fetchmail.server"]._fields[field].groups,
                "base.group_system",
                "incoming credentials must be restricted like the outgoing ones",
            )

    def test_cron_toggle_skips_irrelevant_writes(self):
        server = self._server(name="cron probe")
        calls = []
        original = type(server)._update_cron

        def spy(records, vals_list=None):
            calls.append(vals_list)
            return original(records, vals_list)

        with patch.object(type(server), "_update_cron", spy):
            server.write({"password": "unrelated"})
            self.assertEqual(calls, [[{"password": "unrelated"}]])
            with patch.object(
                type(self.env["ir.cron"]),
                "toggle",
                side_effect=AssertionError("toggled"),
            ):
                server.write({"priority": 9})
            with self.assertRaises(AssertionError):
                with patch.object(
                    type(self.env["ir.cron"]),
                    "toggle",
                    side_effect=AssertionError("toggled"),
                ):
                    server.write({"state": "draft"})


class TestFetchmailConnect(FakedDialCase, FetchmailCommon):
    def test_an_unreachable_configuration_names_the_field(self):
        for values, expected in [
            ({"server": False}, "Server Name"),
            ({"port": 0}, "Port"),
            ({"server": False, "port": 0}, "Server Name, Port"),
        ]:
            with self.subTest(**values):
                server = self._server(name=f"incomplete {expected}", **values)
                with self.assertRaises(UserError) as caught:
                    server._connect__()
                self.assertIn(expected, str(caught.exception))

    def test_a_provider_server_type_supplies_its_own_endpoint(self):
        server = self._server(name="provider", server_type="local", server="", port=0)
        connection = MockedConnection()
        with (
            patch.object(type(server), "_get_connection_type", lambda self: "imap"),
            patch.object(type(server), "_imap_login__", lambda self, conn: None),
            patch(
                "odoo.addons.mail.models.fetchmail_server.connect",
                lambda *a, **kw: connection,
            ),
        ):
            self.assertIs(
                server._connect__(),
                connection,
                "a provider server type needs no operator-supplied endpoint",
            )

    def test_local_server_cannot_connect(self):
        server = self._server(name="local", server_type="local")
        with self.assertRaises(UserError) as caught:
            server._connect__(allow_archived=True)
        message = str(caught.exception)
        self.assertNotIn("local variable", message)
        self.assertIn(
            "does not connect to a mailbox",
            message,
            "a local server carries no host or port by design, so it must not "
            "be told to fill them in",
        )

    def test_archived_server_cannot_connect(self):
        server = self._server(name="archived")
        server.action_archive()
        with self.assertRaises(UserError):
            server._connect__()

    @mute_logger("odoo.addons.mail.models.fetchmail_server")
    def test_connection_errors_are_translated(self):
        server = self._server(name="mapper")
        for exception, expected in [
            (ConnectionRefusedError("refused"), "Could not establish a connection"),
            (TimeoutError("slow"), "No response received"),
            (
                ssl.SSLCertVerificationError("bad cert"),
                "certificate could not be validated",
            ),
            (UnicodeError("weird"), "Invalid server name"),
            (RuntimeError("internal detail leaking"), "Check the server log"),
        ]:
            with self.subTest(exception=type(exception).__name__):
                error = server._prepare_connection_test_error(exception)
                self.assertIn(expected, str(error))
        self.assertNotIn(
            "internal detail leaking",
            str(
                server._prepare_connection_test_error(
                    RuntimeError("internal detail leaking")
                )
            ),
            "an unexpected error must not be echoed to the user (§2.7)",
        )

    def test_confirm_login_reports_success(self):
        server = self._server(name="confirmed", state="draft")
        connection = MockedConnection()
        with patch.object(
            type(server), "_connect__", lambda self, allow_archived=False: connection
        ):
            action = server.button_confirm_login()
        self.assertEqual(server.state, "done")
        self.assertEqual(action["tag"], "display_notification")
        self.assertTrue(connection.disconnected, "the test session must be closed")


class TestFetchmailErrorState(FetchmailCommon):
    @mute_logger(
        "odoo.addons.mail.models.fetchmail_server", "odoo.addons.base.models.ir_cron"
    )
    def test_failure_records_the_latest_message_and_the_first_date(self):
        record = self._server(name="failing")
        with self._polling_cursor() as env:
            server = record.with_env(env)
            for message in ("first cause", "second cause"):
                with patch.object(
                    type(server),
                    "_connect__",
                    side_effect=Exception(message),
                    autospec=True,
                ):
                    server._poll_mailboxes()
            self.assertEqual(
                server.error_message,
                "second cause",
                "a field labelled 'Last Error Message' must hold the last one",
            )
            first_seen = server.error_since
            self.assertTrue(first_seen)
            with patch.object(
                type(server),
                "_connect__",
                side_effect=Exception("third"),
                autospec=True,
            ):
                server._poll_mailboxes()
            self.assertEqual(
                server.error_since, first_seen, "error_since marks the start of the run"
            )

    @mute_logger("odoo.addons.mail.models.fetchmail_server")
    def test_success_clears_the_error_state(self):
        record = self._server(name="recovering")
        record.write({"error_since": "2020-01-01 00:00:00", "error_message": "old"})
        with self._polling_cursor() as env:
            server = record.with_env(env)
            with patch.object(
                type(server), "_connect__", lambda self, **kw: MockedConnection()
            ):
                server._poll_mailboxes()
            self.assertFalse(server.error_since)
            self.assertFalse(server.error_message)

    def test_set_draft_clears_the_error_state(self):
        server = self._server(name="reset")
        server.write({"error_since": "2020-01-01 00:00:00", "error_message": "old"})
        server.set_draft()
        self.assertEqual(server.state, "draft")
        self.assertFalse(server.error_since)
        self.assertFalse(server.error_message)

    def test_reconfirming_clears_the_error_state(self):
        server = self._server(name="repaired", state="draft")
        server.write({"error_since": "2020-01-01 00:00:00", "error_message": "old"})
        with patch.object(
            type(server),
            "_connect__",
            lambda self, allow_archived=False: MockedConnection(),
        ):
            server.button_confirm_login()
        self.assertFalse(server.error_since)
        self.assertFalse(server.error_message)

    @mute_logger(
        "odoo.addons.mail.models.fetchmail_server", "odoo.addons.base.models.ir_cron"
    )
    def test_a_long_run_of_failures_unconfirms_the_server(self):
        record = self._server(name="doomed")
        with self._polling_cursor() as env:
            server = record.with_env(env)
            with patch.object(
                type(server),
                "_connect__",
                side_effect=Exception("down"),
                autospec=True,
            ):
                server._poll_mailboxes()
                self.assertEqual(server.state, "done", "one failure is not enough")
                server.error_since -= MAIL_SERVER_DEACTIVATE_TIME + datetime.timedelta(
                    minutes=1
                )
                server._poll_mailboxes()
            self.assertEqual(server.state, "draft")
            self.assertFalse(
                server.error_since, "unconfirming resets the run it was measuring"
            )


class TestFetchmailPolling(FetchmailCommon):
    def test_fetch_mail_button_refuses_an_ineligible_server(self):
        server = self._server(name="draft one", state="draft")
        with self.assertRaises(UserError):
            server.action_poll_mailbox()
        local = self._server(name="local three", server_type="local")
        with self.assertRaises(UserError):
            local.action_poll_mailbox()

    def test_the_sink_follows_a_replaced_handler(self):
        server = self._server(name="late bound")
        with self.enter_registry_test_mode(), self.registry.cursor() as cr:
            sink = server._prepare_message_sink(cr)
            self.assertEqual(
                sink.options,
                {"model": False, "save_original": False, "strip_attachments": False},
                "the handler's options belong to the sink as data",
            )
            seen = []
            with patch.object(
                self.registry["mixin.mail.thread"],
                "message_process",
                side_effect=lambda obj, **kw: seen.append(kw),
                autospec=True,
            ):
                sink.process(_message(1))
            self.assertEqual(len(seen), 1, "a sink built earlier must still route")
            self.assertEqual(seen[0]["message"], _message(1))

    def test_message_is_processed_and_acknowledged(self):
        server = self._server(name="working")
        connection = MockedConnection({1: _message(1)})
        seen = {}

        def message_process(obj, model, message, **kw):
            seen["model"] = model
            seen["message"] = message

        with (
            self.enter_registry_test_mode(),
            self.registry.cursor() as cr,
            patch.object(type(server), "_connect__", lambda self, **kw: connection),
            patch.object(
                self.registry["mixin.mail.thread"],
                "message_process",
                side_effect=message_process,
                autospec=True,
            ) as process,
        ):
            server.with_env(server.env(cr=cr)).action_poll_mailbox()
            process.assert_called_once()
        self.assertEqual(seen["message"], _message(1))
        self.assertEqual(connection.acknowledged, [1])

    @mute_logger("odoo.addons.mail.models.fetchmail_server")
    def test_a_failed_acknowledgement_does_not_stop_the_batch(self):
        server = self._server(name="flaky ack")
        connection = MockedConnection({1: _message(1), 2: _message(2), 3: _message(3)})
        connection.fail_ack = True
        processed = []

        def message_process(obj, model, message, **kw):
            processed.append(message)

        with (
            self.enter_registry_test_mode(),
            self.registry.cursor() as cr,
            patch.object(type(server), "_connect__", lambda self, **kw: connection),
            patch.object(
                self.registry["mixin.mail.thread"],
                "message_process",
                side_effect=message_process,
                autospec=True,
            ),
        ):
            exception = server.with_env(server.env(cr=cr)).sudo()._poll_mailboxes()
        self.assertEqual(len(processed), 3, "every message must still be offered")
        self.assertIsNone(exception, "a mark-handled failure is not a server failure")
        self.assertFalse(server.error_since, "nor does it feed the deactivation run")

    @mute_logger("odoo.addons.mail.models.fetchmail_server")
    def test_a_failed_message_does_not_stop_the_batch(self):
        server = self._server(name="flaky message")
        connection = MockedConnection({1: _message(1), 2: _message(2)})
        calls = []

        def message_process(obj, model, message, **kw):
            calls.append(message)
            if len(calls) == 1:
                raise ValueError("unparseable")

        with (
            self.enter_registry_test_mode(),
            self.registry.cursor() as cr,
            patch.object(type(server), "_connect__", lambda self, **kw: connection),
            patch.object(
                self.registry["mixin.mail.thread"],
                "message_process",
                side_effect=message_process,
                autospec=True,
            ),
        ):
            server.with_env(server.env(cr=cr)).sudo()._poll_mailboxes()
        self.assertEqual(len(calls), 2)

    def test_batch_limit_stops_the_server_and_leaves_the_rest(self):
        server = self._server(name="busy")
        connection = MockedConnection({n: _message(n) for n in range(1, 6)})
        with (
            self.enter_registry_test_mode(),
            self.registry.cursor() as cr,
            patch.object(type(server), "_connect__", lambda self, **kw: connection),
            patch.object(
                self.registry["mixin.mail.thread"],
                "message_process",
                side_effect=lambda *a, **kw: None,
                autospec=True,
            ),
        ):
            server.with_env(server.env(cr=cr)).sudo()._poll_mailboxes(batch_limit=2)
        self.assertEqual(len(connection.acknowledged), 2)

    def test_servers_are_polled_in_round_robin_order(self):
        Server = self.env["fetchmail.server"]
        Server.search([]).action_archive()
        Server.create(
            [
                {"name": "p2", "priority": 2, "state": "done"},
                {"name": "p1", "priority": 1, "state": "done"},
                {"name": "p3", "priority": 3, "state": "done"},
            ]
        )
        captured = []

        def _poll_mailboxes(records, **kw):
            captured.append(records.mapped("name"))

        cron = self.env.ref("mail.ir_cron_mail_gateway_action")
        with patch.object(
            self.registry["fetchmail.server"], "_poll_mailboxes", _poll_mailboxes
        ):
            Server.with_context(cron_id=cron.id, cron_end_time=0)._poll_due_mailboxes()
        self.assertEqual(captured, [["p1", "p2", "p3"]])

    def test_teardown_time_is_reserved_from_the_cron_budget_not_added_to_it(self):
        Server = self.env["fetchmail.server"]
        Server.create(
            [
                {"name": "one", "state": "done"},
                {"name": "two", "state": "done"},
                {"name": "three", "state": "done"},
            ]
        )
        deadlines = []

        def _poll_mailboxes(records, **kw):
            deadlines.append(records.env.context["cron_end_time"])

        cron = self.env.ref("mail.ir_cron_mail_gateway_action")
        with patch.object(
            self.registry["fetchmail.server"], "_poll_mailboxes", _poll_mailboxes
        ):
            Server.with_context(
                cron_id=cron.id, cron_end_time=1000.0
            )._poll_due_mailboxes()
        self.assertEqual(deadlines, [1000.0 - 3 * SERVER_TEARDOWN_BUDGET])
        self.assertLess(deadlines[0], 1000.0)

    def test_an_archived_server_is_not_pollable(self):
        server = self._server(name="archived poll")
        server.action_archive()
        with self.assertRaises(UserError):
            server.action_poll_mailbox()
        self.assertFalse(
            server.error_since,
            "refusing an ineligible server is not a failure of the server",
        )

    def test_fetch_mails_is_cron_only(self):
        with self.assertRaises(ValueError):
            self.env["fetchmail.server"]._poll_due_mailboxes()


class TestFetchmailDurability(FetchmailCommon):
    def _poll(self, connection, message_process):
        server = self._server(name="durable")
        with (
            self.enter_registry_test_mode(),
            self.registry.cursor() as cr,
            patch.object(type(server), "_connect__", lambda self, **kw: connection),
            patch.object(
                self.registry["mixin.mail.thread"],
                "message_process",
                side_effect=message_process,
                autospec=True,
            ),
        ):
            server.with_env(server.env(cr=cr)).sudo()._poll_mailboxes()
        return server

    def test_a_processed_message_survives_the_poll(self):
        created = []

        def message_process(obj, model, message, **kw):
            created.append(
                obj.env["res.partner"].create({"name": "raised by the gateway"}).id
            )

        self._poll(MockedConnection({1: _message(1), 2: _message(2)}), message_process)
        self.assertEqual(len(created), 2)
        self.assertEqual(
            self.env["res.partner"].browse(created).exists().ids,
            created,
            "what the handler wrote must be committed, not rolled back with the "
            "cursor it was written on",
        )

    @mute_logger("odoo.addons.mail.models.fetchmail_server")
    def test_a_rolled_back_message_is_not_acknowledged(self):
        connection = MockedConnection({1: _message(1), 2: _message(2)})
        created = []

        def message_process(obj, model, message, **kw):
            partner = obj.env["res.partner"].create({"name": "half written"})
            created.append(partner.id)
            if len(created) == 1:
                raise ValueError("unparseable")

        self._poll(connection, message_process)
        self.assertEqual(
            connection.acknowledged,
            [2],
            "only the message that reached the database may be acknowledged",
        )
        self.assertEqual(
            self.env["res.partner"].browse(created).exists().ids,
            created[1:],
            "the failed message must take its own writes down with it, and only "
            "its own",
        )

    def test_a_message_is_committed_before_it_is_acknowledged(self):
        server = self._server(name="ordered")
        connection = MockedConnection({1: _message(1)})
        order = []
        connection.mark_message_handled = lambda num: order.append("acknowledged")
        with self.enter_registry_test_mode(), self.registry.cursor() as cr:
            commit = type(cr).commit

            def spy(this):
                order.append("committed")
                return commit(this)

            with patch.object(
                self.registry["mixin.mail.thread"],
                "message_process",
                side_effect=lambda *a, **kw: None,
                autospec=True,
            ):
                sink = server._prepare_message_sink(cr)
                with patch.object(type(cr), "commit", spy):
                    handled = server._process_one_message(
                        sink, connection, 1, _message(1), ("imap", "ordered")
                    )
        self.assertTrue(handled)
        self.assertEqual(order, ["committed", "acknowledged"])

    def test_the_poll_never_commits_the_cursor_holding_the_row_lock(self):
        server = self._server(name="locked")
        connection = MockedConnection({n: _message(n) for n in range(1, 4)})
        original = type(self.env["ir.cron"])._commit_progress
        polling_cr = []
        seen = []

        def spy(records, processed=0, *, remaining=None, deactivate=False):
            seen.append(records.env.cr)
            return original(
                records, processed, remaining=remaining, deactivate=deactivate
            )

        def message_process(obj, model, message, **kw):
            polling_cr.append(obj.env.cr)

        with (
            self.enter_registry_test_mode(),
            self.registry.cursor() as cr,
            patch.object(type(server), "_connect__", lambda self, **kw: connection),
            patch.object(type(self.env["ir.cron"]), "_commit_progress", spy),
            patch.object(
                self.registry["mixin.mail.thread"],
                "message_process",
                side_effect=message_process,
                autospec=True,
            ),
        ):
            poll_cr = cr
            server.with_env(server.env(cr=cr)).sudo()._poll_mailboxes()
        message_cr = polling_cr[0]
        self.assertIsNot(message_cr, poll_cr, "the handler runs on its own cursor")
        self.assertEqual(
            [c is message_cr for c in seen],
            [False, True, True, True, False],
            "only the opening and closing publications may commit the polling "
            "cursor; the per-message ones go through the message cursor",
        )

    def test_the_poll_is_committed_before_its_progress_is_published(self):
        server = self._server(name="published")
        connection = MockedConnection({n: _message(n) for n in range(1, 3)})
        events = []
        publish = type(self.env["ir.cron"])._commit_progress

        with (
            self.enter_registry_test_mode(),
            self.registry.cursor() as poll_cr,
            patch.object(type(server), "_connect__", lambda self, **kw: connection),
        ):
            commit = type(poll_cr).commit

            def spy_commit(this):
                events.append(("commit", this is poll_cr))
                return commit(this)

            def spy_publish(records, processed=0, *, remaining=None, deactivate=False):
                events.append(("publish", records.env.cr is poll_cr))
                return publish(
                    records, processed, remaining=remaining, deactivate=deactivate
                )

            with (
                patch.object(type(poll_cr), "commit", spy_commit),
                patch.object(
                    type(self.env["ir.cron"]), "_commit_progress", spy_publish
                ),
                patch.object(
                    self.registry["mixin.mail.thread"],
                    "message_process",
                    side_effect=lambda *a, **kw: None,
                    autospec=True,
                ),
            ):
                server.with_env(server.env(cr=poll_cr)).sudo()._poll_mailboxes()

        publications = [i for i, e in enumerate(events) if e == ("publish", True)]
        self.assertEqual(len(publications), 2, "one opening, one per server")
        self.assertEqual(
            events[publications[-1] - 1],
            ("commit", True),
            "the polling cursor must end its transaction, and so refresh its "
            "snapshot, immediately before it publishes",
        )


class TestFetchmailAccounting(FetchmailCommon):
    def _poll(self, connection, batch_limit=50, **kw):
        cron = self.env.ref("mail.ir_cron_mail_gateway_action")
        progress = (
            self.env["ir.cron.progress"]
            .sudo()
            .create(
                {"cron_id": cron.id, "remaining": 0, "done": 0, "timed_out_counter": 0}
            )
        )
        server = self._server(name="accounting", **kw)
        env = self.env(
            context=dict(
                self.env.context, cron_id=cron.id, ir_cron_progress_id=progress.id
            )
        )
        with (
            self.enter_registry_test_mode(),
            self.registry.cursor() as cr,
            patch.object(type(server), "_connect__", lambda self, **kw: connection),
            patch.object(
                self.registry["mixin.mail.thread"],
                "message_process",
                side_effect=lambda *a, **kw: None,
                autospec=True,
            ),
        ):
            return server.with_env(env(cr=cr))._poll_mailbox(batch_limit, remaining=0)

    def test_an_undercounting_server_does_not_become_a_failing_server(self):
        connection = MockedConnection({n: _message(n) for n in range(1, 4)})
        connection.announces = 1
        with self.assertLogs(
            "odoo.addons.mail.models.fetchmail_server", level="WARNING"
        ) as logs:
            outcome = self._poll(connection)
        self.assertIsNone(outcome.exception, "our arithmetic is not their fault")
        self.assertEqual(outcome.remaining, 0)
        self.assertEqual(len(connection.acknowledged), 3, "all three still delivered")
        self.assertTrue(
            any(
                "announced 1 unread message(s) and yielded 3" in line
                for line in logs.output
            ),
            f"expected the undercount warning, got {logs.output}",
        )

    def test_an_overcounting_server_leaves_no_phantom_backlog(self):
        connection = MockedConnection({1: _message(1)}, announces=9)
        outcome = self._poll(connection)
        self.assertIsNone(outcome.exception)
        self.assertEqual(
            outcome.remaining,
            0,
            "a backlog the mailbox did not actually hand over is not work left",
        )

    def test_an_interrupted_poll_keeps_what_it_did_not_reach(self):
        connection = MockedConnection({n: _message(n) for n in range(1, 6)})
        outcome = self._poll(connection, batch_limit=2)
        self.assertEqual(outcome.remaining, 3, "three were announced and never fetched")

    @mute_logger("odoo.addons.mail.models.fetchmail_server")
    def test_delivered_refused_and_unacknowledged_are_counted_apart(self):
        server = self._server(name="counted")
        connection = MockedConnection({1: _message(1), 2: _message(2)})
        calls = []

        def message_process(obj, model, message, **kw):
            calls.append(message)
            if len(calls) == 1:
                raise ValueError("unparseable")

        with (
            self.enter_registry_test_mode(),
            self.registry.cursor() as cr,
            patch.object(type(server), "_connect__", lambda self, **kw: connection),
            patch.object(
                self.registry["mixin.mail.thread"],
                "message_process",
                side_effect=message_process,
                autospec=True,
            ),
            self.assertLogs(
                "odoo.addons.mail.models.fetchmail_server", level="INFO"
            ) as logs,
        ):
            server.with_env(server.env(cr=cr)).sudo()._poll_mailboxes()
        summary = next(line for line in logs.output if "Fetched 2 email(s)" in line)
        self.assertIn("1 delivered", summary)
        self.assertIn("1 refused", summary)
        self.assertIn("0 delivered but not acknowledged", summary)

    @mute_logger("odoo.addons.mail.models.fetchmail_server")
    def test_a_message_the_mailbox_would_not_flag_is_not_reported_as_lost(self):
        server = self._server(name="unflaggable")
        connection = MockedConnection({1: _message(1)}, fail_ack=True)
        with (
            self.enter_registry_test_mode(),
            self.registry.cursor() as cr,
            patch.object(type(server), "_connect__", lambda self, **kw: connection),
            patch.object(
                self.registry["mixin.mail.thread"],
                "message_process",
                side_effect=lambda *a, **kw: None,
                autospec=True,
            ),
            self.assertLogs(
                "odoo.addons.mail.models.fetchmail_server", level="INFO"
            ) as logs,
        ):
            server.with_env(server.env(cr=cr)).sudo()._poll_mailboxes()
        summary = next(line for line in logs.output if "Fetched 1 email(s)" in line)
        self.assertIn("0 refused", summary)
        self.assertIn("1 delivered but not acknowledged", summary)


class TestFetchmailProgress(FetchmailCommon):
    def _progress(self):
        cron = self.env.ref("mail.ir_cron_mail_gateway_action")
        progress = (
            self.env["ir.cron.progress"]
            .sudo()
            .create(
                {"cron_id": cron.id, "remaining": 0, "done": 0, "timed_out_counter": 0}
            )
        )
        return cron, progress

    def test_backlog_is_published_while_it_is_being_worked(self):
        cron, progress = self._progress()
        server = self._server(name="progress")
        connection = MockedConnection({1: _message(1), 2: _message(2), 3: _message(3)})
        observed = []
        original = type(self.env["ir.cron"])._commit_progress

        def spy(records, processed=0, *, remaining=None, deactivate=False):
            result = original(
                records, processed, remaining=remaining, deactivate=deactivate
            )
            progress.invalidate_recordset()
            observed.append(progress.remaining)
            return result

        env = self.env(
            context=dict(
                self.env.context, cron_id=cron.id, ir_cron_progress_id=progress.id
            )
        )
        with (
            self.enter_registry_test_mode(),
            self.registry.cursor() as cr,
            patch.object(type(server), "_connect__", lambda self, **kw: connection),
            patch.object(type(self.env["ir.cron"]), "_commit_progress", spy),
            patch.object(
                self.registry["mixin.mail.thread"],
                "message_process",
                side_effect=lambda *a, **kw: None,
                autospec=True,
            ),
        ):
            server.with_env(env(cr=cr)).sudo()._poll_mailboxes()
        self.assertEqual(
            observed,
            [1, 2, 1, 0, 0],
            "the discovered backlog must reach ir.cron, not stay a local variable",
        )

    def test_a_skipped_server_does_not_leave_phantom_work(self):
        cron, progress = self._progress()
        server = self._server(name="held elsewhere")
        env = self.env(
            context=dict(
                self.env.context, cron_id=cron.id, ir_cron_progress_id=progress.id
            )
        )
        with (
            self.enter_registry_test_mode(),
            self.registry.cursor() as cr,
            patch.object(
                self.registry["fetchmail.server"],
                "try_lock_for_update",
                lambda self, **kw: self.browse(),
            ),
        ):
            server.with_env(env(cr=cr)).sudo()._poll_mailboxes()
        progress.invalidate_recordset()
        self.assertEqual(
            progress.remaining,
            0,
            "a server another worker holds is not this pass's remaining work",
        )
        self.assertEqual(
            self.registry["ir.cron"]
            ._resolve_completion_status(
                success=True, done=progress.done, remaining=progress.remaining
            )
            .value,
            "fully done",
            "reporting it as remaining reschedules the cron at once and spins "
            "against the worker that does hold the server",
        )

    @mute_logger("odoo.addons.mail.models.fetchmail_server")
    def test_a_broken_server_does_not_leave_phantom_work(self):
        cron, progress = self._progress()
        server = self._server(name="broken")

        class Broken:
            def count_unread_messages(self):
                return 100

            def get_unread_messages(self):
                raise OSError("dropped mid-batch")

            def mark_message_handled(self, num):
                pass

            def disconnect(self):
                pass

        env = self.env(
            context=dict(
                self.env.context, cron_id=cron.id, ir_cron_progress_id=progress.id
            )
        )
        with (
            self.enter_registry_test_mode(),
            self.registry.cursor() as cr,
            patch.object(type(server), "_connect__", lambda self, **kw: Broken()),
        ):
            server.with_env(env(cr=cr)).sudo()._poll_mailboxes()
        progress.invalidate_recordset()
        self.assertEqual(
            progress.remaining,
            0,
            "a backlog nobody can deliver this pass is not remaining work",
        )
        self.assertEqual(
            self.registry["ir.cron"]
            ._resolve_completion_status(
                success=True, done=progress.done, remaining=progress.remaining
            )
            .value,
            "fully done",
        )


class TestLocalConfigurationIsPerReader(FetchmailCommon):
    def test_two_readers_in_one_transaction_get_their_own_uid(self):
        server = self._server(server_type="local")
        other = self.env["res.users"].create(
            {
                "name": "Other Reader",
                "login": "fetchmail_other_reader",
                "group_ids": [(6, 0, self.env.ref("base.group_system").ids)],
            }
        )

        mine = server.configuration
        theirs = server.with_user(other).configuration

        self.assertIn(f"-u {self.env.uid} ", mine)
        self.assertIn(f"-u {other.id} ", theirs)
        self.assertNotEqual(
            mine, theirs, "the cached answer must not outlive the reader"
        )

    def test_a_remote_server_has_no_configuration_to_leak(self):
        server = self._server()
        self.assertFalse(server.configuration)
