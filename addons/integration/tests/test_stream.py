import base64
import ssl
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from odoo import fields
from odoo.exceptions import UserError, ValidationError
from odoo.service._stream import RUNTIME, StreamRuntime, process_streams
from odoo.tests import TransactionCase, tagged

from ..tools import stream_protocol, stream_runtime
from ..tools.stream_protocol import StreamProtocol, TlsMaterial, tls_context


class ProbeProtocol(StreamProtocol):
    key = "probe"
    label = "Probe"
    schemes = ("probe",)

    opened: list = []
    fail_next_open: list[str] = []

    def open(self, stream, on_frame, on_state):
        if self.fail_next_open:
            raise ConnectionError(self.fail_next_open.pop(0))
        handle = {
            "stream": stream,
            "on_frame": on_frame,
            "on_state": on_state,
            "sent": [],
            "alive": True,
            "closed": False,
        }
        type(self).opened.append(handle)
        return handle

    def send(self, handle, payload, meta):
        if meta.get("fail"):
            raise OSError("the wire refused the frame")
        handle["sent"].append((payload, dict(meta)))

    def alive(self, handle):
        return handle["alive"]

    def close(self, handle):
        handle["closed"] = True


@tagged("post_install", "-at_install", "integration")
class TestStream(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        stream_protocol.register(ProbeProtocol)
        cls.env.registry.clear_cache()
        cls.db = cls.env.cr.dbname
        cls.subject = cls.env["res.partner"].create({"name": "Stream subject"})

    def setUp(self):
        super().setUp()
        ProbeProtocol.opened = []
        ProbeProtocol.fail_next_open = []
        self.runtime = StreamRuntime()
        self.addCleanup(self.runtime.shutdown)
        patcher = patch.object(stream_runtime, "RUNTIME", self.runtime)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self._forget_open_streams)

    def _forget_open_streams(self):
        for stream_id in list(stream_runtime.held(self.db)):
            stream_runtime.drop(self.db, stream_id)

    def _stream(self, **vals):
        return self.env["integration.stream"].create(
            {
                "name": "Probe stream",
                "protocol": "probe",
                "url": "probe://127.0.0.1:9/feed",
                "res_model": "res.partner",
                "res_id": self.subject.id,
                "backoff_seconds": 5,
                **vals,
            }
        )

    def _reconcile(self):
        with patch.object(
            type(self.env["integration.stream"]),
            "_resolve_addresses",
            lambda self: ("127.0.0.1",),
        ):
            self.env["integration.stream"]._reconcile_with(self.db, self.runtime)

    def test_the_probe_is_a_protocol_the_selection_offers(self):
        keys = dict(self.env["integration.stream"]._selection_protocol())
        self.assertEqual(keys["probe"], "Probe")

    def test_a_url_of_another_scheme_is_refused(self):
        with self.assertRaises(ValidationError):
            self._stream(url="mqtt://broker/feed")

    def test_the_sweep_opens_an_active_stream_and_holds_it(self):
        stream = self._stream()
        self._reconcile()
        self.assertEqual(len(ProbeProtocol.opened), 1)
        handle = ProbeProtocol.opened[0]
        self.assertEqual(handle["stream"].url, "probe://127.0.0.1:9/feed")
        self.assertEqual(handle["stream"].addresses, ("127.0.0.1",))
        self.assertEqual(stream.state, "open")
        self.assertTrue(stream.owner)
        self.assertEqual(stream_runtime.held(self.db), {stream.id})

        self._reconcile()
        self.assertEqual(len(ProbeProtocol.opened), 1, "held, not redialled")

    def test_a_stopped_stream_is_closed_on_the_next_sweep(self):
        stream = self._stream()
        self._reconcile()
        handle = ProbeProtocol.opened[0]
        stream.action_stop()
        self._reconcile()
        self.assertTrue(handle["closed"])
        self.assertEqual(stream.state, "stopped")
        self.assertFalse(stream_runtime.held(self.db))

    def test_a_dropped_connection_is_redialled_under_backoff(self):
        stream = self._stream()
        self._reconcile()
        ProbeProtocol.opened[0]["alive"] = False
        self._reconcile()
        self.assertEqual(stream.state, "backoff")
        self.assertEqual(stream.attempts, 1)
        self.assertGreater(stream.date_next_attempt, fields.Datetime.now())
        self.assertEqual(len(ProbeProtocol.opened), 1, "not before its time")

        stream.date_next_attempt = fields.Datetime.now() - timedelta(seconds=1)
        self._reconcile()
        self.assertEqual(len(ProbeProtocol.opened), 2)
        self.assertEqual((stream.state, stream.attempts), ("open", 0))

    def test_a_dial_that_fails_backs_off_and_says_why(self):
        stream = self._stream()
        ProbeProtocol.fail_next_open.append("broker unreachable")
        self._reconcile()
        self.assertEqual(stream.state, "backoff")
        self.assertIn("broker unreachable", stream.state_message)
        self.assertFalse(stream.owner)
        self.assertFalse(stream_runtime.held(self.db))

    def test_a_changed_row_is_redialled(self):
        stream = self._stream()
        self._reconcile()
        stream.subscriptions = {"topics": ["a/b"]}
        self._reconcile()
        self.assertTrue(ProbeProtocol.opened[0]["closed"])
        self.assertEqual(len(ProbeProtocol.opened), 2)
        self.assertEqual(
            ProbeProtocol.opened[1]["stream"].subscriptions, {"topics": ["a/b"]}
        )

    def test_a_frame_is_a_row_and_reaches_the_subject(self):
        stream = self._stream()
        self._reconcile()
        seen = []

        def on_stream_frame(partner, stream_record, payload, meta):
            seen.append((partner, stream_record, payload, dict(meta)))

        with patch.object(
            type(self.env["res.partner"]),
            "_on_stream_frame",
            on_stream_frame,
            create=True,
        ):
            stream._handle_frame(b'{"t": 21.5}', {"topic": "scale/1"})

        self.assertEqual(seen[0][0], self.subject)
        self.assertEqual(seen[0][2], b'{"t": 21.5}')
        row = self.env["integration.exchange"].search(
            [("channel_id", "=", f"integration.stream,{stream.id}")]
        )
        self.assertEqual(
            (row.direction, row.event_type, row.state),
            ("inbound", "scale/1", "success"),
        )
        self.assertEqual(row.origin_record_id, self.subject.id)
        self.assertEqual(stream.frames_in, 1)
        self.assertTrue(stream.date_last_frame)

    def test_a_subject_that_refuses_a_frame_fails_the_row_and_keeps_the_stream(self):
        stream = self._stream()

        def refuse(partner, stream_record, payload, meta):
            raise ValueError("bad frame")

        with patch.object(
            type(self.env["res.partner"]), "_on_stream_frame", refuse, create=True
        ):
            stream._handle_frame(b"garbage", {})

        row = self.env["integration.exchange"].search(
            [("channel_id", "=", f"integration.stream,{stream.id}")]
        )
        self.assertEqual(row.state, "failed")
        self.assertIn("bad frame", row.error_message)

    def test_the_subject_hears_every_state(self):
        self._stream()
        heard = []

        def on_stream_state(partner, stream_record, state, message):
            heard.append((state, message))

        with patch.object(
            type(self.env["res.partner"]),
            "_on_stream_state",
            on_stream_state,
            create=True,
        ):
            self._reconcile()
            ProbeProtocol.opened[0]["alive"] = False
            self._reconcile()
        self.assertEqual(
            [state for state, _m in heard], ["connecting", "open", "backoff"]
        )
        self.assertEqual(heard[-1][1], "the connection dropped")

    def test_the_outbox_is_sent_through_the_open_stream(self):
        stream = self._stream()
        self._reconcile()
        stream.send(b'{"cmd": "tare"}', topic="scale/1/cmd", qos=1)
        stream.send("second", fail=True)
        self._reconcile()

        handle = ProbeProtocol.opened[0]
        self.assertEqual(
            handle["sent"], [(b'{"cmd": "tare"}', {"topic": "scale/1/cmd", "qos": 1})]
        )
        rows = self.env["integration.stream.outbox"].search(
            [("stream_id", "=", stream.id)], order="id"
        )
        self.assertEqual(rows.mapped("state"), ["sent", "failed"])
        self.assertIn("refused the frame", rows[1].error)
        self.assertEqual(stream.frames_out, 1)
        outbound = self.env["integration.exchange"].search(
            [
                ("channel_id", "=", f"integration.stream,{stream.id}"),
                ("direction", "=", "outbound"),
            ],
            order="id",
        )
        self.assertEqual(outbound.mapped("state"), ["success", "failed"])

        rows[1].action_retry()
        self.assertEqual(rows[1].state, "pending")

    def test_the_worker_s_own_writes_do_not_wake_it(self):
        stream = self._stream()
        self.env.cr.postcommit.data.pop("integration.stream.notify", None)
        stream._set_state("open", None)
        self.assertNotIn("integration.stream.notify", self.env.cr.postcommit.data)
        stream.url = "probe://127.0.0.1:9/other"
        self.assertTrue(self.env.cr.postcommit.data.get("integration.stream.notify"))

    def test_the_stream_is_an_exchange_channel(self):
        channels = dict(self.env["integration.exchange"]._selection_channel_models())
        self.assertIn("integration.stream", channels)

    def test_the_wire_s_own_reason_dates_the_redial(self):
        stream = self._stream()
        self._reconcile()
        stream._note_state("backoff", "closed: 1006 gone")
        self.assertEqual(
            (stream.state, stream.attempts, stream.state_message),
            ("backoff", 1, "closed: 1006 gone"),
        )
        self.assertGreater(stream.date_next_attempt, fields.Datetime.now())
        ProbeProtocol.opened[0]["alive"] = False
        self._reconcile()
        self.assertEqual(stream.attempts, 1, "the sweep does not date it twice")
        self.assertEqual(stream.state_message, "closed: 1006 gone")
        self.assertFalse(stream_runtime.held(self.db))

    def test_a_refusal_the_wire_reports_keeps_its_state_and_still_redials(self):
        stream = self._stream()
        self._reconcile()
        stream._note_state("error", "connection refused: 5")
        self.assertEqual(stream.state, "error")
        self.assertGreater(stream.date_next_attempt, fields.Datetime.now())
        stream._note_state("open", None)
        self.assertEqual((stream.state, stream.attempts), ("open", 0))
        self.assertFalse(stream.date_next_attempt)

    def test_a_stream_with_no_certificate_carries_no_tls_material(self):
        snapshot = self._stream()._snapshot(self.db, addresses=False)
        self.assertIsNone(snapshot.tls)
        self.assertIsInstance(tls_context(snapshot), ssl.SSLContext)

    def test_the_snapshot_carries_the_certificate_the_key_and_the_authority(self):
        certificate, authority = self._certificates()
        stream = self._stream(
            certificate_id=certificate.id, ca_certificate_id=authority.id
        )
        snapshot = stream._snapshot(self.db, addresses=False)
        self.assertTrue(snapshot.tls.certificate.startswith("-----BEGIN CERTIFICATE"))
        self.assertTrue(snapshot.tls.key.startswith("-----BEGIN PRIVATE KEY"))
        self.assertTrue(snapshot.tls.ca.startswith("-----BEGIN CERTIFICATE"))
        context = tls_context(snapshot)
        self.assertEqual(
            [entry["subject"][-1][0][1] for entry in context.get_ca_certs()],
            ["Stream Test CA"],
        )

    def test_a_certificate_without_its_key_refuses_to_dial(self):
        certificate, _authority = self._certificates()
        certificate.private_key_id = False
        stream = self._stream(certificate_id=certificate.id)
        with self.assertRaises(UserError):
            stream._snapshot(self.db, addresses=False)
        self._reconcile()
        self.assertEqual(stream.state, "backoff")
        self.assertIn("no private key", stream.state_message)

    def test_a_rotated_certificate_redials(self):
        certificate, authority = self._certificates()
        stream = self._stream(certificate_id=certificate.id)
        self._reconcile()
        stream.ca_certificate_id = authority
        self._reconcile()
        self.assertEqual(len(ProbeProtocol.opened), 2)
        self.assertEqual(
            ProbeProtocol.opened[1]["stream"].tls,
            TlsMaterial(
                certificate=ProbeProtocol.opened[0]["stream"].tls.certificate,
                key=ProbeProtocol.opened[0]["stream"].tls.key,
                ca=stream._pem_text(authority),
            ),
        )

    def _certificates(self):
        def pem(certificate):
            return base64.b64encode(
                certificate.public_bytes(serialization.Encoding.PEM)
            )

        def issue(name, key, issuer=None, signer=None):
            subject = x509.Name(
                [x509.NameAttribute(x509.oid.NameOID.COMMON_NAME, name)]
            )
            return (
                x509.CertificateBuilder()
                .subject_name(subject)
                .issuer_name(issuer or subject)
                .public_key(key.public_key())
                .serial_number(x509.random_serial_number())
                .not_valid_before(datetime.now(UTC) - timedelta(days=1))
                .not_valid_after(datetime.now(UTC) + timedelta(days=1))
                .add_extension(
                    x509.BasicConstraints(ca=issuer is None, path_length=None),
                    critical=True,
                )
                .sign(signer or key, hashes.SHA256())
            )

        ca_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        ca = issue("Stream Test CA", ca_key)
        client_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        client = issue("stream-client", client_key, issuer=ca.subject, signer=ca_key)
        key = self.env["certificate.key"].create(
            {
                "name": "stream client key",
                "content": base64.b64encode(
                    client_key.private_bytes(
                        encoding=serialization.Encoding.PEM,
                        format=serialization.PrivateFormat.PKCS8,
                        encryption_algorithm=serialization.NoEncryption(),
                    )
                ),
            }
        )
        Certificate = self.env["certificate.certificate"]
        certificate = Certificate.create(
            {
                "name": "stream client",
                "content": pem(client),
                "private_key_id": key.id,
            }
        )
        authority = Certificate.create({"name": "stream ca", "content": pem(ca)})
        return certificate, authority


