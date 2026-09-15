import json
import logging
from typing import Any

from odoo import fields, models
from odoo.exceptions import ValidationError
from odoo.libs import redact

from ..tools.authentication import (
    CaseInsensitiveHeaders,
    execute_signature_verification,
    is_ip_in_allowlist,
    is_timestamp_valid,
)
from ..tools.exchange_queue import queue_exchange_values
from odoo.addons.rate_limit.tools import get_caller_rate_limiter

_logger = logging.getLogger(__name__)


class MixinInboundGate(models.AbstractModel):
    _name = "mixin.inbound.gate"
    _inherit = ["mixin.credential.auth"]
    _description = "Inbound Request Gate Mixin"

    signature_header = fields.Char(
        default="X-Hub-Signature-256",
        help="HTTP header containing the HMAC signature",
    )
    signature_prefix = fields.Char(
        default="sha256=",
        help="Prefix before signature value (e.g., 'sha256=')",
    )
    verification_method = fields.Char(
        help="Python method path for custom verification (format: 'model.method_name'). "
        "Method signature: method(headers: dict, body: str) -> bool"
    )

    timestamp_verification_enabled = fields.Boolean(
        default=False,
        help="Enable timestamp verification to prevent replay attacks",
    )
    timestamp_header = fields.Char(
        default="X-Webhook-Timestamp",
        help="HTTP header containing the request timestamp",
    )
    timestamp_max_age_seconds = fields.Integer(
        default=300,
        help="Maximum age of request timestamp. Default: 5 minutes",
    )

    ip_whitelist = fields.Text(
        help="Comma-separated list of allowed IPs or CIDRs (e.g., '192.168.1.0/24, 10.0.0.5'). "
        "Leave empty to allow all IPs."
    )
    max_payload_size = fields.Integer(
        default=1048576,
        help="Maximum allowed payload size for DoS prevention. Default: 1MB",
    )

    rate_limit_strict = fields.Boolean(default=True)
    rate_limit_window_seconds = fields.Integer(
        string="Rate Window (s)",
        default=60,
        help="Length of the rate-limit window in seconds.",
    )

    AUTH_MODE_ENFORCE = "enforce"
    AUTH_MODE_AUDIT = "audit"
    AUTH_MODE_OFF = "off"

    _BODY_DEPENDENT_AUTH_TYPES = ("hmac_sha256", "hmac_sha512", "custom")

    def _check_inbound_request(
        self,
        headers: dict[str, Any],
        body: str | bytes | None = None,
        remote_addr: str | None = None,
        mode: str = AUTH_MODE_ENFORCE,
        caller_already_checked: bool = False,
    ) -> tuple[bool, int, str]:
        allowed, status, reason, outcome = self._decide_inbound_request(
            headers,
            body=body,
            remote_addr=remote_addr,
            mode=mode,
            caller_already_checked=caller_already_checked,
        )
        self._record_inbound_verdict(
            allowed,
            status,
            reason,
            outcome,
            headers=headers,
            remote_addr=remote_addr,
            mode=mode,
        )
        return allowed, status, reason

    def _decide_inbound_request(
        self,
        headers: dict[str, Any],
        body: str | bytes | None = None,
        remote_addr: str | None = None,
        mode: str = AUTH_MODE_ENFORCE,
        caller_already_checked: bool = False,
    ) -> tuple[bool, int, str, str]:
        self.check_singleton()
        if mode == self.AUTH_MODE_OFF:
            return True, 200, "", "allowed"

        headers = CaseInsensitiveHeaders(headers)

        if not caller_already_checked:
            allowed, status, reason = self._check_inbound_caller(remote_addr)
            if not allowed:
                return (
                    allowed,
                    status,
                    reason,
                    "caller_limited" if status == 429 else "address_refused",
                )

        if (
            body is not None
            and self.max_payload_size
            and len(body) > self.max_payload_size
        ):
            return (
                False,
                413,
                f"payload too large for {self.display_name}",
                "payload_too_large",
            )

        authenticated, refusal = self._authenticate_inbound_identity(headers, body)
        if authenticated:
            if self.rate_limit_enabled and not self.check_rate_limit():
                return (
                    False,
                    429,
                    f"rate limit exceeded for {self.display_name}",
                    "rate_limited",
                )
            return True, 200, "", "allowed"

        if mode == self.AUTH_MODE_AUDIT:
            return (
                True,
                200,
                refusal or "no valid credential presented",
                "audit_accepted",
            )

        if refusal:
            return False, 401, refusal, "misconfigured"

        return (
            False,
            401,
            f"unauthenticated request for {self.display_name} from {remote_addr}",
            "unauthenticated",
        )

    def _authenticate_inbound_identity(
        self,
        headers: dict[str, Any],
        body: str | bytes | None,
    ) -> tuple[bool, str]:
        self.check_singleton()

        if body is None and self.auth_type in self._BODY_DEPENDENT_AUTH_TYPES:
            return False, (
                f"{self.display_name} authenticates with {self.auth_type}, "
                f"which verifies the request body, but the caller passed none"
            )

        try:
            return bool(self._authenticate_by_scheme(headers, body)), ""
        except ValidationError as e:
            return False, f"{self.display_name}: {e}"

    def _authenticate_by_scheme(
        self,
        headers: dict[str, Any],
        body: str | bytes | None = None,
    ) -> bool:
        self.check_singleton()

        scheme = getattr(self, f"_authenticate_scheme_{self.auth_type}", None)

        if (
            not scheme
            and not self.credential_id
            and self.auth_type not in ("none", "custom")
        ):
            raise ValidationError(
                self.env._("No credential configured for endpoint '%s'")
                % self.display_name,
            )

        if self.timestamp_verification_enabled:
            timestamp_value = headers.get(self.timestamp_header)
            if not timestamp_value:
                _logger.debug(
                    "Missing timestamp header '%s' for %s",
                    self.timestamp_header,
                    self.display_name,
                )
                return False
            if not is_timestamp_valid(
                timestamp_value=timestamp_value,
                max_age_seconds=self.timestamp_max_age_seconds,
                env=self.env,
            ):
                _logger.debug("Timestamp verification failed for %s", self.display_name)
                return False

        if self.auth_type == "none":
            return True

        if scheme:
            return bool(scheme(headers, body))

        if self.auth_type in ("bearer", "api_key"):
            token = self._presented_token(headers)
            if not token:
                _logger.debug("No bearer token presented for %s", self.display_name)
                return False
            return self.is_valid_token(token)

        secret = None
        if self.auth_type in ("hmac_sha256", "hmac_sha512"):
            secret = self.credential_id._use_secret("inbound_gate:verify")

        return execute_signature_verification(
            signature_type=self.auth_type,
            headers=headers,
            body=body or "",
            secret=secret,
            signature_header=self.signature_header,
            signature_prefix=self.signature_prefix,
            verification_method=self.verification_method,
            env=self.env,
        )

    _INBOUND_PAYLOAD_LOG_BYTES = 64 * 1024

    def _get_inbound_payload_log_bytes(self) -> int:
        """Return the logged payload byte limit; zero disables truncation."""
        return self._INBOUND_PAYLOAD_LOG_BYTES

    def _record_inbound_exchange(
        self,
        *,
        method: str | None = None,
        path: str | None = None,
        body: str | bytes | None = None,
        status_code: int = 200,
        error: str | None = None,
        remote_addr: str | None = None,
        user_agent: str | None = None,
        duration_ms: float = 0.0,
        event_type: str | None = None,
        event_id_external: str | None = None,
        processing_result: str | None = None,
    ) -> None:
        self.check_singleton()
        if getattr(self.env.cr, "readonly", False):
            return
        failed = bool(error) or status_code >= 400
        vals = {
            "direction": "inbound",
            "channel_id": f"{self._name},{self.id}",
            "company_id": self._get_inbound_company_id() or False,
            "request_method": (method or "").upper() or False,
            "request_url": (path or "")[:2048] or False,
            "status_code": status_code,
            "duration_ms": duration_ms,
            "source_ip": remote_addr or False,
            "user_agent": (user_agent or "")[:512] or False,
            "event_type": event_type or False,
            "event_id_external": event_id_external or False,
            "processing_result": processing_result or False,
            "state": "failed" if failed else "success",
            "date_completed": fields.Datetime.now(),
            "signature_verified": not failed and self.auth_type != "none",
            **self._prepare_inbound_payload_vals(body),
        }
        if error:
            vals["error_message"] = redact.mask_text(error)
        queue_exchange_values(self.env, vals)

    def _prepare_inbound_payload_vals(self, body: str | bytes | None) -> dict[str, Any]:
        """Prepare redacted, size-limited payload fields for an exchange record."""
        if not body:
            return {}
        text = (
            body.decode("utf-8", errors="replace") if isinstance(body, bytes) else body
        )
        try:
            text = json.dumps(redact.mask_data(json.loads(text)))
        except ValueError, TypeError:
            text = redact.mask_text(text)
        limit = self._get_inbound_payload_log_bytes()
        size = len(text.encode("utf-8"))
        if limit and size > limit:
            return {
                "request_payload": text.encode("utf-8")[:limit].decode(
                    "utf-8", errors="ignore"
                ),
                "request_payload_omitted_bytes": size - limit,
            }
        return {"request_payload": text}

    def _presented_token(self, headers: dict[str, Any]) -> str:
        auth_header = headers.get("Authorization") or ""
        if auth_header[:7].lower() == "bearer ":
            return auth_header[7:].strip()
        return (headers.get("X-Device-Token") or "").strip()

    log_inbound_access = fields.Boolean(
        string="Log Every Inbound Request",
        default=False,
        help="Record admitted requests as well as refused ones. Refusals are "
        "always recorded. Turn this on only for an endpoint whose traffic you "
        "want a row per call for — a device reporting once per position fix "
        "will fill the table.",
    )

    def _record_inbound_verdict(
        self,
        allowed: bool,
        status: int,
        reason: str,
        outcome: str,
        headers: Any = None,
        remote_addr: str | None = None,
        mode: str = AUTH_MODE_ENFORCE,
    ) -> None:
        if mode == self.AUTH_MODE_OFF:
            return
        if outcome == "allowed" and not self.log_inbound_access:
            return

        try:
            is_news = self._store_inbound_verdict(
                outcome,
                allowed=allowed,
                status=status,
                reason=reason,
                headers=headers,
                remote_addr=remote_addr,
                mode=mode,
            )
        except Exception:
            _logger.exception(
                "Could not record the inbound verdict for %s; the decision "
                "itself stands and was %s",
                self.display_name,
                "allow" if allowed else "refuse",
            )
            return

        if not is_news:
            return

        if outcome == "audit_accepted":
            _logger.warning(
                "UNAUTHENTICATED request accepted for %s from %s (audit mode): "
                "%s. Provision the credential, then switch to 'enforce'.",
                self.display_name,
                remote_addr,
                reason,
            )
        elif outcome == "misconfigured":
            _logger.error(
                "%s is refusing EVERY request and will keep doing so until it "
                "is fixed: %s. Callers see a 401, so this reads to them as "
                "their credentials being wrong.",
                self.display_name,
                reason,
            )

    _COALESCED_OUTCOMES = ("caller_limited", "audit_accepted", "misconfigured")

    _COUNTED_OUTCOMES = ("caller_limited",)

    _COALESCED_PER_CALLER = ("caller_limited",)

    STANDING_WINDOW_PARAM = "credential.inbound_standing_window_seconds"
    STANDING_WINDOW_DEFAULT = 3600

    def _get_inbound_coalesce_window(self, outcome: str) -> int:
        """Return the caller-limit or standing-condition window in seconds."""
        if outcome == "caller_limited":
            return self.rate_limit_window_seconds or 60
        window = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param_int(self.STANDING_WINDOW_PARAM, self.STANDING_WINDOW_DEFAULT)
        )
        return max(60, window)

    def _store_inbound_verdict(
        self,
        outcome: str,
        allowed: bool,
        status: int,
        reason: str,
        headers: Any,
        remote_addr: str | None,
        mode: str,
    ) -> bool:
        logs = self.env["inbound.access.log"].sudo()
        now = fields.Datetime.now()

        if outcome in self._COALESCED_OUTCOMES:
            window = self._get_inbound_coalesce_window(outcome)
            domain = [
                ("gate_model", "=", self._name),
                ("gate_id", "=", self.id),
                ("outcome", "=", outcome),
                ("timestamp", ">=", fields.Datetime.subtract(now, seconds=window)),
            ]
            if outcome in self._COALESCED_PER_CALLER:
                domain.append(("source_ip", "=", remote_addr or False))
            standing = logs.search(domain, order="timestamp desc", limit=1)
            if standing:
                if outcome in self._COUNTED_OUTCOMES:
                    standing.write(
                        {
                            "attempt_count": standing.attempt_count + 1,
                            "last_seen_at": now,
                        }
                    )
                return False

        logs.create(
            {
                "gate_model": self._name,
                "gate_id": self.id,
                "gate_name": self.display_name,
                "company_id": self._get_inbound_company_id(),
                "timestamp": now,
                "last_seen_at": now,
                "allowed": allowed,
                "outcome": outcome,
                "status_code": status,
                "reason": reason or False,
                "source_ip": remote_addr or False,
                "user_agent": (headers or {}).get("User-Agent") or False,
                "auth_type": self.auth_type or False,
                "mode": mode,
            }
        )
        return True

    def _get_inbound_company_id(self):
        """Return the gate's company ID, or False when no company is bound."""
        company = self._fields.get("company_id") and self.company_id
        return company.id if company else False

    def _check_inbound_caller(self, remote_addr) -> tuple[bool, int, str]:
        self.check_singleton()
        if self.ip_whitelist and not is_ip_in_allowlist(remote_addr, self.ip_whitelist):
            return False, 403, f"IP {remote_addr} not allowed for {self.display_name}"

        if self.rate_limit_enabled and not self._consume_caller_allowance(remote_addr):
            return False, 429, f"caller rate limit exceeded for {self.display_name}"

        return True, 200, ""

    PREAUTH_MULTIPLIER_PARAM = "credential.inbound_preauth_multiplier"
    PREAUTH_MULTIPLIER_DEFAULT = 10

    def _consume_caller_allowance(self, remote_addr) -> bool:
        """Cheap, best-effort pre-auth throttle by caller IP.

        Backed by ``get_caller_rate_limiter``, an in-memory limiter held
        per worker process (see ``registry_singleton``), not shared across
        ``--workers=N``: a caller balanced across N workers can consume up
        to N times ``rate_limit_requests * PREAUTH_MULTIPLIER_DEFAULT``
        before this gate denies anything. That is an accepted trade-off,
        not an oversight -- this multiplier is already a coarse pre-filter
        ahead of the real, DB-backed per-identity limit
        (``rate.limit.bucket``, correct across workers), so it favors
        avoiding a DB write on every unauthenticated request over exact
        cross-worker accounting.
        """
        self.check_singleton()
        if not remote_addr:
            return True

        multiplier = int(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param(
                self.PREAUTH_MULTIPLIER_PARAM,
                default=self.PREAUTH_MULTIPLIER_DEFAULT,
            )
        )
        if multiplier <= 0:
            return True

        limit = max(1, (self.rate_limit_requests or 0) * multiplier)
        window = self.rate_limit_window_seconds or 60
        result = get_caller_rate_limiter(self.env).check(
            (self._name, self.id, remote_addr),
            limit=limit,
            window_seconds=window,
        )
        if not result["allowed"]:
            _logger.warning(
                "Pre-auth rate limit exceeded for %s from %s: %s/%s in %ss",
                self.display_name,
                remote_addr,
                result["attempts"],
                result["limit"],
                window,
            )
        return result["allowed"]

    def _rate_limit_company_id(self):
        return self._get_inbound_company_id()

    def is_ip_allowed(self, source_ip: str) -> bool:
        self.check_singleton()
        return is_ip_in_allowlist(source_ip, self.ip_whitelist)
