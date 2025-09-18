"""
Security and cryptographic utilities for Odoo.

This module provides utilities for:
- HMAC computation with database secrets
- Signed token generation and verification (JWT-like)
- Field-level access token management
"""

import base64
import datetime
import hashlib
import hmac as hmac_lib
import time
import typing
import zlib
from collections.abc import Callable

from odoo.libs.json import dumps as json_dumps
from odoo.libs.json import loads as json_loads

if typing.TYPE_CHECKING:
    from odoo.api import Environment
    from odoo.orm._typing import BaseModel

# Constant-time string comparison (prevents timing attacks)
consteq = hmac_lib.compare_digest


def hmac(
    env: Environment,
    scope: str,
    message: typing.Any,
    hash_function: Callable = hashlib.sha256,
) -> str:
    """Compute HMAC with `database.secret` config parameter as key.

    Uses the database's secret key to compute an HMAC signature for
    authentication purposes. Different scopes ensure the same message
    produces different signatures in different contexts.

    :param env: sudo environment to use for retrieving config parameter
    :param scope: scope of the authentication, to have different signature
        for the same message in different usage contexts
    :param message: message to authenticate
    :param hash_function: hash function to use for HMAC (default: SHA-256)
    :return: hexadecimal digest of the HMAC
    :rtype: str
    :raises ValueError: if scope is empty
    """
    if not scope:
        raise ValueError("Non-empty scope required")

    secret = env["ir.config_parameter"].get_param("database.secret")
    message = repr((scope, message))
    return hmac_lib.new(
        secret.encode(),
        message.encode(),
        hash_function,
    ).hexdigest()


def hash_sign(
    env: Environment,
    scope: str,
    message_values: typing.Any,
    expiration: datetime.datetime | datetime.timedelta | None = None,
    expiration_hours: float | None = None,
) -> str:
    """Generate a URL-safe signed token with optional expiration.

    Creates a signed payload similar to JWT but using Odoo's HMAC
    implementation. The token includes the message values, expiration
    timestamp, and cryptographic signature.

    :param env: sudo environment to use for retrieving config parameter
    :param scope: scope of the authentication, to have different signature
        for the same message in different usage contexts
    :param message_values: values to be encoded inside the payload
        (must be JSON-serializable)
    :param expiration: optional datetime or timedelta for token expiration
    :param expiration_hours: optional number of hours before expiration
        (cannot be set at the same time as expiration)
    :return: URL-safe base64-encoded signed token
    :rtype: str
    :raises AssertionError: if both expiration and expiration_hours are set,
        or if message_values is None
    """
    assert not (expiration and expiration_hours)
    assert message_values is not None

    if expiration_hours:
        expiration = datetime.datetime.now() + datetime.timedelta(
            hours=expiration_hours
        )
    elif isinstance(expiration, datetime.timedelta):
        expiration = datetime.datetime.now() + expiration
    expiration_timestamp = 0 if not expiration else int(expiration.timestamp())
    message_strings = json_dumps(message_values)
    hash_value = hmac(
        env,
        scope,
        f"1:{message_strings}:{expiration_timestamp}",
        hash_function=hashlib.sha256,
    )
    token = (
        b"\x01"
        + expiration_timestamp.to_bytes(8, "little")
        + bytes.fromhex(hash_value)
        + message_strings.encode()
    )
    return base64.urlsafe_b64encode(token).decode().rstrip("=")


def verify_hash_signed(env: Environment, scope: str, payload: str) -> typing.Any | None:
    """Verify and extract data from a signed token.

    Validates the signature and expiration of a token generated
    by hash_sign(), returning the original message values if valid.

    :param env: sudo environment to use for retrieving config parameter
    :param scope: scope of the authentication (must match the scope
        used when the token was created)
    :param payload: the token to verify
    :return: the message_values if verification succeeds, None otherwise
    :raises ValueError: if the token version is unknown
    """
    token = base64.urlsafe_b64decode(payload.encode() + b"===")
    version = token[:1]
    if version != b"\x01":
        raise ValueError("Unknown token version")

    expiration_value, hash_value, message = (
        token[1:9],
        token[9:41].hex(),
        token[41:].decode(),
    )
    expiration_value = int.from_bytes(expiration_value, byteorder="little")
    hash_value_expected = hmac(
        env,
        scope,
        f"1:{message}:{expiration_value}",
        hash_function=hashlib.sha256,
    )

    if consteq(hash_value, hash_value_expected) and (
        expiration_value == 0 or datetime.datetime.now().timestamp() < expiration_value
    ):
        return json_loads(message)
    return None


def limited_field_access_token(
    record: BaseModel,
    field_name: str,
    timestamp: str | None = None,
    *,
    scope: str,
) -> str:
    """Generate a token granting access to a specific record field.

    Creates a time-limited access token for a specific record and field
    combination. Used to grant temporary access to resources without
    requiring full authentication.

    The validity of the token is determined by the timestamp parameter.
    When not specified, a timestamp is automatically generated with a
    validity of at least 14 days. For a given record and field_name, the
    generated timestamp is deterministic within a 14-day period to allow
    browser caching, and expires after maximum 42 days. Different
    record/field combinations expire at different times to prevent
    thundering herd problems.

    :param record: the record to generate the token for
    :type record: odoo.models.Model
    :param field_name: the field name to generate the token for
    :param timestamp: optional expiration timestamp (hex format),
        or None to generate automatically
    :param scope: scope of the authentication, to have different
        signatures for the same record/field in different contexts
    :return: the token, which includes the timestamp in hex format
    :rtype: str
    """
    record.ensure_one()
    if not timestamp:
        unique_str = repr((record._name, record.id, field_name))
        two_weeks = 1209600  # 2 * 7 * 24 * 60 * 60
        start_of_period = int(time.time()) // two_weeks * two_weeks
        adler32_max = 4294967295
        jitter = two_weeks * zlib.adler32(unique_str.encode()) // adler32_max
        timestamp = hex(start_of_period + 2 * two_weeks + jitter)
    token = hmac(
        record.env(su=True),
        scope,
        (record._name, record.id, field_name, timestamp),
    )
    return f"{token}o{timestamp}"


def verify_limited_field_access_token(
    record: BaseModel,
    field_name: str,
    access_token: str,
    *,
    scope: str,
) -> bool:
    """Verify a field access token.

    Validates that the given access token grants access to the
    specified record and field, and that the token has not expired.

    :param record: the record to verify the token for
    :type record: odoo.models.Model
    :param field_name: the field name to verify the token for
    :param access_token: the access token to verify
    :param scope: scope of the authentication (must match the scope
        used when the token was created)
    :return: whether the token is valid for the record/field at
        the current date and time
    :rtype: bool
    """
    *_, timestamp = access_token.rsplit("o", 1)
    return consteq(
        access_token,
        limited_field_access_token(record, field_name, timestamp, scope=scope),
    ) and datetime.datetime.now() < datetime.datetime.fromtimestamp(int(timestamp, 16))
