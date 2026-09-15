import json
import logging
from datetime import timedelta
from typing import Any
from urllib.parse import urlparse

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import SQL

from odoo.addons.integration.tools import compute_payload_hash

_logger = logging.getLogger(__name__)


class IntegrationExchange(models.Model):
    _name = "integration.exchange"
    _description = "Communication Event Log"
    _order = "timestamp desc, id desc"
    _rec_name = "display_name"

    direction = fields.Selection(
        selection=[
            ("inbound", "Inbound"),
            ("outbound", "Outbound"),
        ],
        index=True,
        required=True,
        help="Direction of communication: inbound (receiving) or outbound (sending)",
    )
    channel_id = fields.Reference(
        selection="_selection_channel_models",
        index=True,
        required=True,
        help="Reference to the channel (endpoint or service) for this event",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        compute="_compute_company_id",
        store=True,
        index=True,
        readonly=False,
        help="Company that owns this log entry. Defaults to the channel "
        "(endpoint) company, but the caller can override at create time "
        "with the effective request company (e.g. the credential's "
        "company in multi-tenant outbound calls).",
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        index=True,
        help="User who initiated the request (outbound) or processed the event (inbound)",
    )
    credential_id = fields.Many2one(
        comodel_name="credential.credential",
        index=True,
        ondelete="set null",
        help="Credential used for this communication",
    )
    connection_id = fields.Many2one(
        comodel_name="integration.connection",
        index="btree_not_null",
        ondelete="set null",
        help="The record's connection the call went through: which provider, "
        "terminal or carrier it was for.",
    )
    display_name = fields.Char(
        compute="_compute_display_name",
        store=True,
    )
    channel_name = fields.Char(
        compute="_compute_channel_name",
        store=True,
        index=True,
        help="Cached channel name for faster searches",
    )

    timestamp = fields.Datetime(
        default=fields.Datetime.now,
        index=True,
        required=True,
        help="When the event was received (inbound) or request was initiated (outbound)",
    )
    date_completed = fields.Datetime(
        readonly=True,
        help="Timestamp when processing completed",
    )
    duration_ms = fields.Float(
        digits=(10, 2),
        help="Processing time in milliseconds",
    )
    performance_rating = fields.Selection(
        selection=[
            ("excellent", "Excellent (< 100ms)"),
            ("good", "Good (100-500ms)"),
            ("average", "Average (500-1000ms)"),
            ("slow", "Slow (1-3s)"),
            ("very_slow", "Very Slow (> 3s)"),
        ],
        compute="_compute_performance_rating",
        store=True,
    )

    request_payload = fields.Text(
        help="Request body (inbound: received payload, outbound: sent body)"
    )
    request_payload_hash = fields.Char(
        compute="_compute_payload_hash",
        store=True,
        index=True,
        help="SHA256 hash for duplicate detection",
    )
    request_payload_hash_override = fields.Char(
        help="The hash of the body as received, set when the body itself was "
        "not stored in full.\n\n"
        "Duplicate detection compares this column against a hash the caller "
        "computed from the request. Deriving it from a stored body that was "
        "truncated would answer a different question and silently stop "
        "detecting anything."
    )
    request_payload_omitted_bytes = fields.Integer(
        help="Size of the body that was not stored, so the recorded size still "
        "describes the request rather than the placeholder standing in for it."
    )
    request_payload_size = fields.Integer(
        compute="_compute_payload_sizes",
        store=True,
    )

    request_method = fields.Selection(
        selection=[
            ("GET", "GET"),
            ("POST", "POST"),
            ("PUT", "PUT"),
            ("PATCH", "PATCH"),
            ("DELETE", "DELETE"),
            ("HEAD", "HEAD"),
            ("OPTIONS", "OPTIONS"),
        ],
        index=True,
    )
    request_url = fields.Char(index=True)
    request_endpoint = fields.Char(
        compute="_compute_request_endpoint",
        store=True,
        index=True,
    )
    request_headers = fields.Json()

    response_payload = fields.Text(
        help="Response body (inbound: our response, outbound: received response)"
    )
    response_payload_size = fields.Integer(
        compute="_compute_payload_sizes",
        store=True,
    )
    response_headers = fields.Json()

    status_code = fields.Integer(index=True)
    status_category = fields.Selection(
        selection=[
            ("success", "2xx Success"),
            ("redirect", "3xx Redirect"),
            ("client_error", "4xx Client Error"),
            ("server_error", "5xx Server Error"),
            ("unknown", "Unknown"),
        ],
        compute="_compute_status_category",
        store=True,
        index=True,
    )

    source_ip = fields.Char(
        index=True,
        help="IP address of the client that sent the event",
    )

    event_type = fields.Char(
        index=True,
        help="Type of event (e.g., 'payment.success', 'push'). Used for inbound webhooks.",
    )
    event_id_external = fields.Char(
        index=True,
        help="Unique event ID from external service for deduplication",
    )
    signature_verified = fields.Boolean(
        default=False,
        help="Whether the inbound request signature was successfully verified",
    )
    user_agent = fields.Char(help="HTTP User-Agent header from the inbound request")
    processing_result = fields.Text(
        help="Return value or result from handler execution"
    )
    stack_trace = fields.Text(help="Full stack trace for debugging failed events")

    state = fields.Selection(
        selection=[
            ("pending", "Pending"),
            ("processing", "Processing"),
            ("success", "Success"),
            ("failed", "Failed"),
            ("duplicate", "Duplicate"),
            ("retry", "Retry Scheduled"),
        ],
        default="pending",
        index=True,
        required=True,
        help="Current processing state",
    )
    is_success = fields.Boolean(
        compute="_compute_is_success",
        store=True,
        index=True,
    )

    error_message = fields.Text(readonly=True)
    error_type = fields.Selection(
        selection=[
            ("network", "Network Error"),
            ("timeout", "Timeout"),
            ("auth", "Authentication Error"),
            ("validation", "Validation Error"),
            ("rate_limit", "Rate Limit Exceeded"),
            ("server", "Server Error"),
            ("duplicate", "Duplicate Event"),
            ("other", "Other"),
        ]
    )

    retry_count = fields.Integer(
        default=0,
        readonly=True,
    )
    date_next_retry = fields.Datetime(
        index=True,
        readonly=True,
    )

    cache_hit = fields.Boolean(
        default=False,
        index=True,
    )
    cache_key = fields.Char(index=True)

    trace_id = fields.Char(
        index=True,
        help="Unique ID for correlating related events",
    )
    origin_model = fields.Char(help="Odoo model that triggered this communication")
    origin_record_id = fields.Integer()
    tags = fields.Char(help="Comma-separated tags for categorization")

    _duplicate_detection_idx = models.Index(
        "(channel_id, request_payload_hash, timestamp)",
    )

    _retry_queue_idx = models.Index(
        "(state, date_next_retry)",
    )

    _rate_limit_idx = models.Index(
        "(channel_id, timestamp, company_id)",
    )

    _event_external_unique = models.UniqueIndex(
        "(channel_id, event_id_external) WHERE event_id_external IS NOT NULL",
        "External event ID must be unique per channel!",
    )

    _CHANNEL_MIXINS = ("mixin.integration.channel", "mixin.inbound.gate")

    @api.model
    def _selection_channel_models(self):
        roots = [
            self.env.registry.get(name)
            for name in self._CHANNEL_MIXINS
            if self.env.registry.get(name)
        ]
        if not roots:
            return [("integration.service", "Outbound Service")]

        channels = []
        visited = set()
        queue = [child for root in roots for child in root._inherit_children]

        while queue:
            child_name = queue.pop(0)
            if child_name in visited or child_name in self._CHANNEL_MIXINS:
                continue
            visited.add(child_name)

            child_cls = self.env.registry.get(child_name)
            if not child_cls:
                continue

            queue.extend(child_cls._inherit_children)

            if not getattr(child_cls, "_abstract", False):
                label = getattr(child_cls, "_description", child_name)
                channels.append((child_name, label))

        return channels or [("integration.service", "Outbound Service")]

    @api.depends("channel_id")
    def _compute_company_id(self):
        for record in self:
            if record.company_id:
                continue
            if record.channel_id and hasattr(record.channel_id, "company_id"):
                record.company_id = record.channel_id.company_id
            else:
                record.company_id = False

    @api.depends("channel_id")
    def _compute_channel_name(self):
        for record in self:
            if record.channel_id:
                record.channel_name = record.channel_id.display_name
            else:
                record.channel_name = False

    @api.depends("direction", "channel_name", "timestamp", "request_method")
    def _compute_display_name(self):
        for record in self:
            parts = []
            if record.direction:
                parts.append(record.direction.upper()[:2])
            if record.request_method:
                parts.append(record.request_method)
            if record.channel_name:
                parts.append(record.channel_name[:30])
            if record.timestamp:
                parts.append(fields.Datetime.to_string(record.timestamp))

            record.display_name = " | ".join(parts) if parts else f"Event {record.id}"

    @api.depends("request_payload", "request_payload_hash_override")
    def _compute_payload_hash(self):
        for record in self:
            if record.request_payload_hash_override:
                record.request_payload_hash = record.request_payload_hash_override
            elif record.request_payload:
                record.request_payload_hash = compute_payload_hash(
                    record.request_payload
                )
            else:
                record.request_payload_hash = False

    @api.depends("request_payload", "response_payload", "request_payload_omitted_bytes")
    def _compute_payload_sizes(self):
        for record in self:
            record.request_payload_size = record.request_payload_omitted_bytes or (
                len(record.request_payload.encode("utf-8"))
                if record.request_payload
                else 0
            )
            record.response_payload_size = (
                len(record.response_payload.encode("utf-8"))
                if record.response_payload
                else 0
            )

    @api.depends("request_url", "channel_id")
    def _compute_request_endpoint(self):
        for record in self:
            if record.request_url and record.channel_id:
                base_url = getattr(record.channel_id, "endpoint_url", "") or ""
                if base_url and record.request_url.startswith(base_url):
                    record.request_endpoint = record.request_url[len(base_url) :]
                else:
                    parsed = urlparse(record.request_url)
                    record.request_endpoint = parsed.path
            else:
                record.request_endpoint = "/"

    @api.depends("status_code")
    def _compute_status_category(self):
        for record in self:
            if not record.status_code:
                record.status_category = "unknown"
            elif 200 <= record.status_code < 300:
                record.status_category = "success"
            elif 300 <= record.status_code < 400:
                record.status_category = "redirect"
            elif 400 <= record.status_code < 500:
                record.status_category = "client_error"
            elif 500 <= record.status_code < 600:
                record.status_category = "server_error"
            else:
                record.status_category = "unknown"

    @api.depends("state", "status_category")
    def _compute_is_success(self):
        for record in self:
            if record.direction == "inbound":
                record.is_success = record.state == "success"
            else:
                record.is_success = record.status_category in (
                    "success",
                    "redirect",
                )

    @api.depends("duration_ms")
    def _compute_performance_rating(self):
        for record in self:
            if not record.duration_ms:
                record.performance_rating = False
            elif record.duration_ms < 100:
                record.performance_rating = "excellent"
            elif record.duration_ms < 500:
                record.performance_rating = "good"
            elif record.duration_ms < 1000:
                record.performance_rating = "average"
            elif record.duration_ms < 3000:
                record.performance_rating = "slow"
            else:
                record.performance_rating = "very_slow"

    def mark_processing(self):
        self.write({"state": "processing"})

    def mark_success(self):
        self.write(
            {
                "state": "success",
                "date_completed": fields.Datetime.now(),
                "error_message": False,
                "error_type": False,
            },
        )

    def mark_failed(self, error_message, error_type="other", schedule_retry=True):
        self.check_singleton()

        values = {
            "state": "failed",
            "error_message": error_message,
            "error_type": error_type,
            "retry_count": self.retry_count + 1,
        }

        channel = self.channel_id
        if (
            schedule_retry
            and hasattr(channel, "retry_enabled")
            and channel.retry_enabled
        ):
            max_retries = getattr(channel, "retry_max_attempts", 3)

            if self.retry_count < max_retries:
                delay_seconds = channel.get_retry_delay(self.retry_count + 1)
                next_retry = fields.Datetime.now() + timedelta(seconds=delay_seconds)
                values["date_next_retry"] = next_retry
                values["state"] = "retry"
                _logger.info(
                    "Event %d failed (attempt %d/%d). Retrying in %ds",
                    self.id,
                    self.retry_count + 1,
                    max_retries,
                    delay_seconds,
                )
            else:
                values["date_completed"] = fields.Datetime.now()
                values["date_next_retry"] = False
                _logger.error(
                    "Event %d permanently failed after %d retries: %s",
                    self.id,
                    self.retry_count,
                    error_message,
                )
        else:
            values["date_completed"] = fields.Datetime.now()

        self.write(values)

    def mark_duplicate(self):
        self.write(
            {
                "state": "duplicate",
                "date_completed": fields.Datetime.now(),
                "error_type": "duplicate",
            },
        )

    def action_retry_now(self) -> dict[str, Any]:
        self.check_singleton()

        if self.state not in ["failed", "pending", "retry"]:
            raise ValidationError(
                self.env._(
                    "Only failed, pending, or scheduled-retry events can be retried"
                )
            )

        self.write(
            {
                "state": "pending",
                "date_next_retry": fields.Datetime.now(),
                "error_message": False,
                "error_type": False,
            },
        )

        if self.direction == "inbound":
            if not hasattr(self.channel_id, "_run_queued_event"):
                raise ValidationError(
                    self.env._("Channel does not support event processing")
                )
            self._enqueue_processing()

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": self.env._("Retry Scheduled"),
                "message": self.env._("Event has been queued for retry"),
                "type": "success",
                "sticky": False,
            },
        }

    def action_view_channel(self) -> dict[str, Any]:
        self.check_singleton()

        if not self.channel_id:
            raise ValidationError(self.env._("No channel associated with this event"))

        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Channel"),
            "res_model": self.channel_id._name,
            "res_id": self.channel_id.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_view_related_events(self) -> dict[str, Any] | None:
        self.check_singleton()

        if not self.trace_id:
            return None

        return {
            "name": self.env._("Related Events"),
            "type": "ir.actions.act_window",
            "res_model": "integration.exchange",
            "view_mode": "list,form",
            "domain": [("trace_id", "=", self.trace_id)],
        }

    def _enqueue_processing(self, delay: int | None = None) -> None:
        """Hand this event to a worker, once.

        `identity_key` is what stops one event being processed twice. `ir_job`
        holds a unique index over it for queued states, and those include
        `started`, so a job already running blocks a second enqueue as surely as
        a pending one does. All three callers fire at moments when another may
        already be in flight: the route that queues the event, the manual Retry
        button, and the retry cron -- whose domain matches an event from the
        instant it is created, since `queue_event` leaves it `pending` with
        `date_next_retry` unset and the domain asks for exactly that. Any cron
        run that beat the first job to the claim enqueued a second one, and
        `_run_queued_event` neither locks the event nor checks its state, so an
        inbound payload was handled twice -- duplicate records out of whatever
        the endpoint's `_process_queued_event` builds.
        """
        for event in self:
            event.delayed(
                identity_key=f"integration.event:{event.id}",
                eta=delay or None,
                name=f"Process inbound event {event.id}",
            )._job_process_inbound()

    @api.job(channel="integration_inbound", max_retries=0)
    def _job_process_inbound(self) -> None:
        self.check_singleton()
        channel = self.channel_id
        if not hasattr(channel, "_run_queued_event"):
            self.mark_failed(
                "Channel does not support event processing",
                schedule_retry=False,
            )
            return
        channel._run_queued_event(self.id)

    @api.model
    def _cron_retry_failed_events(self):
        now = fields.Datetime.now()

        batch_size = int(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("integration.retry_batch_size", default="100"),
        )

        processing_timeout = int(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("integration.retry_processing_timeout", default="300"),
        )

        events_to_retry = self.search(
            [
                ("direction", "=", "inbound"),
                ("state", "in", ["pending", "retry"]),
                "|",
                ("date_next_retry", "=", False),
                ("date_next_retry", "<=", now),
            ],
            limit=batch_size,
        )

        if not events_to_retry:
            return

        _logger.info("Retrying %d failed events", len(events_to_retry))

        for event in events_to_retry:
            try:
                channel = event.channel_id
                if event.state == "pending" and (
                    getattr(channel, "processing_mode", None) == "sync"
                ):
                    _logger.warning(
                        "Leaving event %d pending: endpoint %s handles it "
                        "synchronously and should have called mark_success() "
                        "or mark_failed() instead of leaving it here; not "
                        "replaying it, to avoid processing it a second time",
                        event.id,
                        channel.display_name,
                    )
                    continue
                if hasattr(channel, "_run_queued_event"):
                    event.date_next_retry = now + timedelta(seconds=processing_timeout)
                    event._enqueue_processing()
                else:
                    _logger.warning(
                        "Channel %s does not implement _run_queued_event()",
                        channel,
                    )
                    event.mark_failed(
                        "Channel does not support event processing",
                        schedule_retry=False,
                    )
            except Exception as e:
                _logger.exception("Failed to queue event %d for retry", event.id)
                event.mark_failed(str(e), schedule_retry=True)

    @api.autovacuum
    def _gc_old_logs(self):
        default_retention = int(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param(
                "integration.log_retention_days",
                default="90",
            ),
        )
        overrides = (
            self.env["integration.service"]
            .sudo()
            .with_context(active_test=False)
            .search([("log_retention_days", ">", 0)])
        )
        overridden_refs = [f"integration.service,{e.id}" for e in overrides]

        for endpoint in overrides:
            self._remove_logs_past_retention(
                endpoint.log_retention_days,
                SQL("channel_id = %s", f"integration.service,{endpoint.id}"),
            )

        if default_retention > 0:
            self._remove_logs_past_retention(
                default_retention,
                SQL("NOT (channel_id = ANY(%s))", overridden_refs)
                if overridden_refs
                else SQL("TRUE"),
            )

    def _remove_logs_past_retention(self, days, scope):
        """Delete expired exchange rows within a supplied SQL scope predicate.

        Settled rows use their completion date; pending/retry rows use their
        creation date. Execute direct SQL without ORM unlink hooks.

        :rtype: None
        """
        cutoff = fields.Datetime.now() - timedelta(days=days)
        self.env.cr.execute(
            SQL(
                """
                DELETE FROM integration_exchange
                WHERE %s
                  AND (
                        (state IN ('success', 'failed', 'duplicate')
                         AND date_completed < %s)
                     OR (state IN ('pending', 'retry') AND create_date < %s)
                  )
                """,
                scope,
                cutoff,
                cutoff,
            )
        )
        if self.env.cr.rowcount:
            _logger.info(
                "Garbage collected %d event logs older than %d days",
                self.env.cr.rowcount,
                days,
            )

    def get_payload_dict(self) -> dict[str, Any]:
        self.check_singleton()
        try:
            return json.loads(self.request_payload) if self.request_payload else {}
        except (json.JSONDecodeError, ValueError) as e:
            _logger.warning("Failed to parse payload for event %d: %s", self.id, e)
            return {}

    @api.model
    def get_duplicate_info(
        self,
        channel_ref: str,
        payload_json: str,
        event_id_external: str | None = None,
        dedup_window_hours: int = 1,
    ) -> dict[str, Any]:
        """Read duplicate metadata by external ID, then recent payload hash.

        :returns: ``is_duplicate``, ``duplicate_event_id`` and ``reason``;
            the latter two are None when no match is found

        This read does not reserve an event or enforce uniqueness. Caught hash
        lookup errors fall through to the no-match result.
        """
        if event_id_external:
            existing_by_external_id = self.search(
                [
                    ("channel_id", "=", channel_ref),
                    ("event_id_external", "=", event_id_external),
                ],
                limit=1,
            )
            if existing_by_external_id:
                _logger.info(
                    "Duplicate event detected by external ID: %s (original event: %s)",
                    event_id_external,
                    existing_by_external_id.id,
                )
                return {
                    "is_duplicate": True,
                    "duplicate_event_id": existing_by_external_id.id,
                    "reason": "external_id",
                }

        try:
            payload_hash = compute_payload_hash(payload_json)

            cutoff = fields.Datetime.now() - timedelta(hours=dedup_window_hours)
            existing_by_hash = self.search(
                [
                    ("channel_id", "=", channel_ref),
                    ("request_payload_hash", "=", payload_hash),
                    ("timestamp", ">=", cutoff),
                ],
                limit=1,
            )
            if existing_by_hash:
                _logger.info(
                    "Duplicate event detected by payload hash: %s... (original event: %s)",
                    payload_hash[:16],
                    existing_by_hash.id,
                )
                return {
                    "is_duplicate": True,
                    "duplicate_event_id": existing_by_hash.id,
                    "reason": "payload_hash",
                }
        except Exception as e:
            _logger.warning("Failed to compute payload hash for deduplication: %s", e)

        return {
            "is_duplicate": False,
            "duplicate_event_id": None,
            "reason": None,
        }