@tagged("post_install", "-at_install", "integration")
class TestStreamLease(TransactionCase):
    def test_a_second_runtime_cannot_lead_while_the_first_does(self):
        first, second = StreamRuntime(), StreamRuntime()
        self.addCleanup(first.shutdown)
        self.addCleanup(second.shutdown)
        db = self.env.cr.dbname
        self.assertTrue(first.lease(db, self.env.registry))
        self.assertFalse(second.lease(db, self.env.registry), "one leader per database")
        first.release(db)
        self.assertTrue(second.lease(db, self.env.registry), "released, it moves")

    def test_releasing_closes_what_the_runtime_held(self):
        runtime = StreamRuntime()
        self.addCleanup(runtime.shutdown)
        closed = []
        runtime.hold("some_db", 1, lambda: closed.append(1))
        runtime.hold("some_db", 2, lambda: closed.append(2))
        self.assertEqual(runtime.held("some_db"), {1, 2})
        runtime.release("some_db")
        self.assertEqual(sorted(closed), [1, 2])
        self.assertFalse(runtime.held("some_db"))

    def test_the_step_leaves_a_database_it_cannot_lead(self):
        other = StreamRuntime()
        self.addCleanup(other.shutdown)
        db = self.env.cr.dbname
        self.assertTrue(other.lease(db, self.env.registry))
        with patch.object(
            type(self.env["integration.stream"]), "_reconcile"
        ) as reconcile:
            process_streams(db)
        reconcile.assert_not_called()
        self.assertFalse(RUNTIME.leads(db))
