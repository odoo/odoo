import json
import logging
import random
import secrets
import time
from datetime import timedelta
from urllib.parse import urlsplit

import psycopg

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.http import request
from odoo.tools import SQL

from odoo.addons.integration.tools.connection_gate import breaker_for

_logger = logging.getLogger(__name__)

TRANSPORT_VERBS = ("connect", "disconnect", "read_data")


class DeviceDevice(models.Model):
    _name = "device.device"
    _description = "IoT Remote Device"
    _inherit = [
        "mixin.bus.listener",
        "mixin.integration.receiver",
        "mixin.mail.thread",
        "mixin.mail.activity",
    ]
    _order = "name"
    _rec_names_search = [
        "name",
        "identifier",
    ]

    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
        index=True,
    )
    config_id = fields.Many2one(
        comodel_name="device.profile",
        tracking=True,
        help="Configuration profile with communication settings, authentication, and data retention policies",
    )
    parent_id = fields.Many2one(
        comodel_name="device.device",
        string="Part Of",
        index=True,
        ondelete="cascade",
        tracking=True,
        help="The device this one is a part of: a peripheral belongs to the "
        "box that carries it, and goes with it.",
    )
    child_ids = fields.One2many(
        comodel_name="device.device",
        inverse_name="parent_id",
        string="Parts",
    )
    child_count = fields.Count(count_of="child_ids")
    device_category_id = fields.Many2one(
        comodel_name="device.kind",
        ondelete="restrict",
        tracking=True,
    )
    category_color = fields.Integer(
        compute="_compute_category_color",
        help="Kanban accent color (Odoo palette index) resolved per device type.",
    )
    category_icon = fields.Char(
        compute="_compute_category_icon",
        help="Font Awesome class used to badge the device by type in the kanban.",
    )
    name = fields.Char(
        size=255,
        translate=True,
        required=True,
        tracking=True,
    )
    active = fields.Boolean(
        default=True,
        tracking=True,
    )
    is_demo = fields.Boolean(
        default=False,
        help="Demo devices skip actual network connections to prevent timeout errors",
    )
    identifier = fields.Char(
        size=255,
        index=True,
        required=True,
        help="Unique identifier for the device (MAC address, serial number, etc.) different than IMEI",
    )
    imei = fields.Char(
        index=True,
        help="IMEI (International Mobile Equipment Identity) different than MAC",
    )
    plate = fields.Char(help="Vehicle license plate, mainly for GPS-tracked assets.")
    description = fields.Text()

    firmware_version = fields.Char()
    hardware_version = fields.Char()
    serial_number = fields.Char()
    location = fields.Char(help="Physical location of the device")
    connection_state = fields.Selection(
        selection=[
            ("disconnected", "Disconnected"),
            ("connected", "Connected"),
            ("error", "Error"),
        ],
        default="disconnected",
        index=True,
    )
    connection_state_message = fields.Char(readonly=True)
    link_mode = fields.Selection(
        selection=[
            ("push", "Pushes to Odoo"),
            ("pull", "Odoo dials it"),
            ("stream", "Held open by the stream worker"),
        ],
        compute="_compute_link_mode",
        store=True,
        index=True,
        readonly=False,
        help="How the device and Odoo reach each other. The kind's word when "
        "it has one, else proposed from the protocol and the address; a device "
        "that is reachable but reports on its own is set to push by hand.",
    )
    stream_id = fields.Many2one(
        comodel_name="integration.stream",
        copy=False,
        readonly=True,
        ondelete="set null",
        help="The connection the stream worker holds for this device, for a "
        "protocol that keeps one open.",
    )
    connection_id = fields.Many2one(
        comodel_name="integration.connection",
        copy=False,
        readonly=True,
        ondelete="set null",
        help="The connection Odoo dials this device through, for a protocol Odoo "
        "reaches out on: its address, its secret, its breaker and budget.",
    )
    dial_credential_id = fields.Many2one(
        comodel_name="credential.credential",
        string="Dial Secret",
        copy=False,
        ondelete="set null",
        groups="base.group_system",
        help="The secret Odoo dials this device with, when it is not the profile's "
        "shared one.",
    )
    certificate_id = fields.Many2one(
        comodel_name="certificate.certificate",
        string="Client Certificate",
        help="X.509 client certificate and private key the device's own "
        "connection presents (mutual TLS). Distinct from the device's "
        "credential, which holds its REST bearer token.",
    )
    date_last_data_received = fields.Datetime(readonly=True)
    comm_protocol = fields.Selection(
        selection=[
            ("http", "HTTP/REST"),
            ("https", "HTTPS/REST"),
        ],
        default="http",
        required=True,
        tracking=True,
        help="A value here exists only where a transport implements it. Each "
        "protocol module adds its own through selection_add and supplies "
        "the three verbs in TRANSPORT_VERBS.",
    )
    endpoint = fields.Char(
        index=True,
        help="Hostname or IP address of the device",
    )
    port = fields.Integer(help="Leave empty to use protocol default")

    http_endpoint_path = fields.Char(
        help="Path to append to the endpoint (e.g., /api/data)"
    )
    http_headers = fields.Text(
        help="Custom HTTP headers in JSON format. Leave empty to use config default."
    )

    auto_reconnect_override = fields.Selection(
        selection=[
            ("on", "Always reconnect"),
            ("off", "Never reconnect"),
        ],
        help="Override the configuration profile's auto-reconnect setting for "
        "this device. Leave empty to inherit the profile.",
    )
    use_auto_reconnect = fields.Boolean(
        compute="_compute_use_auto_reconnect",
        store=True,
        help="Effective auto-reconnect setting (device override or config default)",
    )

    log_ids = fields.One2many(
        comodel_name="device.data.log",
        inverse_name="device_id",
        help="Historical data points received from this device",
    )
    log_count = fields.Integer(
        compute="_compute_log_count",
        store=False,
        help="Data points received in the last 24 hours.",
    )
    log_last_id = fields.Many2one(
        comodel_name="device.data.log",
        readonly=True,
        help="Most recent data point value",
    )

    display_endpoint = fields.Char(compute="_compute_display_endpoint")

    # NULLS NOT DISTINCT: company_id merely defaults to the current company,
    # so a device written with no company is possible and every such device
    # escaped the identifier check -- and the identifier is how a device is
    # addressed, so two of them sharing one is the failure this prevents.
    _company_device_uniq = models.UniqueIndex(
        "(identifier, company_id) NULLS NOT DISTINCT",
        "Device identifier must be unique per company.",
    )

    _DEVICE_ENDPOINT_DEFAULTS = {
        "auth_type": "bearer",
        "processing_mode": "sync",
        "rate_limit_enabled": True,
        "rate_limit_requests": 100,
        "rate_limit_window_seconds": 60,
        "max_payload_size": 1048576,
        "duplicate_detection_enabled": False,
    }

    def action_view_parts(self):
        self.check_singleton()
        return {
            "name": self.env._("Parts of %(device)s", device=self.display_name),
            "type": "ir.actions.act_window",
            "res_model": "device.device",
            "view_mode": "list,form,kanban",
            "domain": [("parent_id", "=", self.id)],
            "context": {"default_parent_id": self.id},
        }

    @api.constrains("parent_id")
    def _check_parent_id(self):
        if self._has_cycle():
            raise ValidationError(self.env._("A device cannot be part of itself."))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            for field_name, default in self._DEVICE_ENDPOINT_DEFAULTS.items():
                vals.setdefault(field_name, default)

            if "credential_id" not in vals:
                vals["credential_id"] = self._create_inbound_credential(
                    vals.get("identifier") or vals.get("name") or "Unknown",
                    vals.get("company_id") or self.env.company.id,
                ).id

        devices = super().create(vals_list)
        devices._sync_stream()
        devices._sync_connection()
        return devices

    def write(self, vals):
        result = super().write(vals)
        if vals.keys() & self._stream_fields():
            self._sync_stream()
        if vals.keys() & self._connection_fields():
            self._sync_connection()
        return result

    def unlink(self):
        streams = self.sudo().stream_id
        connections = self.sudo().connection_id
        result = super().unlink()
        streams.unlink()
        connections.unlink()
        return result

    @api.model
    def _create_inbound_credential(self, label, company_id):
        bearer_token_category = self.env.ref(
            "credential.credential_category_bearer_token",
            raise_if_not_found=False,
        )
        return (
            self.env["credential.credential"]
            .sudo()
            .create(
                {
                    "name": "Device %s Token" % label,
                    "company_id": company_id,
                    "category_id": (
                        bearer_token_category.id if bearer_token_category else False
                    ),
                    "credential_value": self._generate_api_token(),
                },
            )
        )

    @api.depends(
        "comm_protocol",
        "endpoint",
        "port",
        "http_endpoint_path",
        "config_id.endpoint_url",
    )
    def _compute_display_endpoint(self):
        for device in self:
            device.display_endpoint = (
                device._protocol_display_endpoint() or device.endpoint
            )

    def _protocol_display_endpoint(self):
        self.check_singleton()
        return False

    @api.depends(
        "comm_protocol",
        "endpoint",
        "config_id.endpoint_url",
        "device_category_id.link_mode",
    )
    def _compute_link_mode(self):
        streamed = self._streamed_protocols()
        polled = self._polled_protocols()
        for device in self:
            if device.device_category_id.link_mode:
                device.link_mode = device.device_category_id.link_mode
            elif device.comm_protocol in streamed:
                device.link_mode = "stream"
            elif device.comm_protocol in polled and (
                device.endpoint or device.config_id.endpoint_url
            ):
                device.link_mode = "pull"
            else:
                device.link_mode = "push"

    @api.depends("device_category_id", "device_category_id.icon")
    def _compute_category_icon(self):
        # A category owns its own icon. Overriding it by code here decided the
        # look of categories other modules ship.
        for device in self:
            device.category_icon = device.device_category_id.icon or "fa-microchip"

    @api.depends("device_category_id", "device_category_id.color")
    def _compute_category_color(self):
        # Same contract as the icon: the colour picker on the category form is
        # the only place that decides this.
        for device in self:
            device.category_color = device.device_category_id.color or 0

    _LOG_COUNT_WINDOW_HOURS = 24

    @api.depends("log_ids")
    def _compute_log_count(self):
        if not self.ids:
            for device in self:
                device.log_count = 0
            return
        since = fields.Datetime.now() - timedelta(hours=self._LOG_COUNT_WINDOW_HOURS)
        counts = dict(
            self.env["device.data.log"]._read_group(
                [("device_id", "in", self.ids), ("timestamp", ">=", since)],
                groupby=["device_id"],
                aggregates=["__count"],
            )
        )
        for device in self:
            device.log_count = counts.get(device, 0)

    @api.model
    def _find_by_inbound_token(self, token, domain=None):
        return self._get_by_credential_token(token, domain=domain)

    @api.depends("auto_reconnect_override", "config_id", "config_id.auto_reconnect")
    def _compute_use_auto_reconnect(self):
        for device in self:
            if device.auto_reconnect_override:
                device.use_auto_reconnect = device.auto_reconnect_override == "on"
            elif device.config_id:
                device.use_auto_reconnect = device.config_id.auto_reconnect
            else:
                device.use_auto_reconnect = True

    @api.onchange("device_category_id")
    def _onchange_device_category_id(self):
        if self.device_category_id:
            if self.device_category_id.comm_protocol:
                self.comm_protocol = self.device_category_id.comm_protocol

    @api.onchange("comm_protocol")
    def _onchange_comm_protocol(self):
        self.port = self._protocol_default_port() or self.port

    def _protocol_default_port(self):
        self.check_singleton()
        return {"http": 80, "https": 443}.get(self.comm_protocol, False)

    def _notify(self, title, message, kind="success", sticky=False):
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": title,
                "message": message,
                "type": kind,
                "sticky": sticky,
            },
        }

    def _transport_method(self, verb):
        # The transport contract. A protocol module contributes its value to
        # comm_protocol and one method per verb in TRANSPORT_VERBS; nothing
        # else in the device knows the protocol exists.
        self.check_singleton()
        method = getattr(self, f"{self.comm_protocol}_{verb}", None)
        return method if callable(method) else None

    @api.model
    def _device_kind_categories(self, kind):
        # Which device categories count as this kind. A module that makes its
        # own devices answer to somebody else's kind says so here, instead of
        # the kind's owner guessing from a field value.
        return []

    def _is_device_kind(self, kind):
        self.check_singleton()
        codes = self._device_kind_categories(kind)
        return bool(codes) and self.device_category_id.code in codes

    @api.model
    def _polled_protocols(self):
        # Protocols Odoo reaches out to on a schedule. Request/response.
        return ["http", "https"]

    @api.model
    def _persistent_protocols(self):
        # Protocols that hold a connection open and push. The reconnect cron
        # leaves these alone; their own supervisor owns them. Every one of them
        # arrives with a transport module.
        return []

    @api.model
    def _streamed_protocols(self):
        # Persistent protocols whose connection is an integration.stream: the
        # stream worker holds it, and the device's state follows the row.
        return []

    @api.model
    def _stream_fields(self):
        return frozenset(
            {
                "name",
                "active",
                "comm_protocol",
                "endpoint",
                "port",
                "config_id",
                "certificate_id",
            }
        )

    def _stream_vals(self):
        # What the device's stream row says, or None when its protocol keeps
        # no connection of its own; a streamed protocol module answers.
        self.check_singleton()

    def _sync_stream(self, active=None):
        for device in self:
            vals = device._stream_vals()
            stream = device.sudo().stream_id
            if vals is None:
                if stream:
                    stream.write({"active": False})
                continue
            vals.update(
                name=f"{device.name} ({vals['protocol']})",
                res_model=device._name,
                res_id=device.id,
                company_id=device.company_id.id or False,
                certificate_id=device.certificate_id.id,
                ca_certificate_id=device.config_id.ca_certificate_id.id,
            )
            if active is not None:
                vals["active"] = active
            elif not device.active:
                vals["active"] = False
            if stream:
                stream.write(vals)
            else:
                vals.setdefault("active", device.active)
                device.sudo().stream_id = (
                    self.env["integration.stream"].sudo().create(vals)
                )

    def _on_stream_frame(self, stream, payload, meta):
        self.check_singleton()
        text = (
            payload.decode(errors="replace") if isinstance(payload, bytes) else payload
        )
        try:
            data = json.loads(text)
        except ValueError:
            data = {"raw": text, "topic": meta.get("topic")}
        self._store_data_point(data, source_topic=meta.get("topic"), raw_payload=text)

    _STREAM_STATES = {
        "open": "connected",
        "connecting": "disconnected",
        "stopped": "disconnected",
        "backoff": "error",
        "error": "error",
    }

    def _on_stream_state(self, stream, state, message):
        self.check_singleton()
        connection_state = self._STREAM_STATES.get(state, "error")
        self._set_connection_state(connection_state, message or False)
        self._bus_send(
            "device_status",
            {"connection_state": connection_state, "device_id": self.id},
        )

    def _register_hook(self):
        # The only thing a restart knows that a cron cannot: every connection
        # this process held is gone, so a device still recorded as connected is
        # recorded wrongly. A streamed protocol's connection is the stream
        # worker's, and its state follows the row, so it is left alone.
        res = super()._register_hook()
        persistent_protocols = [
            protocol
            for protocol in self._persistent_protocols()
            if protocol not in self._streamed_protocols()
        ]
        if not persistent_protocols:
            return res

        domain = [
            ("comm_protocol", "in", persistent_protocols),
            ("connection_state", "=", "connected"),
        ]

        def _reset(env):
            stale = env["device.device"].search(domain)
            if stale:
                stale.write(
                    {
                        "connection_state": "disconnected",
                        "connection_state_message": "Reset on server restart",
                    }
                )

        self._run_with_state_retry(_reset, "device: startup device-state reset")
        return res

    def action_connect(self):
        self.check_singleton()
        connect_method = self._transport_method("connect")

        if connect_method is None:
            raise UserError(
                self.env._("Protocol %s is not implemented yet") % self.comm_protocol,
            )

        try:
            result = connect_method()  # pylint: disable=not-callable
            if result is False:
                raise UserError(
                    self.env._("Could not connect to device %s; see the server log.")
                    % self.name
                )
            return result
        except Exception as e:
            _logger.error("Connection error for device %s: %s", self.name, e)
            self._write_state_retry(
                {
                    "connection_state": "error",
                    "connection_state_message": str(e),
                },
                "device: action connect error",
            )
            raise UserError(self.env._("Connection failed: %s") % str(e)) from e

    def action_disconnect(self):
        self.check_singleton()
        disconnect_method = self._transport_method("disconnect")

        if disconnect_method is not None:
            try:
                disconnect_method()  # pylint: disable=not-callable
            except Exception:
                _logger.exception("Disconnection error for device %s", self.name)

    def action_read_data(self):
        self.check_singleton()
        read_method = self._transport_method("read_data")

        if read_method is None:
            raise UserError(
                self.env._("Data reading not implemented for protocol %s")
                % self.comm_protocol,
            )

        try:
            read_method()  # pylint: disable=not-callable
            return self._notify(
                self.env._("Success"),
                self.env._("Data read successfully"),
            )
        except Exception as e:
            _logger.error("Data reading error for device %s: %s", self.name, e)
            raise UserError(self.env._("Failed to read data: %s") % str(e)) from e

    def action_test_connection(self):
        self.check_singleton()
        try:
            self.action_connect()
            return self._notify(
                self.env._("Connection Test"),
                self.env._("Connection successful!"),
            )
        except Exception as e:
            _logger.warning(
                "Connection test failed for device %s", self.name, exc_info=True
            )
            return self._notify(
                self.env._("Connection Test"),
                self.env._("Connection failed: %s") % str(e),
                "danger",
                True,
            )

    # Both halves of the push route store through here. They used to build the
    # call themselves, and the async half forgot `source`, so the same device
    # pushing the same body to the same route landed in `webhook` or in `iot`
    # depending on processing_mode -- a dimension device.data.log.report groups
    # and filters by. One writer is what keeps them from drifting again.
    _PUSH_SOURCE = "webhook"

    def _store_push_data_point(self, data, raw_payload=None):
        self.check_singleton()
        return self._store_data_point(
            data=data,
            source_topic=f"http_push/{self.identifier}",
            raw_payload=raw_payload,
            source=self._PUSH_SOURCE,
        )

    def _process_queued_event(self, event):
        try:
            event.mark_processing()

            data = event.get_payload_dict()

            self._store_push_data_point(data, raw_payload=event.request_payload)

            event.mark_success()

        except Exception as e:
            _logger.exception("Error processing device event %s", event.id)
            event.mark_failed(str(e), schedule_retry=True)

    _STATE_LOCK_TIMEOUT = "5s"

    def _run_with_state_retry(self, func, what, max_attempts=3):
        for attempt in range(1, max_attempts + 1):
            try:
                with self.pool.cursor() as cr:
                    cr.execute(
                        SQL(
                            "SELECT set_config('lock_timeout', %s, true)",
                            self._STATE_LOCK_TIMEOUT,
                        )
                    )
                    return func(self.env(cr=cr, su=True))
            except psycopg.errors.LockNotAvailable:
                _logger.warning(
                    "%s: device_device stayed locked for %s; skipped. The next "
                    "CONNACK/poll self-heals the state",
                    what,
                    self._STATE_LOCK_TIMEOUT,
                )
                return None
            except psycopg.errors.SerializationFailure:
                _logger.info(
                    "%s: serialization conflict (attempt %s/%s) — retrying",
                    what,
                    attempt,
                    max_attempts,
                )
                if attempt < max_attempts:
                    time.sleep(random.uniform(0.05, 0.2) * attempt)
            except Exception:
                _logger.exception("%s failed", what)
                return None
        _logger.warning(
            "%s: dropped after %s serialization retries; the next CONNACK/poll "
            "self-heals the state",
            what,
            max_attempts,
        )
        return None

    def _write_state_retry(self, vals, what):
        device_id = self.id
        state_keys = (
            "connection_state",
            "connection_state_message",
            "date_last_data_received",
        )

        def _apply(env):
            target = env["device.device"].browse(device_id).exists()
            if not target:
                return
            if "connection_state" in vals:
                target._set_connection_state(
                    vals["connection_state"],
                    vals.get("connection_state_message", False),
                    when=vals.get("date_last_data_received"),
                )
            leftovers = {k: v for k, v in vals.items() if k not in state_keys}
            if leftovers:
                target.write(leftovers)

        self._run_with_state_retry(_apply, what)

    def _run_in_callback(self, func, what):
        device_id = self.id

        def _apply(env):
            device = env["device.device"].browse(device_id).exists()
            if not device:
                return None
            return func(device)

        return self._run_with_state_retry(_apply, what)

    def _write_state_retry_multi(self, vals, what):
        ids = self.ids

        def _apply(env):
            env["device.device"].browse(ids).write(vals)

        self._run_with_state_retry(_apply, what)

    @api.model
    def _cron_poll_devices(self):
        domain = [
            ("connection_state", "=", "connected"),
            ("link_mode", "=", "pull"),
            ("active", "=", True),
            ("is_demo", "=", False),
        ]

        devices = self.search(
            domain, order="date_last_data_received asc NULLS FIRST, id"
        ).filtered(lambda device: not device._connection_paused())
        if not devices:
            return

        _logger.info("Polling %s devices", len(devices))

        deadline = time.monotonic() + self._POLL_BUDGET_SECONDS
        for attempted, device in enumerate(devices):
            if time.monotonic() >= deadline:
                _logger.info(
                    "Poll budget of %ss spent after %s/%s device(s); the rest "
                    "are picked up next tick (least recently heard from first).",
                    self._POLL_BUDGET_SECONDS,
                    attempted,
                    len(devices),
                )
                break
            try:
                device.action_read_data()
            except Exception as e:
                _logger.exception("Error polling device %s", device.name)
                device._write_state_retry(
                    {
                        "connection_state": "error",
                        "connection_state_message": str(e),
                    },
                    "device: cron poll error",
                )

    # The cron fires every minute and one HTTP read costs up to the profile's
    # http_timeout, so an unbounded sweep holds a cron worker while every other
    # job waits behind it. Same treatment as _RECONNECT_BUDGET_SECONDS.
    _POLL_BUDGET_SECONDS = 45

    def _disconnect_timeout(self):
        default_timeout = int(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("device.disconnect_timeout_default", default="300")
        )
        return {
            device.id: (
                device.device_category_id.disconnect_timeout_seconds
                or device.config_id.disconnect_timeout
                or default_timeout
            )
            for device in self
        }

    @api.model
    def _cron_check_health(self):
        # A device is connected while its data is fresh, whoever calls whom;
        # a streamed one that holds its link open but has gone quiet is in
        # error, because its wire is up and silent.
        now = fields.Datetime.now()
        devices = self.search([("active", "=", True)])
        timeouts = devices._disconnect_timeout()

        to_connect, to_disconnect, stale_sockets = [], [], []
        for device in devices:
            threshold = now - timedelta(seconds=timeouts[device.id])
            is_fresh = (
                bool(device.date_last_data_received)
                and device.date_last_data_received >= threshold
            )
            if device.link_mode == "stream":
                if not is_fresh and device.connection_state == "connected":
                    stale_sockets.append(device.id)
            elif is_fresh and device.connection_state != "connected":
                to_connect.append(device.id)
            elif not is_fresh and device.connection_state == "connected":
                to_disconnect.append(device.id)

        if to_connect:
            _logger.info(
                "Promoting %s push devices to connected (fresh data)", len(to_connect)
            )
            self.browse(to_connect)._write_state_retry_multi(
                {
                    "connection_state": "connected",
                    "connection_state_message": False,
                },
                "device: cron promote connected",
            )

        if to_disconnect:
            _logger.info(
                "Demoting %s push devices to disconnected (stale data)",
                len(to_disconnect),
            )
            self.browse(to_disconnect)._write_state_retry_multi(
                {
                    "connection_state": "disconnected",
                    "connection_state_message": "No recent activity",
                },
                "device: cron demote disconnected",
            )

        if stale_sockets:
            _logger.info(
                "Marking %s persistent-protocol devices as error (stale)",
                len(stale_sockets),
            )
            self.browse(stale_sockets)._write_state_retry_multi(
                {
                    "connection_state": "error",
                    "connection_state_message": "No recent activity",
                },
                "device: cron mark stale error",
            )

        if to_disconnect:
            self.browse(to_disconnect)._notify_devices_went_quiet("disconnected")
        if stale_sockets:
            self.browse(stale_sockets)._notify_devices_went_quiet("error")

    def _notify_devices_went_quiet(self, state):
        # The state is passed in, never re-read. _write_state_retry_multi wrote it
        # on a cursor of its own, so this transaction still sees the old value.
        for device in self:
            if not device.config_id.alert_on_disconnect:
                continue
            last_seen = (
                fields.Datetime.to_string(device.date_last_data_received)
                if device.date_last_data_received
                else self.env._("never")
            )
            device.message_post(
                body=self.env._(
                    "No data received from this device. "
                    "Last reading: %(last_seen)s. Status is now %(state)s.",
                    last_seen=last_seen,
                    state=state,
                ),
                message_type="notification",
            )

    @api.model
    def _cron_auto_reconnect(self):
        domain = [
            ("use_auto_reconnect", "=", True),
            ("connection_state", "in", ["disconnected", "error"]),
            ("active", "=", True),
            ("link_mode", "=", "pull"),
        ]

        deadline = time.monotonic() + self._RECONNECT_BUDGET_SECONDS
        devices = self.search(
            domain, order="date_last_data_received asc NULLS FIRST, id"
        ).filtered(lambda device: not device._connection_paused())
        for attempted, device in enumerate(devices):
            if time.monotonic() >= deadline:
                _logger.info(
                    "Auto-reconnect budget of %ss spent after %s/%s device(s); "
                    "the rest are picked up next tick (least recently heard from "
                    "first).",
                    self._RECONNECT_BUDGET_SECONDS,
                    attempted,
                    len(devices),
                )
                break
            try:
                device.action_connect()
            except Exception:
                _logger.exception(
                    "Auto-reconnect failed for device %s",
                    device.name,
                )

    _RECONNECT_BUDGET_SECONDS = 120

    def _connection_paused(self):
        self.check_singleton()
        connection = self.sudo().connection_id
        if not connection:
            return False
        breaker = breaker_for(self.env, connection)
        return not breaker.closed and breaker.cooldown_remaining > 0

    def _set_connection_state(self, state, message=False, when=None):
        stale = self.browse()
        for device in self:
            if (
                device.connection_state != state
                or device.connection_state_message != message
                or when
            ):
                stale |= device
        if not stale:
            return
        vals = {"connection_state": state, "connection_state_message": message}
        if when:
            vals["date_last_data_received"] = when
        stale.sudo().write(vals)

    def _touch_last_seen(self, when=None):
        self.check_singleton()
        self._set_connection_state(
            "connected", message=False, when=when or fields.Datetime.now()
        )

    @api.model
    def _generate_api_token(self):
        return secrets.token_hex(32)

    _INBOUND_UNLOGGED_EVENTS = frozenset({"device_status"})

    def _inbound_event_logged(self, event_type):
        return event_type not in self._INBOUND_UNLOGGED_EVENTS

    @api.model
    def _receiver_for_identifier(self, identifier, domain=None, **_path_args):
        """The device a machine route addresses by identifier. Identifiers are
        unique per company, not globally, so when several companies hold one
        the device whose credential the request carries is the subject; when
        none does, the first is, and the gate refuses on it."""
        candidates = self.sudo().search(
            [*(domain or []), ("identifier", "=", identifier), ("active", "=", True)]
        )
        if len(candidates) <= 1:
            return candidates
        headers = dict(request.httprequest.headers)
        body = request.httprequest.get_data(cache=True)
        for candidate in candidates:
            authenticated, _reason = candidate._authenticate_inbound_identity(
                headers, body
            )
            if authenticated:
                return candidate
        return candidates[:1]

    def _get_effective_endpoint(self):
        self.check_singleton()
        if self.endpoint:
            return self.endpoint
        return urlsplit(self.config_id.endpoint_url or "").hostname or ""

    def _get_port_effective(self):
        self.check_singleton()
        if self.port:
            return self.port
        try:
            return urlsplit(self.config_id.endpoint_url or "").port or 0
        except ValueError:
            return 0

    def _dial_url(self):
        # The address Odoo dials for a request/response protocol; empty when
        # the device names none and the profile's default applies.
        self.check_singleton()
        if not self.endpoint:
            return ""
        scheme = "https" if self.comm_protocol == "https" else "http"
        url = f"{scheme}://{self.endpoint}"
        if self.port:
            url += f":{self.port}"
        return url

    # -- the connection Odoo dials the device through -------------------------

    @api.model
    def _connection_fields(self):
        return frozenset(
            {
                "active",
                "comm_protocol",
                "company_id",
                "config_id",
                "dial_credential_id",
                "endpoint",
                "link_mode",
                "name",
                "port",
            }
        )

    def _connection_service(self):
        self.check_singleton()
        return self.config_id.sudo().service_id

    def _connection_values(self, service):
        # None when Odoo does not dial this device: a pushing or streamed
        # protocol, or no address anywhere.
        self.check_singleton()
        if not service or self.link_mode != "pull":
            return None
        base_url = self._dial_url()
        if not base_url and not service.endpoint_url:
            return None
        credential = (
            self.sudo().dial_credential_id or self.config_id.sudo().credential_id
        )
        return {
            "name": self.name,
            "service_id": service.id,
            "credential_id": credential.id,
            "company_id": self.company_id.id,
            "environment": service.environment,
            "base_url": base_url,
            "active": self.active,
            "res_model": self._name,
            "res_id": self.id,
        }

    def _sync_connection(self):
        connections = self.env["integration.connection"].sudo()
        stale = connections.browse()
        for device in self.sudo().with_context(active_test=False):
            vals = device._connection_values(device._connection_service())
            connection = device.connection_id
            if not vals:
                if connection:
                    stale |= connection
                    device.connection_id = False
                continue
            if connection:
                connection.write(vals)
            else:
                device.connection_id = connections.create(vals)
        stale.unlink()

    def _get_connection(self):
        self.check_singleton()
        if not self.sudo().connection_id:
            self._sync_connection()
        return self.sudo().connection_id

    def _require_connection(self):
        connection = self._get_connection()
        if connection:
            return connection
        raise UserError(
            self.env._(
                "Device %s has no connection to call it through.", self.display_name
            )
        )

    def _store_data_point(
        self, data, source_topic=None, raw_payload=None, source="iot"
    ):
        self.check_singleton()
        data_point_model = self.env["device.data.log"]

        self._touch_last_seen()

        try:
            values = {
                "device_id": self.id,
                "data_type": "json",
                "source_topic": source_topic,
                "raw_payload": raw_payload,
                "quality": "good",
                "source": source,
                "value_json": data,
            }

            # The savepoint is what makes the degraded write below possible: a
            # database error here aborts the transaction, and every later
            # statement on the same cursor -- the fallback create included --
            # would raise InFailedSqlTransaction and lose the payload anyway.
            with self.env.cr.savepoint():
                point = data_point_model.create(values)
            self.sudo().log_last_id = point.id

            _logger.info(
                "Stored complete payload for device %s from %s",
                self.name,
                source_topic or "unknown source",
            )

            return point

        except Exception:
            _logger.exception(
                "Error storing data point for device %s",
                self.name,
            )
            return data_point_model.create(
                {
                    "device_id": self.id,
                    "data_type": "text",
                    "value_text": str(data),
                    "source_topic": source_topic,
                    "raw_payload": raw_payload,
                    "quality": "bad",
                    "source": source,
                },
            )

    @api.model
    def _cron_poll_demo_devices(self):
        domain = [
            ("active", "=", True),
            ("is_demo", "=", True),
            ("comm_protocol", "in", self._polled_protocols()),
        ]

        devices = self.search(domain)
        _logger.info("Polling %s demo devices", len(devices))

        for device in devices:
            try:
                generate = getattr(
                    device, f"_demo_generate_{device.comm_protocol}_data", None
                )
                if generate:
                    generate()
            except Exception:
                _logger.exception("Error polling demo device %s", device.name)
