import logging
import time
from collections.abc import Iterable
from typing import Any

import psycopg
import werkzeug.exceptions

import odoo.api
from odoo.libs.debug_log import DebugLog

from ._cookies import get_cookie_identity
from ._protocols import RequestState
from .constants import (
    SESSION_LIFETIME,
    SESSION_ROTATION_EXCLUDED_PATHS,
    SESSION_ROTATION_INTERVAL,
    prepare_default_session,
)
from .exceptions import SessionExpiredException
from .session import Session
from .wrappers import Response

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)


def get_session_max_inactivity(env: Any) -> int:
    if env is None or env.cr.closed:
        _debug.logic(
            "http.session.max_inactivity",
            source="no_env" if env is None else "cursor_closed",
        )
        return SESSION_LIFETIME

    ICP = env["ir.config_parameter"].sudo()

    try:
        value = int(ICP.get_param("sessions.max_inactivity_seconds", SESSION_LIFETIME))
        if value <= 0:
            _logger.warning(
                "Non-positive value for 'sessions.max_inactivity_seconds' "
                "(%r), using default value.",
                value,
            )
            _debug.logic("http.session.max_inactivity", source="non_positive")
            return SESSION_LIFETIME
        _debug.logic("http.session.max_inactivity", source="param", value=value)
        return value
    except ValueError:
        _logger.warning(
            "Invalid value for 'sessions.max_inactivity_seconds', using default value."
        )
        _debug.logic("http.session.max_inactivity", source="invalid")
        return SESSION_LIFETIME
    except psycopg.Error:
        _logger.debug(
            "Could not read session max inactivity from DB, using default.",
            exc_info=True,
        )
        _debug.logic("http.session.max_inactivity", source="db_error")
        return SESSION_LIFETIME


_UNIONED_HEADERS = frozenset({"vary"})


def _union_header_tokens(values: Iterable[str]) -> str:
    seen: dict[str, str] = {}
    for value in values:
        for token in value.split(","):
            token = token.strip()
            if token:
                seen.setdefault(token.lower(), token)
    if "*" in seen:
        return "*"
    return ", ".join(seen.values())


