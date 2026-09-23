import base64
import logging
import os
import socket
from datetime import timedelta
from urllib.parse import urlsplit

from odoo import SUPERUSER_ID, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.libs import backoff, redact
from odoo.modules.registry import Registry
from odoo.service.transaction import retrying
from odoo.tools.constants import STREAM_CHANNEL

from ..tools import stream_protocol, stream_runtime
from ..tools.stream_protocol import StreamSnapshot, TlsMaterial
from odoo.addons.base.models.ir_cron import notify_channel, schedule_notify_after_commit

_logger = logging.getLogger(__name__)

NOTIFY_PENDING_KEY = "integration.stream.notify"

_FRAME_LOG_BYTES = 64 * 1024


class IntegrationStream(models.Model):
    _name = "integration.stream"
    _description = "Stream"
    _order = "name, id"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    protocol = fields.Selection(
        selection="_selection_protocol",
        required=True,
    )
    url = fields.Char(
        required=True,
        help="Where the stream dials: ws://, wss://, mqtt://, mqtts://, modbus://.",
    )
    credential_id = fields.Many2one(
        comodel_name="credential.credential",
        ondelete="restrict",
        help="The secret the dial presents; its login, when the wire takes one.",
    )
    login = fields.Char(help="The login presented beside the credential.")
    certificate_id = fields.Many2one(
        comodel_name="certificate.certificate",
        ondelete="restrict",
        help="The client certificate and key the dial presents (mutual TLS).",
    )
    ca_certificate_id = fields.Many2one(
        comodel_name="certificate.certificate",
        ondelete="restrict",
        help="The authority the peer's certificate is checked against, when it "
        "is not one of the system's.",
    )
    connection_id = fields.Many2one(
        comodel_name="integration.connection",
        ondelete="set null",
        help="The outbound connection whose breaker and budget this stream shares.",
    )
    company_id = fields.Many2one(comodel_name="res.company")
    res_model = fields.Char(index=True)
    res_id = fields.Many2oneReference(
        model_field="res_model",
        index=True,
    )
    subscriptions = fields.Json(
        help="What the stream listens to: topics, registers or paths, as the "
        "protocol reads them."
    )
    options = fields.Json(help="Protocol options: TLS, QoS, client id, unit id.")
    heartbeat_seconds = fields.Integer(
        default=30,
        help="How often the wire is asked whether it is still open.",
    )
    backoff_seconds = fields.Integer(
        default=5,
        help="The first wait before redialling a stream that dropped.",
    )
    backoff_max_seconds = fields.Integer(
        default=300,
        help="The longest wait between redials.",
    )

    state = fields.Selection(
        selection=[
            ("stopped", "Stopped"),
            ("connecting", "Connecting"),
            ("open", "Open"),
            ("backoff", "Waiting to redial"),
            ("error", "Error"),
        ],
        default="stopped",
        index=True,
        readonly=True,
    )
    state_message = fields.Char(readonly=True)
    owner = fields.Char(
        readonly=True,
        help="The worker holding the connection: host:pid.",
    )
    attempts = fields.Integer(readonly=True)
    date_state = fields.Datetime(readonly=True)
    date_next_attempt = fields.Datetime(readonly=True)
    date_last_frame = fields.Datetime(readonly=True)
    frames_in = fields.Integer(readonly=True)
    frames_out = fields.Integer(readonly=True)
    outbox_pending_count = fields.Integer(compute="_compute_outbox_pending_count")

    @api.model
    def _selection_protocol(self):
        return [
            (key, protocol.label or key)
            for key, protocol in sorted(stream_protocol.STREAM_PROTOCOLS.items())
        ]

    @api.constrains("heartbeat_seconds", "backoff_seconds", "backoff_max_seconds")
    def _check_timing(self):
        for stream in self:
            if stream.heartbeat_seconds <= 0 or stream.backoff_seconds <= 0:
                raise ValidationError(
                    self.env._("A stream's heartbeat and backoff are positive seconds.")
                )
            if stream.backoff_max_seconds < stream.backoff_seconds:
                raise ValidationError(
                    self.env._("A stream's longest wait is at least its first.")
                )

    @api.constrains("url", "protocol")
    def _check_url_scheme(self):
        for stream in self:
            protocol = stream_protocol.STREAM_PROTOCOLS.get(stream.protocol)
            scheme = (stream.url or "").partition("://")[0].lower()
            if protocol and protocol.schemes and scheme not in protocol.schemes:
                raise ValidationError(
                    self.env._(
                        "%(protocol)s dials %(schemes)s, not %(scheme)s://.",
                        protocol=protocol.label or protocol.key,
                        schemes=", ".join(f"{s}://" for s in protocol.schemes),
                        scheme=scheme or "?",
                    )
                )

    def _compute_outbox_pending_count(self):
        pending = dict(
            self.env["integration.stream.outbox"]._read_group(
                [("stream_id", "in", self.ids), ("state", "=", "pending")],
                ["stream_id"],
                ["__count"],
            )
        )
        for stream in self:
            stream.outbox_pending_count = pending.get(stream, 0)

    # -- what changes a stream wakes the worker ------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        streams = super().create(vals_list)
        self._notify_after_commit()
        return streams

    def write(self, vals):
        result = super().write(vals)
        if not vals.keys() <= self._WORKER_FIELDS:
            self._notify_after_commit()
        return result

    def unlink(self):
        result = super().unlink()
        self._notify_after_commit()
        return result

    # The worker's own writes never wake the worker.
    _WORKER_FIELDS = frozenset(
        {
            "state",
            "state_message",
            "owner",
            "attempts",
            "date_state",
            "date_next_attempt",
            "date_last_frame",
            "frames_in",
            "frames_out",
        }
    )

    def _notify_after_commit(self):
        schedule_notify_after_commit(
            self.env.cr, NOTIFY_PENDING_KEY, self._notify_workers
        )

    @staticmethod
    def _notify_workers(db_name):
        notify_channel(STREAM_CHANNEL, db_name)

    def send(self, payload, **meta):
        """Queue a frame for the worker to send; the row is the record of it."""
        self.check_singleton()
        outbox = self.env["integration.stream.outbox"].create(
            {
                "stream_id": self.id,
                "payload": payload.decode("utf-8", errors="replace")
                if isinstance(payload, bytes)
                else payload,
                "meta": meta or None,
            }
        )
        self._notify_after_commit()
        return outbox

    def action_stop(self):
        self.write({"active": False})

    def action_start(self):
        self.write({"active": True, "date_next_attempt": False, "attempts": 0})

    # -- the sweep -----------------------------------------------------------

    @staticmethod
    def _worker_identity():
        return f"{socket.gethostname()}:{os.getpid()}"

    @staticmethod
    def _reconcile(db_name, runtime):
        """One pass for the database this process leads: open what should
        be open, close what should not, redial what dropped, send what is
        queued. Called by the stream worker under the lease."""
        registry = Registry(db_name)
        with registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            env["integration.stream"]._reconcile_with(db_name, runtime)
            cr.commit()

    def _reconcile_with(self, db_name, runtime):
        wanted = self.sudo().search([("active", "=", True)])
        held = stream_runtime.held(db_name)
        for stream_id in held - set(wanted.ids):
            stream_runtime.drop(db_name, stream_id)
            gone = self.sudo().browse(stream_id).exists()
            if gone:
                gone._set_state("stopped", "stopped by the worker", owner=False)
        now = fields.Datetime.now()
        for stream in wanted:
            open_stream = stream_runtime.get(db_name, stream.id)
            if open_stream is not None:
                if open_stream.snapshot != stream._snapshot(db_name, addresses=False):
                    stream_runtime.drop(db_name, stream.id)
                    open_stream = None
                elif not open_stream.protocol.alive(open_stream.handle):
                    stream_runtime.drop(db_name, stream.id)
                    open_stream = None
                    if not stream.date_next_attempt or stream.date_next_attempt <= now:
                        stream._schedule_redial("the connection dropped")
            if open_stream is None:
                if stream.date_next_attempt and stream.date_next_attempt > now:
                    continue
                open_stream = stream._open(db_name)
            if open_stream is not None:
                stream._drain_outbox(open_stream)

    def _snapshot(self, db_name, *, addresses=True):
        self.check_singleton()
        credential = self.sudo().credential_id
        return StreamSnapshot(
            id=self.id,
            db_name=db_name,
            name=self.name,
            protocol=self.protocol,
            url=self.url,
            secret=credential.credential_value if credential else None,
            login=self.login or (credential.username if credential else None) or None,
            subscriptions=dict(self.subscriptions or {}),
            heartbeat_seconds=self.heartbeat_seconds,
            options=dict(self.options or {}),
            addresses=self._resolve_addresses() if addresses else (),
            tls=self._tls_material(),
        )

    def _tls_material(self):
        certificate = self.sudo().certificate_id
        authority = self.sudo().ca_certificate_id
        if not certificate and not authority:
            return None
        material = {}
        if certificate:
            key = certificate.private_key_id
            if not certificate.pem_certificate or not key:
                raise UserError(
                    self.env._(
                        "Certificate %s carries no certificate or no private key.",
                        certificate.display_name,
                    )
                )
            material["certificate"] = self._pem_text(certificate)
            material["key"] = key._get_unencrypted_pem_key(formatting="pem").decode()
        if authority:
            if not authority.pem_certificate:
                raise UserError(
                    self.env._(
                        "Certificate %s carries no certificate.", authority.display_name
                    )
                )
            material["ca"] = self._pem_text(authority)
        return TlsMaterial(**material)

    @staticmethod
    def _pem_text(certificate):
        return base64.b64decode(
            certificate.with_context(bin_size=False).pem_certificate
        ).decode()

    def _resolve_addresses(self):
        # A serial line (modbus+rtu:///dev/ttyUSB0) names no host to check.
        if not urlsplit(self.url).hostname:
            return ()
        destination = self.env["ir.egress"].check_url(self.url, policy="private")
        return tuple(str(address) for address in destination.addresses)

    def _open(self, db_name):
        self.check_singleton()
        stream_id, name = self.id, self.name
        try:
            protocol = stream_protocol.get(self.protocol)
            snapshot = self._snapshot(db_name)
            self._set_state("connecting", None)
            handle = protocol.open(
                snapshot,
                lambda payload, meta: self._record_frame(
                    db_name, stream_id, payload, meta
                ),
                lambda state, message: self._record_state(
                    db_name, stream_id, state, message
                ),
            )
        except Exception as error:
            _logger.warning(
                "Stream %s (%s) did not open: %s", name, stream_id, error, exc_info=True
            )
            self._schedule_redial(f"{type(error).__name__}: {error}")
            return None
        open_stream = stream_runtime.OpenStream(
            protocol, handle, self._snapshot(db_name, addresses=False)
        )
        stream_runtime.hold(db_name, open_stream)
        self._set_state("open", None, owner=self._worker_identity(), attempts=0)
        return open_stream

    def _schedule_redial(self, message, state="backoff"):
        self.check_singleton()
        attempt = self.attempts + 1
        delay = backoff.get_delay(
            attempt, base=self.backoff_seconds, cap=self.backoff_max_seconds
        )
        self._set_state(
            state,
            message,
            owner=False,
            attempts=attempt,
            date_next_attempt=fields.Datetime.now() + timedelta(seconds=delay),
        )

    def _set_state(self, state, message, **vals):
        self.sudo().write(
            {
                "state": state,
                "state_message": (message or "")[:256] or False,
                "date_state": fields.Datetime.now(),
                **vals,
            }
        )
        subject = self._subject()
        told = getattr(subject, "_on_stream_state", None) if subject else None
        if told is not None:
            try:
                with self.env.cr.savepoint():
                    told(self, state, message)
            except Exception:
                _logger.warning(
                    "Stream %s: the subject refused the state %s",
                    self.name,
                    state,
                    exc_info=True,
                )

    def _drain_outbox(self, open_stream):
        self.check_singleton()
        pending = (
            self.env["integration.stream.outbox"]
            .sudo()
            .search(
                [("stream_id", "=", self.id), ("state", "=", "pending")], order="id"
            )
        )
        sent = 0
        for row in pending:
            try:
                open_stream.protocol.send(
                    open_stream.handle, row.payload.encode("utf-8"), row.meta or {}
                )
            except Exception as error:
                _logger.warning(
                    "Stream %s: sending an outbox row failed", self.name, exc_info=True
                )
                row.write(
                    {
                        "state": "failed",
                        "attempts": row.attempts + 1,
                        "error": redact.mask_text(f"{type(error).__name__}: {error}")[
                            :512
                        ],
                    }
                )
                self._record_exchange(
                    row.payload, row.meta or {}, direction="outbound", error=str(error)
                )
                continue
            row.write({"state": "sent", "date_sent": fields.Datetime.now()})
            self._record_exchange(row.payload, row.meta or {}, direction="outbound")
            sent += 1
        if sent:
            self.sudo().write({"frames_out": self.frames_out + sent})

    # -- what the wire reports, on its own thread -----------------------------

    @staticmethod
    def _record_frame(db_name, stream_id, payload, meta):
        IntegrationStream._on_wire(
            db_name,
            stream_id,
            lambda stream: stream._handle_frame(payload, dict(meta or {})),
        )

    @staticmethod
    def _on_wire(db_name, stream_id, act):
        # The wire's thread writes beside the sweep's own transaction, which
        # may still hold the row it just dialled: a serialization failure is
        # retried, as a request's would be.
        registry = Registry(db_name)
        with registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})

            def work():
                stream = env["integration.stream"].browse(stream_id).exists()
                if stream:
                    act(stream)

            retrying(work, env)

    def _handle_frame(self, payload, meta):
        self.check_singleton()
        text = (
            payload.decode("utf-8", errors="replace")
            if isinstance(payload, bytes)
            else payload
        )
        exchange = self._record_exchange(text, meta, direction="inbound")
        self.sudo().write(
            {"frames_in": self.frames_in + 1, "date_last_frame": fields.Datetime.now()}
        )
        subject = self._subject()
        handler = getattr(subject, "_on_stream_frame", None) if subject else None
        if handler is None:
            return
        try:
            with self.env.cr.savepoint():
                handler(self, payload, meta)
        except Exception as error:
            _logger.warning(
                "Stream %s: the subject refused a frame: %s",
                self.name,
                error,
                exc_info=True,
            )
            exchange.mark_failed(
                redact.mask_text(f"{type(error).__name__}: {error}"),
                schedule_retry=False,
            )

    @staticmethod
    def _record_state(db_name, stream_id, state, message):
        IntegrationStream._on_wire(
            db_name, stream_id, lambda stream: stream._note_state(state, message)
        )

    def _note_state(self, state, message):
        self.check_singleton()
        if state not in dict(self._fields["state"].selection):
            return
        if state in ("backoff", "error"):
            self._schedule_redial(message, state=state)
        elif state == "open":
            self._set_state(state, message, date_next_attempt=False, attempts=0)
        else:
            self._set_state(state, message)

    def _subject(self):
        self.check_singleton()
        if self.res_model and self.res_id and self.res_model in self.env:
            return self.env[self.res_model].sudo().browse(self.res_id).exists()
        return None

    def _record_exchange(self, text, meta, *, direction, error=None):
        self.check_singleton()
        body = redact.mask_text(text or "")
        if len(body.encode("utf-8")) > _FRAME_LOG_BYTES:
            body = body.encode("utf-8")[:_FRAME_LOG_BYTES].decode("utf-8", "ignore")
        vals = {
            "direction": direction,
            "channel_id": f"{self._name},{self.id}",
            "company_id": self.company_id.id or False,
            "event_type": str(meta.get("topic") or meta.get("event") or "frame")[:128],
            "request_payload": body,
            "request_url": self.url[:2048],
            "state": "failed" if error else "success",
            "date_completed": fields.Datetime.now(),
            "error_message": redact.mask_text(error)[:512] if error else False,
            "error_type": "other" if error else False,
            "signature_verified": True,
            "origin_model": self.res_model or False,
            "origin_record_id": self.res_id or 0,
        }
        return self.env["integration.exchange"].sudo().create(vals)


class IntegrationStreamOutbox(models.Model):
    _name = "integration.stream.outbox"
    _description = "Stream Outbox"
    _order = "id"

    stream_id = fields.Many2one(
        comodel_name="integration.stream",
        index=True,
        required=True,
        ondelete="cascade",
    )
    payload = fields.Text(required=True)
    meta = fields.Json(help="Where and how the frame goes: topic, QoS, register.")
    state = fields.Selection(
        selection=[("pending", "Pending"), ("sent", "Sent"), ("failed", "Failed")],
        default="pending",
        index=True,
        required=True,
    )
    attempts = fields.Integer()
    error = fields.Char()
    date_sent = fields.Datetime()

    def action_retry(self):
        self.write({"state": "pending", "error": False})
        self.stream_id._notify_after_commit()

    @api.autovacuum
    def _gc_sent(self):
        retention = int(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("integration.log_retention_days", default="90")
        )
        if retention <= 0:
            return
        cutoff = fields.Datetime.now() - timedelta(days=retention)
        self.sudo().search(
            [("state", "in", ("sent", "failed")), ("write_date", "<", cutoff)]
        ).unlink()
