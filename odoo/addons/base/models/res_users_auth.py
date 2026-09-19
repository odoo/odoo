from __future__ import annotations

import hmac
import logging
import typing
from hashlib import sha256

from odoo.libs.debug_log import DebugLog
from odoo.libs.password import _MAX_ROUNDS, CryptContext

if typing.TYPE_CHECKING:
    from odoo.orm.runtime import Environment

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)

MIN_ROUNDS = 600_000


class PasswordStore:
    __slots__ = ("env",)

    def __init__(self, env: Environment) -> None:
        self.env = env

    def crypt_context(self) -> CryptContext:
        raw = self.env.registry.settings.get(self.env, "password.hashing.rounds", 0)
        try:
            configured = int(raw)
        except TypeError, ValueError:
            _logger.warning(
                "Ignoring non-numeric password.hashing.rounds %r; using %d",
                raw,
                MIN_ROUNDS,
            )
            configured = 0
        rounds = min(_MAX_ROUNDS, max(MIN_ROUNDS, configured))
        _debug.logic(
            "crypt_context_built",
            configured=configured,
            rounds=rounds,
            clamped=rounds != configured,
        )
        return CryptContext(
            ["pbkdf2_sha512", "plaintext"],
            deprecated=["auto"],
            pbkdf2_sha512__rounds=rounds,
        )

    def stored_hash(self, users, uid: int) -> str | None:
        stored = self.env.backend.columns.read(users.sudo(), "password", [uid])
        return stored.get(uid, None) if uid in stored else None

    def match_and_update(
        self, users, uid: int, password: str
    ) -> tuple[bool, str | None]:
        hashed = self.stored_hash(users, uid)
        if hashed is None:
            _debug.logic("password_match_skipped", uid=uid, reason="no_hash")
            return False, None
        with _debug.perf("password_matched", uid=uid) as span:
            valid, replacement = users._get_crypt_context().match_and_update(
                password, hashed or ""
            )
            span.set(valid=valid, rehashed=replacement is not None)
        return valid, replacement

    def store(self, users, hashed: typing.Collection[tuple[int, str]]) -> None:
        if not hashed:
            return
        ctx = users._get_crypt_context()
        if any(ctx.identify(pw) == "plaintext" for _uid, pw in hashed):
            _debug.logic(
                "password_store_refused", reason="plaintext", count=len(hashed)
            )
            msg = "Refusing to store a plaintext password -- encrypt first."
            raise ValueError(msg)
        _debug.lifecycle("password_hashes_stored", count=len(hashed))
        self.env.backend.columns.write(users.sudo(), "password", hashed)

    def clear(self, users) -> None:
        _debug.lifecycle("password_hashes_cleared", users=users.ids)
        self.env.backend.columns.write(
            users.sudo(), "password", [(uid, None) for uid in users.ids]
        )


def session_token(
    sid: str, field_values: tuple[tuple[str, typing.Any], ...] | bool
) -> str | bool:
    if not field_values:
        _debug.logic("session_token_skipped", reason="no_field_values")
        return False
    key_tuple = tuple((k, v) for k, v in field_values if v is not None)
    key = str(key_tuple).encode()
    return hmac.new(key, sid.encode(), sha256).hexdigest()
