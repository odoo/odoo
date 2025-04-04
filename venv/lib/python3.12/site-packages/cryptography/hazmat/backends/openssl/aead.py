# This file is dual licensed under the terms of the Apache License, Version
# 2.0, and the BSD License. See the LICENSE file in the root of this repository
# for complete details.

from __future__ import annotations

import typing

from cryptography.exceptions import InvalidTag

if typing.TYPE_CHECKING:
    from cryptography.hazmat.backends.openssl.backend import Backend
    from cryptography.hazmat.primitives.ciphers.aead import (
        AESCCM,
        AESGCM,
    )

    _AEADTypes = typing.Union[AESCCM, AESGCM]


def _aead_cipher_supported(backend: Backend, cipher: _AEADTypes) -> bool:
    cipher_name = _evp_cipher_cipher_name(cipher)

    return backend._lib.EVP_get_cipherbyname(cipher_name) != backend._ffi.NULL


def _encrypt(
    backend: Backend,
    cipher: _AEADTypes,
    nonce: bytes,
    data: bytes,
    associated_data: list[bytes],
    tag_length: int,
) -> bytes:
    return _evp_cipher_encrypt(
        backend, cipher, nonce, data, associated_data, tag_length
    )


def _decrypt(
    backend: Backend,
    cipher: _AEADTypes,
    nonce: bytes,
    data: bytes,
    associated_data: list[bytes],
    tag_length: int,
) -> bytes:
    return _evp_cipher_decrypt(
        backend, cipher, nonce, data, associated_data, tag_length
    )


_ENCRYPT = 1
_DECRYPT = 0


def _evp_cipher_cipher_name(cipher: _AEADTypes) -> bytes:
    from cryptography.hazmat.primitives.ciphers.aead import (
        AESCCM,
        AESGCM,
    )

    if isinstance(cipher, AESCCM):
        return f"aes-{len(cipher._key) * 8}-ccm".encode("ascii")
    else:
        assert isinstance(cipher, AESGCM)
        return f"aes-{len(cipher._key) * 8}-gcm".encode("ascii")


def _evp_cipher(cipher_name: bytes, backend: Backend):
    evp_cipher = backend._lib.EVP_get_cipherbyname(cipher_name)
    backend.openssl_assert(evp_cipher != backend._ffi.NULL)
    return evp_cipher


def _evp_cipher_aead_setup(
    backend: Backend,
    cipher_name: bytes,
    key: bytes,
    nonce: bytes,
    tag: bytes | None,
    tag_len: int,
    operation: int,
):
    evp_cipher = _evp_cipher(cipher_name, backend)
    ctx = backend._lib.EVP_CIPHER_CTX_new()
    ctx = backend._ffi.gc(ctx, backend._lib.EVP_CIPHER_CTX_free)
    res = backend._lib.EVP_CipherInit_ex(
        ctx,
        evp_cipher,
        backend._ffi.NULL,
        backend._ffi.NULL,
        backend._ffi.NULL,
        int(operation == _ENCRYPT),
    )
    backend.openssl_assert(res != 0)
    # CCM requires the IVLEN to be set before calling SET_TAG on decrypt
    res = backend._lib.EVP_CIPHER_CTX_ctrl(
        ctx,
        backend._lib.EVP_CTRL_AEAD_SET_IVLEN,
        len(nonce),
        backend._ffi.NULL,
    )
    backend.openssl_assert(res != 0)
    if operation == _DECRYPT:
        assert tag is not None
        _evp_cipher_set_tag(backend, ctx, tag)
    elif cipher_name.endswith(b"-ccm"):
        res = backend._lib.EVP_CIPHER_CTX_ctrl(
            ctx,
            backend._lib.EVP_CTRL_AEAD_SET_TAG,
            tag_len,
            backend._ffi.NULL,
        )
        backend.openssl_assert(res != 0)

    nonce_ptr = backend._ffi.from_buffer(nonce)
    key_ptr = backend._ffi.from_buffer(key)
    res = backend._lib.EVP_CipherInit_ex(
        ctx,
        backend._ffi.NULL,
        backend._ffi.NULL,
        key_ptr,
        nonce_ptr,
        int(operation == _ENCRYPT),
    )
    backend.openssl_assert(res != 0)
    return ctx


def _evp_cipher_set_tag(backend, ctx, tag: bytes) -> None:
    tag_ptr = backend._ffi.from_buffer(tag)
    res = backend._lib.EVP_CIPHER_CTX_ctrl(
        ctx, backend._lib.EVP_CTRL_AEAD_SET_TAG, len(tag), tag_ptr
    )
    backend.openssl_assert(res != 0)


def _evp_cipher_set_length(backend: Backend, ctx, data_len: int) -> None:
    intptr = backend._ffi.new("int *")
    res = backend._lib.EVP_CipherUpdate(
        ctx, backend._ffi.NULL, intptr, backend._ffi.NULL, data_len
    )
    backend.openssl_assert(res != 0)


