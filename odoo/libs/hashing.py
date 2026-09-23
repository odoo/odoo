import hashlib
from pathlib import Path
from typing import Any

try:
    from blake3 import blake3 as _blake3
except ImportError:
    _blake3 = None  # type: ignore[assignment]

__all__ = [
    "ALGO_TAG",
    "CONTENT_DIGEST_LEN",
    "CONTENT_DIGEST_MAX_LEN",
    "HAS_BLAKE3",
    "cache_hash",
    "content_hash",
    "content_hash_file",
    "prepare_cache_hasher",
    "prepare_content_hasher",
    "update_from_file",
]

HAS_BLAKE3 = _blake3 is not None

ALGO_TAG = "b3" if HAS_BLAKE3 else "s1"

_CONTENT_DIGEST_LEN_BY_TAG = {"s1": 40, "b3": 64}

CONTENT_DIGEST_LEN = _CONTENT_DIGEST_LEN_BY_TAG[ALGO_TAG]

CONTENT_DIGEST_MAX_LEN = 64

if CONTENT_DIGEST_LEN > CONTENT_DIGEST_MAX_LEN:
    raise RuntimeError(
        f"content digest is {CONTENT_DIGEST_LEN} hex chars but the schema "
        f"holds at most {CONTENT_DIGEST_MAX_LEN}: widen "
        "ir_attachment.checksum and migrate existing databases before "
        "switching to a longer algorithm"
    )

_MT_MIN_BYTES = 1 << 20

_FILE_CHUNK = 1 << 20


def _prepare_blake3_hasher(mt: bool = False) -> Any:
    return _blake3(max_threads=_blake3.AUTO if mt else 1)


def prepare_content_hasher() -> Any:
    return (
        _prepare_blake3_hasher(mt=True)
        if HAS_BLAKE3
        else hashlib.sha1(usedforsecurity=False)
    )


def content_hash(data: bytes) -> str:
    data = data or b""
    if not HAS_BLAKE3:
        return hashlib.sha1(data, usedforsecurity=False).hexdigest()
    hasher = _prepare_blake3_hasher(mt=len(data) >= _MT_MIN_BYTES)
    hasher.update(data)
    return hasher.hexdigest()


def content_hash_file(path: str | Path) -> str:
    if not HAS_BLAKE3:
        digest = hashlib.sha1(usedforsecurity=False)
        with Path(path).open("rb") as fd:
            while chunk := fd.read(_FILE_CHUNK):
                digest.update(chunk)
        return digest.hexdigest()
    hasher = _prepare_blake3_hasher(mt=True)
    hasher.update_mmap(str(path))
    return hasher.hexdigest()


def update_from_file(hasher: Any, path: str | Path) -> None:
    if HAS_BLAKE3:
        hasher.update_mmap(str(path))
        return
    with Path(path).open("rb") as fd:
        while chunk := fd.read(_FILE_CHUNK):
            hasher.update(chunk)


def prepare_cache_hasher() -> Any:
    return _prepare_blake3_hasher() if HAS_BLAKE3 else hashlib.sha256()


def cache_hash(data: bytes) -> str:
    if not HAS_BLAKE3:
        return hashlib.sha256(data).hexdigest()
    hasher = _prepare_blake3_hasher(mt=len(data) >= _MT_MIN_BYTES)
    hasher.update(data)
    return hasher.hexdigest()
