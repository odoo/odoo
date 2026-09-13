import json
import logging
from time import monotonic
from typing import Any, Self

from odoo import api, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.credential.tools.session_cache import (
    get_session_cache,
)

_logger = logging.getLogger(__name__)


class CredentialCredential(models.Model):
    _inherit = "credential.credential"

    endpoint_id = fields.Many2one(
        comodel_name="api.endpoint.outbound",
        string="Outbound Endpoint",
        index=True,
        ondelete="cascade",
        help="The outbound API endpoint this credential is associated with.",
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
            self.env["api.endpoint.outbound"]
            .sudo()
            .search([("code", "=", endpoint_code), ("active", "=", True)], limit=1)
        )
        if not service:
            return self.browse()
        return self._get_for_endpoint(service, company=company, user=user)

    @api.model
    def _get_for_endpoint(self, service, company=None, user=None):
        company_id = getattr(company, "id", company) or self.env.company.id

        if service.allow_user_credentials:
            user_id = getattr(user, "id", user) or self.env.uid
            personal = self.sudo().search(
                [
                    ("endpoint_id", "=", service.id),
                    ("owner_user_id", "=", user_id),
                    ("company_id", "in", (company_id, False)),
                    ("active", "=", True),
                ],
                order="sequence, id",
                limit=1,
            )
            if personal:
                return personal

        return self.sudo().search(
            [
                ("endpoint_id", "=", service.id),
                ("company_id", "=", company_id),
                ("owner_user_id", "=", False),
                ("active", "=", True),
            ],
            order="sequence, id",
            limit=1,
        )

    def _oauth_client_id(self) -> str:
        self.check_singleton()
        return self.endpoint_id.oauth_client_id or self.oauth_client_id

    def _get_auth_headers(self):
        self.check_singleton()
        headers = {}

        if not self.endpoint_id:
            return headers

        auth_type = self.endpoint_id.auth_type

        if auth_type == "bearer":
            token = self._use_secret(prefer="bearer_token")
            if token:
                headers["Authorization"] = f"Bearer {token}"
        elif auth_type == "api_key":
            api_key = self._use_secret(prefer="api_key")
            if api_key:
                headers.update(self.endpoint_id._api_key_headers(api_key))
        elif auth_type == "oauth2":
            access_token = self._use_secret_payload().get("oauth_access_token")
            if access_token:
                headers["Authorization"] = f"Bearer {access_token}"

        if self.custom_headers:
            try:
                headers.update(json.loads(self.custom_headers))
            except json.JSONDecodeError, ValueError, TypeError:
                _logger.warning(
                    "Invalid custom_headers JSON for credential %s: %s",
                    self.id,
                    self.custom_headers[:100] if self.custom_headers else "",
                )

        return headers

    @api.constrains(
        "endpoint_id", "company_id", "environment", "active", "owner_user_id"
    )
    def _check_unique_active_credential(self) -> None:
        constrained = self.filtered(
            lambda cred: (
                cred.active
                and cred.endpoint_id
                and not cred.endpoint_id.allow_multiple_credentials
            )
        )
        if not constrained:
            return

        companies = set(constrained.company_id.ids)
        if any(not cred.company_id for cred in constrained):
            companies.add(False)
        peers = self.search(
            [
                ("endpoint_id", "in", constrained.endpoint_id.ids),
                ("company_id", "in", list(companies) or [False]),
                ("environment", "in", list(set(constrained.mapped("environment")))),
                ("active", "=", True),
            ],
        )
        ids_by_key: dict[tuple, set[int]] = {}
        for peer in peers:
            key = (
                peer.endpoint_id.id,
                peer.company_id.id,
                peer.environment,
                peer.owner_user_id.id,
            )
            ids_by_key.setdefault(key, set()).add(peer.id)

        for cred in constrained:
            key = (
                cred.endpoint_id.id,
                cred.company_id.id,
                cred.environment,
                cred.owner_user_id.id,
            )
            if ids_by_key.get(key, set()) - {cred.id}:
                raise ValidationError(
                    self.env._(
                        "Only one active credential per service/company/"
                        "environment, and per user for a personal credential."
                    )
                )

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
            service = self.env["api.endpoint.outbound"].browse(vals["endpoint_id"])
            xml_id = self._CATEGORY_BY_AUTH_TYPE.get(service.auth_type)
            if xml_id:
                category = self.env.ref(xml_id, raise_if_not_found=False)
                if category:
                    vals["category_id"] = category.id

        records = super().create(vals_list)

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

    def _validate_health(self) -> dict[str, Any]:
        self.check_singleton()
        if not self.endpoint_id:
            return super()._validate_health()

        code = self.endpoint_id.code
        started = monotonic()
        error = None
        try:
            client = self.endpoint_id.with_company(self.company_id)._get_api_client(
                self
            )
            healthy = client.health_check()
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
            "res_model": "api.event.log",
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
            credential_hash = record.credential_hash

            def is_invalidation_required(key, _sc=endpoint_code, _ch=credential_hash):
                parts = key.split(":")
                if len(parts) != 3:
                    return False
                key_service, _key_company, key_hash = parts
                if _sc and key_service != _sc:
                    return False
                return not (_ch and key_hash != _ch)

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
