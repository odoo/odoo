# This file is dual licensed under the terms of the Apache License, Version
# 2.0, and the BSD License. See the LICENSE file in the root of this repository
# for complete details.

from __future__ import annotations

import collections
import contextlib
import itertools
import typing

from cryptography import utils, x509
from cryptography.exceptions import UnsupportedAlgorithm
from cryptography.hazmat.backends.openssl import aead
from cryptography.hazmat.backends.openssl.ciphers import _CipherContext
from cryptography.hazmat.bindings._rust import openssl as rust_openssl
from cryptography.hazmat.bindings.openssl import binding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives._asymmetric import AsymmetricPadding
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric import utils as asym_utils
from cryptography.hazmat.primitives.asymmetric.padding import (
    MGF1,
    OAEP,
    PSS,
    PKCS1v15,
)
from cryptography.hazmat.primitives.asymmetric.types import (
    PrivateKeyTypes,
)
from cryptography.hazmat.primitives.ciphers import (
    CipherAlgorithm,
)
from cryptography.hazmat.primitives.ciphers.algorithms import (
    AES,
    AES128,
    AES256,
    ARC4,
    SM4,
    Camellia,
    ChaCha20,
    TripleDES,
    _BlowfishInternal,
    _CAST5Internal,
    _IDEAInternal,
    _SEEDInternal,
)
from cryptography.hazmat.primitives.ciphers.modes import (
    CBC,
    CFB,
    CFB8,
    CTR,
    ECB,
    GCM,
    OFB,
    XTS,
    Mode,
)
from cryptography.hazmat.primitives.serialization.pkcs12 import (
    PBES,
    PKCS12Certificate,
    PKCS12KeyAndCertificates,
    PKCS12PrivateKeyTypes,
    _PKCS12CATypes,
)

_MemoryBIO = collections.namedtuple("_MemoryBIO", ["bio", "char_ptr"])


# Not actually supported, just used as a marker for some serialization tests.
class _RC2:
    pass