class _RequestSessionMixin(RequestState):
    def _select_session_and_dbname(
        self, sid: str | None = None
    ) -> tuple[Session, str | None]:
        session = self._load_session(sid)
        return session, self._select_dbname(session)

    def _load_session(self, sid: str | None = None) -> Session:
        root = self.app

        if sid is None:
            sid = self.httprequest.session_id
        with _debug.perf("http.session.load", has_cookie=bool(sid)) as span:
            if not sid or not root.session_store.is_valid_key(sid):
                session = root.session_store.new()
            else:
                session = root.session_store.get(sid)
            span.set(found=not session.is_new)

        for key, val in prepare_default_session().items():
            session.setdefault(key, val)
        if not isinstance(session.context, dict):
            session.context = {}
        if not session.context.get("lang"):
            session.context["lang"] = self.get_default_lang()
        if session.pop("_rotate_pending", None):
            session.should_rotate = True
        session.mark_clean()
        return session

    def _select_dbname(self, session: Session) -> str | None:
        root = self.app

        dbname = None
        source = "none"  # debuglog
        host = self.httprequest.environ.get("HTTP_HOST", "")
        header_dbname = self.httprequest.headers.get("X-Odoo-Database")
        if session.db and root.filter_dbs_served([session.db], host):
            dbname = session.db
            source = "session"  # debuglog
            if header_dbname and header_dbname != dbname:
                _debug.logic(
                    "http.session.db_conflict",
                    session_db=dbname,
                    header_db=header_dbname,
                )
                e = (
                    f"The session cookie is bound to database {dbname!r} and the "
                    f"X-Odoo-Database header names {header_dbname!r}. Send one or "
                    f"the other, or make them agree."
                )
                raise werkzeug.exceptions.Forbidden(e)
        elif header_dbname:
            session.can_save = False
            header_served = root.filter_dbs_served([header_dbname], host)
            _debug.logic(
                "http.session.header_db",
                header_db=header_dbname,
                accepted=bool(header_served),
            )
            if header_served:
                dbname = header_dbname
                source = "header"  # debuglog
        else:
            all_dbs = root.get_dbs_served(host)
            if len(all_dbs) == 1:
                dbname = all_dbs[0]
                source = "single"  # debuglog
            _debug.logic("http.session.db_inferred", candidates=len(all_dbs))

        if session.db != dbname:
            if session.db:
                _logger.warning(
                    "Logged into database %r, but dbfilter rejects it; logging session out.",
                    session.db,
                )
                _debug.logic(
                    "http.session.db_rejected", session_db=session.db, served_db=dbname
                )
                session.logout(keep_db=False)
            session.db = dbname
            session.mark_clean()

        _debug.logic(
            "http.session.selected",
            db=dbname,
            source=source,
            session_new=session.is_new,
            uid=session.uid,
            rotate=session.should_rotate,
        )
        return dbname

    def _bind_session_transaction(self, cr: Any) -> None:
        if self._session_transaction_cursor is cr:
            return
        self._session_transaction_cursor = cr
        self._session_save_pending = False
        self._session_response = None
        self._session_snapshot = self.session.snapshot()
        self._session_written_in_transaction = False
        cr.postcommit.add(self._flush_session)
        cr.postrollback.add(self._restore_session_snapshot)
        _debug.lifecycle("http.session.transaction_bound", uid=self.session.uid)

    def _restore_session_snapshot(self) -> None:
        snapshot = self._session_snapshot
        if snapshot is None:
            _debug.lifecycle("http.session.restore_skipped", reason="no_snapshot")
            return
        current = self.session
        if self._session_written_in_transaction:
            # An explicit-environment save persisted the session during the
            # attempt (a rotation may have replaced its file): the disk copy is
            # the identity the cookie must carry, the snapshot's file may be gone.
            restored = self._load_session(current.sid)
            source = "disk"  # debuglog
        else:
            restored = snapshot.snapshot()
            source = "snapshot"  # debuglog
        restored.can_save &= current.can_save
        self.session = restored
        self._session_save_pending = False
        self._session_transaction_cursor = None
        self._session_response = None
        _debug.lifecycle(
            "http.session.restored_on_rollback",
            source=source,
            uid=restored.uid,
            can_save=restored.can_save,
        )

    def _flush_session(self) -> None:
        self._session_transaction_cursor = None
        self._session_snapshot = None
        self._session_written_in_transaction = False
        _debug.pipeline(
            "http.session.flush",
            pending=self._session_save_pending,
            has_response=self._session_response is not None,
        )
        if not self._session_save_pending:
            return
        self._session_save_pending = False
        self._persist_session(self.env)
        if self._session_response is not None:
            self._update_response_from_future(self._session_response)

    def _get_session_max_age(self, env: odoo.api.Environment | None) -> int:
        # An error response is built after `_serve_db` released the cursor, so the
        # budget read while the environment was live is the one the cookie keeps.
        if env is not None and not env.cr.closed:
            self._session_max_age = get_session_max_inactivity(env)
        elif self._session_max_age is None:
            self._session_max_age = SESSION_LIFETIME
        return self._session_max_age

    def _is_periodic_rotation_due(self) -> bool:
        session = self.session
        return bool(
            session.uid
            and time.time() >= session["create_time"] + SESSION_ROTATION_INTERVAL
            and self.httprequest.path not in SESSION_ROTATION_EXCLUDED_PATHS
        )

    def _stage_session_save(self, env: odoo.api.Environment) -> None:
        session = self.session
        self._session_save_pending = True
        periodic_rotation = self._is_periodic_rotation_due()
        _debug.lifecycle(
            "http.session.save_staged",
            rotate=session.should_rotate,
            periodic=periodic_rotation,
        )
        if session.should_rotate or periodic_rotation:
            self.app.session_store.stage_rotation(
                session, env, soft=not session.should_rotate
            )

    def _update_response_from_future(self, response: Response) -> Response:
        headers = response.headers
        staged = self.future_response.headers

        staged_cookies = staged.getlist("Set-Cookie")
        if staged_cookies:
            staged_names = {get_cookie_identity(cookie) for cookie in staged_cookies}
            kept = [
                cookie
                for cookie in headers.getlist("Set-Cookie")
                if get_cookie_identity(cookie) not in staged_names
            ]
            headers.setlist("Set-Cookie", kept + staged_cookies)

        overridden: set[str] = set()
        for key, value in staged.items():
            lowered = key.lower()
            if lowered == "set-cookie":
                continue
            if lowered in _UNIONED_HEADERS:
                headers.set(key, _union_header_tokens([*headers.getlist(key), value]))
            elif lowered in overridden:
                headers.add(key, value)
            else:
                headers.set(key, value)
                overridden.add(lowered)
        _debug.pipeline(
            "http.response.future_applied",
            cookies=len(staged_cookies),
            headers=len(overridden),
            status=getattr(response, "status_code", None),
        )
        return response

    def _save_session(self, env: odoo.api.Environment | None = None) -> None:
        sess = self.session
        if env is None:
            env = self.env

        if not sess.can_save:
            _debug.logic("http.session.save_skipped", reason="cannot_save")
            return

        if (
            env is not None
            and self.env is not None
            and env.cr is self.env.cr
            and not env.cr.closed
        ):
            self._bind_session_transaction(env.cr)
            self._stage_session_save(env)
            _debug.pipeline("http.session.save_deferred", uid=sess.uid)
            return

        self._persist_session(env)

    def _persist_session(self, env: odoo.api.Environment | None) -> None:
        root = self.app

        sess = self.session
        if not sess.can_save:
            _debug.logic("http.session.save_skipped", reason="cannot_save")
            return

        max_age = self._get_session_max_age(env) if sess.uid else SESSION_LIFETIME
        stale = sess.mtime is not None and time.time() - sess.mtime > max_age / 2
        content_changed = sess.has_content_changed()
        modified = sess.is_dirty or content_changed or stale

        can_rotate = not sess.uid or (env is not None and not env.cr.closed)

        strategy = "none"  # debuglog
        try:
            if sess.should_rotate and can_rotate:
                root.session_store.rotate(sess, env)
                written = True
                strategy = "rotate"  # debuglog
            elif sess.should_rotate:
                sess["_rotate_pending"] = True
                root.session_store.save(sess)
                written = True
                strategy = "rotate_pending"  # debuglog
            elif can_rotate and self._is_periodic_rotation_due():
                root.session_store.rotate(sess, env, True)
                written = True
                strategy = "periodic_rotate"  # debuglog
            elif content_changed or (sess.is_dirty and sess.is_new):
                root.session_store.save(sess)
                written = True
                strategy = "save"  # debuglog
            elif sess.is_dirty or stale:
                root.session_store.keep_alive(sess)
                written = True
                strategy = "keep_alive"  # debuglog
            else:
                written = False
        except SessionExpiredException:
            sess.can_save = False
            _logger.info("Discarding a late save of a revoked session")
            _debug.logic("http.session.save_revoked", sid=sess.sid[:8])
            return
        except OSError:
            _logger.warning(
                "Could not persist session %r; keeping the current cookie",
                sess.sid,
                exc_info=True,
            )
            _debug.logic("http.session.save_failed", sid=sess.sid[:8])
            return

        if written and self._session_snapshot is not None:
            self._session_written_in_transaction = True
        on_disk = written or not sess.is_new
        cookie_sid = self.httprequest.session_id
        _debug.logic(
            "http.session.saved",
            strategy=strategy,
            written=written,
            modified=modified,
            content_changed=content_changed,
            stale=stale,
            rotate=sess.should_rotate,
            can_rotate=can_rotate,
            on_disk=on_disk,
            cookie_set=on_disk and (modified or cookie_sid != sess.sid),
        )

        if on_disk and (modified or cookie_sid != sess.sid):
            self.future_response.set_cookie(
                "session_id",
                sess.sid,
                max_age=max_age,
                expires=None,
                httponly=True,
            )
