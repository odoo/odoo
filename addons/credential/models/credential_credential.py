import ipaddress
import json
import logging
from datetime import timedelta
from typing import Any, Self

from cryptography.fernet import Fernet, InvalidToken

from odoo import api, fields, models, tools
from odoo.exceptions import UserError, ValidationError
from odoo.libs import redact
from odoo.tools import SQL

from .credential_use import check_purpose

_logger = logging.getLogger(__name__)

DAYS_NO_EXPIRY = 999

EXPIRY_WARNING_DAYS = 30


class CredentialCredential(models.Model):
    _name = "credential.credential"
    _inherit = ["mixin.credential.store"]
    _description = "Credential"
    _order = "company_id, sequence, name"
    _rec_name = "name"

    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
        index=True,
        required=False,
        ondelete="cascade",
        help="Company that owns this credential. Leave empty for system-wide credentials visible to all companies.",
    )

    category_id = fields.Many2one(
        comodel_name="credential.category",
        index=True,
        required=True,
        ondelete="restrict",
        help="Type of credential (API Key, OAuth, Certificate, etc.)",
    )
    category_code = fields.Char(
        related="category_id.code",
        help="Technical code of the category for programmatic access",
    )
    category_description = fields.Text(
        related="category_id.description",
        store=False,
        help="Description of the credential category",
    )
    category_icon = fields.Char(
        related="category_id.icon",
        store=False,
    )
    storage_hint = fields.Selection(
        related="category_id.storage_hint",
        string="Storage Type",
        store=False,
        help="Recommended storage method from category",
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Created By",
        default=lambda self: self.env.user,
        index=True,
        readonly=True,
        help="User who created this credential",
    )
    owner_user_id = fields.Many2one(
        comodel_name="res.users",
        string="Personal Credential Of",
        index=True,
        ondelete="cascade",
        help="Make this a personal credential belonging to one user. Calls "
        "that resolve it act as that user rather than as the company. Only "
        "consulted for endpoints that allow personal credentials; leave empty "
        "for the ordinary company-wide credential.",
    )
    name = fields.Char(
        string="Credential Name",
        index=True,
        required=True,
        help="Descriptive name for this credential",
    )
    active = fields.Boolean(
        default=True,
        help="Only active credentials are used. Archiving is an admin-only "
        "control enforced by record rules / access rights — a field-level "
        "``groups=`` cannot be used here because the ORM's active_test reads "
        "``active`` on every search (including for plain users).",
    )
    sequence = fields.Integer(
        string="Priority",
        default=10,
        help="Lower number = higher priority when multiple credentials exist",
    )
    display_name = fields.Char(
        compute="_compute_display_name",
        store=False,
    )
    username = fields.Char(
        compute="_compute_credential_accessors",
        inverse="_inverse_username",
        copy=False,
        groups="base.group_system",
        help="Username stored in JSON credential data",
    )
    password = fields.Char(
        compute="_compute_credential_accessors",
        inverse="_inverse_password",
        copy=False,
        groups="base.group_system",
        help="Password stored in JSON credential data",
    )
    notes = fields.Text(
        help="Additional notes or documentation for this credential.\n\n"
        "⚠️ SECURITY WARNING: Notes are stored in PLAIN TEXT (not encrypted).\n"
        "Do NOT store passwords, API keys, or other secrets in notes."
    )

    health_status = fields.Selection(
        selection=[
            ("unknown", "Unknown"),
            ("healthy", "Healthy"),
            ("warning", "Warning"),
            ("error", "Error"),
        ],
        default="unknown",
        index=True,
        readonly=True,
        help="Health status from last validation check",
    )
    health_message = fields.Text(
        readonly=True,
        help="Details from last health check",
    )
    last_health_check = fields.Datetime(
        readonly=True,
        help="Timestamp of most recent health check",
    )
    last_health_check_latency = fields.Float(
        string="Last Check Latency (ms)",
        digits=(6, 2),
        readonly=True,
        help="Response time of last health check in milliseconds",
    )
    last_used_at = fields.Datetime(
        string="Last Used",
        readonly=True,
        help="Timestamp of most recent credential usage",
    )
    last_error = fields.Text(
        readonly=True,
        help="Error message from last failed operation",
    )
    last_error_date = fields.Datetime(
        readonly=True,
        help="Date and time of last error",
    )
    total_health_checks = fields.Integer(
        default=0,
        readonly=True,
        help="Total number of health check tests performed",
    )
    failed_health_checks = fields.Integer(
        default=0,
        readonly=True,
        help="Number of failed health check tests",
    )
    health_check_success_rate = fields.Float(
        string="Health Check Success Rate (%)",
        digits=(5, 2),
        compute="_compute_health_check_success_rate",
        store=True,
        help="Percentage of successful health checks",
    )

    usage_count = fields.Integer(
        default=0,
        readonly=True,
        help="Total number of times this credential was used",
    )
    success_count = fields.Integer(
        default=0,
        readonly=True,
        help="Number of successful credential uses",
    )
    error_count = fields.Integer(
        default=0,
        readonly=True,
        help="Number of failed credential uses",
    )
    success_rate = fields.Float(
        string="Success Rate (%)",
        compute="_compute_success_rate",
        store=True,
        help="Percentage of successful credential uses",
    )

    date_expiration = fields.Datetime(
        string="Expires At",
        help="Date when this credential expires (optional)",
    )
    is_expired = fields.Boolean(
        string="Expired",
        compute="_compute_is_expired",
        search="_search_is_expired",
        help="Whether the expiration date has passed, read against the current time",
    )
    days_until_expiry = fields.Integer(
        compute="_compute_days_until_expiry",
        help=f"Number of days until credential expires. Returns {DAYS_NO_EXPIRY} "
        "if no expiration date is set.",
    )
    date_expiry_warned = fields.Datetime(
        string="Expiry Warning Logged",
        copy=False,
        readonly=True,
        help="When cron_check_expiring_credentials last reported this "
        "credential as approaching expiry. Cleared whenever the expiration "
        "date is rewritten, so a renewed credential is warned about again.",
    )

    allow_key_fallback = fields.Boolean(
        string="Allow Old Key Fallback",
        default=True,
        help="If enabled, will try decrypting with old key versions when current key fails. "
        "Default from category, can be overridden.",
    )
    auto_validate_health = fields.Boolean(
        string="Automatic Health Validation",
        default=False,
        help="If enabled, this credential will be automatically validated by scheduled health checks. "
        "Default from category, can be overridden.",
    )

    decrypt_rate_limit_enabled = fields.Boolean(
        string="Cap Decryptions",
        default=True,
        groups="credential.group_credential_admin",
        help="Cap how often this credential's secret may be decrypted. Default from "
        "category, can be overridden.",
    )
    decrypt_rate_limit_max = fields.Integer(
        string="Decryptions / hour",
        default=100,
        groups="credential.group_credential_admin",
        help="Maximum number of decryption operations allowed per user per hour. "
        "Default from category, can be overridden.",
    )

    environment = fields.Selection(
        selection=[
            ("test", "Test/Sandbox"),
            ("staging", "Staging"),
            ("production", "Production"),
        ],
        default="test",
        index=True,
        help="Environment for this credential (test, staging, production).",
    )

    is_system_wide = fields.Boolean(
        string="System-wide Configuration",
        compute="_compute_is_system_wide",
        store=True,
        help="True if this is a system-wide credential (company_id is not set)",
    )
    bypass_format_validation = fields.Boolean(
        default=False,
        groups="base.group_system",
        help="Allow non-standard credential formats. Use only for credentials with unusual format requirements.",
    )

    api_key = fields.Char(
        string="API Key",
        compute="_compute_credential_accessors",
        inverse="_inverse_api_key",
        copy=False,
        groups="base.group_system",
        help="API Key stored in JSON credential data",
    )
    api_secret = fields.Char(
        string="API Secret",
        compute="_compute_credential_accessors",
        inverse="_inverse_api_secret",
        copy=False,
        groups="base.group_system",
        help="API Secret stored in JSON credential data",
    )
    bearer_token = fields.Char(
        compute="_compute_credential_accessors",
        inverse="_inverse_bearer_token",
        copy=False,
        groups="base.group_system",
        help="Bearer Token stored in JSON credential data",
    )

    oauth_access_token = fields.Char(
        string="OAuth Access Token",
        compute="_compute_credential_accessors",
        inverse="_inverse_oauth_access_token",
        copy=False,
        groups="base.group_system",
        help="OAuth Access Token stored in JSON credential data",
    )
    oauth_refresh_token = fields.Char(
        string="OAuth Refresh Token",
        compute="_compute_credential_accessors",
        inverse="_inverse_oauth_refresh_token",
        copy=False,
        groups="base.group_system",
        help="OAuth Refresh Token stored in JSON credential data",
    )
    oauth_client_id = fields.Char(
        string="OAuth Client ID",
        compute="_compute_credential_accessors",
        inverse="_inverse_oauth_client_id",
        copy=False,
        groups="base.group_system",
        help="OAuth Client ID stored in JSON credential data",
    )
    oauth_client_secret = fields.Char(
        string="OAuth Client Secret",
        compute="_compute_credential_accessors",
        inverse="_inverse_oauth_client_secret",
        copy=False,
        groups="base.group_system",
        help="OAuth Client Secret stored in JSON credential data",
    )
    oauth_token_date_expiration = fields.Datetime(
        string="OAuth Token Expiration",
        groups="base.group_system",
        help="When the OAuth access token expires. Set by OAuth integration code "
        "when tokens are refreshed (comes from provider's 'expires_in' response).",
    )

    secret_values = fields.Json(
        compute="_compute_secret_values",
        inverse="_inverse_secret_values",
        store=False,
        copy=False,
        readonly=False,
        groups="base.group_system",
        help="One entry per field the category declares, carrying its label and "
        "whether it holds a value -- never the value itself. An entry given a "
        "'value' string is stored; an empty one clears the key; an entry with "
        "no 'value' is left alone.",
    )

    encryption_key_is_current = fields.Boolean(
        compute="_compute_encryption_key_is_current",
        store=False,
        help="True when this credential's ciphertext was written with the "
        "current ODOO_API_ENCRYPTION_KEY. Drives the key-rotation warning "
        "banner: only credentials still on an OLD key version show it.",
    )
    last_validated = fields.Datetime(
        readonly=True,
        help="Timestamp of last successful credential validation",
    )

    _credential_system_unique = models.UniqueIndex(
        "(name) WHERE company_id IS NULL AND active = true",
        "Active system-wide credential names must be unique!",
    )

    _credential_company_unique = models.UniqueIndex(
        "(company_id, name) WHERE company_id IS NOT NULL AND active = true",
        "Active credential names must be unique per company!",
    )

    def _check_required_fields_for_category(self):
        self.invalidate_recordset(["credential_value_encrypted", "is_provisioned"])

        for record in self.filtered("is_provisioned"):
            specs = record.category_id.sudo().field_ids._requirement_specs()
            if not specs:
                continue

            record = record.sudo()
            payload = record._decrypted_payload_dict()

            missing = [
                spec[0].code
                for spec in specs
                if not record._satisfies_requirement(spec, payload)
            ]
            if not missing:
                continue

            raise ValidationError(
                self.env._(
                    "%(message)s\n\nMissing fields: %(fields)s",
                    message=record.category_id.sudo()._requirement_message(),
                    fields=", ".join(missing),
                )
            )

    def _decrypted_payload_dict(self) -> dict:
        self.check_singleton()
        encrypted = self.with_context(bin_size=False).credential_value_encrypted
        if not encrypted:
            return {}
        decrypted = self._decrypt_value(encrypted)
        if not decrypted:
            return {}
        try:
            parsed = json.loads(decrypted)
        except json.JSONDecodeError, ValueError:
            return {}
        return parsed if isinstance(parsed, dict) else {}

    def _satisfies_requirement(self, spec, payload: dict) -> bool:
        return any(
            getattr(self, definition.code, None) or payload.get(definition.code)
            for definition in spec
        )

    @api.constrains("notes")
    def _check_notes_for_secrets(self):
        for record in self:
            if not record.notes:
                continue
            matched_names = redact.find_secret_shapes(record.notes)
            if not matched_names:
                continue
            _logger.warning(
                "Possible secret pattern in notes for credential %s: "
                "matched pattern(s) %s (value not logged).",
                record.id or "new",
                ", ".join(matched_names),
            )

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.context.get(self._INTERNAL_STATS_UPDATE_KEY):
            for vals in vals_list:
                protected_being_set = vals.keys() & self._PROTECTED_STATS_FIELDS
                if protected_being_set:
                    raise ValidationError(
                        self.env._(
                            "Cannot seed protected statistics fields at creation!\n\n"
                            "The following fields are managed internally: %(fields)s\n\n"
                            "Create the credential first, then use the dedicated "
                            "methods (increment_usage, action_probe_health, "
                            "mark_as_used) to update statistics.",
                        )
                        % {
                            "fields": ", ".join(sorted(protected_being_set)),
                        },
                    )

        if not self.env.context.get(self._INTERNAL_STORAGE_UPDATE_KEY):
            for vals in vals_list:
                if self._STORAGE_METHOD_GUARD_FIELD in vals:
                    raise ValidationError(
                        self.env._(
                            "storage_method cannot be set directly at creation. "
                            "It is sealed automatically by the first payload write "
                            "(credential_value -> 'simple', credential_data or any "
                            "JSON accessor -> 'json').",
                        ),
                    )

        unset_policy = [
            [name for name in self._CATEGORY_POLICY_DEFAULTS if name not in vals]
            for vals in vals_list
        ]

        current_version = self._get_current_encryption_key_version() or 1

        for vals in vals_list:
            if "encryption_key_version" not in vals:
                has_encrypted_content = any(
                    vals.get(field) for field in self._ENCRYPTED_PAYLOAD_FIELDS
                )
                if has_encrypted_content:
                    vals["encryption_key_version"] = current_version

        records = super().create(vals_list)
        if records._touches_system_secrets():
            self.env.registry.clear_cache()

        # The policy fields belong to the credential administrators, so a creator
        # outside that group cannot be handed them as create values; the category
        # applies them afterwards, and only where the creator chose nothing.
        for record, names in zip(records.sudo(), unset_policy, strict=True):
            category = record.category_id
            policy = {
                name: category[self._CATEGORY_POLICY_DEFAULTS[name]]
                for name in names
                if record[name] != category[self._CATEGORY_POLICY_DEFAULTS[name]]
            }
            if category and policy:
                record.write(policy)

        records._check_required_fields_for_category()

        return records

    _PROTECTED_STATS_FIELDS = frozenset(
        {
            "usage_count",
            "success_count",
            "error_count",
            "health_status",
            "health_message",
            "last_health_check",
            "last_health_check_latency",
            "total_health_checks",
            "failed_health_checks",
            "last_used_at",
            "last_error",
            "last_error_date",
        }
    )

    _INTERNAL_STATS_UPDATE_KEY = "_credential_internal_stats_update"

    _ENCRYPTED_PAYLOAD_FIELDS = (
        "credential_value",
        "credential_data",
        "username",
        "password",
        "api_key",
        "api_secret",
        "oauth_access_token",
        "oauth_refresh_token",
        "bearer_token",
    )

    def write(self, vals):
        if self._touches_system_secrets(vals):
            self.env.registry.clear_cache()
        if "date_expiration" in vals and "date_expiry_warned" not in vals:
            vals = {**vals, "date_expiry_warned": False}

        if not self.env.context.get(self._INTERNAL_STATS_UPDATE_KEY):
            protected_being_modified = set(vals.keys()) & self._PROTECTED_STATS_FIELDS
            if protected_being_modified:
                raise ValidationError(
                    self.env._(
                        "Cannot modify protected statistics fields directly!\n\n"
                        "The following fields are managed internally: %(fields)s\n\n"
                        "Use the appropriate methods:\n"
                        "- increment_usage() for usage statistics\n"
                        "- action_probe_health() for health checks\n"
                        "- mark_as_used() for last_used_at",
                    )
                    % {"fields": ", ".join(sorted(protected_being_modified))},
                )

        if self._STORAGE_METHOD_GUARD_FIELD in vals and not self.env.context.get(
            self._INTERNAL_STORAGE_UPDATE_KEY,
        ):
            raise ValidationError(
                self.env._(
                    "storage_method is a write-once invariant managed by the "
                    "credential model. It is sealed on the first payload write "
                    "and cannot be modified directly. To change storage mode, "
                    "archive this credential and create a new one.",
                ),
            )

        adding_encrypted_content = any(
            vals.get(field) for field in self._ENCRYPTED_PAYLOAD_FIELDS
        )

        if adding_encrypted_content:
            current_version = self._get_current_encryption_key_version() or 1

            stamped = self.filtered(lambda r: not r.encryption_key_version)
            if stamped:
                self.env.cr.execute(
                    """
                    UPDATE credential_credential
                    SET encryption_key_version = %s
                    WHERE id = ANY(%s) AND (encryption_key_version IS NULL
                                            OR encryption_key_version = 0)
                    """,
                    [current_version, stamped.ids],
                )
                stamped.invalidate_recordset(
                    ["encryption_key_version", "encryption_key_is_current"],
                )

        result = super().write(vals)
        if self._touches_system_secrets(vals):
            self.env.registry.clear_cache()

        category_changed = "category_id" in vals
        if category_changed or adding_encrypted_content:
            self._check_required_fields_for_category()

        return result

    def unlink(self):
        if self._touches_system_secrets():
            self.env.registry.clear_cache()
        source_ip = self._get_request_source_ip()
        vals_list = [
            {
                **record._prepare_access_log_vals("delete", source_ip),
                "credential_id": False,
            }
            for record in self.filtered(lambda r: r.id)
        ]

        result = super().unlink()

        if vals_list:
            try:
                self.env["credential.access.log"].sudo().create(vals_list)
            except Exception as e:
                _logger.error(
                    "Failed to write delete audit log for credentials %s: %s",
                    [vals.get("credential_name") for vals in vals_list],
                    e,
                )

        return result

    @api.depends("name", "company_id", "category_id")
    def _compute_display_name(self):
        for record in self:
            parts = [record.name or ""]
            if record.category_id:
                parts.append(f"[{record.category_id.name}]")
            if record.company_id:
                parts.append(f"({record.company_id.name})")
            else:
                parts.append("(System-wide)")
            record.display_name = " ".join(parts)

    @api.depends("company_id")
    def _compute_is_system_wide(self):
        for record in self:
            record.is_system_wide = not record.company_id

    @api.depends("date_expiration")
    def _compute_is_expired(self):
        now = fields.Datetime.now()
        for record in self:
            record.is_expired = bool(
                record.date_expiration and record.date_expiration < now
            )

    def _search_is_expired(self, operator: str, value: Any):
        if operator not in ("=", "!=") or not isinstance(value, bool):
            return NotImplemented
        expired = [("date_expiration", "<", fields.Datetime.now())]
        if (operator == "=") == value:
            return expired
        return ["!", *expired]

    @api.depends("date_expiration")
    def _compute_days_until_expiry(self):
        now = fields.Datetime.now()
        for record in self:
            if record.date_expiration:
                delta = record.date_expiration - now
                record.days_until_expiry = delta.days
            else:
                record.days_until_expiry = DAYS_NO_EXPIRY

    @api.depends("success_count", "error_count")
    def _compute_success_rate(self):
        for record in self:
            total = record.success_count + record.error_count
            if total > 0:
                record.success_rate = (record.success_count / total) * 100
            else:
                record.success_rate = 0.0

    @api.depends("total_health_checks", "failed_health_checks")
    def _compute_health_check_success_rate(self):
        for record in self:
            if record.total_health_checks > 0:
                success = record.total_health_checks - record.failed_health_checks
                record.health_check_success_rate = (
                    success / record.total_health_checks
                ) * 100
            else:
                record.health_check_success_rate = 0.0

    _JSON_ACCESSOR_FIELDS = (
        "api_key",
        "api_secret",
        "bearer_token",
        "username",
        "password",
        "oauth_access_token",
        "oauth_refresh_token",
        "oauth_client_id",
        "oauth_client_secret",
    )

    @api.depends("cached_plaintext", "storage_method")
    def _compute_credential_accessors(self) -> None:
        for record in self:
            parsed: dict[str, Any] = record._parse_plaintext_dict()
            for field_name in self._JSON_ACCESSOR_FIELDS:
                record[field_name] = parsed.get(field_name, False)

    @api.depends("encryption_key_version")
    def _compute_encryption_key_is_current(self):
        current_version = self._get_current_encryption_key_version() or 1
        for record in self:
            record.encryption_key_is_current = (
                not record.encryption_key_version
                or record.encryption_key_version >= current_version
            )

    def _inverse_api_key(self) -> None:
        self._inverse_credential_json_field("api_key")

    def _inverse_api_secret(self) -> None:
        self._inverse_credential_json_field("api_secret")

    def _inverse_username(self) -> None:
        self._inverse_credential_json_field("username")

    def _inverse_password(self) -> None:
        self._inverse_credential_json_field("password")

    def _inverse_oauth_access_token(self) -> None:
        self._inverse_credential_json_field("oauth_access_token")

    def _inverse_oauth_refresh_token(self) -> None:
        self._inverse_credential_json_field("oauth_refresh_token")

    def _inverse_oauth_client_id(self) -> None:
        self._inverse_credential_json_field("oauth_client_id")

    def _inverse_oauth_client_secret(self) -> None:
        self._inverse_credential_json_field("oauth_client_secret")

    def _inverse_bearer_token(self) -> None:
        self._inverse_credential_json_field("bearer_token")

    @api.depends("credential_data", "category_id")
    def _compute_secret_values(self) -> None:
        for record in self:
            payload = record.get_credential_dict()
            record.secret_values = [
                {
                    "code": definition.code,
                    "label": definition.name,
                    "placeholder": definition.placeholder or "",
                    "help": definition.help_text or "",
                    "required": definition.required,
                    "filled": bool(payload.get(definition.code)),
                }
                for definition in record.category_id.sudo().field_ids
                if definition.is_blob_key
            ]

    def _inverse_secret_values(self) -> None:
        for record in self:
            written = {
                entry["code"]: entry["value"]
                for entry in (record.secret_values or [])
                if isinstance(entry, dict) and isinstance(entry.get("value"), str)
            }
            if not written:
                continue
            record._check_secret_codes(written)
            record._seal_storage_method("json")
            payload = record._read_credential_dict_raw()
            for code, value in written.items():
                if value:
                    payload[code] = value
                else:
                    payload.pop(code, None)
            record.set_credential_dict(payload)

    def _check_secret_codes(self, written: dict) -> None:
        self.check_singleton()
        declared = set(self.category_id.sudo().field_ids.mapped("code"))
        if undeclared := sorted(set(written) - declared):
            raise ValidationError(
                self.env._(
                    "%(category)s declares no field named %(fields)s, so there is "
                    "nowhere to put the value.",
                    category=self.category_id.display_name,
                    fields=", ".join(undeclared),
                )
            )

    def action_reveal_secret_field(self, code: str) -> str:
        self.check_singleton()
        self._check_secret_codes({code: ""})
        self.check_access("read")
        record = self.sudo()
        record._enforce_access_rate_limit()
        value = record._read_credential_dict_raw().get(code) or ""
        record._log_access_guarded("read")
        return value

    _CATEGORY_POLICY_DEFAULTS = {
        "decrypt_rate_limit_enabled": "default_decrypt_rate_limit_enabled",
        "decrypt_rate_limit_max": "default_decrypt_rate_limit_max",
        "auto_validate_health": "default_auto_validate_health",
        "allow_key_fallback": "default_allow_key_fallback",
    }

    @api.onchange("category_id")
    def _onchange_category_id(self):
        if self.category_id:
            category = self.category_id.sudo()
            for field_name, default_name in self._CATEGORY_POLICY_DEFAULTS.items():
                self[field_name] = category[default_name]

    def action_migrate_encryption_keys(self) -> dict[str, Any]:
        if not self.env.user.has_group(
            "credential.group_credential_admin",
        ):
            raise UserError(
                self.env._(
                    "Only Credential Manager administrators can migrate encryption keys."
                ),
            )
        self.check_access("write")

        current_version = self._get_current_encryption_key_version()

        totals = {
            "total": 0,
            "eligible": 0,
            "skipped": 0,
            "migrated": 0,
            "failed": 0,
            "errors": [],
            "current_key_version": current_version,
            "models": {},
        }

        for model_name in self._get_encryption_migration_models():
            model = self.env[model_name].sudo()
            eligible = model.search(
                [
                    "|",
                    ("encryption_key_version", "=", False),
                    ("encryption_key_version", "<", current_version),
                ],
            )
            total_all = model.search_count([])  # noqa: E8507  one query per model, not per record
            stats = {
                "total": total_all,
                "eligible": len(eligible),
                "skipped": total_all - len(eligible),
                "migrated": 0,
                "failed": 0,
            }

            _logger.info(
                "Encryption key migration [%s]: %d eligible / %d total "
                "(%d already at key version %d)",
                model_name,
                stats["eligible"],
                total_all,
                stats["skipped"],
                current_version,
            )

            for record in eligible:
                try:
                    with self.env.cr.savepoint():
                        migrated = record._reencrypt_with_current_key()
                        if migrated:
                            record._stamp_encryption_key_version(current_version)
                except Exception as e:
                    stats["failed"] += 1
                    error_msg = f"{model_name} (ID: {record.id}): {e!s}"
                    totals["errors"].append(error_msg)
                    _logger.error("Failed to migrate record: %s", error_msg)
                else:
                    stats["migrated"] += bool(migrated)

            totals["models"][model_name] = stats
            for key in ("total", "eligible", "skipped", "migrated", "failed"):
                totals[key] += stats[key]

        _logger.info(
            "Encryption key migration complete across %d model(s): "
            "%d migrated, %d failed, %d skipped (key version %d)",
            len(totals["models"]),
            totals["migrated"],
            totals["failed"],
            totals["skipped"],
            current_version,
        )

        return totals

    def action_test_encryption_keys(self) -> dict[str, Any]:
        if not self.env.user.has_group(
            "credential.group_credential_admin",
        ):
            raise UserError(
                self.env._(
                    "Only Credential Manager administrators can test encryption keys."
                ),
            )
        credentials = self
        total = len(credentials)

        results = {
            "total": total,
            "current_key": 0,
            "old_keys": 0,
            "failed": 0,
            "details": [],
        }

        current_version = self._get_current_encryption_key_version()

        for cred in credentials:
            try:
                if not cred.credential_value_encrypted:
                    continue

                encrypted = cred.credential_value_encrypted
                if isinstance(encrypted, str):
                    encrypted = encrypted.encode("utf-8")

                try:
                    cipher = Fernet(cred._get_encryption_key())
                    cipher.decrypt(encrypted)
                    results["current_key"] += 1
                    results["details"].append(
                        {
                            "name": cred.name,
                            "id": cred.id,
                            "key_version": "current",
                        },
                    )
                    continue
                except InvalidToken:
                    pass

                found = False
                for version in range(1, current_version) if current_version else []:
                    try:
                        old_key = cred._get_encryption_key(version=version)
                        if old_key:
                            cipher = Fernet(old_key)
                            cipher.decrypt(encrypted)
                            results["old_keys"] += 1
                            results["details"].append(
                                {
                                    "name": cred.name,
                                    "id": cred.id,
                                    "key_version": f"v{version}",
                                },
                            )
                            found = True
                            break
                    except Exception:
                        _logger.debug(
                            "Key version %s did not decrypt credential %s",
                            version,
                            cred.id,
                            exc_info=True,
                        )
                        continue

                if not found:
                    results["failed"] += 1
                    results["details"].append(
                        {
                            "name": cred.name,
                            "id": cred.id,
                            "key_version": "FAILED",
                        },
                    )

            except Exception as e:
                results["failed"] += 1
                _logger.error("Test failed for credential %s: %s", cred.name, e)

        return results

    def action_probe_health(self) -> dict[str, Any]:
        self.check_singleton()
        result = self._probe_health()
        if result.get("not_implemented"):
            kind, title = "warning", self.env._("Not Validated")
        elif result.get("success"):
            kind, title = "success", self.env._("Credential Valid")
        else:
            kind, title = "danger", self.env._("Validation Failed")
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {"title": title, "message": result.get("message"), "type": kind},
        }

    def _probe_health(self) -> dict[str, Any]:
        """Run the credential-specific probe and store its health result.

        This fallback records unknown health and a check timestamp; extensions
        provide the service probe. An unsuccessful probe is a returned outcome,
        not a raising validation contract.

        :returns: ``success`` and ``message``; this fallback also returns
            ``not_implemented=True``
        """
        self.check_singleton()

        _logger.info(
            "Validating credential %s (category: %s)",
            self.name,
            self.category_code,
        )

        result = {
            "success": False,
            "not_implemented": True,
            "message": self.env._(
                "No built-in validation for category '%s'. "
                "Override _probe_health in an inheriting "
                "module to add a service-specific probe."
            )
            % (self.category_code or "unknown"),
        }
        new_status = "unknown"

        self.with_context(**{self._INTERNAL_STATS_UPDATE_KEY: True}).write(
            {
                "health_status": new_status,
                "health_message": result.get("message") or result.get("error", ""),
                "last_health_check": fields.Datetime.now(),
            },
        )

        return result

    @api.model
    def _cron_probe_credentials(self):
        credentials = self.search(
            [
                ("auto_validate_health", "=", True),
                ("active", "=", True),
            ],
        )

        total = len(credentials)
        healthy = 0
        errors = 0
        skipped = 0

        _logger.info("Starting automated health validation for %d credentials", total)

        for cred in credentials:
            try:
                result = cred._probe_health()
                if result.get("not_implemented"):
                    skipped += 1
                elif result.get("success"):
                    healthy += 1
                else:
                    errors += 1
            except Exception as e:
                errors += 1
                _logger.error(
                    "Automated health check failed for credential %s: %s",
                    cred.name,
                    e,
                )

        _logger.info(
            "Automated health validation complete: %d healthy, %d errors, "
            "%d skipped (no built-in validator) out of %d",
            healthy,
            errors,
            skipped,
            total,
        )

        return {
            "total": total,
            "healthy": healthy,
            "errors": errors,
            "skipped": skipped,
        }

    def _expiry_warning_context(self) -> str:
        self.check_singleton()
        return ""

    @api.model
    def cron_check_expiring_credentials(self) -> dict[str, int]:
        now = fields.Datetime.now()
        threshold = now + timedelta(days=EXPIRY_WARNING_DAYS)

        domain = [
            ("date_expiration", "<=", threshold),
            ("date_expiration", ">", now),
            ("active", "=", True),
        ]
        expiring = self.sudo().search(domain)
        unwarned = expiring.filtered(lambda cred: not cred.date_expiry_warned)

        for cred in unwarned:
            _logger.warning(
                "Credential %s (id=%s)%s expires on %s; rotate or renew it "
                "before that date.",
                cred.name,
                cred.id,
                cred._expiry_warning_context(),
                cred.date_expiration,
            )

        if unwarned:
            unwarned.write({"date_expiry_warned": now})

        return {
            "expiring": len(expiring),
            "warned": len(unwarned),
            "window_days": EXPIRY_WARNING_DAYS,
        }

    @api.model
    def _get_active_for_category(self, code: str) -> Self:
        category = self.env["credential.category"].search(
            [("code", "=", code)], limit=1
        )
        if not category:
            return self.browse()
        return self.sudo().search(
            [("category_id", "=", category.id), ("active", "=", True)],
            order="write_date desc, id desc",
            limit=1,
        )

    _SECRET_ACCESSOR_PRIORITY = (
        "bearer_token",
        "api_key",
        "api_secret",
        "oauth_access_token",
        "password",
    )

    def _get_secret(self, prefer: str | None = None) -> str | bool:
        self.check_singleton()
        candidates = self._SECRET_ACCESSOR_PRIORITY
        if prefer:
            candidates = (prefer, *(f for f in candidates if f != prefer))
        for field_name in candidates:
            value = getattr(self, field_name, False)
            if value:
                return value
        return self.credential_value or False

    # The use path: trusted server code placing a secret on the wire or checking a
    # signature with it. It skips the per-user decrypt allowance and the per-read
    # audit row, both of which exist to stop a person harvesting secrets and which
    # made the hundred-and-first outbound call of an hour fail. It is private so no
    # RPC call reaches it; transport exchanges are recorded in their own log.
    def _use_secret_payload(self, purpose: str) -> dict:
        self.check_singleton()
        check_purpose(purpose)
        record = self.with_context(bin_size=False)
        if self.id:
            self.env["credential.use"]._queue(self.id, purpose)
            record.fetch(["credential_value_encrypted", "storage_method"])
        encrypted = record.credential_value_encrypted
        if not encrypted:
            return {}
        plaintext = self._decrypt_value_safe(encrypted, default=None)
        if plaintext is None:
            _logger.warning(
                "Credential %s: could not decrypt for use (key missing or "
                "rotated); treating as unset.",
                self.id or "new",
            )
            return {}
        if self.storage_method != "json":
            return {"credential_value": plaintext} if plaintext else {}
        try:
            data = json.loads(plaintext)
        except json.JSONDecodeError, ValueError:
            return {}
        return data if isinstance(data, dict) else {}

    def _use_secret(self, purpose: str, prefer: str | None = None) -> str | bool:
        payload = self._use_secret_payload(purpose)
        candidates = self._SECRET_ACCESSOR_PRIORITY
        if prefer:
            candidates = (prefer, *(f for f in candidates if f != prefer))
        for key in candidates:
            if payload.get(key):
                return payload[key]
        return payload.get("credential_value") or False

    def _use_basic_auth(self, purpose: str) -> tuple[str, str] | None:
        payload = self._use_secret_payload(purpose)
        if payload.get("username") and payload.get("password"):
            return (payload["username"], payload["password"])
        return None

    # A secret that belongs to the database rather than to a company or an
    # endpoint (an OAuth application's client secret, say), which used to be an
    # ir.config_parameter kept in clear.
    _SYSTEM_SECRET_PREFIX = "System secret: "

    @api.model
    def _get_system_secret_credential(self, key: str) -> Self:
        return (
            self.sudo()
            .with_context(active_test=False)
            .search(
                [
                    ("name", "=", f"{self._SYSTEM_SECRET_PREFIX}{key}"),
                    ("company_id", "=", False),
                ],
                limit=1,
            )
        )

    @api.model
    def _get_system_secret(self, key: str) -> str | bool:
        credential_id = self._provisioned_system_secrets().get(
            f"{self._SYSTEM_SECRET_PREFIX}{key}"
        )
        if not credential_id:
            return False
        credential = self.sudo().browse(credential_id)
        return credential._use_secret_payload("system_secret").get("value") or False

    @api.model
    def _set_system_secret(self, key: str, value: str | bool) -> None:
        credential = self._get_system_secret_credential(key)
        if not value:
            credential.unlink()
            return
        if credential:
            credential.set_credential_dict({"value": value})
            return
        self.env.registry.clear_cache()
        self.sudo().create(
            {
                "name": f"{self._SYSTEM_SECRET_PREFIX}{key}",
                "category_id": self.env.ref("credential.credential_category_custom").id,
                "company_id": False,
                "credential_data": json.dumps({"value": value}),
            }
        )

    @api.model
    def _has_system_secret(self, key: str) -> bool:
        return (
            f"{self._SYSTEM_SECRET_PREFIX}{key}" in self._provisioned_system_secrets()
        )

    @tools.ormcache()
    def _provisioned_system_secrets(self) -> dict[str, int]:
        self.flush_model(
            ["name", "company_id", "credential_value_encrypted", "sequence", "active"]
        )
        self.env.cr.execute(
            SQL(
                "SELECT name, id FROM credential_credential"
                " WHERE company_id IS NULL AND name LIKE %s"
                " AND credential_value_encrypted IS NOT NULL"
                " ORDER BY sequence DESC, id DESC",
                f"{self._SYSTEM_SECRET_PREFIX}%",
            )
        )
        return dict(self.env.cr.fetchall())

    def _touches_system_secrets(self, vals=None) -> bool:
        return bool(
            (vals and vals.keys() & {"name", "company_id"})
            or any(
                not record.company_id
                and (record.name or "").startswith(self._SYSTEM_SECRET_PREFIX)
                for record in self.sudo()
            )
        )

    @api.model
    def _move_parameters_into_system_secrets(self, keys) -> int:
        """Migrate `ir.config_parameter` secrets into system secrets.

        Each non-empty parameter is moved and every named row deleted, so the
        value does not stay readable in `ir_config_parameter` or later backups.
        """
        parameters = (
            self.env["ir.config_parameter"].sudo().search([("key", "in", list(keys))])
        )
        held = parameters.filtered("value")
        if held and not self._is_encryption_key_configured():
            raise UserError(
                self.env._(
                    "System parameters %(keys)s hold secrets that must move into "
                    "encrypted credentials. Set ODOO_API_ENCRYPTION_KEY and run the "
                    "upgrade again.",
                    keys=", ".join(held.mapped("key")),
                )
            )
        for parameter in held:
            self._set_system_secret(parameter.key, parameter.value)
        parameters.unlink()
        return len(held)

    def get_basic_auth(self):
        self.check_singleton()
        if self.username and self.password:
            return (self.username, self.password)
        return None

    def increment_usage(self, success: bool = True):
        self.check_singleton()
        vals = {
            "usage_count": self.usage_count + 1,
            "last_used_at": fields.Datetime.now(),
        }
        if success:
            vals["success_count"] = self.success_count + 1
        else:
            vals["error_count"] = self.error_count + 1
        self.with_context(**{self._INTERNAL_STATS_UPDATE_KEY: True}).write(vals)

    @api.model
    def _get_request_source_ip(self) -> str | bool:
        raw_ip = self.env["ir.http"]._get_request_remote_addr()
        if not raw_ip:
            return False
        try:
            ipaddress.ip_address(raw_ip)
        except ValueError:
            _logger.warning("Invalid IP address format in request: %s", raw_ip[:50])
            return "invalid"
        return raw_ip

    def _access_log_extras(self, operation: str) -> dict:
        self.check_singleton()
        return {}

    def _prepare_access_log_vals(self, operation: str, source_ip) -> dict:
        self.check_singleton()
        return {
            "credential_id": self.id,
            "credential_name": self.name,
            "user_id": self.env.uid,
            "user_login": self.env.user.login,
            "company_id": self.company_id.id if self.company_id else False,
            "operation": operation,
            "timestamp": fields.Datetime.now(),
            "source_ip": source_ip,
            **self._access_log_extras(operation),
        }

    def _log_access(self, operation: str = "read"):
        self.check_singleton()
        source_ip = self._get_request_source_ip()
        self.env["credential.access.log"].sudo().create(
            self._prepare_access_log_vals(operation, source_ip),
        )

    def _log_access_guarded(self, operation: str = "read") -> None:
        self.check_singleton()
        if self.env.cr.readonly:
            self._log_access_out_of_band(operation)
            return
        self._log_access(operation)
        # The plaintext was produced whether or not the caller's transaction
        # commits, so a rollback must not take the audit row with it.
        record = self
        self.env.cr.postrollback.add(lambda: record._log_access_out_of_band(operation))

    def _enforce_access_rate_limit(self) -> None:
        self.check_singleton()
        if not self.id:
            return
        config = self.sudo()
        if not (
            config.decrypt_rate_limit_enabled and config.decrypt_rate_limit_max > 0
        ):
            return

        cap = config.decrypt_rate_limit_max
        if self._consume_decryption_allowance(cap):
            return

        _logger.warning(
            "SECURITY: Rate limit exceeded for credential '%s' (id=%s) "
            "by user %s. Limit: %d decryptions per hour.",
            self.name,
            self.id,
            self.env.uid,
            cap,
        )
        self._log_access_out_of_band("read_rate_limited")
        raise ValidationError(
            self.env._(
                "Rate limit exceeded for credential '%(name)s'.\n\n"
                "Limit: %(limit)s decryptions per hour, per user.\n"
                "The allowance refills continuously; retry shortly.",
            )
            % {
                "name": self.name,
                "limit": cap,
            },
        )

    _DECRYPT_BUCKET_MODEL = "credential.credential.decrypt"
    _DECRYPT_WINDOW_SECONDS = 3600

    def _consume_decryption_allowance(self, cap: int) -> bool:
        self.check_singleton()
        return self.env["rate.limit.bucket"].consume_for_key(
            f"{self._DECRYPT_BUCKET_MODEL}:{self.id}:{self.env.uid}",
            subject_model=self._DECRYPT_BUCKET_MODEL,
            subject_id=self.id,
            capacity=cap,
            window_seconds=self._DECRYPT_WINDOW_SECONDS,
        )

    def _log_access_out_of_band(self, operation: str) -> None:
        records = self.filtered(lambda r: r.id)
        if not records:
            return
        source_ip = self._get_request_source_ip()
        vals_list = [
            record._prepare_access_log_vals(operation, source_ip) for record in records
        ]
        try:
            with self.env.registry.cursor() as cr:
                env = self.env(cr=cr)
                env["credential.access.log"].sudo().create(vals_list)
        except Exception as e:
            _logger.error(
                "Out-of-band audit log failed for credentials %s op=%s: %s. "
                "Falling back to rollback-coupled write.",
                records.ids,
                operation,
                e,
            )
            for record in records:
                try:
                    record._log_access(operation)
                except Exception as inner:
                    _logger.error(
                        "Fallback audit log ALSO failed for credential %s: %s",
                        record.id,
                        inner,
                    )

    def mark_as_used(self):
        self.check_singleton()
        self.with_context(**{self._INTERNAL_STATS_UPDATE_KEY: True}).write(
            {"last_used_at": fields.Datetime.now()}
        )
        self._log_access("use")
