# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import hashlib
import json
import binascii
import time
import enum
import hmac

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, utils

# ------------------------------------------------------------
# Errors specific to JWT
# ------------------------------------------------------------

class InvalidVapidError(Exception):
    pass

# ------------------------------------------------------------
# JWT
# ------------------------------------------------------------

class Algorithm(enum.Enum):
    ES256 = "ES256"  # ECDSA SHA-256
    HS256 = "HS256"  # HMAC SHA-256


def _generate_keys(key_encoding, key_format) -> (bytes, bytes):
    private_object = ec.generate_private_key(ec.SECP256R1(), default_backend())
    private_int = private_object.private_numbers().private_value
    private_bytes = private_int.to_bytes(32, "big")
    public_object = private_object.public_key()
    public_bytes = public_object.public_bytes(
        encoding=key_encoding,
        format=key_format,
    )
    return private_bytes, public_bytes


def generate_vapid_keys() -> (str, str):
    """
    Generate the VAPID (Voluntary Application Server Identification) used for the Web Push
    This function generates a signing key pair usable with the Elliptic Curve Digital
    Signature Algorithm (ECDSA) over the P-256 curve.
    https://www.rfc-editor.org/rfc/rfc8292

    :return: tuple (private_key, public_key)
    """
    private, public = _generate_keys(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    private_string = base64.urlsafe_b64encode(private).decode("ascii").strip("=")
    public_string = base64.urlsafe_b64encode(public).decode("ascii").strip("=")
    return private_string, public_string


def base64_decode_with_padding(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "==")


def _generate_jwt(claims: dict, key: str, algorithm: Algorithm) -> str:
    JOSE_header = base64.urlsafe_b64encode(json.dumps({"typ": "JWT", "alg": algorithm.value}).encode())
    payload = base64.urlsafe_b64encode(json.dumps(claims).encode())
    unsigned_token = "{}.{}".format(JOSE_header.decode().strip("="), payload.decode().strip("="))
    key_decoded = base64_decode_with_padding(key)

    match algorithm:
        case Algorithm.HS256:
            signature = hmac.new(key_decoded, unsigned_token.encode(), hashlib.sha256).digest()
            sig = base64.urlsafe_b64encode(signature)
        case Algorithm.ES256:
            # Retrieve the private key using a P256 elliptic curve
            private_key = ec.derive_private_key(
                int(binascii.hexlify(key_decoded), 16), ec.SECP256R1(), default_backend()
            )
            signature = private_key.sign(unsigned_token.encode(), ec.ECDSA(hashes.SHA256()))
            (r, s) = utils.decode_dss_signature(signature)
            sig = base64.urlsafe_b64encode(r.to_bytes(32, "big") + s.to_bytes(32, "big"))
        case _:
            raise ValueError(f"Unsupported algorithm: {algorithm}")

    return "{}.{}".format(unsigned_token, sig.decode().strip("="))


def sign(claims: dict, key: str, ttl: int, algorithm: Algorithm) -> str:
    """
    A JSON Web Token is a signed pair of JSON objects, turned into base64 strings.

    RFC: https://www.rfc-editor.org/rfc/rfc7519

    :param claims: the payload of the jwt: https://www.rfc-editor.org/rfc/rfc7519#section-4.1
    :param key: base64 string
    :param ttl: the time to live of the token in seconds ('exp' claim)
    :param algorithm: to use to sign the token
    :return: JSON Web Token
    """
    non_padded_key = key.strip("=")
    assert ttl
    claims["exp"] = int(time.time()) + ttl
    return _generate_jwt(claims, non_padded_key, algorithm=algorithm)
