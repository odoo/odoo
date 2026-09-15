import logging
import re
from datetime import timedelta
from typing import Any
from urllib.parse import urlparse

from odoo import api, fields, models
from odoo.db import get_or_create_row
from odoo.exceptions import ValidationError

from ..tools.api_client import is_private_host

_logger = logging.getLogger(__name__)


class IntegrationService(models.Model):
    _name = "integration.service"
    _inherit = ["mixin.integration.channel"]
    _description = "Outbound Endpoint"
    _api_event_direction = "outbound"
    _order = "sequence, name"
    _rec_name = "name"

    rate_limit_period = fields.Selection(
        selection=[
            ("second", "Per Second"),
            ("minute", "Per Minute"),
            ("hour", "Per Hour"),
            ("day", "Per Day"),
        ],
        default="minute",
        help="Time period for rate limiting",
    )

    category = fields.Selection(
        selection=[
            ("payment", "Payment Gateway"),
            ("delivery", "Delivery & Shipping"),
            ("communication", "Communication"),
            ("social", "Social Media"),
            ("tax", "Tax & EDI"),
            ("calendar", "Calendar & Scheduling"),
            ("cloud", "Cloud Storage"),
            ("ai", "Artificial Intelligence"),
            ("geocoding", "Geocoding & Maps"),
            ("analytics", "Analytics"),
            ("other", "Other"),
        ],
        default="other",
        required=True,
    )
    provider = fields.Char(help="Company providing the service")
    website = fields.Char()
    documentation_url = fields.Char()
    environment = fields.Selection(
        selection=[
            ("test", "Test/Sandbox"),
            ("staging", "Staging"),
            ("production", "Production"),
        ],
        default="test",
        index=True,
        required=True,
    )

    endpoint_url = fields.Char(
        help="Base URL for production environment",
    )
    endpoint_url_test = fields.Char(help="Base URL for test environment")
    allowed_hosts = fields.Char(
        help="Hosts, besides those of the endpoint URLs, that may receive this "
        "endpoint's credential, separated by commas. 'private' admits any "
        "private-network host, for an endpoint that reaches devices at their own "
        "addresses. A call to any other host that would carry the credential is "
        "refused."
    )

    def _is_credential_host_allowed(self, host):
        self.check_singleton()
        host = (host or "").strip("[]").lower()
        if not host:
            return False
        own_hosts = {
            (urlparse(url).hostname or "").lower()
            for url in (self.endpoint_url, self.endpoint_url_test)
            if url
        }
        if host in own_hosts:
            return True
        listed = {
            entry.strip().lower()
            for entry in (self.allowed_hosts or "").replace("\n", ",").split(",")
            if entry.strip()
        }
        if host in listed:
            return True
        return "private" in listed and is_private_host(host)

    api_version = fields.Char()
    send_version_headers = fields.Boolean(
        string="Send Generic Version Headers",
        default=True,
        help="Send API-Version and X-API-Version built from the API Version "
        "field. Turn this off for a vendor that carries its version its own "
        "way — in the URL path, or in a header of its own name — where the "
        "generic pair is at best ignored and at worst rejected.",
    )
    auth_type = fields.Selection(
        selection_add=[
            ("basic", "Basic Authentication"),
            ("digest", "Digest Authentication"),
            ("oauth2", "OAuth 2.0"),
        ],
        ondelete={
            "basic": "set default",
            "digest": "set default",
            "oauth2": "set default",
        },
    )
    allow_user_credentials = fields.Boolean(
        string="Allow Personal Credentials",
        default=False,
        help="Let a user hold their own credential for this endpoint, so calls "
        "they trigger are attributed to them rather than to the company. When "
        "a user has no personal credential the company one is used, so turning "
        "this on changes nothing until someone creates one.",
    )
    api_key_header = fields.Char(
        string="API Key Header",
        help="Header carrying the API key for this vendor, when it wants one "
        "of its own — 'x-api-key' for Anthropic, 'x-goog-api-key' for Google. "
        "Leave empty for the generic 'Authorization: Bearer' and 'X-API-Key' "
        "pair, which most vendors accept.",
    )
    api_key_scheme = fields.Char(
        string="API Key Scheme",
        help="Word in front of the key in the Authorization header when the "
        "vendor does not use 'Bearer' — 'Token' for Deepgram. Ignored when an "
        "API Key Header names a header of its own.",
    )
    api_version_header = fields.Char(
        string="API Version Header",
        help="Header carrying the API Version for a vendor that names its own "
        "— 'anthropic-version' for Anthropic. Leave empty when the version "
        "travels the generic way (see Send Generic Version Headers) or not in "
        "a header at all, as Google's does in the URL path.",
    )

    def _api_key_headers(self, api_key):
        self.check_singleton()
        if not api_key:
            return {}
        if self.api_key_header:
            return {self.api_key_header: api_key}
        scheme = self.api_key_scheme or "Bearer"
        if self.auth_type == "bearer":
            return {"Authorization": f"{scheme} {api_key}"}
        return {"Authorization": f"{scheme} {api_key}", "X-API-Key": api_key}

    def _exchange_usage_values(self, url, request_kwargs, response_body):
        return {}

    def _check_before_request(self, company_id):
        return None

    verify_tls = fields.Boolean(
        string="Verify TLS certificate",
        default=True,
        help="Uncheck only for an endpoint presenting a certificate this server "
        "cannot validate — typically a device on the local network with a "
        "self-signed certificate. Unchecking makes the connection "
        "interceptable; it is not a way to silence a certificate warning "
        "from a public endpoint.",
    )

    @api.constrains("endpoint_url", "per_record_connections")
    def _check_endpoint_url_is_set(self):
        for service in self:
            if not service.endpoint_url and not service.per_record_connections:
                raise ValidationError(
                    self.env._(
                        "Service %s needs a URL, unless each of its connections "
                        "carries its own.",
                        service.display_name,
                    )
                )

    @api.constrains("verify_tls", "endpoint_url")
    def _check_tls_disabled_only_off_public_internet(self):
        for endpoint in self:
            if endpoint.verify_tls or not endpoint.endpoint_url:
                continue
            host = urlparse(endpoint.endpoint_url).hostname or ""
            if not host or is_private_host(host):
                continue
            raise ValidationError(
                self.env._(
                    "TLS verification can only be disabled for an endpoint on a "
                    "private network. '%(host)s' is not one, so disabling it "
                    "would expose this endpoint's credential to anyone able to "
                    "answer in its place.",
                    host=host,
                )
            )

    oauth_client_id = fields.Char()
    oauth_auth_endpoint = fields.Char()
    oauth_token_endpoint = fields.Char()
    oauth_scope = fields.Char(default="read write")

    timeout_connect = fields.Integer(default=10)
    timeout_read = fields.Integer(default=30)

    health_check_enabled = fields.Boolean(default=True)
    health_check_endpoint = fields.Char()
    health_check_interval = fields.Integer(default=15)
    health_check_environment = fields.Selection(
        selection=[
            ("production", "Production"),
            ("staging", "Staging"),
            ("test", "Test/Sandbox"),
            ("any", "Any Active Credential"),
        ],
        default="production",
    )
    last_health_check = fields.Datetime(readonly=True)
    is_healthy = fields.Boolean(
        default=True,
        readonly=True,
    )
    health_message = fields.Char(readonly=True)

    cache_enabled = fields.Boolean(default=False)
    cache_ttl = fields.Integer(default=300)
    cache_error_count = fields.Integer(
        default=0,
        readonly=True,
    )
    cache_last_error = fields.Datetime(readonly=True)
    cache_health = fields.Selection(
        selection=[
            ("healthy", "Healthy"),
            ("degraded", "Degraded"),
            ("failed", "Failed"),
        ],
        compute="_compute_cache_health",
        store=True,
    )

    log_retention_days = fields.Integer(
        default=0,
        help="Delete this endpoint's event logs older than this many days. 0 uses "
        "the retention set in API Transport settings.",
    )
    log_request_payload = fields.Boolean(
        default=True,
        help="Store the request body on each integration.exchange row.\n\n"
        "Turn this off for a service whose payload is secret by construction "
        "rather than by field name — signing and cancellation calls that carry "
        "a private key, for instance. Redaction matches key names, so it cannot "
        "protect a payload whose names it does not know, and these rows are "
        "readable by everyone with API Transport access. The exchange is still "
        "recorded: URL, status, timing, error and trace id are unaffected.",
    )
    allow_multiple_credentials = fields.Boolean(
        default=False,
        help="Allow multiple active credentials per company/environment. "
        "Useful for services like Telegram that support multiple bots.",
    )
    per_record_connections = fields.Boolean(
        string="Connections per Record",
        help="Each connection belongs to one record, such as a device, and carries "
        "its own address. Calls name the connection they use; none is picked by "
        "company, and the service needs no URL of its own.",
    )

    credential_ids = fields.One2many(
        comodel_name="credential.credential",
        inverse_name="endpoint_id",
        string="Credentials",
    )
    connection_ids = fields.One2many(
        comodel_name="integration.connection",
        inverse_name="service_id",
        string="Connections",
    )

    def unlink(self) -> bool:
        credentials = self.sudo().credential_ids
        if credentials:
            self.sudo().credential_id = False
            credentials.unlink()
        return super().unlink()

    credential_count = fields.Integer(
        compute="_compute_credential_count",
        store=True,
    )
    total_requests = fields.Integer(compute="_compute_statistics")
    success_rate = fields.Float(compute="_compute_statistics")
    avg_response_time = fields.Float(compute="_compute_statistics")

    _code_unique = models.Constraint(
        "UNIQUE(code)",
        "Service code must be unique!",
    )

    @api.model
    def _get_per_record_service(self, code: str, name: str, category: str):
        services = self.sudo().with_context(active_test=False)
        service = services.search([("code", "=", code)], limit=1)
        if service:
            return service
        service, _created = get_or_create_row(
            self.env.cr,
            lambda: services.create(
                {
                    "name": name,
                    "code": code,
                    "category": category,
                    "per_record_connections": True,
                    "auth_type": "none",
                    "rate_limit_enabled": False,
                    "health_check_enabled": False,
                }
            ),
            lambda: services.search([("code", "=", code)], limit=1),
            conflict=f"integration.service {code!r}",
        )
        return service

    @api.constrains("code")
    def _check_code_format(self):
        for service in self:
            if service.code and not re.match(r"^[a-z0-9_]+$", service.code):
                raise ValidationError(
                    self.env._(
                        "Code must contain only lowercase letters, numbers, and underscores"
                    ),
                )

    @api.constrains("endpoint_url", "endpoint_url_test")
    def _check_endpoint_https(self):
        for record in self:
            if record.endpoint_url:
                if record.endpoint_url.startswith(
                    ("http://localhost", "http://127.0.0.1")
                ):
                    _logger.warning(
                        "Service '%s' uses localhost: %s",
                        record.name,
                        record.endpoint_url,
                    )
                elif not record.endpoint_url.startswith("https://"):
                    if not self.env.context.get("allow_http_production"):
                        raise ValidationError(
                            self.env._("Production endpoint must use HTTPS: %s")
                            % record.endpoint_url,
                        )

    @api.depends("connection_ids", "connection_ids.active")
    def _compute_credential_count(self):
        for service in self:
            service.credential_count = len(service.connection_ids.filtered("active"))

    @api.depends("cache_error_count", "cache_last_error", "cache_enabled")
    def _compute_cache_health(self):
        for service in self:
            if not service.cache_enabled:
                service.cache_health = False
            elif service.cache_error_count == 0:
                service.cache_health = "healthy"
            elif service.cache_error_count < 10:
                service.cache_health = "degraded"
            else:
                service.cache_health = "failed"

    def _compute_statistics(self):
        if not self.ids:
            for service in self:
                service.total_requests = 0
                service.success_rate = 0.0
                service.avg_response_time = 0.0
            return

        month_start = fields.Datetime.now().replace(
            day=1,
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )

        channel_refs = [f"integration.service,{sid}" for sid in self.ids]

        self.env.cr.execute(
            """
            SELECT
                channel_id,
                COUNT(*) as total_requests,
                COUNT(*) FILTER (WHERE status_code >= 200 AND status_code < 300) as successful,
                AVG(duration_ms) FILTER (WHERE duration_ms IS NOT NULL) as avg_duration
            FROM integration_exchange
            WHERE channel_id = ANY(%s)
              AND direction = 'outbound'
              AND timestamp >= %s
            GROUP BY channel_id
            """,
            (channel_refs, month_start),
        )

        stats_by_channel = {
            row["channel_id"]: row for row in self.env.cr.dictfetchall()
        }

        for service in self:
            channel_ref = f"integration.service,{service.id}"
            stats = stats_by_channel.get(channel_ref)

            if stats:
                total = stats["total_requests"] or 0
                successful = stats["successful"] or 0
                service.total_requests = total
                service.success_rate = (successful / total * 100) if total > 0 else 0.0
                service.avg_response_time = stats["avg_duration"] or 0.0
            else:
                service.total_requests = 0
                service.success_rate = 0.0
                service.avg_response_time = 0.0

    def action_test_connection(self) -> dict[str, Any]:
        self.check_singleton()
        credential = self.env["integration.connection"]._resolve(self).credential_id
        if not credential:
            raise ValidationError(self.env._("No active credentials configured"))

        endpoint = self.health_check_endpoint or "/"
        try:
            client = self._get_api_client(credential)
            response = client.get(endpoint)
        except Exception as e:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": self.env._("Connection failed"),
                    "message": str(e)[:255],
                    "type": "danger",
                    "sticky": False,
                },
            }

        status_code = response.get("status_code", 0)
        ok = 200 <= status_code < 300
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": self.env._("Connection OK") if ok else self.env._("Warning"),
                "message": self.env._("Service responded with HTTP %s", status_code),
                "type": "success" if ok else "warning",
                "sticky": False,
            },
        }

    def action_view_credentials(self) -> dict[str, Any]:
        self.check_singleton()
        return {
            "name": self.env._("Credentials"),
            "type": "ir.actions.act_window",
            "res_model": "credential.credential",
            "view_mode": "list,form",
            "domain": [("endpoint_id", "=", self.id)],
            "context": {"default_service_id": self.id},
        }

    def action_view_logs(self) -> dict[str, Any]:
        self.check_singleton()
        channel_ref = f"{self._name},{self.id}"
        return {
            "name": self.env._("Request Logs"),
            "type": "ir.actions.act_window",
            "res_model": "integration.exchange",
            "view_mode": "list,form",
            "domain": [
                ("channel_id", "=", channel_ref),
                ("direction", "=", "outbound"),
            ],
        }

    def action_check_health(self) -> dict[str, Any]:
        for record in self:
            try:
                record._probe_health()
            except Exception as e:
                _logger.exception("Health check failed for service %s", record.code)
                record.write(
                    {
                        "last_health_check": fields.Datetime.now(),
                        "is_healthy": False,
                        "health_message": str(e)[:255],
                    },
                )
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": self.env._("Health Check"),
                "message": self.env._(
                    "Health check completed for %s service(s).", len(self)
                ),
                "type": "info",
            },
        }

    @api.model
    def cron_reset_cache_errors(self):
        services = self.search([("cache_error_count", ">", 0)])
        if services:
            services.write(
                {
                    "cache_error_count": 0,
                    "cache_last_error": False,
                },
            )
            _logger.info("Reset cache errors for %d services", len(services))

    @api.model
    def cron_health_check_all(self):
        services = self.search(
            [
                ("active", "=", True),
                ("health_check_enabled", "=", True),
            ],
        )
        now = fields.Datetime.now()
        due = services.filtered(
            lambda service: (
                not service.last_health_check
                or service.health_check_interval <= 0
                or service.last_health_check
                + timedelta(minutes=service.health_check_interval)
                <= now
            )
        )

        for service in due:
            try:
                service._probe_health()
            except Exception as e:
                _logger.error("Health check failed for %s: %s", service.code, e)

    def _probe_health(self):
        """Probe with an eligible connection and store this service's status.

        A missing credential or failed request records unhealthy status. A
        response is healthy for HTTP 2xx. This uses the normal GET request path,
        including its configured cache and logging behavior.

        :rtype: None
        """
        self.check_singleton()
        connections = self.connection_ids.filtered(
            lambda c: c.active and (not c.credential_id or c.credential_id.active)
        )
        if self.health_check_environment == "any":
            connection = connections.sorted(
                key=lambda c: (c.environment != "production", c.sequence),
            )[:1]
        else:
            connection = connections.filtered(
                lambda c: c.environment == self.health_check_environment,
            )[:1]
        credential = connection.credential_id

        if not credential:
            env_label = (
                "active"
                if self.health_check_environment == "any"
                else self.health_check_environment
            )
            self.write(
                {
                    "last_health_check": fields.Datetime.now(),
                    "is_healthy": False,
                    "health_message": f"No {env_label} credentials",
                },
            )
            return

        endpoint = self.health_check_endpoint or "/"
        try:
            client = self._get_api_client(credential)
            response = client.get(endpoint)
        except Exception as e:
            _logger.warning("Health check call failed for %s: %s", self.code, e)
            self.write(
                {
                    "last_health_check": fields.Datetime.now(),
                    "is_healthy": False,
                    "health_message": str(e)[:255],
                },
            )
            return

        status_code = response.get("status_code", 0)
        is_ok = 200 <= status_code < 300
        self.write(
            {
                "last_health_check": fields.Datetime.now(),
                "is_healthy": is_ok,
                "health_message": (
                    f"HTTP {status_code}"
                    if is_ok
                    else f"Unexpected status {status_code}"
                ),
            },
        )

    def _get_api_client(self, credential=None):
        self.check_singleton()
        from odoo.addons.integration.tools import (  # pylint: disable=import-outside-toplevel
            get_api_client,
        )

        return get_api_client(
            self.env,
            self.code,
            company_id=(credential.company_id.id if credential else None) or None,
            credential_id=credential.id if credential else None,
        )
