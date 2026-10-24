# This file is dual licensed under the terms of the Apache License, Version
# 2.0, and the BSD License. See the LICENSE file in the root of this repository
# for complete details.


import typing

from cryptography.hazmat._types import (
    _PRIVATE_KEY_TYPES,
    _PUBLIC_KEY_TYPES,
)
from cryptography.hazmat.backends import _get_backend
from cryptography.hazmat.primitives.asymmetric import dh


def load_pem_private_key(
    data: bytes, password: typing.Optional[bytes], backend=None
) -> _PRIVATE_KEY_TYPES:
    backend = _get_backend(backend)
    return backend.load_pem_private_key(data, password)


def load_pem_public_key(data: bytes, backend=None) -> _PUBLIC_KEY_TYPES:
    backend = _get_backend(backend)
    return backend.load_pem_public_key(data)


def load_pem_parameters(data: bytes, backend=None) -> "dh.DHParameters":
    backend = _get_backend(backend)
    return backend.load_pem_parameters(data)


def load_der_private_key(
    data: bytes, password: typing.Optional[bytes], backend=None
) -> _PRIVATE_KEY_TYPES:
    backend = _get_backend(backend)
    return backend.load_der_private_key(data, password)


def load_der_public_key(data: bytes, backend=None) -> _PUBLIC_KEY_TYPES:
    backend = _get_backend(backend)
    return backend.load_der_public_key(data)


def load_der_parameters(data: bytes, backend=None) -> "dh.DHParameters":
    backend = _get_backend(backend)
    return backend.load_der_parameters(data)
