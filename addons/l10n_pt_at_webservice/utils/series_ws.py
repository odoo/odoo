import base64
import os
from datetime import datetime, timezone

from cryptography import x509
from cryptography.hazmat.primitives import padding as symmetric_padding
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from odoo.tools import file_open

from odoo.addons.l10n_pt_at_webservice.const import PT_AT_WS_PUBLIC_KEY_PATH


def get_at_public_certificate():
    """The AT's public key certificate (KpubSA), shipped with the module: the same for every taxpayer."""
    with file_open(PT_AT_WS_PUBLIC_KEY_PATH, 'rb') as f:
        return x509.load_pem_x509_certificate(f.read())


def seal_username_token(username, password):
    """
    The WS-Security UsernameToken of the AT webservices, as the AT specifies it: each request draws a
    new AES-128 key, which encrypts the password and the creation time (AES/ECB/PKCS5), and is itself
    sent as the Nonce, encrypted with the AT's public key (RSA, PKCS#1 v1.5). Only the AT can open it:
    the proxy that calls the AT writes it in the request as it is.

    :return: ``{'username', 'password', 'nonce', 'created'}``, the last three base64
    """
    public_key = get_at_public_certificate().public_key()
    key = os.urandom(16)
    created = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
    return {
        'username': username,
        'password': _aes_encrypt(key, password),
        'nonce': base64.b64encode(public_key.encrypt(key, padding.PKCS1v15())).decode('ascii'),
        'created': _aes_encrypt(key, created),
    }


def _aes_encrypt(key, value):
    padder = symmetric_padding.PKCS7(algorithms.AES.block_size).padder()
    padded = padder.update(value.encode('utf-8')) + padder.finalize()
    encryptor = Cipher(algorithms.AES(key), modes.ECB()).encryptor()  # noqa: S305 - the AT's scheme
    return base64.b64encode(encryptor.update(padded) + encryptor.finalize()).decode('ascii')
