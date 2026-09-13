import contextlib
import functools
import logging
import time
from collections.abc import Callable, Iterable
from typing import Any

import babel.core
import werkzeug.datastructures
import werkzeug.exceptions

import odoo
from odoo.libs.debug_log import DebugLog
from odoo.libs.json import loads as _fast_loads
from odoo.libs.worker_thread import current_worker_thread
from odoo.modules.registry import Registry
from odoo.tools import profiler

from ._csrf import _RequestCsrfMixin
from ._protocols import get_ir_http
from ._response import _RequestResponseMixin
from ._serve import _RequestServeMixin
from .constants import (
    DEFAULT_LANG,
    SESSION_LIFETIME,
    SESSION_ROTATION_EXCLUDED_PATHS,
    SESSION_ROTATION_INTERVAL,
    prepare_default_session,
)
from .dispatcher import _dispatchers
from .exceptions import SessionExpiredException
from .geoip import GeoIP
from .helpers import get_session_max_inactivity
from .session import Session
from .wrappers import FutureResponse, HTTPRequest, Response, get_cookie_identity

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)

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


class Request(_RequestServeMixin, _RequestResponseMixin, _RequestCsrfMixin):
    def __init__(self, httprequest: HTTPRequest, app: Any) -> None:
        self.app = app

        self.httprequest: HTTPRequest = httprequest
        self.future_response: FutureResponse = FutureResponse()
        self.dispatcher = _dispatchers["http"](self)
        self._params: dict[str, Any] = {}
        self._params_source: Callable[[], dict[str, Any]] | None = None

        self.geoip: GeoIP = GeoIP(httprequest.remote_addr, app=app)
        self.registry: Registry | None = None
        self.env: odoo.api.Environment | None = None
        self._post_init_done: bool = False
        self.database_detached: bool = False
        self._cookies_memo: tuple[bool, Any] | None = None
        self._json_memo: tuple[HTTPRequest, Any] | None = None
        self._session_transaction_cursor: Any = None
        self._session_response: Response | None = None
        self._session_save_pending = False
        self._session_uses_transactions = False
        self._session_flush_active = False

    def detach_database(self) -> None:
        self.database_detached = True
        _debug.lifecycle(
            "http.request.database_detached",
            db=self.db,
            cursor_open=self.env is not None and not self.env.cr.closed,
        )
        if self.env is not None and not self.env.cr.closed:
            self.env.cr.close()

    def _post_init(self) -> None:
        if self._post_init_done:
            return
        self.session, self.db = self._select_session_and_dbname()
        self._post_init_done = True

    def _select_session_and_dbname(
        self, sid: str | None = None
    ) -> tuple[Session, str | None]:
        from odoo import http

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

        dbname = None
        source = "none"  # debuglog
        host = self.httprequest.environ.get("HTTP_HOST", "")
        header_dbname = self.httprequest.headers.get("X-Odoo-Database")
        if session.db and http.filter_dbs_served([session.db], host=host):
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
            if http.filter_dbs_served([header_dbname], host=host):
                dbname = header_dbname
                source = "header"  # debuglog
            else:
                _debug.logic("http.session.header_db_rejected", header_db=header_dbname)
        else:
            all_dbs = http.get_dbs_served(force=True, host=host)
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
        return session, dbname

    @property
    def params(self) -> dict[str, Any]:
        source = self._params_source
        if source is not None:
            self._params_source = None
            self._params = source()
            _debug.lifecycle(
                "http.request.params_materialized", params=len(self._params)
            )
        return self._params

    @params.setter
    def params(self, params: dict[str, Any]) -> None:
        self._params_source = None
        self._params = params

    def update_env(
        self,
        user: int | Any | None = None,
        context: dict[str, Any] | None = None,
        su: bool | None = None,
    ) -> None:
        env = self.env
        assert env is not None, "update_env() needs a database-bound request"
        self.env = env = env(None, user, context, su)
        env.transaction.default_env = env
        current_worker_thread().uid = env.uid
        _debug.lifecycle("http.request.env_updated", uid=env.uid, su=env.su)

    def update_context(self, **overrides: Any) -> None:
        env = self.env
        assert env is not None, "update_context() needs a database-bound request"
        context = env.context | overrides
        if context == env.context and env.transaction.default_env is env:
            _debug.lifecycle("http.request.context_unchanged", keys=len(overrides))
            return
        self.update_env(context=context)

    @functools.cached_property
    def best_lang(self):
        lang = self.httprequest.accept_languages.best
        if not lang:
            return None

        try:
            code, territory = babel.core.parse_locale(lang, sep="-")[:2]
            if territory:
                lang = f"{code}_{territory}"
            else:
                lang = babel.core.LOCALE_ALIASES[code]
            _debug.logic("http.lang.negotiated", lang=lang, territory=bool(territory))
            return lang
        except ValueError, KeyError:
            _debug.logic("http.lang.unparsed", header=lang)
            return None

    @property
    def cookies(self):
        registry = self.registry
        sanitized = registry is not None
        memo = self._cookies_memo
        if memo is not None and memo[0] is sanitized:
            return memo[1]

        cookies = werkzeug.datastructures.MultiDict(self.httprequest.cookies)
        if registry is not None:
            get_ir_http(registry)._sanitize_cookies(cookies)
            _debug.logic(
                "http.cookies.sanitized",
                before=len(self.httprequest.cookies),
                after=len(cookies),
            )
        result = werkzeug.datastructures.ImmutableMultiDict(cookies)
        self._cookies_memo = (sanitized, result)
        return result

    @cookies.setter
    def cookies(self, value: Any) -> None:
        self._cookies_memo = (
            self.registry is not None,
            werkzeug.datastructures.ImmutableMultiDict(value),
        )

    def get_default_context(self) -> dict[str, Any]:
        return {"lang": self.get_default_lang()}

    def get_default_lang(self) -> str:
        return self.best_lang or DEFAULT_LANG

    def get_http_params(self) -> dict[str, Any]:
        return {
            **self.httprequest.args,
            **self.httprequest.form,
            **self.httprequest.files,
        }

    def get_json_data(self) -> Any:
        memo = self._json_memo
        if memo is not None and memo[0] is self.httprequest:
            _debug.perf.count("http.json.body", cached=True)
            return memo[1]
        _debug.perf.count(
            "http.json.body",
            bytes=getattr(self.httprequest, "content_length", None),
            cached=False,
        )
        data = _fast_loads(self.httprequest.get_data())
        self._json_memo = (self.httprequest, data)
        return data

    def _profile_request(self) -> contextlib.AbstractContextManager:
        if self.session.get("profile_session") and self.db:
            if self.session.get("profile_expiration", "") < str(
                odoo.fields.Datetime.now()
            ):
                self.session["profile_session"] = None
                _logger.warning("Profiling expiration reached, disabling profiling")
                _debug.logic("http.profiler.skipped", reason="expired")
            elif "set_profiling" in self.httprequest.path:
                _logger.debug("Profiling disabled on set_profiling route")
                _debug.logic("http.profiler.skipped", reason="set_profiling_route")
            elif self.httprequest.path.startswith("/websocket"):
                _logger.debug("Profiling disabled for websocket")
                _debug.logic("http.profiler.skipped", reason="websocket")
            elif odoo.evented:
                _logger.debug("Profiling disabled for evented server")
                _debug.logic("http.profiler.skipped", reason="evented")
            else:
                try:
                    _debug.logic(
                        "http.profiler.enabled",
                        db=self.db,
                        collectors=len(self.session.get("profile_collectors", [])),
                    )
                    return profiler.Profiler(
                        db=self.db,
                        description=self.httprequest.full_path,
                        profile_session=self.session["profile_session"],
                        collectors=self.session.get("profile_collectors", []),
                        params=self.session.get("profile_params", {}),
                    )._get_cm_proxy()
                except Exception:
                    _logger.exception("Failure during Profiler creation")
                    self.session["profile_session"] = None
                    _debug.logic("http.profiler.skipped", reason="creation_failed")

        return contextlib.nullcontext()

    def _reset_for_replay(self, cr: Any = None) -> None:
        _debug.lifecycle(
            "http.request.reset_for_replay",
            explicit_cursor=cr is not None,
            has_env=self.env is not None,
        )
        self.future_response = FutureResponse()
        self.params = {}
        self._cookies_memo = None
        self.__dict__.pop("_response_version", None)
        if cr is None and self.env is not None:
            cr = self.env.cr
        if cr is not None:
            self.env = odoo.api.Environment(
                cr, self.session.uid, self.session.context or {}
            )
            self._bind_session_transaction(cr)

    def _bind_session_transaction(self, cr: Any) -> None:
        if self._session_transaction_cursor is cr:
            return
        self._session_transaction_cursor = cr
        self._session_uses_transactions = True
        self._session_save_pending = False
        self._session_response = None
        original = self.session.snapshot()
        cr.postcommit.add(self._flush_session)
        _debug.lifecycle("http.session.transaction_bound", uid=self.session.uid)

        def restore_session() -> None:
            can_save = self.session.can_save
            self.session = original.snapshot()
            self.session.can_save &= can_save
            self._session_save_pending = False
            self._session_transaction_cursor = None
            self._session_response = None
            _debug.lifecycle(
                "http.session.restored_on_rollback",
                uid=self.session.uid,
                can_save=self.session.can_save,
            )

        cr.postrollback.add(restore_session)

    def _flush_session(self) -> None:
        self._session_transaction_cursor = None
        _debug.pipeline(
            "http.session.flush",
            pending=self._session_save_pending,
            has_response=self._session_response is not None,
        )
        if not self._session_save_pending:
            return
        self._session_save_pending = False
        self._session_flush_active = True
        try:
            self._save_session()
        finally:
            self._session_flush_active = False
        if self._session_response is not None:
            self._update_response_from_future(self._session_response)

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
        root = self.app

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
            and self._session_uses_transactions
            and not self._session_flush_active
            and not env.cr.closed
        ):
            self._bind_session_transaction(env.cr)
            self._stage_session_save(env)
            _debug.pipeline("http.session.save_deferred", uid=sess.uid)
            return

        max_age = get_session_max_inactivity(env) if sess.uid else SESSION_LIFETIME
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
