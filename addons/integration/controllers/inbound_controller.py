import json
import logging
from typing import Any

from odoo import fields
from odoo.http import request

from .base_controller import BaseCommController, ValidationResult
from odoo.addons.integration.tools import (
    compute_payload_hash,
    inspect_json_payload,
)

_logger = logging.getLogger(__name__)

_OMITTED_PAYLOAD_HEAD_CHARS = 512


class InboundController(BaseCommController):
    def _get_identifier_field(self, endpoint_model: str) -> str:
        return "identifier"

    def _mark_stored(self, result: ValidationResult) -> None:
        """Close the request's event log as a success; a sync endpoint's retry
        cron otherwise warns about it on every run until it is garbage-collected."""
        if result.event_log:
            result.event_log.sudo().mark_success()

    def _mark_refused(self, result: ValidationResult, reason: str) -> None:
        if result.event_log:
            result.event_log.sudo().mark_failed(reason, schedule_retry=False)

    def _payload_too_large(self, endpoint: Any) -> ValidationResult:
        _logger.warning(
            "Payload too large for endpoint %s (limit: %d bytes)",
            endpoint.display_name,
            endpoint.max_payload_size,
        )
        return ValidationResult(
            success=False,
            response=self._json_response(
                {
                    "error": "payload_too_large",
                    "message": "Request exceeds maximum size of "
                    f"{endpoint.max_payload_size // 1024}KB",
                    "limit_bytes": endpoint.max_payload_size,
                },
                status=413,
            ),
            error_message="Payload too large",
        )

    def inspect_inbound_request(  # pylint: disable=too-many-return-statements
        self,
        endpoint_model: str,
        endpoint_identifier: str,
        endpoint_domain: list | None = None,
        require_json: bool = True,
        check_rate_limit: bool = True,
        check_duplicates: bool = True,
        create_event_log: bool = True,
    ) -> ValidationResult:
        start_time = fields.Datetime.now()
        remote_addr = self._get_remote_address()

        candidates = self._find_endpoints(
            endpoint_model, endpoint_identifier, endpoint_domain
        )
        if not candidates:
            return self._refuse_unknown_endpoint(
                endpoint_model, endpoint_identifier, remote_addr
            )
        endpoint = candidates[:1]

        refusal = self._refuse_declared_oversize(endpoint) or self._refuse_caller(
            endpoint, remote_addr, check_rate_limit
        )
        if refusal:
            return refusal

        body_bytes = request.httprequest.get_data(as_text=False)
        if len(body_bytes) > endpoint.max_payload_size:
            return self._payload_too_large(endpoint)
        body_str = body_bytes.decode("utf-8", errors="replace")

        endpoint, refusal = self._authenticate(
            candidates,
            body_bytes,
            remote_addr,
            endpoint_model,
            endpoint_identifier,
        )
        if refusal:
            return refusal

        payload_dict, payload_hash, refusal = self._read_payload(body_str, require_json)
        if refusal:
            return refusal

        event_log = self._open_event_log(
            endpoint, body_str, remote_addr, create_event_log, payload_hash
        )

        refusal = self._refuse_duplicate(
            endpoint, payload_hash, event_log, check_duplicates
        )
        if refusal:
            return refusal

        duration = (fields.Datetime.now() - start_time).total_seconds()
        _logger.debug(
            "Request validated in %.3fs for %s",
            duration,
            endpoint.display_name,
        )

        return ValidationResult(
            success=True,
            endpoint=endpoint,
            payload=payload_dict,
            payload_hash=payload_hash,
            event_log=event_log,
        )

    def _find_endpoints(
        self,
        endpoint_model: str,
        endpoint_identifier: str,
        endpoint_domain: list | None,
    ) -> Any:
        identifier_field = self._get_identifier_field(endpoint_model)
        domain = [
            *(endpoint_domain or []),
            (identifier_field, "=", endpoint_identifier),
            ("active", "=", True),
        ]
        return request.env[endpoint_model].sudo().search(domain)

    def _refuse_unknown_endpoint(
        self,
        endpoint_model: str,
        endpoint_identifier: str,
        remote_addr: str | None = None,
    ) -> ValidationResult:
        _logger.warning(
            "Endpoint not found: %s with %s=%s",
            endpoint_model,
            self._get_identifier_field(endpoint_model),
            endpoint_identifier,
        )
        request.env["inbound.access.log"]._record_unknown_caller(
            endpoint_model,
            endpoint_identifier,
            remote_addr,
            user_agent=request.httprequest.headers.get("User-Agent"),
        )
        return ValidationResult(
            success=False,
            response=self._error_response(
                "endpoint_not_found",
                "Endpoint not found or inactive",
                404,
            ),
            error_message="Endpoint not found",
        )

    def _refuse_declared_oversize(self, endpoint: Any) -> ValidationResult | None:
        content_length = request.httprequest.content_length
        if content_length and content_length > endpoint.max_payload_size:
            return self._payload_too_large(endpoint)
        return None

    def _refuse_caller(
        self, endpoint: Any, remote_addr: str, check_rate_limit: bool
    ) -> ValidationResult | None:
        allowed, status, reason = endpoint._check_inbound_caller(remote_addr)
        if allowed:
            return None
        if status == 429 and not check_rate_limit:
            return None
        _logger.warning("Refused %s: %s", endpoint.display_name, reason)
        code, message = (
            ("ip_not_allowed", "Your IP address is not authorized")
            if status == 403
            else ("rate_limit_exceeded", "Too many requests - please slow down")
        )
        return ValidationResult(
            success=False,
            response=self._error_response(code, message, status),
            error_message=reason,
        )

    def _authenticate(
        self,
        candidates: Any,
        body_bytes: bytes,
        remote_addr: str,
        endpoint_model: str,
        endpoint_identifier: str,
    ) -> tuple[Any, ValidationResult | None]:
        headers = dict(request.httprequest.headers)
        last_reason = None
        for candidate in candidates:
            try:
                allowed, status, reason = candidate._check_inbound_request(
                    headers,
                    body=body_bytes,
                    remote_addr=remote_addr,
                    caller_already_checked=True,
                )
                if allowed:
                    return candidate, None
                last_reason = reason
                if status == 429:
                    return candidate, ValidationResult(
                        success=False,
                        response=self._error_response(
                            "rate_limit_exceeded",
                            "Too many requests - please slow down",
                            429,
                        ),
                        error_message=reason,
                    )
            except Exception as e:
                last_reason = str(e)
                _logger.exception(
                    "Authentication error for %s %s",
                    endpoint_model,
                    endpoint_identifier,
                )

        _logger.warning(
            "Authentication failed for %s %s: %s",
            endpoint_model,
            endpoint_identifier,
            last_reason or "no candidate verified",
        )
        return candidates[:1], ValidationResult(
            success=False,
            response=self._error_response(
                "authentication_failed",
                "Invalid credentials",
                401,
            ),
            error_message=last_reason or "Authentication failed",
        )

    def _read_payload(
        self, body_str: str, require_json: bool
    ) -> tuple[dict | None, str | None, ValidationResult | None]:
        if not require_json:
            return None, None, None

        is_valid, payload_dict, error = inspect_json_payload(body_str)
        if not is_valid:
            _logger.warning("Invalid JSON payload: %s", error)
            return (
                None,
                None,
                ValidationResult(
                    success=False,
                    response=self._error_response("invalid_json", error, 400),
                    error_message=error,
                ),
            )
        return payload_dict, compute_payload_hash(payload_dict), None

    def _open_event_log(
        self,
        endpoint: Any,
        body_str: str,
        remote_addr: str,
        create_event_log: bool,
        payload_hash: str | None = None,
    ) -> Any:
        if not create_event_log:
            return None
        vals = {
            "direction": "inbound",
            "channel_id": f"{endpoint._name},{endpoint.id}",
            "request_payload": body_str,
            "source_ip": remote_addr,
            "state": "pending",
        }
        vals.update(self._payload_log_vals(endpoint, body_str, payload_hash))
        return request.env["integration.exchange"].sudo().create(vals)

    def _payload_log_vals(
        self, endpoint: Any, body_str: str, payload_hash: str | None
    ) -> dict:
        limit = endpoint._payload_log_limit()
        size = len(body_str.encode("utf-8"))
        if not limit or size <= limit:
            return {}
        _logger.info(
            "Body of %d bytes exceeds the %d-byte log limit for endpoint %s; "
            "storing a placeholder in its stead",
            size,
            limit,
            endpoint.display_name,
        )
        return {
            "request_payload": json.dumps(
                {
                    "_omitted": {
                        "bytes": size,
                        "reason": "larger than this endpoint's payload log limit",
                        "head": body_str[:_OMITTED_PAYLOAD_HEAD_CHARS],
                    },
                },
            ),
            "request_payload_hash_override": payload_hash or False,
            "request_payload_omitted_bytes": size,
        }

    def _refuse_duplicate(
        self,
        endpoint: Any,
        payload_hash: str | None,
        event_log: Any,
        check_duplicates: bool,
    ) -> ValidationResult | None:
        if not (
            check_duplicates
            and endpoint.duplicate_detection_enabled
            and payload_hash
            and event_log
        ):
            return None
        if not endpoint.check_duplicate_event(
            payload_hash, exclude_event_id=event_log.id
        ):
            return None

        _logger.info(
            "Duplicate event detected for endpoint %s (event %d)",
            endpoint.display_name,
            event_log.id,
        )
        event_log.mark_duplicate()
        return ValidationResult(
            success=False,
            response=self._error_response(
                "duplicate_event",
                "Duplicate event detected",
                409,
            ),
            error_message="Duplicate event",
        )
