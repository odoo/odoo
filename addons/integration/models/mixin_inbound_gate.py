import json
import logging
import time
from typing import Any, NamedTuple

import psycopg.errors
from werkzeug.exceptions import RequestEntityTooLarge

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.http import request
from odoo.libs import redact

from ..tools.admission import Admission, Refused, Resolution
from ..tools.authentication import (
    CaseInsensitiveHeaders,
    execute_signature_verification,
    is_ip_in_allowlist,
    is_timestamp_valid,
)
from ..tools.exchange_queue import keep_row_on_rollback, queue_exchange_values
from odoo.addons.rate_limit.tools import get_caller_rate_limiter

_logger = logging.getLogger(__name__)

_OMITTED_PAYLOAD_HEAD_CHARS = 512

DEFAULT_MAX_PAYLOAD_SIZE = 1024 * 1024

# (dbname, gate model, gate id, condition) -> when it was last reported
_STANDING_CONDITIONS_REPORTED: dict[tuple, float] = {}


class Verdict(NamedTuple):
    allowed: bool
    status: int
    reason: str
    code: str


INBOUND_SUBJECT_KEY = "inbound_subject"
INBOUND_VERIFY_KEY = "inbound_verify"


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
    log_retention_days = fields.Integer(
        default=0,
        help="Delete this gate's exchange rows older than this many days. 0 uses "
        "the retention set in API Transport settings.",
    )

    @api.constrains("log_request_payload_max_bytes")
    def _check_log_request_payload_max_bytes(self):
        for record in self:
            if record.log_request_payload_max_bytes < 0:
                raise ValidationError(
                    self.env._("The payload log limit cannot be negative."),
                )

    ip_whitelist = fields.Text(
        help="Comma-separated list of allowed IPs or CIDRs (e.g., '192.168.1.0/24, 10.0.0.5'). "
        "Leave empty to allow all IPs."
    )
    max_payload_size = fields.Integer(
        default=DEFAULT_MAX_PAYLOAD_SIZE,
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

    @api.model
    def _resolve_route_receiver(
        self,
        declaration: str,
        path_args: dict[str, Any],
        event_type: str | None = None,
    ):
        """The ``Resolution`` of a route's ``receiver=`` declaration.

        ``<model>:<field>`` searches the subject by the path variable of that
        name; ``<model>:_method`` calls the method with the path variables, and
        it answers a record or ``(record, extra)`` -- what it parsed on the way,
        handed to the handler on ``request.admission.extra``. The gate is the
        subject itself when it carries this mixin, else the receiver row of the
        record its ``_inbound_gate_owner()`` names (itself by default; a
        ``(record, name, purpose)`` tuple names the receiver's purpose too)."""
        model_name, _, selector = declaration.partition(":")
        model = self.env[model_name].sudo()
        if selector in model._fields:
            value = path_args.get(selector)
            subject = (
                model.search([(selector, "=", value)], limit=1) if value else model
            )
            resolution = Resolution(subject)
        elif selector and callable(getattr(model, selector, None)):
            answer = getattr(model, selector)(
                **path_args, **({"receiver_event": event_type} if event_type else {})
            )
            if isinstance(answer, Resolution):
                resolution = answer
            elif isinstance(answer, tuple):
                resolution = Resolution(*answer)
            else:
                resolution = Resolution(answer)
        else:
            raise ValueError(
                f"receiver={declaration!r} names neither a field nor a method of "
                f"{model_name}"
            )
        subject = resolution.subject
        if not subject:
            return Resolution(
                model.browse(),
                resolution.extra,
                model.browse(),
                claimed=resolution.claimed,
            )
        if resolution.gate is None:
            if hasattr(subject, "admit"):
                resolution.gate = subject
            else:
                owner = getattr(subject, "_inbound_gate_owner", None)
                resolution.gate = owner() if owner is not None else subject
        if not hasattr(resolution.gate, "admit"):
            owner, name, purpose = (
                resolution.gate
                if isinstance(resolution.gate, tuple)
                else (resolution.gate, None, None)
            )
            resolution.gate = self.env["integration.receiver"]._for_record(
                owner, name or owner.display_name, purpose
            )
        return resolution

    def admit(
        self,
        subject=None,
        event_type: str | None = None,
        verify=None,
        event_id: str | None = None,
    ) -> Admission:
        self.check_singleton()
        gate = self
        if subject is not None and subject is not self:
            gate = gate.with_context(
                **{INBOUND_SUBJECT_KEY: (subject._name, subject.id)}
            )
        if verify is not None:
            gate = gate.with_context(**{INBOUND_VERIFY_KEY: verify})
        httprequest = request.httprequest
        remote_addr = httprequest.remote_addr
        content_length = httprequest.content_length
        limit = self._inbound_max_payload_size()
        if content_length and content_length > limit:
            self._record_inbound_verdict(
                False,
                413,
                f"payload too large for {self.display_name}",
                "payload_too_large",
                headers=dict(httprequest.headers),
                remote_addr=remote_addr,
            )
            raise Refused(
                413,
                f"Request exceeds maximum size of {limit // 1024}KB",
                "payload_too_large",
                detail={"limit_bytes": limit},
            )
        # A body past the limit is refused while it is still being read.
        httprequest.max_content_length = limit
        try:
            body = httprequest.get_data(cache=True)
        except RequestEntityTooLarge:
            self._record_inbound_verdict(
                False,
                413,
                f"payload too large for {self.display_name}",
                "payload_too_large",
                headers=dict(httprequest.headers),
                remote_addr=remote_addr,
            )
            raise Refused(
                413,
                f"Request exceeds maximum size of {limit // 1024}KB",
                "payload_too_large",
                detail={"limit_bytes": limit},
            ) from None
        # The verdict is written on its own cursor: a refusal raises, the
        # request rolls back, and the refusal must outlive that.
        with self.env.registry.cursor() as verdict_cr:
            verdict = gate.with_env(gate.env(cr=verdict_cr))._inbound_verdict(
                dict(httprequest.headers), body=body, remote_addr=remote_addr
            )
        if not verdict.allowed:
            raise Refused(verdict.status, verdict.reason, verdict.code)
        admission = Admission(
            gate=self,
            subject=subject or self,
            body=body,
            remote_addr=remote_addr,
            event_type=event_type,
            method=httprequest.method,
            path=httprequest.path,
            user_agent=httprequest.headers.get("User-Agent"),
            auth_mode="audit" if verdict.code == "audit_accepted" else "enforce",
            event_id=event_id,
        )
        admission.event_type = self._inbound_event_type(admission, event_type)
        if self._inbound_event_logged(admission.event_type):
            self._open_inbound_exchange(admission, admission.event_type)
        return admission

    def _inbound_event_type(
        self, admission: Admission, event_type: str | None
    ) -> str | None:
        """The event this call is, once the body can say more than the route
        did: a JSON-RPC method, a webhook's own type field."""
        return event_type

    def _inbound_event_logged(self, event_type: str | None) -> bool:
        """Whether an admitted call of this kind leaves a row. A poll that a
        reader repeats every few seconds is not worth one per repetition; its
        failure still is, and `Admission.settle` writes that one."""
        return True

    def _inbound_payload_logged(self, event_type: str | None) -> bool:
        """Whether the row keeps the body. A conversation's content is not
        the operator's to read; the hash of the body is kept either way."""
        return True

    def _inbound_event_id(
        self, admission: Admission, event_type: str | None
    ) -> str | None:
        """The sender's own id for this event, when it has one (a Telegram
        update_id, a Stripe event id): the row claims it, and a redelivery
        is refused as a duplicate while the first is processing or once it
        has been processed, whatever the body's bytes. A resolver that read
        the id hands it over on its `Resolution`; a gate that knows its
        sender's envelope overrides this."""
        return admission.event_id

    def _open_inbound_exchange(
        self, admission: Admission, event_type: str | None
    ) -> None:
        """The row is the call: created now, in the request's transaction,
        processing until the handler or the end of the request settles it,
        kept as a failed row when the request rolls back."""
        vals = self._inbound_exchange_vals(admission, event_type)
        Exchange = self.env["integration.exchange"].sudo()
        # The claim is the index's: what this transaction settled must be in
        # the table before the insert is judged against it.
        Exchange.flush_model()
        try:
            with self.env.cr.savepoint():
                exchange = Exchange.create(vals)
        except psycopg.errors.UniqueViolation:
            Exchange._record_refusal(
                self,
                "duplicate_event",
                f"event {vals['event_id_external']} already received",
                409,
                admission.remote_addr,
                user_agent=admission.user_agent,
                auth_mode=admission.auth_mode,
                company_id=vals["company_id"],
                method=admission.method,
                path=admission.path,
            )
            raise Refused(
                409, "Duplicate event detected", "duplicate_event", commit=True
            ) from None
        keep_row_on_rollback(self.env, vals, admission)
        admission.exchange = exchange

    def _inbound_exchange_vals(
        self, admission: Admission, event_type: str | None
    ) -> dict[str, Any]:
        return {
            "direction": "inbound",
            "channel_id": f"{self._name},{self.id}",
            "company_id": self._get_inbound_company_id() or False,
            "request_method": admission.method,
            "request_url": admission.path[:2048],
            "source_ip": admission.remote_addr or False,
            "user_agent": (admission.user_agent or "")[:512] or False,
            "event_type": event_type or False,
            "event_id_external": self._inbound_event_id(admission, event_type) or False,
            "state": "processing",
            "signature_verified": self.auth_type != "none"
            and admission.auth_mode != "audit",
            "auth_mode": admission.auth_mode,
            **self._inbound_payload_vals(admission, event_type),
            # The hash of the body as received, whatever the row keeps of it.
            "request_payload_hash_override": admission.payload_hash,
        }

    def _inbound_payload_vals(
        self, admission: Admission, event_type: str | None
    ) -> dict[str, Any]:
        if not self._inbound_payload_logged(event_type):
            return {}
        body = admission.body.decode("utf-8", errors="replace")
        return self._omitted_payload_vals(body) or self._prepare_inbound_payload_vals(
            body
        )

    def _omitted_payload_vals(self, body: str) -> dict[str, Any]:
        limit = self._payload_log_limit()
        size = len(body.encode("utf-8"))
        if not limit or size <= limit:
            return {}
        return {
            "request_payload": json.dumps(
                {
                    "_omitted": {
                        "bytes": size,
                        "reason": "larger than this endpoint's payload log limit",
                        "head": redact.mask_text(body, _OMITTED_PAYLOAD_HEAD_CHARS),
                    },
                },
            ),
            "request_payload_omitted_bytes": size,
        }

    def _payload_log_limit(self) -> int:
        self.check_singleton()
        return max(0, self.log_request_payload_max_bytes)

    def _inbound_auth_mode(self, parameter_key: str | None = None) -> str:
        return self.AUTH_MODE_ENFORCE

    def _check_inbound_request(
        self,
        headers: dict[str, Any],
        body: str | bytes | None = None,
        remote_addr: str | None = None,
        mode: str | None = None,
        caller_already_checked: bool = False,
    ) -> tuple[bool, int, str]:
        return self._inbound_verdict(
            headers,
            body=body,
            remote_addr=remote_addr,
            mode=mode,
            caller_already_checked=caller_already_checked,
        )[:3]

    def _inbound_verdict(
        self,
        headers: dict[str, Any],
        body: str | bytes | None = None,
        remote_addr: str | None = None,
        mode: str | None = None,
        caller_already_checked: bool = False,
    ) -> Verdict:
        """The gate's decision, recorded: `(allowed, status, reason, code)`,
        the code being the word the caller's problem document carries."""
        if mode is None:
            mode = self._inbound_auth_mode()
        verdict = Verdict(
            *self._decide_inbound_request(
                headers,
                body=body,
                remote_addr=remote_addr,
                mode=mode,
                caller_already_checked=caller_already_checked,
            )
        )
        self._record_inbound_verdict(
            verdict.allowed,
            verdict.status,
            verdict.reason,
            verdict.code,
            headers=headers,
            remote_addr=remote_addr,
            mode=mode,
        )
        return verdict

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
                    "caller_limited" if status == 429 else "ip_not_allowed",
                )

        if body is not None and len(body) > self._inbound_max_payload_size():
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
                    "rate_limit_exceeded",
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
            "authentication_failed",
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

        # A route's resolver may hand the gate the check itself -- a Basic
        # login on a bearer-keyed device, a signed link, a per-user API key
        # on a gate that holds no credential of its own -- and then that is
        # the identity for this call, whatever the gate's own scheme.
        verify = self.env.context.get(INBOUND_VERIFY_KEY)
        if verify is not None:
            return bool(verify(headers, body))

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
        limit = self._get_inbound_payload_log_bytes()
        # masked and cut in one pass that stops a byte past the limit, so a
        # large body costs what is kept; one byte more says it was cut
        bound = limit + 1 if limit else None
        try:
            masked = redact.dump_masked(json.loads(text), bound)
        except ValueError, TypeError:
            masked = redact.mask_text(text, bound)
        encoded = masked.encode("utf-8")
        if limit and len(encoded) > limit:
            return {
                "request_payload": encoded[:limit].decode("utf-8", errors="ignore"),
                "request_payload_omitted_bytes": max(
                    len(text.encode("utf-8")) - limit, 0
                ),
            }
        return {"request_payload": masked}

    def _presented_token(self, headers: dict[str, Any]) -> str:
        auth_header = headers.get("Authorization") or ""
        if auth_header[:7].lower() == "bearer ":
            return auth_header[7:].strip()
        return (headers.get("X-Device-Token") or "").strip()

    def _record_inbound_verdict(
        self,
        allowed: bool,
        status: int,
        reason: str,
        code: str,
        headers: Any = None,
        remote_addr: str | None = None,
        mode: str = AUTH_MODE_ENFORCE,
    ) -> None:
        """A refusal is an exchange row of the gate; an admission is recorded
        by the admission itself. An audit-mode admission and a misconfigured
        gate are standing conditions, reported once per window."""
        if mode == self.AUTH_MODE_OFF:
            return
        if allowed:
            if code == "audit_accepted" and self._standing_condition_is_news(code):
                _logger.warning(
                    "UNAUTHENTICATED request accepted for %s from %s (audit mode): "
                    "%s. Provision the credential, then switch to 'enforce'.",
                    self.display_name,
                    remote_addr,
                    reason,
                )
            return
        try:
            is_news = self._store_inbound_refusal(
                code,
                status,
                reason,
                headers=headers,
                remote_addr=remote_addr,
                mode=mode,
            )
        except Exception:
            _logger.exception(
                "Could not record the refusal for %s; the decision itself stands",
                self.display_name,
            )
            return
        if is_news and code == "misconfigured":
            _logger.error(
                "%s is refusing EVERY request and will keep doing so until it "
                "is fixed: %s. Callers see a 401, so this reads to them as "
                "their credentials being wrong.",
                self.display_name,
                reason,
            )

    # A caller's own limit collapses per caller and is counted; a gate's
    # standing fault collapses per gate and is not, because counting is an
    # UPDATE of a row every concurrent request shares.
    _COALESCED_REFUSALS = {
        "caller_limited": {"per_caller": True, "counted": True},
        "misconfigured": {"per_caller": False, "counted": False},
    }

    STANDING_WINDOW_PARAM = "credential.inbound_standing_window_seconds"
    STANDING_WINDOW_DEFAULT = 3600

    def _get_inbound_coalesce_window(self, code: str) -> int:
        """Return the caller-limit or standing-condition window in seconds."""
        if code == "caller_limited":
            return self.rate_limit_window_seconds or 60
        window = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param_int(self.STANDING_WINDOW_PARAM, self.STANDING_WINDOW_DEFAULT)
        )
        return max(60, window)

    def _standing_condition_is_news(self, code: str) -> bool:
        """Once per gate per window, without a row: the admission rows say
        `auth_mode = audit` for themselves."""
        key = (self.env.cr.dbname, self._name, self.id, code)
        now = time.monotonic()
        window = self._get_inbound_coalesce_window(code)
        reported = _STANDING_CONDITIONS_REPORTED.get(key)
        if reported is not None and now - reported < window:
            return False
        _STANDING_CONDITIONS_REPORTED[key] = now
        return True

    def _store_inbound_refusal(
        self,
        code: str,
        status: int,
        reason: str,
        headers: Any,
        remote_addr: str | None,
        mode: str,
    ) -> bool:
        collapse = self._COALESCED_REFUSALS.get(code, {})
        httprequest = request.httprequest if request else None
        return self.env["integration.exchange"]._record_refusal(
            self,
            code,
            reason,
            status,
            remote_addr,
            user_agent=(headers or {}).get("User-Agent"),
            auth_mode=mode,
            company_id=self._get_inbound_company_id(),
            window=self._get_inbound_coalesce_window(code) if collapse else 0,
            method=httprequest.method if httprequest else None,
            path=httprequest.path if httprequest else None,
            **collapse,
        )

    def _inbound_max_payload_size(self) -> int:
        """Return the largest body, in bytes, the gate admits.

        :return: the gate's own limit, or the field default when it has none
        :rtype: int
        """
        self.check_singleton()
        # A row that predates the field's default holds NULL, which reads as
        # 0. The limit exists against DoS and a receiver may not set it to 0,
        # so an empty one is the default -- neither "no limit" nor "0 bytes".
        return self.max_payload_size or DEFAULT_MAX_PAYLOAD_SIZE

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
