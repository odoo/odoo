# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging as logger
import os
import struct
import textwrap

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from urllib.parse import urlsplit

from . import jwt

MAX_PAYLOAD_SIZE = 4096

# size of the overhead of the header for all encryption blocks
# +-----------+-----------------+---------------------------+------------------------+
# | salt (16) | record_size (4) | sender_public_key.len (1) | sender_public_key (65) |
# +-----------+-----------------+---------------------------+------------------------+
# sender_public_key = 0x04 (1 byte) | X-coord (32 bytes) | Y-coord (32 bytes)
# using SECP256R1 curve + X9.62 encoding + SEC1 uncompressed formatting
ENCRYPTION_HEADER_SIZE = 16 + 4 + 1 + (1 + 32 + 32)

# size of the overhead of encryption per encryption block
# 1 padding delimiter (continue or final block) + 16-bytes in-message authentication tag from AEAD_AES_128_GCM
ENCRYPTION_BLOCK_OVERHEAD = 1 + 16

class PUSH_NOTIFICATION_TYPE:
    CALL = "CALL"
    CANCEL = "CANCEL"


class PUSH_NOTIFICATION_ACTION:
    ACCEPT = "ACCEPT"
    DECLINE = "DECLINE"


_logger = logger.getLogger(__name__)


# ------------------------------------------------------------
# Errors specific to web push
# ------------------------------------------------------------

class DeviceUnreachableError(Exception):
    pass

# ------------------------------------------------------------
# Web Push
# ------------------------------------------------------------

def _iv(base, counter):
    mask = int.from_bytes(base[4:], 'big')
    return base[:4] + (counter ^ mask).to_bytes(8, 'big')

def _derive_key(salt, private_key, device):
    # browser keys
    device_keys = json.loads(device["keys"])
    p256dh = jwt.base64_decode_with_padding(device_keys.get('p256dh'))
    auth = jwt.base64_decode_with_padding(device_keys.get('auth'))

    # generate a public key derived from the browser public key
    pub_key = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), p256dh)
    sender_pub_key = private_key.public_key().public_bytes(
        Encoding.X962, PublicFormat.UncompressedPoint
    )

    context = b"WebPush: info\x00" + p256dh + sender_pub_key
    key_info = b"Content-Encoding: aes128gcm\x00"
    nonce_info = b"Content-Encoding: nonce\x00"

    # Create the 3 HKDF keys needed to encrypt the message (auth, key, nonce)
    hkdf_auth = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=auth,
        info=context,
        backend=default_backend(),
    )
    hkdf_key = HKDF(
        algorithm=hashes.SHA256(),
        length=16,
        salt=salt,
        info=key_info,
        backend=default_backend(),
    )
    hkdf_nonce = HKDF(
        algorithm=hashes.SHA256(),
        length=12,
        salt=salt,
        info=nonce_info,
        backend=default_backend(),
    )
    secret = hkdf_auth.derive(private_key.exchange(ec.ECDH(), pub_key))
    return hkdf_key.derive(secret), hkdf_nonce.derive(secret)

def _encrypt_payload(content, device, record_size=MAX_PAYLOAD_SIZE):
    """
    Encrypt a payload for Push Notification Endpoint using AES128GCM

    https://www.rfc-editor.org/rfc/rfc7516
    https://www.rfc-editor.org/rfc/rfc8188
    :param content: the unencrypted payload
    :param device: the web push user browser information
    :param record_size: record size must be bigger than 18
    :return: the encrypted payload
    """
    # The private_key is an ephemeral ECDH key used only for a transaction
    private_key = ec.generate_private_key(ec.SECP256R1(), default_backend())
    salt = os.urandom(16)
    # generate key
    (key, nonce) = _derive_key(salt=salt, private_key=private_key, device=device)
    # AEAD_AES_128_GCM produces ciphertext 16 octets longer than its input plaintext.
    # Therefore, the unencrypted content of each record is shorter than the record size by 16 octets.
    # Valid records always contain at least a padding delimiter octet and a 16-octet authentication tag.
    overhead = 1 + 16
    chunk_size = record_size - overhead

    body = b""
    end = len(content)
    aesgcm = AESGCM(key)
    for i in range(0, end, chunk_size):
        padding = b"\x02" if (i + chunk_size) >= end else b"\x01"
        body += aesgcm.encrypt(nonce, content[i: i + chunk_size] + padding, None)

    sender_public_key = private_key.public_key().public_bytes(
        Encoding.X962, PublicFormat.UncompressedPoint
    )

    # +-----------+-----------------+---------------------------+-------------------------------------------+
    # | salt (16) | record_size (4) | sender_public_key.len (1) | sender_public_key (sender_public_key.len) |
    # +-----------+-----------------+---------------------------+-------------------------------------------+
    header = struct.pack("!16sLB", salt, record_size, len(sender_public_key))
    header += sender_public_key
    return header + body

def push_to_end_point(base_url, device, payload, vapid_private_key, vapid_public_key, session):
    """
    https://www.rfc-editor.org/rfc/rfc8291
    """
    endpoint = device["endpoint"]
    url = urlsplit(endpoint)
    # The TDL ".invalid" is intended for use in online construction of domain names that are sure to be invalid and
    # which it is obvious at a glance are invalid.
    # https://datatracker.ietf.org/doc/html/rfc2606#section-2
    if url.netloc.endswith(".invalid"):
        raise DeviceUnreachableError("Device Unreachable")
    jwt_claims = {
        # aud: The “Audience” is a JWT construct that indicates the recipient scheme and host
        # e.g. for an endpoint like https://updates.push.services.mozilla.com/wpush/v2/gAAAAABY...,
        #      the “aud” would be https://updates.push.services.mozilla.com
        'aud': '{}://{}'.format(url.scheme, url.netloc),
        # sub: the sub value needs to be either a URL address. This is so that if a push service needed to reach out
        # to sender, it can find contact information from the JWT.
        'sub': base_url,
    }
    token = jwt.sign(jwt_claims, vapid_private_key, ttl=12 * 60 * 60, algorithm=jwt.Algorithm.ES256)
    body_payload = payload.encode()
    payload = _encrypt_payload(body_payload, device)
    headers = {
        #  Authorization header field contains these parameters:
        #  - "t" is the JWT;
        #  - "k" the base64url-encoded key that signed that token.
        'Authorization': 'vapid t={}, k={}'.format(token, vapid_public_key),
        'Content-Encoding': 'aes128gcm',
        # The TTL is set to '60' as workaround because the push notifications
        # are not received on Edge with TTL ='0'.
        # Using the TTL '0' , the microsoft endpoint returns a 400 bad request error.
        # and we are sure that the notification will be received
        'TTL': '60',
    }

    response = session.post(endpoint, headers=headers, data=payload, timeout=5)
    if response.status_code == 201:
        _logger.debug('Sent push notification %s', endpoint)
    else:
        error_message_shorten = textwrap.shorten(response.text, 100)
        _logger.warning('Failed push notification %s %d - %s',
                        endpoint, response.status_code, error_message_shorten)

        # Invalid subscription
        if response.status_code == 404 or response.status_code == 410:
            raise DeviceUnreachableError("Device Unreachable")
