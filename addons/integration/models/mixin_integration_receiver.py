import json
import logging
from datetime import timedelta
from typing import Any

from odoo import api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class MixinIntegrationReceiver(models.AbstractModel):
    _name = "mixin.integration.receiver"
    _inherit = ["mixin.integration.channel", "mixin.inbound.gate"]
    _description = "Inbound Endpoint"
    _api_event_direction = "inbound"

    duplicate_detection_enabled = fields.Boolean(
        default=True,
        help="Prevent duplicate event processing using payload hash",
    )
    duplicate_window_seconds = fields.Integer(
        default=60,
        help="Time window for duplicate detection",
    )

    log_request_payload_max_bytes = fields.Integer(
        default=0,
        help="Store at most this many bytes of each request body on the "
        "integration.exchange row; 0 keeps the whole body.\n\n"
        "For an endpoint that accepts a file the body is the file: a phone "
        "posting a call recording as base64 wrote roughly 48 MB of text into a "
        "log column, beside the same audio already stored as an attachment. "
        "Duplicate detection is unaffected -- the hash of the body as received "
        "is kept either way. Ignored for an asynchronous endpoint, where the "
        "stored body is the work queue and not merely a record of it.",
    )

    @api.constrains("log_request_payload_max_bytes")
    def _check_log_request_payload_max_bytes(self):
        for record in self:
            if record.log_request_payload_max_bytes < 0:
                raise ValidationError(
                    self.env._("The payload log limit cannot be negative."),
                )

    def _payload_log_limit(self) -> int:
        self.check_singleton()
        if self.processing_mode == "async":
            return 0
        return max(0, self.log_request_payload_max_bytes)

    processing_mode = fields.Selection(
        selection=[
            ("sync", "Synchronous"),
            ("async", "Asynchronous"),
        ],
        default="async",
        required=True,
        help="Sync: Process immediately. Async: Queue for background processing.",
    )

    event_count = fields.Integer(compute="_compute_event_count")

    @api.constrains("max_payload_size")
    def _check_max_payload_size(self):
        max_limit = int(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("integration.max_payload_size_limit", default="104857600"),
        )

        for record in self:
            if record.max_payload_size <= 0:
                raise ValidationError(
                    self.env._("Max payload size must be greater than 0")
                )
            if record.max_payload_size > max_limit:
                max_mb = max_limit / (1024 * 1024)
                raise ValidationError(
                    self.env._(
                        "Max payload size cannot exceed %(max_mb).0fMB (%(max_bytes)d bytes)",
                        max_mb=max_mb,
                        max_bytes=max_limit,
                    ),
                )

    @api.constrains("duplicate_window_seconds")
    def _check_duplicate_window(self):
        max_window = int(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("integration.max_duplicate_window_seconds", default="3600"),
        )

        for record in self:
            if record.duplicate_detection_enabled:
                if record.duplicate_window_seconds <= 0:
                    raise ValidationError(
                        self.env._("Duplicate detection window must be greater than 0"),
                    )
                if record.duplicate_window_seconds > max_window:
                    raise ValidationError(
                        self.env._(
                            "Duplicate detection window cannot exceed %(max)d seconds",
                            max=max_window,
                        ),
                    )

    @api.constrains("auth_type", "verification_method")
    def _check_custom_verification(self):
        for record in self:
            if record.auth_type == "custom":
                if not record.verification_method:
                    raise ValidationError(
                        self.env._(
                            "Custom verification method is required when auth type is 'custom'"
                        ),
                    )

                if "." not in record.verification_method:
                    raise ValidationError(
                        self.env._(
                            "Verification method must be in format 'model_name.method_name'"
                        ),
                    )

                parts = record.verification_method.rsplit(".", 1)
                if len(parts) != 2:
                    raise ValidationError(
                        self.env._("Invalid verification method format: '%s'")
                        % record.verification_method,
                    )

                model_name, method_name = parts

                if not method_name.lstrip("_").startswith("verify_"):
                    raise ValidationError(
                        self.env._(
                            "Verification method name must start with "
                            "'verify_' or '_verify_' (got '%s'). Custom "
                            "verification runs with elevated rights and only "
                            "dedicated verify methods may be invoked.",
                        )
                        % method_name,
                    )

                if model_name not in self.env:
                    raise ValidationError(
                        self.env._("Model '%s' does not exist") % model_name,
                    )

                model_obj = self.env[model_name]
                if not hasattr(model_obj, method_name):
                    raise ValidationError(
                        self.env._(
                            "Method '%(method)s' not found in model '%(model)s'",
                            method=method_name,
                            model=model_name,
                        ),
                    )

                method = getattr(model_obj, method_name)
                if not callable(method):
                    raise ValidationError(
                        self.env._(
                            "'%(model)s.%(method)s' is not callable",
                            model=model_name,
                            method=method_name,
                        ),
                    )

    def unlink(self) -> bool:
        endpoint_refs = [f"{record._name},{record.id}" for record in self]

        event_logs = (
            self.env["integration.exchange"]
            .sudo()
            .search([("channel_id", "in", endpoint_refs)])
        )

        if event_logs:
            _logger.info(
                "Deleting %d event logs for %d endpoints",
                len(event_logs),
                len(self),
            )
            event_logs.unlink()

        return super().unlink()

    def _compute_event_count(self):
        counts_by_ref: dict[str, int] = {}
        if self.ids:
            groups = self.env["integration.exchange"]._read_group(
                domain=self._integration_exchange_domain(),
                groupby=["channel_id"],
                aggregates=["__count"],
            )
            counts_by_ref = dict(groups)
        for record in self:
            record.event_count = counts_by_ref.get(f"{record._name},{record.id}", 0)

    def authenticate_request(
        self,
        headers: dict[str, Any],
        body: str | bytes | None = None,
    ) -> bool:
        self.check_singleton()
        is_valid = self._authenticate_by_scheme(headers, body)
        if is_valid and self.credential_id:
            self.credential_id.mark_as_used()
        return is_valid

    @api.model
    def _inbound_auth_mode(self, parameter_key: str) -> str:
        mode = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param(parameter_key, default=self.AUTH_MODE_ENFORCE)
        )
        if mode not in (
            self.AUTH_MODE_ENFORCE,
            self.AUTH_MODE_AUDIT,
            self.AUTH_MODE_OFF,
        ):
            _logger.warning(
                "Unknown value %r for %s; falling back to 'enforce'",
                mode,
                parameter_key,
            )
            return self.AUTH_MODE_ENFORCE
        return mode

    def check_inbound_auth(
        self,
        headers: dict[str, Any],
        remote_addr: str,
        mode: str = "enforce",
        body: str | bytes | None = None,
    ) -> tuple[bool, str]:
        self.check_singleton()
        allowed, _status, reason = self._check_inbound_request(
            headers, body=body, remote_addr=remote_addr, mode=mode
        )
        return allowed, reason

    @api.job(channel="integration_inbound", max_retries=0)
    def _run_queued_event(self, event_id):
        self.check_singleton()
        event = self.env["integration.exchange"].browse(event_id).exists()
        if not event:
            _logger.warning("Queued event %s no longer exists", event_id)
            return
        self._process_queued_event(event)

    def _process_queued_event(self, event):
        _logger.info(
            "Processing event %d for %s - override _process_queued_event()",
            event.id,
            self.display_name,
        )

    def queue_event(
        self,
        payload: dict[str, Any] | str | None = None,
        metadata: dict[str, Any] | None = None,
        event_log: models.Model | None = None,
    ) -> models.Model:
        self.check_singleton()

        if event_log:
            event = event_log
        else:
            payload_str: str
            if isinstance(payload, str):
                payload_str = payload
            elif isinstance(payload, dict):
                payload_str = json.dumps(payload)
            else:
                payload_str = json.dumps({"data": payload})

            event = self.env["integration.exchange"].create(
                {
                    "direction": "inbound",
                    "channel_id": f"{self._name},{self.id}",
                    "request_payload": payload_str,
                    "source_ip": (metadata.get("source_ip") if metadata else None),
                    "state": "pending",
                },
            )

        if self.processing_mode == "async":
            event._enqueue_processing()

        self.update_date_last_activity()

        return event

    def check_duplicate_event(
        self,
        payload_hash: str,
        exclude_event_id: int | None = None,
    ) -> bool:
        self.check_singleton()

        if not self.duplicate_detection_enabled:
            return False

        now = fields.Datetime.now()
        since = now - timedelta(seconds=self.duplicate_window_seconds)

        endpoint_ref = f"{self._name},{self.id}"

        domain = [
            ("channel_id", "=", endpoint_ref),
            ("request_payload_hash", "=", payload_hash),
            ("timestamp", ">=", since),
        ]

        if exclude_event_id:
            domain.append(("id", "!=", exclude_event_id))

        return self.env["integration.exchange"].sudo().search_count(domain, limit=1) > 0