def _evp_cipher_process_aad(
    backend: Backend, ctx, associated_data: bytes
) -> None:
    outlen = backend._ffi.new("int *")
    a_data_ptr = backend._ffi.from_buffer(associated_data)
    res = backend._lib.EVP_CipherUpdate(
        ctx, backend._ffi.NULL, outlen, a_data_ptr, len(associated_data)
    )
    backend.openssl_assert(res != 0)


def _evp_cipher_process_data(backend: Backend, ctx, data: bytes) -> bytes:
    outlen = backend._ffi.new("int *")
    buf = backend._ffi.new("unsigned char[]", len(data))
    data_ptr = backend._ffi.from_buffer(data)
    res = backend._lib.EVP_CipherUpdate(ctx, buf, outlen, data_ptr, len(data))
    backend.openssl_assert(res != 0)
    return backend._ffi.buffer(buf, outlen[0])[:]


def _evp_cipher_encrypt(
    backend: Backend,
    cipher: _AEADTypes,
    nonce: bytes,
    data: bytes,
    associated_data: list[bytes],
    tag_length: int,
) -> bytes:
    from cryptography.hazmat.primitives.ciphers.aead import AESCCM

    cipher_name = _evp_cipher_cipher_name(cipher)
    ctx = _evp_cipher_aead_setup(
        backend,
        cipher_name,
        cipher._key,
        nonce,
        None,
        tag_length,
        _ENCRYPT,
    )

    # CCM requires us to pass the length of the data before processing
    # anything.
    # However calling this with any other AEAD results in an error
    if isinstance(cipher, AESCCM):
        _evp_cipher_set_length(backend, ctx, len(data))

    for ad in associated_data:
        _evp_cipher_process_aad(backend, ctx, ad)
    processed_data = _evp_cipher_process_data(backend, ctx, data)
    outlen = backend._ffi.new("int *")
    # All AEADs we support besides OCB are streaming so they return nothing
    # in finalization. OCB can return up to (16 byte block - 1) bytes so
    # we need a buffer here too.
    buf = backend._ffi.new("unsigned char[]", 16)
    res = backend._lib.EVP_CipherFinal_ex(ctx, buf, outlen)
    backend.openssl_assert(res != 0)
    processed_data += backend._ffi.buffer(buf, outlen[0])[:]
    tag_buf = backend._ffi.new("unsigned char[]", tag_length)
    res = backend._lib.EVP_CIPHER_CTX_ctrl(
        ctx, backend._lib.EVP_CTRL_AEAD_GET_TAG, tag_length, tag_buf
    )
    backend.openssl_assert(res != 0)
    tag = backend._ffi.buffer(tag_buf)[:]

    return processed_data + tag


def _evp_cipher_decrypt(
    backend: Backend,
    cipher: _AEADTypes,
    nonce: bytes,
    data: bytes,
    associated_data: list[bytes],
    tag_length: int,
) -> bytes:
    from cryptography.hazmat.primitives.ciphers.aead import AESCCM

    if len(data) < tag_length:
        raise InvalidTag

    tag = data[-tag_length:]
    data = data[:-tag_length]
    cipher_name = _evp_cipher_cipher_name(cipher)
    ctx = _evp_cipher_aead_setup(
        backend,
        cipher_name,
        cipher._key,
        nonce,
        tag,
        tag_length,
        _DECRYPT,
    )

    # CCM requires us to pass the length of the data before processing
    # anything.
    # However calling this with any other AEAD results in an error
    if isinstance(cipher, AESCCM):
        _evp_cipher_set_length(backend, ctx, len(data))

    for ad in associated_data:
        _evp_cipher_process_aad(backend, ctx, ad)
    # CCM has a different error path if the tag doesn't match. Errors are
    # raised in Update and Final is irrelevant.
    if isinstance(cipher, AESCCM):
        outlen = backend._ffi.new("int *")
        buf = backend._ffi.new("unsigned char[]", len(data))
        d_ptr = backend._ffi.from_buffer(data)
        res = backend._lib.EVP_CipherUpdate(ctx, buf, outlen, d_ptr, len(data))
        if res != 1:
            backend._consume_errors()
            raise InvalidTag

        processed_data = backend._ffi.buffer(buf, outlen[0])[:]
    else:
        processed_data = _evp_cipher_process_data(backend, ctx, data)
        outlen = backend._ffi.new("int *")
        # OCB can return up to 15 bytes (16 byte block - 1) in finalization
        buf = backend._ffi.new("unsigned char[]", 16)
        res = backend._lib.EVP_CipherFinal_ex(ctx, buf, outlen)
        processed_data += backend._ffi.buffer(buf, outlen[0])[:]
        if res == 0:
            backend._consume_errors()
            raise InvalidTag

    return processed_data
