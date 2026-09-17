import contextlib
import functools
import logging
import re
import secrets
from collections.abc import Callable
from typing import Any

import babel.core
import werkzeug.datastructures

import odoo
from odoo.libs.debug_log import DebugLog
from odoo.libs.json import loads as _fast_loads
from odoo.libs.worker_thread import current_worker_thread
from odoo.modules.registry import Registry
from odoo.tools import profiler

from ._cookies import FutureResponse
from ._csrf import _RequestCsrfMixin
from ._protocols import get_ir_http
from ._response import _RequestResponseMixin
from ._serve import _RequestServeMixin
from ._session_lifecycle import _RequestSessionMixin
from .constants import DEFAULT_LANG
from .dispatcher import _dispatchers
from .geoip import GeoIP
from .session import Session
from .wrappers import HTTPRequest, Response

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)

_REQUEST_ID_RE = re.compile(r"[A-Za-z0-9._:-]{1,200}")


def _get_request_id(httprequest: Any) -> str:
    headers = getattr(httprequest, "headers", None)
    offered = headers.get("X-Request-Id") if headers is not None else None
    if offered and _REQUEST_ID_RE.fullmatch(offered):
        return offered
    minted = secrets.token_urlsafe(9)
    if offered:
        _debug.logic(
            "http.request.id_replaced",
            offered_length=len(offered),
            minted=minted,
        )
    return minted


class Request(
    _RequestServeMixin,
    _RequestResponseMixin,
    _RequestCsrfMixin,
    _RequestSessionMixin,
):
    def __init__(self, httprequest: HTTPRequest, app: Any) -> None:
        self.app = app

        self.httprequest: HTTPRequest = httprequest
        self.id: str = _get_request_id(httprequest)
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
        self._session_snapshot: Session | None = None
        self._session_written_in_transaction = False
        self._session_max_age: int | None = None
        self._session_response: Response | None = None
        self._session_save_pending = False

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
        *,
        anonymous: bool = False,
    ) -> None:
        env = self.env
        if env is None:
            raise RuntimeError("update_env() needs a database-bound request")
        if anonymous:
            if user is not None:
                raise RuntimeError("anonymous=True and user= are exclusive")
            env = odoo.api.Environment(
                env.cr, None, env.context if context is None else context
            )
        else:
            env = env(None, user, context, su)
        self.env = env
        env.transaction.default_env = env
        current_worker_thread().uid = env.uid
        _debug.lifecycle("http.request.env_updated", uid=env.uid, su=env.su)

    def update_context(self, **overrides: Any) -> None:
        env = self.env
        if env is None:
            raise RuntimeError("update_context() needs a database-bound request")
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
            get_ir_http(registry)._update_cookies(cookies)
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

    def prepare_default_context(self) -> dict[str, Any]:
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