class Backend:
    """
    OpenSSL API binding interfaces.
    """

    name = "openssl"

    # FIPS has opinions about acceptable algorithms and key sizes, but the
    # disallowed algorithms are still present in OpenSSL. They just error if
    # you try to use them. To avoid that we allowlist the algorithms in
    # FIPS 140-3. This isn't ideal, but FIPS 140-3 is trash so here we are.
    _fips_aead: typing.ClassVar[set[bytes]] = {
        b"aes-128-ccm",
        b"aes-192-ccm",
        b"aes-256-ccm",
        b"aes-128-gcm",
        b"aes-192-gcm",
        b"aes-256-gcm",
    }
    # TripleDES encryption is disallowed/deprecated throughout 2023 in
    # FIPS 140-3. To keep it simple we denylist any use of TripleDES (TDEA).
    _fips_ciphers = (AES,)
    # Sometimes SHA1 is still permissible. That logic is contained
    # within the various *_supported methods.
    _fips_hashes = (
        hashes.SHA224,
        hashes.SHA256,
        hashes.SHA384,
        hashes.SHA512,
        hashes.SHA512_224,
        hashes.SHA512_256,
        hashes.SHA3_224,
        hashes.SHA3_256,
        hashes.SHA3_384,
        hashes.SHA3_512,
        hashes.SHAKE128,
        hashes.SHAKE256,
    )
    _fips_ecdh_curves = (
        ec.SECP224R1,
        ec.SECP256R1,
        ec.SECP384R1,
        ec.SECP521R1,
    )
    _fips_rsa_min_key_size = 2048
    _fips_rsa_min_public_exponent = 65537
    _fips_dsa_min_modulus = 1 << 2048
    _fips_dh_min_key_size = 2048
    _fips_dh_min_modulus = 1 << _fips_dh_min_key_size

    def __init__(self) -> None:
        self._binding = binding.Binding()
        self._ffi = self._binding.ffi
        self._lib = self._binding.lib
        self._fips_enabled = rust_openssl.is_fips_enabled()

        self._cipher_registry: dict[
            tuple[type[CipherAlgorithm], type[Mode]],
            typing.Callable,
        ] = {}
        self._register_default_ciphers()

    def __repr__(self) -> str:
        return "<OpenSSLBackend(version: {}, FIPS: {}, Legacy: {})>".format(
            self.openssl_version_text(),
            self._fips_enabled,
            rust_openssl._legacy_provider_loaded,
        )

    def openssl_assert(
        self,
        ok: bool,
        errors: list[rust_openssl.OpenSSLError] | None = None,
    ) -> None:
        return binding._openssl_assert(ok, errors=errors)

    def _enable_fips(self) -> None:
        # This function enables FIPS mode for OpenSSL 3.0.0 on installs that
        # have the FIPS provider installed properly.
        self._binding._enable_fips()
        assert rust_openssl.is_fips_enabled()
        self._fips_enabled = rust_openssl.is_fips_enabled()

    def openssl_version_text(self) -> str:
        """
        Friendly string name of the loaded OpenSSL library. This is not
        necessarily the same version as it was compiled against.

        Example: OpenSSL 1.1.1d  10 Sep 2019
        """
        return self._ffi.string(
            self._lib.OpenSSL_version(self._lib.OPENSSL_VERSION)
        ).decode("ascii")

    def openssl_version_number(self) -> int:
        return self._lib.OpenSSL_version_num()

    def _evp_md_from_algorithm(self, algorithm: hashes.HashAlgorithm):
        if algorithm.name in ("blake2b", "blake2s"):
            alg = f"{algorithm.name}{algorithm.digest_size * 8}".encode(
                "ascii"
            )
        else:
            alg = algorithm.name.encode("ascii")

        evp_md = self._lib.EVP_get_digestbyname(alg)
        return evp_md

    def _evp_md_non_null_from_algorithm(self, algorithm: hashes.HashAlgorithm):
        evp_md = self._evp_md_from_algorithm(algorithm)
        self.openssl_assert(evp_md != self._ffi.NULL)
        return evp_md

    def hash_supported(self, algorithm: hashes.HashAlgorithm) -> bool:
        if self._fips_enabled and not isinstance(algorithm, self._fips_hashes):
            return False

        evp_md = self._evp_md_from_algorithm(algorithm)
        return evp_md != self._ffi.NULL

    def signature_hash_supported(
        self, algorithm: hashes.HashAlgorithm
    ) -> bool:
        # Dedicated check for hashing algorithm use in message digest for
        # signatures, e.g. RSA PKCS#1 v1.5 SHA1 (sha1WithRSAEncryption).
        if self._fips_enabled and isinstance(algorithm, hashes.SHA1):
            return False
        return self.hash_supported(algorithm)

    def scrypt_supported(self) -> bool:
        if self._fips_enabled:
            return False
        else:
            return self._lib.Cryptography_HAS_SCRYPT == 1

    def hmac_supported(self, algorithm: hashes.HashAlgorithm) -> bool:
        # FIPS mode still allows SHA1 for HMAC
        if self._fips_enabled and isinstance(algorithm, hashes.SHA1):
            return True

        return self.hash_supported(algorithm)

    def cipher_supported(self, cipher: CipherAlgorithm, mode: Mode) -> bool:
        if self._fips_enabled:
            # FIPS mode requires AES. TripleDES is disallowed/deprecated in
            # FIPS 140-3.
            if not isinstance(cipher, self._fips_ciphers):
                return False

        try:
            adapter = self._cipher_registry[type(cipher), type(mode)]
        except KeyError:
            return False
        evp_cipher = adapter(self, cipher, mode)
        return self._ffi.NULL != evp_cipher

    def register_cipher_adapter(self, cipher_cls, mode_cls, adapter) -> None:
        if (cipher_cls, mode_cls) in self._cipher_registry:
            raise ValueError(
                f"Duplicate registration for: {cipher_cls} {mode_cls}."
            )
        self._cipher_registry[cipher_cls, mode_cls] = adapter

    def _register_default_ciphers(self) -> None:
        for cipher_cls in [AES, AES128, AES256]:
            for mode_cls in [CBC, CTR, ECB, OFB, CFB, CFB8, GCM]:
                self.register_cipher_adapter(
                    cipher_cls,
                    mode_cls,
                    GetCipherByName(
                        "{cipher.name}-{cipher.key_size}-{mode.name}"
                    ),
                )
        for mode_cls in [CBC, CTR, ECB, OFB, CFB]:
            self.register_cipher_adapter(
                Camellia,
                mode_cls,
                GetCipherByName("{cipher.name}-{cipher.key_size}-{mode.name}"),
            )
        for mode_cls in [CBC, CFB, CFB8, OFB]:
            self.register_cipher_adapter(
                TripleDES, mode_cls, GetCipherByName("des-ede3-{mode.name}")
            )
        self.register_cipher_adapter(
            TripleDES, ECB, GetCipherByName("des-ede3")
        )
        # ChaCha20 uses the Long Name "chacha20" in OpenSSL, but in LibreSSL
        # it uses "chacha"
        self.register_cipher_adapter(
            ChaCha20,
            type(None),
            GetCipherByName(
                "chacha" if self._lib.CRYPTOGRAPHY_IS_LIBRESSL else "chacha20"
            ),
        )
        self.register_cipher_adapter(AES, XTS, _get_xts_cipher)
        for mode_cls in [ECB, CBC, OFB, CFB, CTR, GCM]:
            self.register_cipher_adapter(
                SM4, mode_cls, GetCipherByName("sm4-{mode.name}")
            )
        # Don't register legacy ciphers if they're unavailable. Hypothetically
        # this wouldn't be necessary because we test availability by seeing if
        # we get an EVP_CIPHER * in the _CipherContext __init__, but OpenSSL 3
        # will return a valid pointer even though the cipher is unavailable.
        if (
            rust_openssl._legacy_provider_loaded
            or not self._lib.CRYPTOGRAPHY_OPENSSL_300_OR_GREATER
        ):
            for mode_cls in [CBC, CFB, OFB, ECB]:
                self.register_cipher_adapter(
                    _BlowfishInternal,
                    mode_cls,
                    GetCipherByName("bf-{mode.name}"),
                )
            for mode_cls in [CBC, CFB, OFB, ECB]:
                self.register_cipher_adapter(
                    _SEEDInternal,
                    mode_cls,
                    GetCipherByName("seed-{mode.name}"),
                )
            for cipher_cls, mode_cls in itertools.product(
                [_CAST5Internal, _IDEAInternal],
                [CBC, OFB, CFB, ECB],
            ):
                self.register_cipher_adapter(
                    cipher_cls,
                    mode_cls,
                    GetCipherByName("{cipher.name}-{mode.name}"),
                )
            self.register_cipher_adapter(
                ARC4, type(None), GetCipherByName("rc4")
            )
            # We don't actually support RC2, this is just used by some tests.
            self.register_cipher_adapter(
                _RC2, type(None), GetCipherByName("rc2")
            )

    def create_symmetric_encryption_ctx(
        self, cipher: CipherAlgorithm, mode: Mode
    ) -> _CipherContext:
        return _CipherContext(self, cipher, mode, _CipherContext._ENCRYPT)

    def create_symmetric_decryption_ctx(
        self, cipher: CipherAlgorithm, mode: Mode
    ) -> _CipherContext:
        return _CipherContext(self, cipher, mode, _CipherContext._DECRYPT)

    def pbkdf2_hmac_supported(self, algorithm: hashes.HashAlgorithm) -> bool:
        return self.hmac_supported(algorithm)

    def _consume_errors(self) -> list[rust_openssl.OpenSSLError]:
        return rust_openssl.capture_error_stack()

    def generate_rsa_parameters_supported(
        self, public_exponent: int, key_size: int
    ) -> bool:
        return (
            public_exponent >= 3
            and public_exponent & 1 != 0
            and key_size >= 512
        )

    def _bytes_to_bio(self, data: bytes) -> _MemoryBIO:
        """
        Return a _MemoryBIO namedtuple of (BIO, char*).

        The char* is the storage for the BIO and it must stay alive until the
        BIO is finished with.
        """
        data_ptr = self._ffi.from_buffer(data)
        bio = self._lib.BIO_new_mem_buf(data_ptr, len(data))
        self.openssl_assert(bio != self._ffi.NULL)

        return _MemoryBIO(self._ffi.gc(bio, self._lib.BIO_free), data_ptr)

    def _create_mem_bio_gc(self):
        """
        Creates an empty memory BIO.
        """
        bio_method = self._lib.BIO_s_mem()
        self.openssl_assert(bio_method != self._ffi.NULL)
        bio = self._lib.BIO_new(bio_method)
        self.openssl_assert(bio != self._ffi.NULL)
        bio = self._ffi.gc(bio, self._lib.BIO_free)
        return bio

    def _read_mem_bio(self, bio) -> bytes:
        """
        Reads a memory BIO. This only works on memory BIOs.
        """
        buf = self._ffi.new("char **")
        buf_len = self._lib.BIO_get_mem_data(bio, buf)
        self.openssl_assert(buf_len > 0)
        self.openssl_assert(buf[0] != self._ffi.NULL)
        bio_data = self._ffi.buffer(buf[0], buf_len)[:]
        return bio_data

    def _oaep_hash_supported(self, algorithm: hashes.HashAlgorithm) -> bool:
        if self._fips_enabled and isinstance(algorithm, hashes.SHA1):
            return False

        return isinstance(
            algorithm,
            (
                hashes.SHA1,
                hashes.SHA224,
                hashes.SHA256,
                hashes.SHA384,
                hashes.SHA512,
            ),
        )

    def rsa_padding_supported(self, padding: AsymmetricPadding) -> bool:
        if isinstance(padding, PKCS1v15):
            return True
        elif isinstance(padding, PSS) and isinstance(padding._mgf, MGF1):
            # SHA1 is permissible in MGF1 in FIPS even when SHA1 is blocked
            # as signature algorithm.
            if self._fips_enabled and isinstance(
                padding._mgf._algorithm, hashes.SHA1
            ):
                return True
            else:
                return self.hash_supported(padding._mgf._algorithm)
        elif isinstance(padding, OAEP) and isinstance(padding._mgf, MGF1):
            return self._oaep_hash_supported(
                padding._mgf._algorithm
            ) and self._oaep_hash_supported(padding._algorithm)
        else:
            return False

    def rsa_encryption_supported(self, padding: AsymmetricPadding) -> bool:
        if self._fips_enabled and isinstance(padding, PKCS1v15):
            return False
        else:
            return self.rsa_padding_supported(padding)

    def dsa_supported(self) -> bool:
        return (
            not self._lib.CRYPTOGRAPHY_IS_BORINGSSL and not self._fips_enabled
        )

    def dsa_hash_supported(self, algorithm: hashes.HashAlgorithm) -> bool:
        if not self.dsa_supported():
            return False
        return self.signature_hash_supported(algorithm)

    def cmac_algorithm_supported(self, algorithm) -> bool:
        return self.cipher_supported(
            algorithm, CBC(b"\x00" * algorithm.block_size)
        )

    def _cert2ossl(self, cert: x509.Certificate) -> typing.Any:
        data = cert.public_bytes(serialization.Encoding.DER)
        mem_bio = self._bytes_to_bio(data)
        x509 = self._lib.d2i_X509_bio(mem_bio.bio, self._ffi.NULL)
        self.openssl_assert(x509 != self._ffi.NULL)
        x509 = self._ffi.gc(x509, self._lib.X509_free)
        return x509

    def _ossl2cert(self, x509_ptr: typing.Any) -> x509.Certificate:
        bio = self._create_mem_bio_gc()
        res = self._lib.i2d_X509_bio(bio, x509_ptr)
        self.openssl_assert(res == 1)
        return x509.load_der_x509_certificate(self._read_mem_bio(bio))

    def _key2ossl(self, key: PKCS12PrivateKeyTypes) -> typing.Any:
        data = key.private_bytes(
            serialization.Encoding.DER,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
        mem_bio = self._bytes_to_bio(data)

        evp_pkey = self._lib.d2i_PrivateKey_bio(
            mem_bio.bio,
            self._ffi.NULL,
        )
        self.openssl_assert(evp_pkey != self._ffi.NULL)
        return self._ffi.gc(evp_pkey, self._lib.EVP_PKEY_free)

    def _handle_key_loading_error(
        self, errors: list[rust_openssl.OpenSSLError]
    ) -> typing.NoReturn:
        if not errors:
            raise ValueError(
                "Could not deserialize key data. The data may be in an "
                "incorrect format or it may be encrypted with an unsupported "
                "algorithm."
            )

        elif (
            errors[0]._lib_reason_match(
                self._lib.ERR_LIB_EVP, self._lib.EVP_R_BAD_DECRYPT
            )
            or errors[0]._lib_reason_match(
                self._lib.ERR_LIB_PKCS12,
                self._lib.PKCS12_R_PKCS12_CIPHERFINAL_ERROR,
            )
            or (
                self._lib.Cryptography_HAS_PROVIDERS
                and errors[0]._lib_reason_match(
                    self._lib.ERR_LIB_PROV,
                    self._lib.PROV_R_BAD_DECRYPT,
                )
            )
        ):
            raise ValueError("Bad decrypt. Incorrect password?")

        elif any(
            error._lib_reason_match(
                self._lib.ERR_LIB_EVP,
                self._lib.EVP_R_UNSUPPORTED_PRIVATE_KEY_ALGORITHM,
            )
            for error in errors
        ):
            raise ValueError("Unsupported public key algorithm.")

        else:
            raise ValueError(
                "Could not deserialize key data. The data may be in an "
                "incorrect format, it may be encrypted with an unsupported "
                "algorithm, or it may be an unsupported key type (e.g. EC "
                "curves with explicit parameters).",
                errors,
            )

    def elliptic_curve_supported(self, curve: ec.EllipticCurve) -> bool:
        if self._fips_enabled and not isinstance(
            curve, self._fips_ecdh_curves
        ):
            return False

        return rust_openssl.ec.curve_supported(curve)

    def elliptic_curve_signature_algorithm_supported(
        self,
        signature_algorithm: ec.EllipticCurveSignatureAlgorithm,
        curve: ec.EllipticCurve,
    ) -> bool:
        # We only support ECDSA right now.
        if not isinstance(signature_algorithm, ec.ECDSA):
            return False

        return self.elliptic_curve_supported(curve) and (
            isinstance(signature_algorithm.algorithm, asym_utils.Prehashed)
            or self.hash_supported(signature_algorithm.algorithm)
        )

    def elliptic_curve_exchange_algorithm_supported(
        self, algorithm: ec.ECDH, curve: ec.EllipticCurve
    ) -> bool:
        return self.elliptic_curve_supported(curve) and isinstance(
            algorithm, ec.ECDH
        )

    def dh_supported(self) -> bool:
        return not self._lib.CRYPTOGRAPHY_IS_BORINGSSL

    def dh_x942_serialization_supported(self) -> bool:
        return self._lib.Cryptography_HAS_EVP_PKEY_DHX == 1

    def x25519_supported(self) -> bool:
        if self._fips_enabled:
            return False
        return True

    def x448_supported(self) -> bool:
        if self._fips_enabled:
            return False
        return (
            not self._lib.CRYPTOGRAPHY_IS_LIBRESSL
            and not self._lib.CRYPTOGRAPHY_IS_BORINGSSL
        )

    def ed25519_supported(self) -> bool:
        if self._fips_enabled:
            return False
        return True

    def ed448_supported(self) -> bool:
        if self._fips_enabled:
            return False
        return (
            not self._lib.CRYPTOGRAPHY_IS_LIBRESSL
            and not self._lib.CRYPTOGRAPHY_IS_BORINGSSL
        )

    def aead_cipher_supported(self, cipher) -> bool:
        return aead._aead_cipher_supported(self, cipher)

    def _zero_data(self, data, length: int) -> None:
        # We clear things this way because at the moment we're not
        # sure of a better way that can guarantee it overwrites the
        # memory of a bytearray and doesn't just replace the underlying char *.
        for i in range(length):
            data[i] = 0

    @contextlib.contextmanager
    def _zeroed_null_terminated_buf(self, data):
        """
        This method takes bytes, which can be a bytestring or a mutable
        buffer like a bytearray, and yields a null-terminated version of that
        data. This is required because PKCS12_parse doesn't take a length with
        its password char * and ffi.from_buffer doesn't provide null
        termination. So, to support zeroing the data via bytearray we
        need to build this ridiculous construct that copies the memory, but
        zeroes it after use.
        """
        if data is None:
            yield self._ffi.NULL
        else:
            data_len = len(data)
            buf = self._ffi.new("char[]", data_len + 1)
            self._ffi.memmove(buf, data, data_len)
            try:
                yield buf
            finally:
                # Cast to a uint8_t * so we can assign by integer
                self._zero_data(self._ffi.cast("uint8_t *", buf), data_len)

    def load_key_and_certificates_from_pkcs12(
        self, data: bytes, password: bytes | None
    ) -> tuple[
        PrivateKeyTypes | None,
        x509.Certificate | None,
        list[x509.Certificate],
    ]:
        pkcs12 = self.load_pkcs12(data, password)
        return (
            pkcs12.key,
            pkcs12.cert.certificate if pkcs12.cert else None,
            [cert.certificate for cert in pkcs12.additional_certs],
        )

    def load_pkcs12(
        self, data: bytes, password: bytes | None
    ) -> PKCS12KeyAndCertificates:
        if password is not None:
            utils._check_byteslike("password", password)

        bio = self._bytes_to_bio(data)
        p12 = self._lib.d2i_PKCS12_bio(bio.bio, self._ffi.NULL)
        if p12 == self._ffi.NULL:
            self._consume_errors()
            raise ValueError("Could not deserialize PKCS12 data")

        p12 = self._ffi.gc(p12, self._lib.PKCS12_free)
        evp_pkey_ptr = self._ffi.new("EVP_PKEY **")
        x509_ptr = self._ffi.new("X509 **")
        sk_x509_ptr = self._ffi.new("Cryptography_STACK_OF_X509 **")
        with self._zeroed_null_terminated_buf(password) as password_buf:
            res = self._lib.PKCS12_parse(
                p12, password_buf, evp_pkey_ptr, x509_ptr, sk_x509_ptr
            )
        if res == 0:
            self._consume_errors()
            raise ValueError("Invalid password or PKCS12 data")

        cert = None
        key = None
        additional_certificates = []

        if evp_pkey_ptr[0] != self._ffi.NULL:
            evp_pkey = self._ffi.gc(evp_pkey_ptr[0], self._lib.EVP_PKEY_free)
            # We don't support turning off RSA key validation when loading
            # PKCS12 keys
            key = rust_openssl.keys.private_key_from_ptr(
                int(self._ffi.cast("uintptr_t", evp_pkey)),
                unsafe_skip_rsa_key_validation=False,
            )

        if x509_ptr[0] != self._ffi.NULL:
            x509 = self._ffi.gc(x509_ptr[0], self._lib.X509_free)
            cert_obj = self._ossl2cert(x509)
            name = None
            maybe_name = self._lib.X509_alias_get0(x509, self._ffi.NULL)
            if maybe_name != self._ffi.NULL:
                name = self._ffi.string(maybe_name)
            cert = PKCS12Certificate(cert_obj, name)

        if sk_x509_ptr[0] != self._ffi.NULL:
            sk_x509 = self._ffi.gc(sk_x509_ptr[0], self._lib.sk_X509_free)
            num = self._lib.sk_X509_num(sk_x509_ptr[0])

            # In OpenSSL < 3.0.0 PKCS12 parsing reverses the order of the
            # certificates.
            indices: typing.Iterable[int]
            if (
                self._lib.CRYPTOGRAPHY_OPENSSL_300_OR_GREATER
                or self._lib.CRYPTOGRAPHY_IS_BORINGSSL
            ):
                indices = range(num)
            else:
                indices = reversed(range(num))

            for i in indices:
                x509 = self._lib.sk_X509_value(sk_x509, i)
                self.openssl_assert(x509 != self._ffi.NULL)
                x509 = self._ffi.gc(x509, self._lib.X509_free)
                addl_cert = self._ossl2cert(x509)
                addl_name = None
                maybe_name = self._lib.X509_alias_get0(x509, self._ffi.NULL)
                if maybe_name != self._ffi.NULL:
                    addl_name = self._ffi.string(maybe_name)
                additional_certificates.append(
                    PKCS12Certificate(addl_cert, addl_name)
                )

        return PKCS12KeyAndCertificates(key, cert, additional_certificates)

    def serialize_key_and_certificates_to_pkcs12(
        self,
        name: bytes | None,
        key: PKCS12PrivateKeyTypes | None,
        cert: x509.Certificate | None,
        cas: list[_PKCS12CATypes] | None,
        encryption_algorithm: serialization.KeySerializationEncryption,
    ) -> bytes:
        password = None
        if name is not None:
            utils._check_bytes("name", name)

        if isinstance(encryption_algorithm, serialization.NoEncryption):
            nid_cert = -1
            nid_key = -1
            pkcs12_iter = 0
            mac_iter = 0
            mac_alg = self._ffi.NULL
        elif isinstance(
            encryption_algorithm, serialization.BestAvailableEncryption
        ):
            # PKCS12 encryption is hopeless trash and can never be fixed.
            # OpenSSL 3 supports PBESv2, but Libre and Boring do not, so
            # we use PBESv1 with 3DES on the older paths.
            if self._lib.CRYPTOGRAPHY_OPENSSL_300_OR_GREATER:
                nid_cert = self._lib.NID_aes_256_cbc
                nid_key = self._lib.NID_aes_256_cbc
            else:
                nid_cert = self._lib.NID_pbe_WithSHA1And3_Key_TripleDES_CBC
                nid_key = self._lib.NID_pbe_WithSHA1And3_Key_TripleDES_CBC
            # At least we can set this higher than OpenSSL's default
            pkcs12_iter = 20000
            # mac_iter chosen for compatibility reasons, see:
            # https://www.openssl.org/docs/man1.1.1/man3/PKCS12_create.html
            # Did we mention how lousy PKCS12 encryption is?
            mac_iter = 1
            # MAC algorithm can only be set on OpenSSL 3.0.0+
            mac_alg = self._ffi.NULL
            password = encryption_algorithm.password
        elif (
            isinstance(
                encryption_algorithm, serialization._KeySerializationEncryption
            )
            and encryption_algorithm._format
            is serialization.PrivateFormat.PKCS12
        ):
            # Default to OpenSSL's defaults. Behavior will vary based on the
            # version of OpenSSL cryptography is compiled against.
            nid_cert = 0
            nid_key = 0
            # Use the default iters we use in best available
            pkcs12_iter = 20000
            # See the Best Available comment for why this is 1
            mac_iter = 1
            password = encryption_algorithm.password
            keycertalg = encryption_algorithm._key_cert_algorithm
            if keycertalg is PBES.PBESv1SHA1And3KeyTripleDESCBC:
                nid_cert = self._lib.NID_pbe_WithSHA1And3_Key_TripleDES_CBC
                nid_key = self._lib.NID_pbe_WithSHA1And3_Key_TripleDES_CBC
            elif keycertalg is PBES.PBESv2SHA256AndAES256CBC:
                if not self._lib.CRYPTOGRAPHY_OPENSSL_300_OR_GREATER:
                    raise UnsupportedAlgorithm(
                        "PBESv2 is not supported by this version of OpenSSL"
                    )
                nid_cert = self._lib.NID_aes_256_cbc
                nid_key = self._lib.NID_aes_256_cbc
            else:
                assert keycertalg is None
                # We use OpenSSL's defaults

            if encryption_algorithm._hmac_hash is not None:
                if not self._lib.Cryptography_HAS_PKCS12_SET_MAC:
                    raise UnsupportedAlgorithm(
                        "Setting MAC algorithm is not supported by this "
                        "version of OpenSSL."
                    )
                mac_alg = self._evp_md_non_null_from_algorithm(
                    encryption_algorithm._hmac_hash
                )
                self.openssl_assert(mac_alg != self._ffi.NULL)
            else:
                mac_alg = self._ffi.NULL

            if encryption_algorithm._kdf_rounds is not None:
                pkcs12_iter = encryption_algorithm._kdf_rounds

        else:
            raise ValueError("Unsupported key encryption type")

        if cas is None or len(cas) == 0:
            sk_x509 = self._ffi.NULL
        else:
            sk_x509 = self._lib.sk_X509_new_null()
            sk_x509 = self._ffi.gc(sk_x509, self._lib.sk_X509_free)

            # This list is to keep the x509 values alive until end of function
            ossl_cas = []
            for ca in cas:
                if isinstance(ca, PKCS12Certificate):
                    ca_alias = ca.friendly_name
                    ossl_ca = self._cert2ossl(ca.certificate)
                    if ca_alias is None:
                        res = self._lib.X509_alias_set1(
                            ossl_ca, self._ffi.NULL, -1
                        )
                    else:
                        res = self._lib.X509_alias_set1(
                            ossl_ca, ca_alias, len(ca_alias)
                        )
                    self.openssl_assert(res == 1)
                else:
                    ossl_ca = self._cert2ossl(ca)
                ossl_cas.append(ossl_ca)
                res = self._lib.sk_X509_push(sk_x509, ossl_ca)
                backend.openssl_assert(res >= 1)

        with self._zeroed_null_terminated_buf(password) as password_buf:
            with self._zeroed_null_terminated_buf(name) as name_buf:
                ossl_cert = self._cert2ossl(cert) if cert else self._ffi.NULL
                ossl_pkey = (
                    self._key2ossl(key) if key is not None else self._ffi.NULL
                )

                p12 = self._lib.PKCS12_create(
                    password_buf,
                    name_buf,
                    ossl_pkey,
                    ossl_cert,
                    sk_x509,
                    nid_key,
                    nid_cert,
                    pkcs12_iter,
                    mac_iter,
                    0,
                )
                if p12 == self._ffi.NULL:
                    errors = self._consume_errors()
                    raise ValueError(
                        (
                            "Failed to create PKCS12 (does the key match the "
                            "certificate?)"
                        ),
                        errors,
                    )

            if (
                self._lib.Cryptography_HAS_PKCS12_SET_MAC
                and mac_alg != self._ffi.NULL
            ):
                self._lib.PKCS12_set_mac(
                    p12,
                    password_buf,
                    -1,
                    self._ffi.NULL,
                    0,
                    mac_iter,
                    mac_alg,
                )

        self.openssl_assert(p12 != self._ffi.NULL)
        p12 = self._ffi.gc(p12, self._lib.PKCS12_free)

        bio = self._create_mem_bio_gc()
        res = self._lib.i2d_PKCS12_bio(bio, p12)
        self.openssl_assert(res > 0)
        return self._read_mem_bio(bio)

    def poly1305_supported(self) -> bool:
        if self._fips_enabled:
            return False
        elif (
            self._lib.CRYPTOGRAPHY_IS_BORINGSSL
            or self._lib.CRYPTOGRAPHY_IS_LIBRESSL
        ):
            return True
        else:
            return self._lib.Cryptography_HAS_POLY1305 == 1

    def pkcs7_supported(self) -> bool:
        return not self._lib.CRYPTOGRAPHY_IS_BORINGSSL


class GetCipherByName:
    def __init__(self, fmt: str):
        self._fmt = fmt

    def __call__(self, backend: Backend, cipher: CipherAlgorithm, mode: Mode):
        cipher_name = self._fmt.format(cipher=cipher, mode=mode).lower()
        evp_cipher = backend._lib.EVP_get_cipherbyname(
            cipher_name.encode("ascii")
        )

        # try EVP_CIPHER_fetch if present
        if (
            evp_cipher == backend._ffi.NULL
            and backend._lib.Cryptography_HAS_300_EVP_CIPHER
        ):
            evp_cipher = backend._lib.EVP_CIPHER_fetch(
                backend._ffi.NULL,
                cipher_name.encode("ascii"),
                backend._ffi.NULL,
            )

        backend._consume_errors()
        return evp_cipher


def _get_xts_cipher(backend: Backend, cipher: AES, mode):
    cipher_name = f"aes-{cipher.key_size // 2}-xts"
    return backend._lib.EVP_get_cipherbyname(cipher_name.encode("ascii"))


backend = Backend()
