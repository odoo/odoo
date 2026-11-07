# This file is dual licensed under the terms of the Apache License, Version
# 2.0, and the BSD License. See the LICENSE file in the root of this repository
# for complete details.


import typing

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.backends.openssl.utils import (
    _calculate_digest_and_algorithm,
)
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import dsa
from cryptography.hazmat.primitives.asymmetric import utils as asym_utils

if typing.TYPE_CHECKING:
    from cryptography.hazmat.backends.openssl.backend import Backend


def _dsa_sig_sign(
    backend: "Backend", private_key: "_DSAPrivateKey", data: bytes
) -> bytes:
    sig_buf_len = backend._lib.DSA_size(private_key._dsa_cdata)
    sig_buf = backend._ffi.new("unsigned char[]", sig_buf_len)
    buflen = backend._ffi.new("unsigned int *")

    # The first parameter passed to DSA_sign is unused by OpenSSL but
    # must be an integer.
    res = backend._lib.DSA_sign(
        0, data, len(data), sig_buf, buflen, private_key._dsa_cdata
    )
    backend.openssl_assert(res == 1)
    backend.openssl_assert(buflen[0])

    return backend._ffi.buffer(sig_buf)[: buflen[0]]


def _dsa_sig_verify(
    backend: "Backend",
    public_key: "_DSAPublicKey",
    signature: bytes,
    data: bytes,
) -> None:
    # The first parameter passed to DSA_verify is unused by OpenSSL but
    # must be an integer.
    res = backend._lib.DSA_verify(
        0, data, len(data), signature, len(signature), public_key._dsa_cdata
    )

    if res != 1:
        backend._consume_errors()
        raise InvalidSignature


class _DSAParameters(dsa.DSAParameters):
    def __init__(self, backend: "Backend", dsa_cdata):
        self._backend = backend
        self._dsa_cdata = dsa_cdata

    def parameter_numbers(self) -> dsa.DSAParameterNumbers:
        p = self._backend._ffi.new("BIGNUM **")
        q = self._backend._ffi.new("BIGNUM **")
        g = self._backend._ffi.new("BIGNUM **")
        self._backend._lib.DSA_get0_pqg(self._dsa_cdata, p, q, g)
        self._backend.openssl_assert(p[0] != self._backend._ffi.NULL)
        self._backend.openssl_assert(q[0] != self._backend._ffi.NULL)
        self._backend.openssl_assert(g[0] != self._backend._ffi.NULL)
        return dsa.DSAParameterNumbers(
            p=self._backend._bn_to_int(p[0]),
            q=self._backend._bn_to_int(q[0]),
            g=self._backend._bn_to_int(g[0]),
        )

    def generate_private_key(self) -> dsa.DSAPrivateKey:
        return self._backend.generate_dsa_private_key(self)


class _DSAPrivateKey(dsa.DSAPrivateKey):
    _key_size: int

    def __init__(self, backend: "Backend", dsa_cdata, evp_pkey):
        self._backend = backend
        self._dsa_cdata = dsa_cdata
        self._evp_pkey = evp_pkey

        p = self._backend._ffi.new("BIGNUM **")
        self._backend._lib.DSA_get0_pqg(
            dsa_cdata, p, self._backend._ffi.NULL, self._backend._ffi.NULL
        )
        self._backend.openssl_assert(p[0] != backend._ffi.NULL)
        self._key_size = self._backend._lib.BN_num_bits(p[0])

    @property
    def key_size(self) -> int:
        return self._key_size

    def private_numbers(self) -> dsa.DSAPrivateNumbers:
        p = self._backend._ffi.new("BIGNUM **")
        q = self._backend._ffi.new("BIGNUM **")
        g = self._backend._ffi.new("BIGNUM **")
        pub_key = self._backend._ffi.new("BIGNUM **")
        priv_key = self._backend._ffi.new("BIGNUM **")
        self._backend._lib.DSA_get0_pqg(self._dsa_cdata, p, q, g)
        self._backend.openssl_assert(p[0] != self._backend._ffi.NULL)
        self._backend.openssl_assert(q[0] != self._backend._ffi.NULL)
        self._backend.openssl_assert(g[0] != self._backend._ffi.NULL)
        self._backend._lib.DSA_get0_key(self._dsa_cdata, pub_key, priv_key)
        self._backend.openssl_assert(pub_key[0] != self._backend._ffi.NULL)
        self._backend.openssl_assert(priv_key[0] != self._backend._ffi.NULL)
        return dsa.DSAPrivateNumbers(
            public_numbers=dsa.DSAPublicNumbers(
                parameter_numbers=dsa.DSAParameterNumbers(
                    p=self._backend._bn_to_int(p[0]),
                    q=self._backend._bn_to_int(q[0]),
                    g=self._backend._bn_to_int(g[0]),
                ),
                y=self._backend._bn_to_int(pub_key[0]),
            ),
            x=self._backend._bn_to_int(priv_key[0]),
        )

    def public_key(self) -> dsa.DSAPublicKey:
        dsa_cdata = self._backend._lib.DSAparams_dup(self._dsa_cdata)
        self._backend.openssl_assert(dsa_cdata != self._backend._ffi.NULL)
        dsa_cdata = self._backend._ffi.gc(
            dsa_cdata, self._backend._lib.DSA_free
        )
        pub_key = self._backend._ffi.new("BIGNUM **")
        self._backend._lib.DSA_get0_key(
            self._dsa_cdata, pub_key, self._backend._ffi.NULL
        )
        self._backend.openssl_assert(pub_key[0] != self._backend._ffi.NULL)
        pub_key_dup = self._backend._lib.BN_dup(pub_key[0])
        res = self._backend._lib.DSA_set0_key(
            dsa_cdata, pub_key_dup, self._backend._ffi.NULL
        )
        self._backend.openssl_assert(res == 1)
        evp_pkey = self._backend._dsa_cdata_to_evp_pkey(dsa_cdata)
        return _DSAPublicKey(self._backend, dsa_cdata, evp_pkey)

    def parameters(self) -> dsa.DSAParameters:
        dsa_cdata = self._backend._lib.DSAparams_dup(self._dsa_cdata)
        self._backend.openssl_assert(dsa_cdata != self._backend._ffi.NULL)
        dsa_cdata = self._backend._ffi.gc(
            dsa_cdata, self._backend._lib.DSA_free
        )
        return _DSAParameters(self._backend, dsa_cdata)

    def private_bytes(
        self,
        encoding: serialization.Encoding,
        format: serialization.PrivateFormat,
        encryption_algorithm: serialization.KeySerializationEncryption,
    ) -> bytes:
        return self._backend._private_key_bytes(
            encoding,
            format,
            encryption_algorithm,
            self,
            self._evp_pkey,
            self._dsa_cdata,
        )

    def sign(
        self,
        data: bytes,
        algorithm: typing.Union[asym_utils.Prehashed, hashes.HashAlgorithm],
    ) -> bytes:
        data, _ = _calculate_digest_and_algorithm(data, algorithm)
        return _dsa_sig_sign(self._backend, self, data)


