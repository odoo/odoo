# This file is dual licensed under the terms of the Apache License, Version
# 2.0, and the BSD License. See the LICENSE file in the root of this repository
# for complete details.

import typing

from cryptography import x509
from cryptography.hazmat.backends import _get_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import dsa, ec, rsa


_ALLOWED_PKCS12_TYPES = typing.Union[
    rsa.RSAPrivateKey,
    dsa.DSAPrivateKey,
    ec.EllipticCurvePrivateKey,
]


def load_key_and_certificates(
    data: bytes, password: typing.Optional[bytes], backend=None
) -> typing.Tuple[
    typing.Optional[_ALLOWED_PKCS12_TYPES],
    typing.Optional[x509.Certificate],
    typing.List[x509.Certificate],
]:
    backend = _get_backend(backend)
    return backend.load_key_and_certificates_from_pkcs12(data, password)


def serialize_key_and_certificates(
    name: typing.Optional[bytes],
    key: typing.Optional[_ALLOWED_PKCS12_TYPES],
    cert: typing.Optional[x509.Certificate],
    cas: typing.Optional[typing.Iterable[x509.Certificate]],
    encryption_algorithm: serialization.KeySerializationEncryption,
) -> bytes:
    if key is not None and not isinstance(
        key,
        (
            rsa.RSAPrivateKey,
            dsa.DSAPrivateKey,
            ec.EllipticCurvePrivateKey,
        ),
    ):
        raise TypeError("Key must be RSA, DSA, or EllipticCurve private key.")
    if cert is not None and not isinstance(cert, x509.Certificate):
        raise TypeError("cert must be a certificate")

    if cas is not None:
        cas = list(cas)
        if not all(isinstance(val, x509.Certificate) for val in cas):
            raise TypeError("all values in cas must be certificates")

    if not isinstance(
        encryption_algorithm, serialization.KeySerializationEncryption
    ):
        raise TypeError(
            "Key encryption algorithm must be a "
            "KeySerializationEncryption instance"
        )

    if key is None and cert is None and not cas:
        raise ValueError("You must supply at least one of key, cert, or cas")

    backend = _get_backend(None)
    return backend.serialize_key_and_certificates_to_pkcs12(
        name, key, cert, cas, encryption_algorithm
    )
