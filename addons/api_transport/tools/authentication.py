import hashlib
import hmac
import ipaddress
import logging
import re
from datetime import UTC, datetime, timedelta

from odoo.http import request

_logger = logging.getLogger(__name__)

_EPOCH_RE = re.compile(r"^\d+(\.\d+)?$")


def _looks_like_epoch(value):
    return bool(_EPOCH_RE.match(value.strip()))


def _get_param_with_legacy(env, suffix, default):
    icp = env["ir.config_parameter"].sudo()
    value = icp.get_param(f"credential.{suffix}", default=None)
    if value is None:
        for legacy in (f"api_transport.{suffix}", f"api_communication.{suffix}"):
            value = icp.get_param(legacy, default=None)
            if value is not None:
                break
    return default if value is None else value


def _resolve_env(env=None):
    if env is not None:
        return env
    try:
        if request and hasattr(request, "env") and request.env:
            return request.env
    except ImportError, RuntimeError:
        pass
    return None


def _get_future_tolerance(env=None):
    try:
        env = _resolve_env(env)
        if env:
            return int(
                _get_param_with_legacy(env, "timestamp_future_tolerance", "60"),
            )
    except ImportError, RuntimeError, ValueError, TypeError:
        pass
    return 60


def _handle_none_signature(env=None):
    env = _resolve_env(env)

    if env:
        allow_none = _get_param_with_legacy(env, "allow_none_signature", "False")
        if allow_none != "True":
            _logger.warning(
                "Signature type 'none' is disabled. "
                "Set credential.allow_none_signature = True to enable "
                "(NEVER in production).",
            )
            return False

    _logger.warning("SECURITY RISK: Signature verification DISABLED")
    return True


class CaseInsensitiveHeaders(dict):
    def __init__(self, source=None):
        super().__init__(source or {})
        self._by_lower = {str(k).lower(): v for k, v in self.items()}

    def get(self, key, default=None):
        return self._by_lower.get(str(key).lower(), default)

    def __getitem__(self, key):
        try:
            return self._by_lower[str(key).lower()]
        except KeyError:
            raise KeyError(key) from None

    def __contains__(self, key):
        return str(key).lower() in self._by_lower


def is_bearer_token_valid(headers, expected_token):
    if not isinstance(headers, dict):
        _logger.error("Headers must be dict, got %s", type(headers).__name__)
        return False

    auth_header = headers.get("Authorization", "")

    if not auth_header.startswith("Bearer "):
        _logger.warning("Authorization header missing or malformed")
        return False

    token = auth_header[7:].strip()

    if not token:
        _logger.warning("Bearer token is empty")
        return False

    if not expected_token:
        _logger.error("No expected token provided")
        return False

    return hmac.compare_digest(token, expected_token)


def _is_custom_verification_valid(verification_method, headers, body, env=None):
    if not verification_method:
        return False

    try:
        env = _resolve_env(env)
        if env is None:
            _logger.error("No environment for custom verification")
            return False

        parts = verification_method.rsplit(".", 1)
        if len(parts) != 2:
            raise ValueError("Invalid method format")

        model_name, method_name = parts
        if not method_name.lstrip("_").startswith("verify_"):
            _logger.error(
                "Custom verification method %r rejected: method name must "
                "start with 'verify_' or '_verify_'.",
                verification_method,
            )
            return False

        model = env[model_name].sudo()
        method = getattr(model, method_name, None)

        if not method or not callable(method):
            raise AttributeError(f"Method {method_name} not found")

        return bool(method(headers, body))

    except Exception:
        _logger.exception("Custom verification failed")
        return False


def is_hmac_signature_valid(
    headers,
    body,
    secret,
    hash_func,
    signature_header="X-Hub-Signature-256",
    signature_prefix="sha256=",
):
    if not isinstance(headers, dict):
        _logger.error("Headers must be dict, got %s", type(headers).__name__)
        return False

    signature = headers.get(signature_header)
    if not signature:
        _logger.warning("Signature header '%s' not found", signature_header)
        return False

    if not secret:
        _logger.error("No secret provided for HMAC verification")
        return False

    if signature_prefix and signature.startswith(signature_prefix):
        signature = signature[len(signature_prefix) :]

    try:
        int(signature, 16)
    except ValueError:
        _logger.warning("Signature is not valid hexadecimal")
        return False

    body_bytes = body if isinstance(body, (bytes, bytearray)) else body.encode("utf-8")
    expected = hmac.new(
        secret.encode("utf-8"),
        body_bytes,
        hash_func,
    ).hexdigest()

    return hmac.compare_digest(signature.lower(), expected.lower())


