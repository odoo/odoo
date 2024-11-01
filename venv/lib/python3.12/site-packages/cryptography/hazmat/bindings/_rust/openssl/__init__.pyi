# This file is dual licensed under the terms of the Apache License, Version
# 2.0, and the BSD License. See the LICENSE file in the root of this repository
# for complete details.

import typing

from cryptography.hazmat.bindings._rust.openssl import (
    aead,
    cmac,
    dh,
    dsa,
    ec,
    ed448,
    ed25519,
    hashes,
    hmac,
    kdf,
    keys,
    poly1305,
    rsa,
    x448,
    x25519,
)

__all__ = [
    "openssl_version",
    "raise_openssl_error",
    "aead",
    "cmac",
    "dh",
    "dsa",
    "ec",
    "hashes",
    "hmac",
    "kdf",
    "keys",
    "ed448",
    "ed25519",
    "rsa",
    "poly1305",
    "x448",
    "x25519",
]

_legacy_provider_loaded: bool

def openssl_version() -> int: ...
def raise_openssl_error() -> typing.NoReturn: ...
def capture_error_stack() -> list[OpenSSLError]: ...
def is_fips_enabled() -> bool: ...

class OpenSSLError:
    @property
    def lib(self) -> int: ...
    @property
    def reason(self) -> int: ...
    @property
    def reason_text(self) -> bytes: ...
    def _lib_reason_match(self, lib: int, reason: int) -> bool: ...
