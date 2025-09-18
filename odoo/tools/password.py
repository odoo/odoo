"""Pure-stdlib password hashing compatible with passlib's $pbkdf2-sha512$ format.

Replaces passlib (abandoned since 2020, broken on Python 3.13+) with ~100 lines
of stdlib code. All existing password hashes in databases remain valid.
"""

import hashlib
import hmac
import os
import re
from base64 import b64decode, b64encode

__all__ = ["CryptContext", "pbkdf2_sha512_hash"]

# Default PBKDF2 parameters matching passlib defaults
_DEFAULT_ROUNDS = 600_000
_SALT_SIZE = 16  # 16 bytes = 128 bits
_HASH_SIZE = 64  # SHA-512 digest = 64 bytes
_MCF_RE = re.compile(r"^\$pbkdf2-sha512\$(\d+)\$([^$]+)\$([^$]+)$")


def _ab64_encode(data: bytes) -> str:
    """Encode bytes using passlib's 'adapted base64' (. instead of +, no padding)."""
    return b64encode(data).rstrip(b"=").replace(b"+", b".").decode("ascii")


def _ab64_decode(data: str) -> bytes:
    """Decode passlib's 'adapted base64' back to bytes."""
    b = data.replace(".", "+").encode("ascii")
    b += b"=" * (4 - len(b) % 4)  # restore padding
    return b64decode(b)


def _pbkdf2_sha512(password: str, salt: bytes, rounds: int) -> bytes:
    """Raw PBKDF2-SHA512 hash."""
    return hashlib.pbkdf2_hmac(
        "sha512", password.encode("utf-8"), salt, rounds, dklen=_HASH_SIZE
    )


def _format_hash(rounds: int, salt: bytes, checksum: bytes) -> str:
    """Format as passlib-compatible MCF string."""
    return f"$pbkdf2-sha512${rounds}${_ab64_encode(salt)}${_ab64_encode(checksum)}"


def _parse_hash(hash_str: str):
    """Parse MCF hash string, returns (rounds, salt_bytes, checksum_bytes) or None."""
    m = _MCF_RE.match(hash_str)
    if not m:
        return None
    return int(m.group(1)), _ab64_decode(m.group(2)), _ab64_decode(m.group(3))


def pbkdf2_sha512_hash(password: str, rounds: int = _DEFAULT_ROUNDS) -> str:
    """Hash a password using PBKDF2-SHA512. Returns MCF-formatted string."""
    salt = os.urandom(_SALT_SIZE)
    checksum = _pbkdf2_sha512(password, salt, rounds)
    return _format_hash(rounds, salt, checksum)


class CryptContext:
    """Minimal CryptContext supporting pbkdf2_sha512 + plaintext schemes.

    API-compatible with the subset of passlib.context.CryptContext used by Odoo.
    """

    def __init__(self, schemes=None, *, deprecated=None, _autoload=True, **kwargs):
        self._schemes = list(schemes) if schemes else ["pbkdf2_sha512"]
        self._deprecated = set(deprecated) if deprecated else set()
        self._rounds = kwargs.get("pbkdf2_sha512__rounds", _DEFAULT_ROUNDS)

    def hash(self, password: str) -> str:
        """Hash a password using the primary scheme (pbkdf2_sha512)."""
        return pbkdf2_sha512_hash(password, self._rounds)

    def verify(self, password: str, hash_str: str) -> bool:
        """Verify a password against a hash."""
        parsed = _parse_hash(hash_str)
        if parsed:
            rounds, salt, expected = parsed
            actual = _pbkdf2_sha512(password, salt, rounds)
            return hmac.compare_digest(actual, expected)
        # plaintext fallback
        if "plaintext" in self._schemes:
            return hmac.compare_digest(
                password.encode("utf-8"), hash_str.encode("utf-8")
            )
        return False

    def verify_and_update(self, password: str, hash_str: str) -> tuple:
        """Verify password and return (valid, replacement_hash_or_None).

        Returns a new hash if the current hash uses deprecated settings
        (wrong scheme or different round count).
        """
        if not self.verify(password, hash_str):
            return False, None

        needs_update = False
        scheme = self.identify(hash_str)

        # Check if scheme is deprecated
        if self._deprecated:
            if "auto" in self._deprecated:
                # 'auto' means everything except the primary scheme is deprecated
                if scheme != self._schemes[0]:
                    needs_update = True
            elif scheme in self._deprecated:
                needs_update = True

        # Check if rounds need updating (only for pbkdf2_sha512)
        if scheme == "pbkdf2_sha512" and not needs_update:
            parsed = _parse_hash(hash_str)
            if parsed and parsed[0] != self._rounds:
                needs_update = True

        replacement = self.hash(password) if needs_update else None
        return True, replacement

    def identify(self, hash_str: str) -> str:
        """Identify the scheme used in a hash string."""
        if hash_str and hash_str.startswith("$pbkdf2-sha512$"):
            return "pbkdf2_sha512"
        return "plaintext"

    def schemes(self) -> list:
        """Return list of configured schemes."""
        return list(self._schemes)

    def update(self, **kwargs):
        """Update context configuration."""
        if "schemes" in kwargs:
            schemes = kwargs["schemes"]
            if isinstance(schemes, str):
                schemes = [schemes]
            assert all(isinstance(s, str) for s in schemes)
            self._schemes = list(schemes)
        if "deprecated" in kwargs:
            dep = kwargs["deprecated"]
            self._deprecated = set(dep) if dep else set()
        if "pbkdf2_sha512__rounds" in kwargs:
            self._rounds = kwargs["pbkdf2_sha512__rounds"]

    def copy(self):
        """Create a copy of this context with the same configuration."""
        ctx = CryptContext.__new__(CryptContext)
        ctx._schemes = list(self._schemes)
        ctx._deprecated = set(self._deprecated)
        ctx._rounds = self._rounds
        return ctx