def is_signature_valid(signature_type, headers, body, secret=None, **kwargs):
    try:
        if signature_type == "hmac_sha256":
            return is_hmac_signature_valid(
                headers,
                body,
                secret,
                hashlib.sha256,
                signature_header=kwargs.get("signature_header", "X-Hub-Signature-256"),
                signature_prefix=kwargs.get("signature_prefix", "sha256="),
            )
        if signature_type == "hmac_sha512":
            return is_hmac_signature_valid(
                headers,
                body,
                secret,
                hashlib.sha512,
                signature_header=kwargs.get("signature_header", "X-Hub-Signature-512"),
                signature_prefix=kwargs.get("signature_prefix", "sha512="),
            )
        if signature_type in ("bearer", "api_key"):
            return is_bearer_token_valid(headers, secret)
        if signature_type == "custom":
            verification_method = kwargs.get("verification_method")
            if not verification_method:
                _logger.error("Custom verification requires 'verification_method'")
                return False
            return _is_custom_verification_valid(
                verification_method, headers, body, kwargs.get("env")
            )
        if signature_type == "none":
            return _handle_none_signature(kwargs.get("env"))
        _logger.warning("Unknown signature type: %s", signature_type)
        return False

    except Exception:
        _logger.exception("Signature verification error")
        return False


def is_timestamp_valid(
    timestamp_value,
    max_age_seconds=300,
    timestamp_format=None,
    future_tolerance_seconds=None,
    env=None,
):
    try:
        if isinstance(timestamp_value, (int, float)):
            if timestamp_value < 0 or timestamp_value > 253402300799:
                _logger.warning("Timestamp out of bounds: %s", timestamp_value)
                return False
            timestamp_dt = datetime.fromtimestamp(timestamp_value, tz=UTC)
        elif isinstance(timestamp_value, str):
            if timestamp_format:
                timestamp_dt = datetime.strptime(timestamp_value, timestamp_format)
                if timestamp_dt.tzinfo is None:
                    timestamp_dt = timestamp_dt.replace(tzinfo=UTC)
            elif _looks_like_epoch(timestamp_value):
                epoch = float(timestamp_value.strip())
                if epoch < 0 or epoch > 253402300799:
                    _logger.warning("Timestamp out of bounds: %s", timestamp_value)
                    return False
                timestamp_dt = datetime.fromtimestamp(epoch, tz=UTC)
            else:
                if timestamp_value.endswith("Z"):
                    timestamp_value = timestamp_value[:-1] + "+00:00"
                timestamp_dt = datetime.fromisoformat(timestamp_value)
        else:
            _logger.warning("Invalid timestamp type: %s", type(timestamp_value))
            return False

        now = datetime.now(tz=UTC)

        if future_tolerance_seconds is None:
            future_tolerance_seconds = _get_future_tolerance(env)

        if timestamp_dt > now + timedelta(seconds=future_tolerance_seconds):
            _logger.warning("Timestamp in future: %s", timestamp_dt)
            return False

        age = (now - timestamp_dt).total_seconds()
        if age > max_age_seconds:
            _logger.warning("Timestamp too old: %ss > %ss", age, max_age_seconds)
            return False

        return True

    except Exception:
        _logger.exception("Timestamp verification error")
        return False


def ip_in_allowlist(remote_addr, allowlist):
    if not remote_addr:
        return False
    try:
        ip = ipaddress.ip_address(remote_addr)
    except ValueError:
        return False

    for token in (allowlist or "").split(","):
        token = token.strip()
        if not token:
            continue
        try:
            if "/" in token:
                if ip in ipaddress.ip_network(token, strict=False):
                    return True
            elif ip == ipaddress.ip_address(token):
                return True
        except ValueError:
            _logger.warning("Ignoring unparseable IP allowlist entry: %r", token)
            continue
    return False
