import base64
import logging
import os
import threading
import time
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

from odoo import api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

_ENCRYPTION_KEY_WARNING_COOLDOWN_SECONDS = 300

_KEY_STATE_LOCK = threading.Lock()

_KEY_STATE: dict[str, Any] = {
    "version_cache": None,
    "version_cache_checked": False,
    "missing_warning_last_at": 0.0,
}


class MixinEncryption(models.AbstractModel):
    """Fernet-at-rest encryption for a model's fields, keyed from the environment."""

    _name = "mixin.encryption"
    _description = "Encrypted Field Mixin"

    _ENCRYPTED_FIELD_PAIRS: tuple = ()
    _ENCRYPTED_FALLBACK_FIELDS: dict[str, str] = {}

    encryption_key_version = fields.Integer(
        readonly=True,
        help="Version of the encryption key used for this record's encrypted "
        "columns (for key-rotation tracking). 0/unset means untracked — the "
        "rotation migration treats such rows as eligible.",
    )

    def _is_encryption_available(self) -> bool:
        """Whether this deployment has opted into encryption at rest.

        Absence of ``ODOO_API_ENCRYPTION_KEY`` is a deliberate opt-out and the
        only thing that makes a consumer fall back to cleartext storage. A key
        that is *present but malformed* is not an opt-out: ``_get_encryption_key``
        raises on it, so a typo cannot silently downgrade a deployment that
        believes it is encrypting.
        """
        return bool(os.environ.get("ODOO_API_ENCRYPTION_KEY"))

    def _compute_optional_encrypted_field(
        self,
        encrypted_field: str,
        cleartext_field: str,
        target_field: str,
        binary: bool,
    ) -> None:
        """Expose whichever backing column holds this field's value.

        Ciphertext wins when present, so a row keeps decrypting after the
        deployment provisions a key, and a row written before it does keeps
        reading from its cleartext column until a rotation promotes it.
        """
        for record in self:
            encrypted_value = getattr(record, encrypted_field)
            if not encrypted_value:
                setattr(record, target_field, getattr(record, cleartext_field) or False)
                continue

            try:
                if binary:
                    setattr(
                        record,
                        target_field,
                        record._decrypt_binary_value(encrypted_value),
                    )
                else:
                    setattr(
                        record,
                        target_field,
                        record._decrypt_value_safe(encrypted_value, default=False),
                    )
            except Exception as e:
                _logger.warning(
                    "Safe decrypt failed for %s record %s: %s",
                    record._name,
                    getattr(record, "id", "new"),
                    e,
                )
                setattr(record, target_field, False)

    def _inverse_optional_encrypted_field(
        self,
        source_field: str,
        encrypted_field: str,
        cleartext_field: str,
        binary: bool,
    ) -> None:
        """Route a written value to the ciphertext column, or to the clear one.

        Exactly one of the two backing columns ever holds a value, so a row
        never carries the same secret in both forms.
        """
        encrypt = self._is_encryption_available()
        for record in self:
            value = getattr(record, source_field)
            if not value:
                setattr(record, encrypted_field, False)
                setattr(record, cleartext_field, False)
                continue

            if encrypt:
                setattr(
                    record,
                    encrypted_field,
                    record._encrypt_binary_value(value)
                    if binary
                    else record._encrypt_value(value),
                )
                setattr(record, cleartext_field, False)
            else:
                setattr(record, cleartext_field, value)
                setattr(record, encrypted_field, False)

    def _coerce_fernet_token(self, encrypted_value: bytes) -> bytes:
        if isinstance(encrypted_value, str):
            encrypted_value = encrypted_value.encode("utf-8")
        else:
            encrypted_value = bytes(encrypted_value)
        if encrypted_value.startswith(b"gAAAAA"):
            return encrypted_value
        try:
            return base64.b64decode(encrypted_value)
        except Exception as e:
            raise ValidationError(self.env._("Invalid encrypted binary data")) from e

    def _allow_key_fallback(self) -> bool:
        return getattr(self.sudo(), "allow_key_fallback", True)

    def _prepare_fallback_disabled_error(self, binary: bool) -> ValidationError:
        if binary:
            return ValidationError(
                self.env._(
                    "Failed to decrypt binary with current key. Fallback disabled."
                ),
            )
        _logger.error(
            "Current key failed for %s record %s. Fallback disabled (allow_key_fallback=False).",
            self._name,
            self.id,
        )
        return ValidationError(
            self.env._(
                "Failed to decrypt credential with current key.\n\n"
                "This credential has fallback disabled (allow_key_fallback=False). "
                "Either:\n"
                "1. Enable fallback temporarily to decrypt with old key\n"
                "2. Fix the encryption key configuration\n"
                "3. Re-create this credential with the current key",
            ),
        )

    def _prepare_no_key_worked_error(
        self, binary: bool, current_version: int | None
    ) -> ValidationError:
        if binary:
            return ValidationError(
                self.env._("Failed to decrypt binary value with any available key."),
            )
        _logger.error(
            "Failed to decrypt value for %s record %s: Invalid encryption key "
            "(tried current + %d old versions)",
            self._name,
            self.id,
            current_version - 1 if current_version else 0,
        )
        return ValidationError(
            self.env._(
                "Failed to decrypt value. Encryption key may have changed.\n\n"
                "If you recently rotated encryption keys, ensure old keys are still "
                "available as ODOO_API_ENCRYPTION_KEY_V1, V2, etc.\n\n"
                "Run the key migration tool to re-encrypt all credentials with the new key.",
            ),
        )

    def _decrypt_with_fallback(
        self,
        encrypted_value: bytes,
        binary: bool,
    ) -> bytes | str | bool:
        if not encrypted_value:
            return False

        allow_fallback = self._allow_key_fallback()
        encrypted_bytes = self._coerce_fernet_token(encrypted_value)

        def decode(raw: bytes) -> bytes | str:
            return base64.b64encode(raw) if binary else raw.decode("utf-8")

        try:
            cipher = Fernet(self._get_encryption_key())
            return decode(cipher.decrypt(encrypted_bytes))
        except ValidationError:
            if not os.environ.get("ODOO_API_ENCRYPTION_KEY"):
                # Genuinely absent: the deliberate opt-out, not a broken config.
                self._warn_encryption_key_missing(binary=binary)
                return False
            # Present but malformed: distinct from "not configured", and it says
            # nothing about whether an old key still works, so fall through to
            # the same old-key fallback path used for a wrong-but-valid key.
            _logger.error(
                "Current encryption key is malformed for %s record %s, "
                "trying old key versions",
                self._name,
                self.id,
            )
            if not allow_fallback:
                raise self._prepare_fallback_disabled_error(binary) from None
        except InvalidToken:
            if not allow_fallback:
                raise self._prepare_fallback_disabled_error(binary) from None
            _logger.debug(
                "Current key failed for %s record %s, trying old key versions",
                self._name,
                self.id,
            )
        except Exception as e:
            _logger.error(
                "Decryption failed for %s record %s: %s", self._name, self.id, e
            )
            if binary:
                raise ValidationError(
                    self.env._("Failed to decrypt binary value: %s") % str(e)
                ) from e
            raise ValidationError(
                self.env._("Failed to decrypt value: %s") % str(e)
            ) from e

        current_version = self._get_current_encryption_key_version()
        if current_version and current_version > 1:
            for version in range(current_version - 1, 0, -1):
                try:
                    old_key = self._get_encryption_key(version=version)
                    if old_key:
                        cipher = Fernet(old_key)
                        decrypted = decode(cipher.decrypt(encrypted_bytes))
                        _logger.info(
                            "Successfully decrypted %s record %s using old key "
                            "version %s. Consider running key migration.",
                            self._name,
                            self.id,
                            version,
                        )
                        return decrypted
                except Exception:
                    _logger.debug(
                        "Decryption with old key v%s for %s record %s failed",
                        version,
                        self._name,
                        self.id,
                        exc_info=True,
                    )
                    continue

        raise self._prepare_no_key_worked_error(binary, current_version)

    def _decrypt_binary_value(self, encrypted_value: bytes) -> bytes | bool:
        return self._decrypt_with_fallback(encrypted_value, binary=True)

    def _decrypt_value(self, encrypted_value: bytes) -> str | bool:
        return self._decrypt_with_fallback(encrypted_value, binary=False)

    def _decrypt_value_safe(
        self,
        encrypted_value: bytes,
        default: Any = False,
    ) -> str | Any:
        if not encrypted_value:
            return default

        try:
            return self._decrypt_value(encrypted_value)
        except Exception as e:
            _logger.warning(
                "Safe decrypt failed for %s record %s: %s",
                self._name,
                getattr(self, "id", "new"),
                e,
            )
            return default

    def _warn_encryption_key_missing(self, binary: bool) -> None:
        now = time.monotonic()
        with _KEY_STATE_LOCK:
            if (
                now - _KEY_STATE["missing_warning_last_at"]
                < _ENCRYPTION_KEY_WARNING_COOLDOWN_SECONDS
            ):
                return
            _KEY_STATE["missing_warning_last_at"] = now
        if binary:
            _logger.warning(
                "Cannot decrypt binary credentials: encryption key not "
                "configured. Set ODOO_API_ENCRYPTION_KEY environment variable.",
            )
        else:
            _logger.warning(
                "Cannot decrypt credentials: encryption key not configured. "
                "Set ODOO_API_ENCRYPTION_KEY environment variable.",
            )

    def _encrypt_binary_value(self, value: bytes) -> bytes | bool:
        if not value:
            return False

        try:
            raw_bytes = base64.b64decode(value)
            key = self._get_encryption_key()
            cipher = Fernet(key)
            return cipher.encrypt(raw_bytes)
        except Exception as e:
            _logger.error("Binary encryption failed: %s", e)
            raise ValidationError(
                self.env._("Failed to encrypt binary value: %s") % str(e)
            ) from e

    def _encrypt_value(
        self,
        value: str,
        key_version: int | None = None,
    ) -> bytes | bool:
        if not value:
            return False

        try:
            key = self._get_encryption_key(version=key_version)
            cipher = Fernet(key)
            return cipher.encrypt(value.encode("utf-8"))
        except Exception as e:
            _logger.error("Encryption failed: %s", e)
            raise ValidationError(
                self.env._("Failed to encrypt value: %s") % str(e)
            ) from e

    def _get_current_encryption_key_version(self) -> int | None:
        with _KEY_STATE_LOCK:
            if _KEY_STATE["version_cache_checked"]:
                return _KEY_STATE["version_cache"]

            if not os.environ.get("ODOO_API_ENCRYPTION_KEY"):
                _KEY_STATE["version_cache"] = None
                _KEY_STATE["version_cache_checked"] = True
                return None

            highest_old_version = 0
            consecutive_misses = 0
            max_consecutive_misses = 2
            for i in range(1, 20):
                if os.environ.get(f"ODOO_API_ENCRYPTION_KEY_V{i}"):
                    highest_old_version = i
                    consecutive_misses = 0
                else:
                    consecutive_misses += 1
                    if consecutive_misses >= max_consecutive_misses:
                        break

            _KEY_STATE["version_cache"] = highest_old_version + 1
            _KEY_STATE["version_cache_checked"] = True
            return _KEY_STATE["version_cache"]

    @api.model
    def _is_encryption_key_configured(self) -> bool:
        return bool(os.environ.get("ODOO_API_ENCRYPTION_KEY"))

    def _get_encryption_key(self, version: int | None = None) -> bytes | None:
        if version is None:
            env_var = "ODOO_API_ENCRYPTION_KEY"
        else:
            env_var = f"ODOO_API_ENCRYPTION_KEY_V{version}"

        key = os.environ.get(env_var)

        if not key:
            if version is None:
                raise ValidationError(
                    self.env._(
                        "Encryption key not configured!\n\n"
                        "The credential manager requires an encryption key to secure credentials.\n"
                        "This key MUST be set as an environment variable (NOT stored in the database).\n\n"
                        "═══════════════════════════════════════════════════════════════\n"
                        "SETUP INSTRUCTIONS:\n"
                        "═══════════════════════════════════════════════════════════════\n\n"
                        "Step 1: Generate encryption key (do this ONCE):\n"
                        "────────────────────────────────────────────────────────────────\n"
                        '  python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"\n\n'
                        "Step 2: Set environment variable:\n"
                        "────────────────────────────────────────────────────────────────\n"
                        "  export %s='<your-generated-key>'\n\n"
                        "See module documentation for detailed setup instructions.\n",
                    )
                    % env_var,
                )
            return None

        try:
            Fernet(key.encode())
            return key.encode()
        except Exception as e:
            raise ValidationError(
                self.env._(
                    "Invalid encryption key format in environment variable '%(env_var)s'!\n\n"
                    "The key must be a valid Fernet key (44 characters, base64-encoded).\n\n"
                    "Generate a new key with:\n"
                    '  python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"\n\n'
                    "Error details: %(error)s",
                    env_var=env_var,
                    error=str(e),
                ),
            ) from e

    @api.model
    def _get_encryption_migration_models(self) -> list[str]:
        names = []
        for name in self.env.registry:
            model = self.env[name]
            if model._abstract or model._transient:
                continue
            if not isinstance(model, MixinEncryption):
                continue
            if not model._ENCRYPTED_FIELD_PAIRS:
                continue
            names.append(name)
        return sorted(names)

    def _reencrypt_with_current_key(self) -> bool:
        self.check_singleton()
        touched = False
        for plain_field, enc_field, is_binary in self._ENCRYPTED_FIELD_PAIRS:
            encrypted = self.with_context(bin_size=False)[enc_field]
            if not encrypted:
                if self._promote_cleartext_field(plain_field, enc_field, is_binary):
                    touched = True
                continue
            if is_binary:
                plaintext_b64 = self._decrypt_binary_value(encrypted)
                if not plaintext_b64:
                    continue
                self[enc_field] = self._encrypt_binary_value(plaintext_b64)
            else:
                plaintext = self._decrypt_value(encrypted)
                if not plaintext:
                    continue
                self[enc_field] = self._encrypt_value(plaintext)
            touched = True
        if touched:
            version = self._get_current_encryption_key_version()
            if version:
                self._stamp_encryption_key_version(version)
        return touched

    def _promote_cleartext_field(
        self,
        plain_field: str,
        encrypted_field: str,
        is_binary: bool,
    ) -> bool:
        """Encrypt a value still held in the clear, once a key exists.

        This is what closes the loop for a deployment that installs without
        ``ODOO_API_ENCRYPTION_KEY`` and provisions one later: the rotation
        driver sweeps the cleartext columns into ciphertext instead of leaving
        them readable forever.
        """
        cleartext_field = self._ENCRYPTED_FALLBACK_FIELDS.get(plain_field)
        if not cleartext_field or not self._is_encryption_available():
            return False

        value = self.with_context(bin_size=False)[cleartext_field]
        if not value:
            return False

        self[encrypted_field] = (
            self._encrypt_binary_value(value)
            if is_binary
            else self._encrypt_value(value)
        )
        self[cleartext_field] = False
        return True

    def _stamp_encryption_key_version(self, version: int) -> None:
        if not self.ids:
            return
        self.env.cr.execute(
            f'UPDATE "{self._table}" SET encryption_key_version = %s '
            f"WHERE id = ANY(%s)",
            [version, self.ids],
        )
        self.invalidate_recordset(["encryption_key_version"])

    def _stamp_encrypted_payload(self, vals_list: list[dict[str, Any]]) -> None:
        if not self:
            return
        plain_fields = {plain for plain, _enc, _binary in self._ENCRYPTED_FIELD_PAIRS}
        to_stamp = self.browse()
        for record, vals in zip(self, vals_list, strict=True):
            if plain_fields & set(vals):
                to_stamp |= record
        if not to_stamp:
            return
        version = self._get_current_encryption_key_version()
        if not version:
            return
        self.env.cr.flush()
        to_stamp._stamp_encryption_key_version(version)

    @classmethod
    def _invalidate_key_version_cache(cls):
        with _KEY_STATE_LOCK:
            _KEY_STATE["version_cache"] = None
            _KEY_STATE["version_cache_checked"] = False
