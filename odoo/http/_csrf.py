from __future__ import annotations

import hashlib
import hmac
import time
from typing import Any

from odoo.libs.debug_log import DebugLog
from odoo.tools import consteq

from ._protocols import RequestState
from .constants import CSRF_TOKEN_MAX_AGE, STORED_SESSION_BYTES

_debug = DebugLog(__name__)


def _get_csrf_secret(env: Any) -> str:
    if env is None:
        raise RuntimeError("CSRF tokens need a database-bound request")
    secret = env["ir.config_parameter"].sudo().get_param("database.secret")
    if not secret:
        _debug.logic(
            "http.csrf.secret_missing",
            db=getattr(getattr(env, "registry", None), "db_name", None),
        )
        msg = "CSRF protection requires a configured database secret"
        raise ValueError(msg)
    return secret


def _get_csrf_digest(secret: str, sid: str, max_ts: int | str) -> str:
    payload = f"{sid[:STORED_SESSION_BYTES]}{max_ts}".encode()
    return hmac.new(secret.encode("ascii"), payload, hashlib.sha256).hexdigest()


class _RequestCsrfMixin(RequestState):
    def csrf_token(self, time_limit: int | None = None) -> str:
        secret = _get_csrf_secret(self.env)

        if time_limit is None:
            time_limit = CSRF_TOKEN_MAX_AGE
        max_ts = int(time.time() + time_limit)
        hm = _get_csrf_digest(secret, self.session.sid, max_ts)

        if self.session.is_new:
            self.session.mark_dirty()
        _debug.lifecycle(
            "http.csrf.token_issued",
            sid=self.session.sid[:8],
            ttl=time_limit,
            session_new=self.session.is_new,
        )
        return f"{hm}o{max_ts}"

    def is_valid_csrf(self, csrf: str | None) -> bool:
        if not isinstance(csrf, str) or not csrf:
            _debug.logic("http.csrf.malformed", reason="empty")
            return False

        secret = _get_csrf_secret(self.env)

        hm, _, max_ts = csrf.rpartition("o")
        if not max_ts:
            _debug.logic("http.csrf.malformed", reason="no_timestamp")
            return False
        try:
            if int(max_ts) < int(time.time()):
                _debug.logic("http.csrf.expired", sid=self.session.sid[:8])
                return False
        except ValueError:
            _debug.logic("http.csrf.malformed", reason="bad_timestamp")
            return False

        if not hm.isascii():
            _debug.logic("http.csrf.malformed", reason="non_ascii")
            return False

        valid = consteq(hm, _get_csrf_digest(secret, self.session.sid, max_ts))
        if not valid:
            _debug.logic("http.csrf.mismatch", sid=self.session.sid[:8])
        return valid
