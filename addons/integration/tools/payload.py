import hashlib
import json
import math
from collections import deque
from typing import Any

from odoo.libs import redact

from .exceptions import ClientError
from odoo.addons.credential.tools import check_json_depth


def inspect_payload_size(
    payload_bytes: bytes,
    max_size_bytes: int,
) -> tuple[bool, str | None]:
    payload_size = len(payload_bytes)

    if payload_size > max_size_bytes:
        return (
            False,
            (
                f"Payload too large: {payload_size} bytes exceeds maximum of "
                f"{max_size_bytes} bytes ({max_size_bytes // 1024}KB)"
            ),
        )

    return True, None


def inspect_content_type(
    content_type: str | None,
    expected: str = "application/json",
) -> tuple[bool, str | None]:
    if not content_type:
        return False, "Missing Content-Type header"

    main_type = content_type.split(";")[0].strip().lower()

    if main_type != expected.lower():
        return (
            False,
            f"Invalid Content-Type: expected '{expected}', got '{content_type}'",
        )

    return True, None


def redact_error_message(error: str | Exception, max_length: int = 500) -> str:
    message = str(error)

    if len(message) > max_length:
        message = message[:max_length] + "... (truncated)"

    return redact.mask_text(message)


def compute_payload_hash(payload: dict | str | Any) -> str:
    if isinstance(payload, dict):
        normalized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    elif isinstance(payload, str):
        try:
            parsed = json.loads(payload)
            normalized = json.dumps(parsed, sort_keys=True, separators=(",", ":"))
        except json.JSONDecodeError, ValueError:
            normalized = payload
    else:
        normalized = json.dumps(payload, sort_keys=True, separators=(",", ":"))

    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def inspect_json_payload(
    body: str,
    max_depth: int = 100,
) -> tuple[bool, dict | None, str | None]:
    if not body or not body.strip():
        return False, None, "Empty payload"

    try:
        parsed = json.loads(body)
        check_json_depth(parsed, max_depth)
        return True, parsed, None
    except json.JSONDecodeError as e:
        return False, None, f"Invalid JSON: {e}"
    except ValueError:
        return (
            False,
            None,
            f"Payload exceeds maximum nesting depth of {max_depth}",
        )
    except Exception as e:
        return False, None, f"Payload validation error: {e}"


def split_large_payload(
    data: list | dict | Any,
    max_size: int = 1024 * 1024,
) -> list:
    if not data:
        return []

    if not isinstance(data, list):
        payload = json.dumps(data)
        payload_size = len(payload.encode())
        if payload_size >= max_size:
            raise ClientError(
                f"Single payload exceeds max size: {payload_size} bytes "
                f"(limit: {max_size} bytes)",
            )
        return [data]

    queue = deque([data])
    results = []

    while queue:
        chunk = queue.popleft()

        if not chunk:
            continue

        if len(chunk) == 1:
            payload = json.dumps(chunk)
            payload_size = len(payload.encode())
            if payload_size >= max_size:
                raise ClientError(
                    f"Single item in list exceeds max size: {payload_size} bytes "
                    f"(limit: {max_size} bytes). Cannot split further.",
                )
            results.append(chunk)
            continue

        payload = json.dumps(chunk)
        if len(payload.encode()) < max_size:
            results.append(chunk)
        else:
            pivot = math.ceil(len(chunk) / 2)
            queue.append(chunk[:pivot])
            queue.append(chunk[pivot:])

    return results
