import json
import logging
from time import monotonic
from typing import Any, Self

from odoo import api, fields, models
from odoo.exceptions import ValidationError

from ..tools.session_cache import (
    get_session_cache,
)

_logger = logging.getLogger(__name__)


class CredentialCredential(models.Model):
    _inherit = "credential.credential"

    endpoint_id = fields.Many2one(
        comodel_name="integration.service",
        string="Outbound Endpoint",
        index=True,
        ondelete="cascade",
        help="The outbound API endpoint this credential is associated with.",
    )
    connection_ids = fields.One2many(
        comodel_name="integration.connection",
        inverse_name="credential_id",
        string="Connections",
    )
    endpoint_auth_type = fields.Selection(
        related="endpoint_id.auth_type",
        readonly=True,
        help="Authentication scheme declared by the outbound endpoint.",
    )
    custom_headers = fields.Text(
        groups="base.group_system",
        help="Additional HTTP headers in JSON format: {'X-Custom-Header': 'value'}",
    )

    @api.constrains("custom_headers")
    def _check_custom_headers_json(self):
        for credential in self:
            if not credential.custom_headers:
                continue
            try:
                parsed = json.loads(credential.custom_headers)
            except (json.JSONDecodeError, ValueError, TypeError) as err:
                raise ValidationError(
                    self.env._(
                        "Custom headers must be valid JSON: %(error)s", error=err
                    )
                ) from err
            if not isinstance(parsed, dict):
                raise ValidationError(
                    self.env._(
                        "Custom headers must be a JSON object of header names to values."
                    )
                )

    @api.model
    def _get_for_endpoint_code(self, endpoint_code, company=None, user=None):
        service = (
            self.env["integration.service"]
            .sudo()
            .search([("code", "=", endpoint_code), ("active", "=", True)], limit=1)
        )
        if not service:
            return self.browse()
        return self._get_for_endpoint(service, company=company, user=user)

    @api.model
    def _get_for_endpoint(self, service, company=None, user=None):
        return (
            self.env["integration.connection"]
            ._resolve(service, company=company, user=user)
            .credential_id
        )

    def _oauth_client_id(self) -> str:
        self.check_singleton()
        return self.endpoint_id.oauth_client_id or self.oauth_client_id

    def _get_auth_headers(self):
        self.check_singleton()
        if not self.endpoint_id:
            return {}
        connection = self.env["integration.connection"]._for_credential(
            self.endpoint_id, self
        ) or self.env["integration.connection"].new(
            {"service_id": self.endpoint_id.id, "credential_id": self.id}
        )
        return connection._get_auth_headers()

    _CATEGORY_BY_AUTH_TYPE = {
        "api_key": "credential.credential_category_api_key",
        "bearer": "credential.credential_category_bearer_token",
        "basic": "credential.credential_category_basic_auth",
        "oauth2": "credential.credential_category_oauth2",
        "custom": "credential.credential_category_custom",
    }

    @api.model_create_multi
    def create(self, vals_list: list[dict[str, Any]]) -> Self:
        for vals in vals_list:
            if vals.get("category_id") or not vals.get("endpoint_id"):
                continue
            service = self.env["integration.service"].browse(vals["endpoint_id"])
            xml_id = self._CATEGORY_BY_AUTH_TYPE.get(service.auth_type)
            if xml_id:
                category = self.env.ref(xml_id, raise_if_not_found=False)
                if category:
                    vals["category_id"] = category.id

        records = super().create(vals_list)
        self.env["integration.connection"]._sync_from_credentials(
            records.filtered("endpoint_id")
        )

        for record in records:
            if record.endpoint_id:
                _logger.info(
                    "API Credential created: %s (ID: %s) for service %s by %s",
                    record.name,
                    record.id,
                    record.endpoint_id.code,
                    self.env.user.login,
                )
        return records

    _CONNECTION_SYNC_FIELDS = frozenset(
        {
            "endpoint_id",
            "company_id",
            "owner_user_id",
            "environment",
            "sequence",
            "active",
        }
    )

    _AUDITED_PAYLOAD_FIELDS = frozenset(
        {
            "api_key",
            "api_secret",
            "bearer_token",
            "oauth_access_token",
            "username",
            "password",
            "oauth_refresh_token",
            "credential_value",
            "credential_data",
        },
    )
    _AUDIT_FIELDS_CONTEXT_KEY = "_credential_audited_fields"

    def _access_log_extras(self, operation: str) -> dict:
        extras = super()._access_log_extras(operation)
        reason = self.env["credential.access.log"].DENIED_OPERATIONS.get(operation)
        extras["success"] = reason is None
        if reason:
            extras["failure_reason"] = reason
        written = self.env.context.get(self._AUDIT_FIELDS_CONTEXT_KEY)
        if written:
            extras["field_accessed"] = ",".join(written)
        return extras

    def write(self, vals: dict[str, Any]) -> bool:
        storage_fields = {
            "credential_data",
            "credential_value",
            "credential_value_encrypted",
        }
        audited = sorted(set(vals) & self._AUDITED_PAYLOAD_FIELDS)
        storage_modified = any(field in vals for field in storage_fields)

        if audited:
            api_credentials = self.filtered("endpoint_id")
            if api_credentials:
                _logger.warning(
                    "API Credentials modified: %s by %s",
                    api_credentials.mapped("name"),
                    self.env.user.login,
                )
            self = self.with_context(**{self._AUDIT_FIELDS_CONTEXT_KEY: audited})

        result = super().write(vals)

        if self._CONNECTION_SYNC_FIELDS & set(vals):
            self.env["integration.connection"]._sync_from_credentials(
                self.with_context(active_test=False)
            )
        if vals.get("endpoint_id"):
            self.sudo().with_context(
                active_test=False
            ).connection_ids._check_credential_serves_this_service()

        if audited or storage_modified:
            api_credentials = self.filtered("endpoint_id")
            if api_credentials:
                api_credentials._invalidate_session_cache()
                _logger.info(
                    "Session cache invalidated for credentials: %s",
                    api_credentials.mapped("name"),
                )

        return result

    def unlink(self) -> bool:
        api_credentials = self.filtered("endpoint_id")
        if api_credentials:
            _logger.warning(
                "API Credentials deleted: %s by %s",
                api_credentials.mapped("name"),
                self.env.user.login,
            )
            api_credentials._invalidate_session_cache()

        return super().unlink()

    def _notify(self, title: str, message: str, kind: str) -> dict[str, Any]:
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {"title": title, "message": message, "type": kind},
        }

    def _notify_not_linked(self) -> dict[str, Any]:
        return self._notify(
            self.env._("Not Applicable"),
            self.env._("Credential is not linked to an API service"),
            "warning",
        )

    def _probe_health(self) -> dict[str, Any]:
        """Probe the linked service and store credential health statistics.

        Record latency, counters and the outcome; on success also record the
        validation timestamp. Unlinked credentials delegate to the base probe.

        :returns: ``success`` and ``message``, or the base probe's result
        """
        self.check_singleton()
        if not self.endpoint_id:
            return super()._probe_health()

        code = self.endpoint_id.code
        started = monotonic()
        error = None
        try:
            client = self.endpoint_id.with_company(self.company_id)._get_api_client(
                self
            )
            healthy = client.probe_health()
        except Exception as e:
            _logger.warning(
                "Health probe of credential %s (service %s) failed: %s",
                self.id,
                code,
                e,
            )
            healthy, error = False, str(e)[:255]
        latency_ms = (monotonic() - started) * 1000

        now = fields.Datetime.now()
        message = (
            self.env._("Service '%s' answered with this credential.", code)
            if healthy
            else error or self.env._("Service '%s' did not answer successfully.", code)
        )
        vals = {
            "health_status": "healthy" if healthy else "error",
            "health_message": message,
            "last_health_check": now,
            "last_health_check_latency": latency_ms,
            "total_health_checks": self.total_health_checks + 1,
            "failed_health_checks": self.failed_health_checks + (0 if healthy else 1),
        }
        if healthy:
            vals["last_validated"] = now
        self.with_context(**{self._INTERNAL_STATS_UPDATE_KEY: True}).write(vals)
        return {"success": healthy, "message": message}

    def action_view_usage_logs(self) -> dict[str, Any]:
        self.check_singleton()
        return {
            "name": self.env._("API Usage Logs"),
            "type": "ir.actions.act_window",
            "res_model": "integration.exchange",
            "view_mode": "list,form",
            "domain": [
                ("credential_id", "=", self.id),
                ("direction", "=", "outbound"),
            ],
        }

    def _expiry_warning_context(self) -> str:
        self.check_singleton()
        if not self.endpoint_id:
            return super()._expiry_warning_context()
        return f" on endpoint {self.endpoint_id.name}"

    def _invalidate_session_cache(self) -> None:
        cache = get_session_cache(self.env)

        for record in self:
            if not record.endpoint_id:
                continue

            endpoint_code = record.endpoint_id.code

            def is_invalidation_required(key, _sc=endpoint_code):
                return key.split(":", 1)[0] == _sc

            count = cache.invalidate_matching(is_invalidation_required)

            _logger.info(
                "Invalidated %d cached sessions for credential '%s' (service: %s)",
                count,
                record.name,
                endpoint_code,
            )

    def action_oauth_authorize(self) -> dict[str, Any]:
        self.check_singleton()

        if not self.endpoint_id:
            return self._notify_not_linked()

        if self.endpoint_id.auth_type != "oauth2":
            return self._notify(
                self.env._("Invalid Configuration"),
                self.env._(
                    "Service '%s' is not configured for OAuth 2.0 authentication",
                )
                % self.endpoint_id.name,
                "warning",
            )

        return {
            "type": "ir.actions.act_url",
            "url": f"/api_transport/oauth/authorize/{self.id}",
            "target": "self",
        }

    def action_oauth_reauthorize(self) -> dict[str, Any]:
        self.check_singleton()

        self.write(
            {
                "oauth_access_token": False,
                "oauth_refresh_token": False,
                "oauth_token_date_expiration": False,
            },
        )

        _logger.info(
            "OAuth re-authorization initiated: credential_id=%s, service=%s, user=%s",
            self.id,
            self.endpoint_id.code if self.endpoint_id else "N/A",
            self.env.user.login,
        )

        return self.action_oauth_authorize()
