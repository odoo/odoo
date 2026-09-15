import base64
import hashlib
import os
from collections.abc import Mapping

from cryptography.fernet import Fernet, InvalidToken, MultiFernet

__all__ = [
    "ENV_KEY",
    "SEALED_PREFIX",
    "TEST_RUN_KEY",
    "SealError",
    "is_configured",
    "is_sealed",
    "old_key_versions",
    "protects",
    "seal",
    "unseal",
]

ENV_KEY = "ODOO_API_ENCRYPTION_KEY"
SEALED_PREFIX = "fernet:"

# Given to a test run that configured no key; public, so it protects nothing.
TEST_RUN_KEY = base64.urlsafe_b64encode(
    hashlib.sha256(b"odoo test run without ODOO_API_ENCRYPTION_KEY").digest()
).decode()

_MAX_OLD_KEY_VERSION = 19
_MISSES_BEFORE_STOP = 2


class SealError(ValueError):
    pass


def old_key_versions(environ: Mapping[str, str] | None = None) -> list[int]:
    """The numbered predecessors of the current key present in the environment.

    Scanning stops after two consecutive missing numbers, so V1, V2 and V4 read
    as V1 and V2 only.
    """
    environ = os.environ if environ is None else environ
    versions = []
    misses = 0
    for version in range(1, _MAX_OLD_KEY_VERSION + 1):
        if environ.get(f"{ENV_KEY}_V{version}"):
            versions.append(version)
            misses = 0
        else:
            misses += 1
            if misses >= _MISSES_BEFORE_STOP:
                break
    return versions


def is_configured(environ: Mapping[str, str] | None = None) -> bool:
    environ = os.environ if environ is None else environ
    return bool(environ.get(ENV_KEY))


def protects(environ: Mapping[str, str] | None = None) -> bool:
    environ = os.environ if environ is None else environ
    return is_configured(environ) and environ[ENV_KEY] != TEST_RUN_KEY


def is_sealed(value: object) -> bool:
    return isinstance(value, str) and value.startswith(SEALED_PREFIX)


def _fernet(raw: str, name: str) -> Fernet:
    try:
        return Fernet(raw.encode())
    except (TypeError, ValueError) as error:
        raise SealError(f"{name} is not a valid Fernet key") from error


def seal(plaintext: str, environ: Mapping[str, str] | None = None) -> str:
    environ = os.environ if environ is None else environ
    if not is_configured(environ):
        raise SealError(f"{ENV_KEY} is not set: nothing can be sealed")
    token = _fernet(environ[ENV_KEY], ENV_KEY).encrypt(plaintext.encode())
    return SEALED_PREFIX + token.decode()


def unseal(value: str, environ: Mapping[str, str] | None = None) -> str:
    environ = os.environ if environ is None else environ
    if not is_sealed(value):
        raise SealError("the value is not sealed")
    names = [ENV_KEY] if is_configured(environ) else []
    names += [
        f"{ENV_KEY}_V{version}" for version in reversed(old_key_versions(environ))
    ]
    if not names:
        raise SealError(f"{ENV_KEY} is not set: the sealed value cannot be opened")
    keys = MultiFernet([_fernet(environ[name], name) for name in names])
    try:
        return keys.decrypt(value.removeprefix(SEALED_PREFIX).encode()).decode()
    except InvalidToken as error:
        raise SealError(
            f"no key among {', '.join(names)} opens the sealed value"
        ) from error
