import json
import logging as logger
import os
import struct
import textwrap
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import urlsplit

import requests
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from odoo.libs.debug_log import DebugLog
from odoo.libs.guarded_http import RefusedDestination

from . import jwt

MAX_PAYLOAD_SIZE = 4096

PUSH_RESPONSE_MAX_BYTES = 64 * 1024

ENCRYPTION_HEADER_SIZE = 16 + 4 + 1 + (1 + 32 + 32)

ENCRYPTION_BLOCK_OVERHEAD = 1 + 16

P256DH_UNCOMPRESSED_POINT_SIZE = 65
P256DH_UNCOMPRESSED_POINT_PREFIX = 0x04
AUTH_SECRET_SIZE = 16


class PUSH_NOTIFICATION_TYPE:
    CALL = "CALL"
    CANCEL = "CANCEL"


class PUSH_NOTIFICATION_ACTION:
    ACCEPT = "ACCEPT"
    DECLINE = "DECLINE"


_logger = logger.getLogger(__name__)
_debug = DebugLog(__name__)


class DeviceUnreachableError(Exception):
    pass


class PushEndpointUnresolvableError(Exception):
    def __init__(self, message: str, retry_after: timedelta | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


def decode_browser_keys(keys: Any) -> tuple[bytes, bytes]:
    if not isinstance(keys, dict):
        raise ValueError("browser keys must be a mapping with p256dh and auth")
    try:
        p256dh = jwt.base64_decode_with_padding(keys.get("p256dh") or "")
        auth = jwt.base64_decode_with_padding(keys.get("auth") or "")
    except (TypeError, ValueError) as error:
        raise ValueError("browser keys are not base64url encoded") from error
    if (
        len(p256dh) != P256DH_UNCOMPRESSED_POINT_SIZE
        or p256dh[0] != P256DH_UNCOMPRESSED_POINT_PREFIX
    ):
        raise ValueError("p256dh is not an uncompressed P-256 point")
    if len(auth) != AUTH_SECRET_SIZE:
        raise ValueError("auth is not a 16 byte secret")
    return p256dh, auth


def _retry_after(response: requests.Response) -> timedelta | None:
    value = response.headers.get("Retry-After")
    if not value:
        return None
    try:
        seconds = int(value)
    except ValueError:
        try:
            seconds = (parsedate_to_datetime(value) - datetime.now(UTC)).total_seconds()
        except TypeError, ValueError:
            return None
    return timedelta(seconds=max(seconds, 0))


def _iv(base: bytes, counter: int) -> bytes:
    mask = int.from_bytes(base[4:], "big")
    return base[:4] + (counter ^ mask).to_bytes(8, "big")


def _get_key_and_nonce(
    salt: bytes,
    private_key: ec.EllipticCurvePrivateKey,
    device: dict[str, Any],
) -> tuple[bytes, bytes]:
    p256dh, auth = decode_browser_keys(json.loads(device["keys"]))

    pub_key = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), p256dh)
    sender_pub_key = private_key.public_key().public_bytes(
        Encoding.X962, PublicFormat.UncompressedPoint
    )

    context = b"WebPush: info\x00" + p256dh + sender_pub_key
    key_info = b"Content-Encoding: aes128gcm\x00"
    nonce_info = b"Content-Encoding: nonce\x00"

    hkdf_auth = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=auth,
        info=context,
    )
    hkdf_key = HKDF(
        algorithm=hashes.SHA256(),
        length=16,
        salt=salt,
        info=key_info,
    )
    hkdf_nonce = HKDF(
        algorithm=hashes.SHA256(),
        length=12,
        salt=salt,
        info=nonce_info,
    )
    secret = hkdf_auth.derive(private_key.exchange(ec.ECDH(), pub_key))
    return hkdf_key.derive(secret), hkdf_nonce.derive(secret)


def _encrypt_payload(
    content: bytes, device: dict[str, Any], record_size: int = MAX_PAYLOAD_SIZE
) -> bytes:
    private_key = ec.generate_private_key(ec.SECP256R1())
    salt = os.urandom(16)
    (key, nonce) = _get_key_and_nonce(salt=salt, private_key=private_key, device=device)
    overhead = 1 + 16
    chunk_size = record_size - overhead

    body = b""
    end = len(content)
    aesgcm = AESGCM(key)
    for seq, i in enumerate(range(0, end, chunk_size)):
        padding = b"\x02" if (i + chunk_size) >= end else b"\x01"
        body += aesgcm.encrypt(
            _iv(nonce, seq), content[i : i + chunk_size] + padding, None
        )

    sender_public_key = private_key.public_key().public_bytes(
        Encoding.X962, PublicFormat.UncompressedPoint
    )

    header = struct.pack("!16sLB", salt, record_size, len(sender_public_key))
    header += sender_public_key
    return header + body


def get_push_session(env: Any) -> requests.Session:
    return env["ir.egress"].session(
        purpose="web_push", max_bytes=PUSH_RESPONSE_MAX_BYTES
    )


def push_to_end_point(
    base_url: str,
    device: dict[str, Any],
    payload: str,
    vapid_private_key: str,
    vapid_public_key: str,
    session: requests.Session,
) -> None:
    endpoint = device["endpoint"]
    url = urlsplit(endpoint)
    if (url.hostname or "").endswith(".invalid"):
        _debug.logic("push_refused", device=device.get("id"), reason="invalid_host")
        raise DeviceUnreachableError("Device Unreachable")
    jwt_claims = {
        "aud": f"{url.scheme}://{url.netloc}",
        "sub": base_url,
    }
    token = jwt.sign(
        jwt_claims, vapid_private_key, ttl=12 * 60 * 60, algorithm=jwt.Algorithm.ES256
    )
    body_payload = payload.encode()
    try:
        encrypted_payload = _encrypt_payload(body_payload, device)
    except (TypeError, ValueError) as error:
        raise DeviceUnreachableError("Device keys cannot be used") from error
    headers = {
        "Authorization": f"vapid t={token}, k={vapid_public_key}",
        "Content-Encoding": "aes128gcm",
        "TTL": "60",
    }

    with _debug.perf(
        "push_posted",
        device=device.get("id"),
        host=url.hostname,
        payload=len(body_payload),
        encrypted=len(encrypted_payload),
    ) as span:
        try:
            response = session.post(
                endpoint,
                headers=headers,
                data=encrypted_payload,
                timeout=5,
                allow_redirects=False,
            )
        except RefusedDestination as refusal:
            reason = "unresolvable" if refusal.unresolvable else "blocked_host"
            _debug.logic("push_refused", device=device.get("id"), reason=reason)
            if refusal.unresolvable:
                raise PushEndpointUnresolvableError(endpoint) from None
            raise DeviceUnreachableError("Device Unreachable") from None
        span.set(status=getattr(response, "status_code", None))
    if response.status_code == 201:
        _logger.debug("Sent push notification %s", endpoint)
    else:
        error_message_shorten = textwrap.shorten(response.text, 100)
        _logger.warning(
            "Failed push notification %s %d - %s",
            endpoint,
            response.status_code,
            error_message_shorten,
        )

        if response.status_code in {404, 410}:
            raise DeviceUnreachableError("Device Unreachable")
        if response.status_code == 429 or response.status_code >= 500:
            raise PushEndpointUnresolvableError(
                f"Push endpoint answered {response.status_code}",
                retry_after=_retry_after(response),
            )
