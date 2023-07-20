# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
import binascii
import json
import logging as logger
import os
import struct
import textwrap
import time

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, utils
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from urllib.parse import urlparse

MAX_PAYLOAD_SIZE = 4096

_logger = logger.getLogger(__name__)

def _base64_decode_with_padding(value):
    return base64.urlsafe_b64decode(value + '==')

def generate_web_push_vapid_key():
    """
    Generate the VAPID (Voluntary Application Server Identification) used for the Web Push
    This function generates a signing key pair usable with the Elliptic Curve Digital
    Signature Algorithm (ECDSA) over the P-256 curve.
    These keys will be used during communication with the endpoint/browser
    https://www.rfc-editor.org/rfc/rfc8292
    """
    private_key = ec.generate_private_key(ec.SECP256R1(), default_backend())
    private_int = private_key.private_numbers().private_value
    private = private_int.to_bytes(32, 'big')
    private_string = base64.urlsafe_b64encode(private).decode('ascii').strip('=')

    public_key = private_key.public_key()
    public = public_key.public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.UncompressedPoint
    )
    public_string = base64.urlsafe_b64encode(public).decode('ascii').strip('=')
    return private_string, public_string

def _generate_jwt(endpoint, base_url, vapid_private_key):
    """
    JWT are a pair of JSON objects, turned into base64 strings, and signed with the private ECDH key
    https://www.rfc-editor.org/rfc/rfc7519
    https://www.rfc-editor.org/rfc/rfc8291
    :param endpoint: the browser endpoint
    :param base_url: the base url
    :param vapid_private_key: the private ECDH key generate at mail_entreprise install
    :return:
    """
    url = urlparse(endpoint)

    jwt_info = base64.urlsafe_b64encode(json.dumps({
        'typ': 'JWT',
        'alg': 'ES256'
    }).encode())

    # The expiration is a timestamp in seconds and must be no longer 12 hours.
    token_validity = 12 * 60 * 60

    jwt_data = base64.urlsafe_b64encode(json.dumps({
        # aud: The “Audience” is a JWT construct that indicates the recipient scheme and host
        # e.g. for an endpoint like https://updates.push.services.mozilla.com/wpush/v2/gAAAAABY...,
        #      the “aud” would be https://updates.push.services.mozilla.com
        'aud': '{}://{}'.format(url.scheme, url.netloc),
        # sub: the sub value needs to be either a URL address. This is so that if a push service needed to reach out
        # to sender, it can find contact information from the JWT.
        'sub': base_url,
        # exp: It's the expiration of the JWT, this prevents snoopers from being able to re-use a JWT if they intercept it.
        'exp': int(time.time()) + token_validity
    }).encode())

    unsigned_token = '{}.{}'.format(jwt_info.decode().strip('='), jwt_data.decode().strip('='))

    # Retrieve the private key using a P256 elliptic curve
    vapid_private_key_decoded = _base64_decode_with_padding(vapid_private_key)
    private_key = ec.derive_private_key(int(binascii.hexlify(vapid_private_key_decoded), 16), ec.SECP256R1(), default_backend())

    # sign with ECDSA SHA-256
    signature = private_key.sign(unsigned_token.encode(), ec.ECDSA(hashes.SHA256()))
    (r, s) = utils.decode_dss_signature(signature)
    sig = base64.urlsafe_b64encode(r.to_bytes(32, 'big') + s.to_bytes(32, 'big'))

    return '{}.{}'.format(unsigned_token, sig.decode().strip('='))

def _iv(base, counter):
    mask = int.from_bytes(base[4:], 'big')
    return base[:4] + (counter ^ mask).to_bytes(8, 'big')

def _derive_key(salt, private_key, device):
    # browser keys
    device_keys = json.loads(device["keys"])
    p256dh = _base64_decode_with_padding(device_keys.get('p256dh'))
    auth = _base64_decode_with_padding(device_keys.get('auth'))

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
    endpoint = device["endpoint"]
    jwt = _generate_jwt(endpoint, base_url, vapid_private_key)
    body_payload = payload.encode()
    payload = _encrypt_payload(body_payload, device)
    headers = {
        #  Authorization header field contains these parameters:
        #  - "t" is the JWT;
        #  - "k" the base64url-encoded key that signed that token.
        'Authorization': 'vapid t={}, k={}'.format(jwt, vapid_public_key),
        'Content-Encoding': 'aes128gcm',
        'TTL': '0',
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


class DeviceUnreachableError(Exception):
    pass
