import binascii
import hashlib
import hmac
import os
import re
from base64 import b64decode, b64encode

from odoo.libs.debug_log import DebugLog

__all__ = ["CryptContext", "pbkdf2_sha512_hash"]

_debug = DebugLog(__name__)

_DEFAULT_ROUNDS = 600_000
_MAX_ROUNDS = 10_000_000
_SALT_SIZE = 16
_HASH_SIZE = 64
_MCF_RE = re.compile(r"^\$pbkdf2-sha512\$(\d+)\$([^$]+)\$([^$]+)$")


def _ab64_encode(data: bytes) -> str:
    return b64encode(data).rstrip(b"=").replace(b"+", b".").decode("ascii")


def _ab64_decode(data: str) -> bytes:
    b = data.replace(".", "+").encode("ascii")
    b += b"=" * (-len(b) % 4)
    return b64decode(b)


def _pbkdf2_sha512(password: str, salt: bytes, rounds: int) -> bytes:
    return hashlib.pbkdf2_hmac(
        "sha512", password.encode("utf-8"), salt, rounds, dklen=_HASH_SIZE
    )


def _check_rounds(rounds: int) -> None:
    if not 0 < rounds <= _MAX_ROUNDS:
        raise ValueError(f"pbkdf2_sha512__rounds must be in (0, {_MAX_ROUNDS}]")


def _format_hash(rounds: int, salt: bytes, checksum: bytes) -> str:
    return f"$pbkdf2-sha512${rounds}${_ab64_encode(salt)}${_ab64_encode(checksum)}"


def _parse_hash(hash_str: str) -> tuple[int, bytes, bytes] | None:
    m = _MCF_RE.match(hash_str)
    if not m:
        return None
    try:
        rounds = int(m.group(1))
        if not 0 < rounds <= _MAX_ROUNDS:
            return None
        return rounds, _ab64_decode(m.group(2)), _ab64_decode(m.group(3))
    except binascii.Error, ValueError:
        return None


def pbkdf2_sha512_hash(password: str, rounds: int = _DEFAULT_ROUNDS) -> str:
    salt = os.urandom(_SALT_SIZE)
    with _debug.perf("password.hash", rounds=rounds):
        checksum = _pbkdf2_sha512(password, salt, rounds)
    return _format_hash(rounds, salt, checksum)


class CryptContext:
    def __init__(
        self,
        schemes: list[str] | None = None,
        *,
        deprecated: list[str] | None = None,
        **kwargs: object,
    ) -> None:
        if isinstance(schemes, str):
            schemes = [schemes]
        self._schemes = list(schemes) if schemes else ["pbkdf2_sha512"]
        self._deprecated = set(deprecated) if deprecated else set()
        rounds = kwargs.get("pbkdf2_sha512__rounds", _DEFAULT_ROUNDS)
        assert isinstance(rounds, int), "pbkdf2_sha512__rounds must be an int"
        _check_rounds(rounds)
        self._rounds = rounds

    def hash(self, password: str) -> str:
        return pbkdf2_sha512_hash(password, self._rounds)

    def is_password_valid(self, password: str, hash_str: str) -> bool:
        parsed = _parse_hash(hash_str)
        if parsed:
            if "pbkdf2_sha512" not in self._schemes:
                _debug.logic("password.verify", scheme="pbkdf2_sha512", accepted=False)
                return False
            rounds, salt, expected = parsed
            with _debug.perf("password.verify", scheme="pbkdf2_sha512", rounds=rounds):
                actual = _pbkdf2_sha512(password, salt, rounds)
            return hmac.compare_digest(actual, expected)
        if self.identify(hash_str) == "pbkdf2_sha512":
            _debug.logic("password.verify", scheme="pbkdf2_sha512", malformed=True)
            return False
        if "plaintext" in self._schemes:
            _debug.logic("password.verify", scheme="plaintext", accepted=True)
            return hmac.compare_digest(
                password.encode("utf-8"), hash_str.encode("utf-8")
            )
        _debug.logic("password.verify", scheme="plaintext", accepted=False)
        return False

    def match_and_update(self, password: str, hash_str: str) -> tuple[bool, str | None]:
        if not self.is_password_valid(password, hash_str):
            return False, None

        needs_update = False
        scheme = self.identify(hash_str)

        if self._deprecated:
            if "auto" in self._deprecated:
                if scheme != self._schemes[0]:
                    needs_update = True
            elif scheme in self._deprecated:
                needs_update = True

        if scheme == "pbkdf2_sha512" and not needs_update:
            parsed = _parse_hash(hash_str)
            if parsed and parsed[0] != self._rounds:
                needs_update = True

        _debug.logic(
            "password.match_and_update",
            scheme=scheme,
            deprecated=scheme in self._deprecated or "auto" in self._deprecated,
            needs_update=needs_update,
            rounds=self._rounds,
        )
        replacement = self.hash(password) if needs_update else None
        return True, replacement

    def identify(self, hash_str: str) -> str:
        if hash_str and hash_str.startswith("$pbkdf2-sha512$"):
            return "pbkdf2_sha512"
        return "plaintext"

    def schemes(self) -> list[str]:
        return list(self._schemes)

    def update(self, **kwargs: object) -> None:
        if "schemes" in kwargs:
            schemes = kwargs["schemes"]
            if isinstance(schemes, str):
                schemes = [schemes]
            assert isinstance(schemes, list | tuple | set), "schemes must be a sequence"
            assert all(isinstance(s, str) for s in schemes)
            self._schemes = list(schemes)
        if "deprecated" in kwargs:
            dep = kwargs["deprecated"]
            assert dep is None or isinstance(dep, list | tuple | set), (
                "deprecated must be a sequence"
            )
            self._deprecated = set(dep) if dep else set()
        if "pbkdf2_sha512__rounds" in kwargs:
            new_rounds = kwargs["pbkdf2_sha512__rounds"]
            assert isinstance(new_rounds, int), "pbkdf2_sha512__rounds must be an int"
            _check_rounds(new_rounds)
            self._rounds = new_rounds
        _debug.lifecycle(
            "password.context_updated",
            schemes=",".join(self._schemes),
            deprecated=",".join(sorted(self._deprecated)) or None,
            rounds=self._rounds,
        )

    def copy(self) -> CryptContext:
        return CryptContext(
            self._schemes,
            deprecated=sorted(self._deprecated),
            pbkdf2_sha512__rounds=self._rounds,
        )
