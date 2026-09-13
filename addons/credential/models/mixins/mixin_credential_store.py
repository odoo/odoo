import hashlib
import json
import logging
from typing import Any

from psycopg import errors as psycopg_errors

from odoo import api, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.credential.tools import check_json_depth

_logger = logging.getLogger(__name__)


MAX_CREDENTIAL_DATA_SIZE = 65536
MAX_CREDENTIAL_VALUE_SIZE = 8192
MAX_JSON_NESTING_DEPTH = 10


class MixinCredentialStore(models.AbstractModel):
    _name = "mixin.credential.store"
    _inherit = ["mixin.encryption"]
    _description = "Encrypted Secret Store Mixin"

    credential_value_encrypted = fields.Binary(
        string="Credential Value (Encrypted)",
        attachment=False,
        copy=False,
        groups="base.group_system",
        help="Encrypted storage for credential value (API key, token, secret, etc.)",
    )

    is_provisioned = fields.Boolean(
        compute="_compute_is_provisioned",
        store=True,
        help="Whether the vault holds a secret for this record. A credential "
        "created by a data or demo file, or one whose secret has not been "
        "entered yet, exists unprovisioned until a secret is stored.",
    )

    cached_plaintext = fields.Char(
        compute="_compute_cached_plaintext",
        store=False,
        copy=False,
        groups="base.group_system",
        help="Internal: single-decrypt memo for credential_value_encrypted. "
        "Do NOT depend on this field outside this model.",
    )

    storage_method = fields.Selection(
        selection=[
            ("none", "Not Set"),
            ("simple", "Simple Value"),
            ("json", "JSON Data"),
        ],
        default="none",
        store=True,
        copy=False,
        readonly=True,
        help="Storage mode for credential_value_encrypted. Write-once: set "
        "by the first payload write and sealed thereafter. Mixing simple "
        "and JSON storage on the same record is not permitted.",
    )

    @api.depends("credential_value_encrypted")
    def _compute_is_provisioned(self):
        for record in self:
            record.is_provisioned = bool(
                record.with_context(bin_size=False).credential_value_encrypted
            )

    credential_value = fields.Char(
        compute="_compute_credential_value",
        inverse="_inverse_credential_value",
        store=False,
        copy=False,
        readonly=False,
        groups="base.group_system",
        help="Credential value (encrypted at rest) - API key, bearer token, etc.",
    )

    credential_data = fields.Text(
        string="Credential Data (JSON)",
        compute="_compute_credential_data",
        inverse="_inverse_credential_data",
        store=False,
        copy=False,
        readonly=False,
        groups="base.group_system",
        help="JSON storage for complex multi-value credentials (e.g., OAuth2). "
        "Example: {'access_token': '...', 'refresh_token': '...'}",
    )

    credential_hash = fields.Char(
        compute="_compute_credential_hash",
        store=True,
        readonly=True,
        help="Hash of encrypted credentials for cache key generation and integrity",
    )

    _INTERNAL_STORAGE_UPDATE_KEY = "_credential_internal_storage_update"

    _STORAGE_METHOD_GUARD_FIELD = "storage_method"

    _ENCRYPTED_FIELD_PAIRS = (
        ("credential_value", "credential_value_encrypted", False),
    )

    # Keys a consumer exposes through a field of its own. The store keeps them
    # out of credential_data so a secret with a masked field of its own is not
    # also rendered in clear text there.
    _JSON_ACCESSOR_FIELDS = ()

    @api.depends("credential_value_encrypted")
    def _compute_cached_plaintext(self):
        for record in self:
            encrypted = record.with_context(bin_size=False).credential_value_encrypted
            if not encrypted:
                record.cached_plaintext = False
                continue

            decrypted = record._decrypt_value_safe(encrypted, default=None)

            if decrypted is None:
                _logger.warning(
                    "Credential %s: could not decrypt credential_value_encrypted "
                    "(key missing or rotated). Field will read as empty.",
                    record.id or "new",
                )
                record.cached_plaintext = False
                continue

            if decrypted and record.id:
                record._enforce_access_rate_limit()

            record.cached_plaintext = decrypted or False

            if decrypted and record.id:
                try:
                    record._log_access_guarded("read")
                except psycopg_errors.ReadOnlySqlTransaction:
                    raise
                except Exception as e:
                    _logger.warning(
                        "Credential %s: failed to write audit log for read: %s",
                        record.id,
                        e,
                    )

    @api.depends("cached_plaintext", "storage_method")
    def _compute_credential_value(self):
        for record in self:
            if record.storage_method != "simple":
                record.credential_value = False
                continue
            record.credential_value = record.cached_plaintext or False

    def _parse_plaintext_dict(self) -> dict:
        self.check_singleton()
        if self.storage_method != "json":
            return {}
        plaintext = self.cached_plaintext
        if not plaintext:
            return {}
        try:
            parsed = json.loads(plaintext)
        except json.JSONDecodeError, ValueError:
            return {}
        return parsed if isinstance(parsed, dict) else {}

    @api.depends("cached_plaintext", "storage_method")
    def _compute_credential_data(self):
        for record in self:
            # Only the keys no named accessor claims. A password reaches the
            # form through its own masked field; putting it here too would
            # render it in clear text and send it to the browser besides.
            extra = {
                key: value
                for key, value in record._parse_plaintext_dict().items()
                if key not in self._JSON_ACCESSOR_FIELDS
            }
            record.credential_data = json.dumps(extra) if extra else "{}"

    @api.depends("credential_value_encrypted")
    def _compute_credential_hash(self) -> None:
        for cred in self:
            if cred.credential_value_encrypted:
                encrypted = cred.credential_value_encrypted
                if isinstance(encrypted, str):
                    encrypted = encrypted.encode("utf-8")
                cred.credential_hash = hashlib.sha256(encrypted).hexdigest()
            else:
                cred.credential_hash = False

    def _seal_storage_method(self, target_mode: str) -> None:
        self.check_singleton()
        current = self.storage_method or "none"
        if current == target_mode:
            return
        if current != "none":
            raise ValidationError(
                self.env._(
                    "This credential is already using %(current)s storage. "
                    "Writing through the %(target)s path would silently "
                    "corrupt the stored value. Archive this credential and "
                    "create a new one if you need to change storage mode.",
                )
                % {"current": current, "target": target_mode},
            )
        self.with_context(
            **{self._INTERNAL_STORAGE_UPDATE_KEY: True},
        ).write({self._STORAGE_METHOD_GUARD_FIELD: target_mode})

    def _inverse_credential_value(self):
        for record in self:
            if record.credential_value:
                value_size = len(record.credential_value.encode("utf-8"))
                if value_size > MAX_CREDENTIAL_VALUE_SIZE:
                    raise ValidationError(
                        self.env._(
                            "Credential value exceeds maximum size!\n\n"
                            "Size: %(size)s bytes\n"
                            "Maximum: %(max)s bytes (8KB)\n\n"
                            "For larger data, use credential_data (JSON format, up to 64KB).",
                        )
                        % {
                            "size": value_size,
                            "max": MAX_CREDENTIAL_VALUE_SIZE,
                        },
                    )

                record._seal_storage_method("simple")
                record.credential_value_encrypted = record._encrypt_value(
                    record.credential_value,
                )
                if record.id:
                    record._log_access("write")
            elif record.storage_method == "simple":
                record.credential_value_encrypted = False

    def _inverse_credential_data(self):
        for record in self:
            if not record.credential_data or record.credential_data == "{}":
                # This field owns the keys no named accessor claims. Emptying it
                # must not destroy a username or a bearer token, which have their
                # own visible field and are written by their own inverse: the
                # form carries this one empty for every category that hides it,
                # so a blanket clear here loses whatever the accessors wrote and
                # the order the fields happen to arrive in decides whether the
                # secret survives.
                if record.storage_method == "json":
                    stored = record._read_credential_dict_raw()
                    owned = {
                        key: value
                        for key, value in stored.items()
                        if key in record._JSON_ACCESSOR_FIELDS
                    }
                    if owned != stored:
                        if owned:
                            record.set_credential_dict(owned)
                        else:
                            record.credential_value_encrypted = False
                continue
            record._seal_storage_method("json")

            data_size = len(record.credential_data.encode("utf-8"))
            if data_size > MAX_CREDENTIAL_DATA_SIZE:
                raise ValidationError(
                    self.env._(
                        "Credential data exceeds maximum size!\n\nSize: %(size)s bytes\nMaximum: %(max)s bytes (64KB)",
                    )
                    % {"size": data_size, "max": MAX_CREDENTIAL_DATA_SIZE},
                )

            try:
                parsed_data = json.loads(record.credential_data)
            except (json.JSONDecodeError, ValueError) as e:
                raise ValidationError(
                    self.env._("Invalid JSON format in credential_data!\nError: %s")
                    % str(e),
                ) from e

            try:
                check_json_depth(parsed_data, MAX_JSON_NESTING_DEPTH)
            except ValueError as e:
                raise ValidationError(
                    self.env._(
                        "Invalid JSON structure!\n\nError: %(error)s\nMaximum nesting depth allowed: %(max)s levels",
                    )
                    % {"error": str(e), "max": MAX_JSON_NESTING_DEPTH},
                ) from e

            claimed = sorted(set(parsed_data) & set(record._JSON_ACCESSOR_FIELDS))
            if claimed:
                raise ValidationError(
                    self.env._(
                        "Set %(fields)s in its own field, not here. This one "
                        "carries the keys the vault has no field for, and a "
                        "secret typed here would be shown in clear text.",
                    )
                    % {"fields": ", ".join(claimed)},
                )

            # Merge rather than replace: the named accessors own their keys and
            # are not shown here, so writing this field alone must not drop them.
            owned = {
                key: value
                for key, value in record._read_credential_dict_raw().items()
                if key in record._JSON_ACCESSOR_FIELDS
            }
            record.set_credential_dict({**owned, **parsed_data})

    def _inverse_credential_json_field(self, field_name: str) -> None:
        for record in self:
            value = getattr(record, field_name)
            if not value and record.storage_method != "json":
                continue
            record._seal_storage_method("json")
            data = record._read_credential_dict_raw()
            if value:
                data[field_name] = value
            else:
                data.pop(field_name, None)
            record.set_credential_dict(data)

    def _read_credential_dict_raw(self) -> dict:
        self.check_singleton()
        if self.storage_method != "json":
            return {}
        if self.id:
            self.env.cr.execute(
                "SELECT id FROM credential_credential WHERE id = %s FOR NO KEY UPDATE",
                [self.id],
            )
            self.invalidate_recordset(["credential_value_encrypted"])
        encrypted = self.with_context(bin_size=False).credential_value_encrypted
        if not encrypted:
            return {}
        plaintext = self._decrypt_value_safe(encrypted, default=None)
        if not plaintext:
            return {}
        try:
            parsed = json.loads(plaintext)
        except json.JSONDecodeError, ValueError:
            return {}
        return parsed if isinstance(parsed, dict) else {}

    def get_credential_dict(self) -> dict[str, Any]:
        """The whole payload, named accessor keys included.

        Read the decrypted dict rather than `credential_data`, which shows only
        the keys no named accessor claims so that a password is never rendered
        in clear text on the form.
        """
        self.check_singleton()
        return self._parse_plaintext_dict()

    def set_credential_dict(self, data_dict: dict[str, Any]):
        self.check_singleton()

        if not isinstance(data_dict, dict):
            raise ValidationError(self.env._("Credential data must be a dictionary"))

        json_str = json.dumps(data_dict)

        data_size = len(json_str.encode("utf-8"))
        if data_size > MAX_CREDENTIAL_DATA_SIZE:
            raise ValidationError(
                self.env._(
                    "Credential data exceeds maximum size!\n\nSize: %(size)s bytes\nMaximum: %(max)s bytes (64KB)",
                )
                % {"size": data_size, "max": MAX_CREDENTIAL_DATA_SIZE},
            )

        try:
            check_json_depth(data_dict, MAX_JSON_NESTING_DEPTH)
        except ValueError as e:
            raise ValidationError(
                self.env._(
                    "Invalid JSON structure!\n\nError: %(error)s\nMaximum nesting depth allowed: %(max)s levels",
                )
                % {"error": str(e), "max": MAX_JSON_NESTING_DEPTH},
            ) from e

        if json_str and json_str != "{}":
            self.credential_value_encrypted = self._encrypt_value(json_str)
        else:
            self.credential_value_encrypted = False
        self._log_access("write")

    def _log_access(self, operation: str = "read"):
        return

    def _log_access_guarded(self, operation: str = "read") -> None:
        return

    def _enforce_access_rate_limit(self) -> None:
        return