class _DSAPublicKey(dsa.DSAPublicKey):
    _key_size: int

    def __init__(self, backend: "Backend", dsa_cdata, evp_pkey):
        self._backend = backend
        self._dsa_cdata = dsa_cdata
        self._evp_pkey = evp_pkey
        p = self._backend._ffi.new("BIGNUM **")
        self._backend._lib.DSA_get0_pqg(
            dsa_cdata, p, self._backend._ffi.NULL, self._backend._ffi.NULL
        )
        self._backend.openssl_assert(p[0] != backend._ffi.NULL)
        self._key_size = self._backend._lib.BN_num_bits(p[0])

    @property
    def key_size(self) -> int:
        return self._key_size

    def public_numbers(self) -> dsa.DSAPublicNumbers:
        p = self._backend._ffi.new("BIGNUM **")
        q = self._backend._ffi.new("BIGNUM **")
        g = self._backend._ffi.new("BIGNUM **")
        pub_key = self._backend._ffi.new("BIGNUM **")
        self._backend._lib.DSA_get0_pqg(self._dsa_cdata, p, q, g)
        self._backend.openssl_assert(p[0] != self._backend._ffi.NULL)
        self._backend.openssl_assert(q[0] != self._backend._ffi.NULL)
        self._backend.openssl_assert(g[0] != self._backend._ffi.NULL)
        self._backend._lib.DSA_get0_key(
            self._dsa_cdata, pub_key, self._backend._ffi.NULL
        )
        self._backend.openssl_assert(pub_key[0] != self._backend._ffi.NULL)
        return dsa.DSAPublicNumbers(
            parameter_numbers=dsa.DSAParameterNumbers(
                p=self._backend._bn_to_int(p[0]),
                q=self._backend._bn_to_int(q[0]),
                g=self._backend._bn_to_int(g[0]),
            ),
            y=self._backend._bn_to_int(pub_key[0]),
        )

    def parameters(self) -> dsa.DSAParameters:
        dsa_cdata = self._backend._lib.DSAparams_dup(self._dsa_cdata)
        dsa_cdata = self._backend._ffi.gc(
            dsa_cdata, self._backend._lib.DSA_free
        )
        return _DSAParameters(self._backend, dsa_cdata)

    def public_bytes(
        self,
        encoding: serialization.Encoding,
        format: serialization.PublicFormat,
    ) -> bytes:
        return self._backend._public_key_bytes(
            encoding, format, self, self._evp_pkey, None
        )

    def verify(
        self,
        signature: bytes,
        data: bytes,
        algorithm: typing.Union[asym_utils.Prehashed, hashes.HashAlgorithm],
    ) -> None:
        data, _ = _calculate_digest_and_algorithm(data, algorithm)
        return _dsa_sig_verify(self._backend, self, signature, data)
