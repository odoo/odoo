import logging
from typing import Any
from urllib.parse import urlparse

import requests

from odoo.libs.debug_log import DebugLog
from odoo.libs.guarded_http import RefusedDestination

__all__ = ["RESPONSE_MAX_BYTES", "deliver", "get_log_target", "scrub_url"]

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)

RESPONSE_MAX_BYTES = 1024 * 1024


def get_log_target(url: str) -> str:
    try:
        return urlparse(url).hostname or "<unknown host>"
    except ValueError:
        return "<malformed URL>"


def scrub_url(message: str, url: str, target: str) -> str:
    parsed = urlparse(url)
    needles = [url]
    if parsed.query:
        needles.append(f"{parsed.path}?{parsed.query}")
    if len(parsed.path) > 1:
        needles.append(parsed.path)
    for needle in needles:
        message = message.replace(needle, f"<{target} webhook URL>")
    return message


def deliver(
    session: Any,
    url: str,
    timeout: float,
    action_label: str,
    target: str,
    json_values: bytes | str,
) -> None:
    _logger.debug("Webhook %s to %s - start", action_label, target)
    try:
        with _debug.perf("webhook_post", target=target, timeout=timeout):
            with session:
                response = session.post(
                    url,
                    data=json_values,
                    headers={"Content-Type": "application/json"},
                    timeout=timeout,
                    allow_redirects=False,
                )
        response.raise_for_status()
        _logger.info("Webhook %s to %s - succeeded", action_label, target)
        _debug.pipeline("webhook_delivered", target=target, status=response.status_code)
    except RefusedDestination as refusal:
        _debug.logic(
            "webhook_guard", phase="delivery", target=target, blocked=str(refusal)
        )
        _logger.error(
            "Webhook %s to %s was NOT sent: %s. The address was allowed when "
            "the action ran and is not any more -- the name resolved "
            "differently between the check and the send.",
            action_label,
            target,
            refusal,
        )
    except requests.exceptions.ReadTimeout:
        _debug.logic("webhook_failed", target=target, reason="timeout")
        _logger.warning(
            "Webhook %s to %s timed out after %ss. The receiver may or "
            "may not have processed it. Raise 'Webhook Timeout (s)' on "
            "the action if the receiver is simply slow; if delivery has "
            "to be certain, this action cannot give you that.",
            action_label,
            target,
            timeout,
        )
    except requests.exceptions.RequestException as e:
        _debug.logic("webhook_failed", target=target, reason=type(e).__name__)
        _logger.error(
            "Webhook %s to %s failed and will NOT be retried: %s",
            action_label,
            target,
            scrub_url(str(e), url, target),
        )
