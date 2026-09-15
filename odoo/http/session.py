import collections.abc
import copy
import logging
import time
from collections.abc import Iterator
from typing import Any

from odoo.libs.debug_log import DebugLog
from odoo.libs.json import dumps_bytes as _dumps_bytes
from odoo.libs.json import loads as _loads
from odoo.tools import get_lang

from ._protocols import get_ir_http
from .constants import DEFAULT_LANG, prepare_default_session
from .core import request

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)

_TRACE_MAX_ENTRIES = 50


_SESSION_JSON_PRIMITIVES = (str, int, float, bool, type(None))


def _merge_session_data(baseline: dict, local: dict, current: dict) -> dict:
    merged = dict(current)
    for key in baseline.keys() - local.keys():
        merged.pop(key, None)
    for key, value in local.items():
        if key in baseline and value == baseline[key]:
            continue
        before, latest = baseline.get(key), current.get(key)
        if (
            isinstance(before, dict)
            and isinstance(value, dict)
            and isinstance(latest, dict)
        ):
            merged[key] = _merge_session_data(before, value, latest)
        else:
            merged[key] = value
    return merged


def _coerce_session_value(value: Any) -> Any:
    if isinstance(value, _SESSION_JSON_PRIMITIVES):
        return value
    if isinstance(value, dict):
        coerced = {}
        for k, v in value.items():
            if not isinstance(k, str):
                raise TypeError(
                    f"Session dict keys must be str, got {type(k).__name__}: {k!r}"
                )
            coerced[k] = _coerce_session_value(v)
        return coerced
    if isinstance(value, (list, tuple)):
        return [_coerce_session_value(v) for v in value]
    raise TypeError(
        f"Session values must be JSON-serializable "
        f"(str/int/float/bool/None/list/dict/tuple), "
        f"got {type(value).__name__}: {value!r}"
    )


class Session(collections.abc.MutableMapping):
    __slots__ = (
        "_Session__baseline",
        "_Session__data",
        "can_save",
        "is_dirty",
        "is_new",
        "mtime",
        "rotation",
        "should_rotate",
        "sid",
        "store",
    )

    def __init__(self, data: dict[str, Any], sid: str, new: bool = False) -> None:
        self.can_save: bool = True
        self.__data: dict[str, Any] = dict(data)
        self.is_dirty: bool = False
        self.__baseline: bytes | None = None
        self.is_new: bool = new
        self.mtime: float | None = None
        self.should_rotate: bool = False
        self.rotation: tuple[Session, bool] | None = None
        self.sid: str = sid
        self.store: Any = None

    def snapshot(self) -> Session:
        snapshot = Session(copy.deepcopy(self.__data), self.sid, self.is_new)
        snapshot.__baseline = self.__baseline
        snapshot.can_save = self.can_save
        snapshot.is_dirty = self.is_dirty
        snapshot.mtime = self.mtime
        snapshot.should_rotate = self.should_rotate
        snapshot.store = self.store
        return snapshot

    def restore(self, snapshot: Session) -> None:
        self.__data = copy.deepcopy(snapshot.__data)
        self.__baseline = snapshot.__baseline
        self.sid = snapshot.sid
        self.is_new = snapshot.is_new
        self.is_dirty = snapshot.is_dirty
        self.mtime = snapshot.mtime
        self.can_save = snapshot.can_save
        self.should_rotate = snapshot.should_rotate
        self.rotation = None
        _debug.lifecycle(
            "http.session.restored", sid=self.sid[:8], uid=self.uid, is_new=self.is_new
        )

    def merge_changes(self, current: Session) -> None:
        _debug.logic(
            "http.session.merge",
            has_baseline=self.__baseline is not None,
            dirty=self.is_dirty,
        )
        if self.__baseline is None:
            return
        before = len(self.__data)  # debuglog
        self.__data = _merge_session_data(
            _loads(self.__baseline), self.__data, dict(current)
        )
        _debug.lifecycle(
            "http.session.merged", keys_before=before, keys_after=len(self.__data)
        )

    def __getitem__(self, item: str) -> Any:
        return self.__data[item]

    def __setitem__(self, item: str, value: Any) -> None:
        value = _coerce_session_value(value)
        if item not in self.__data or self.__data[item] != value:
            self.is_dirty = True
        self.__data[item] = value

    def __delitem__(self, item: str) -> None:
        del self.__data[item]
        self.is_dirty = True

    def __len__(self) -> int:
        return len(self.__data)

    def __iter__(self) -> Iterator[str]:
        return iter(self.__data)

    def clear(self) -> None:
        self.__data.clear()
        self.is_dirty = True

    @property
    def uid(self) -> int | None:
        return self.get("uid")

    @uid.setter
    def uid(self, uid: int | None) -> None:
        self["uid"] = uid

    @property
    def db(self) -> str | None:
        return self.get("db")

    @db.setter
    def db(self, db: str | None) -> None:
        self["db"] = db

    @property
    def login(self) -> str | None:
        return self.get("login")

    @login.setter
    def login(self, login: str | None) -> None:
        self["login"] = login

    @property
    def context(self) -> dict[str, Any] | None:
        return self.get("context")

    @context.setter
    def context(self, context: dict[str, Any] | None) -> None:
        self["context"] = context

    @property
    def debug(self) -> str:
        return self.get("debug") or ""

    @debug.setter
    def debug(self, debug: str | None) -> None:
        self["debug"] = debug

    @property
    def session_token(self) -> str | None:
        return self.get("session_token")

    @session_token.setter
    def session_token(self, session_token: str | None) -> None:
        self["session_token"] = session_token

    def authenticate(self, env: Any, credential: dict[str, Any]) -> dict[str, Any]:
        wsgienv = {
            "interactive": True,
            "base_location": request.httprequest.url_root.rstrip("/"),
            "HTTP_HOST": request.httprequest.environ.get("HTTP_HOST", ""),
            "REMOTE_ADDR": request.httprequest.environ.get("REMOTE_ADDR", ""),
        }
        env = env(user=None, su=False)
        with _debug.perf(
            "http.session.authenticate",
            cr=getattr(env, "cr", None),
            auth_type=credential.get("type"),
        ) as span:
            auth_info = env["res.users"].authenticate(credential, wsgienv)
            span.set(uid=auth_info["uid"])
        pre_uid = auth_info["uid"]

        self.uid = None
        self["pre_login"] = credential["login"]
        self["pre_uid"] = pre_uid

        user = env["res.users"].browse(pre_uid)
        mfa_required = auth_info.get("mfa") != "skip" and bool(user._get_mfa_url())
        _debug.logic(
            "http.session.authenticated",
            db=env.registry.db_name,
            uid=pre_uid,
            mfa_required=mfa_required,
            auth_type=credential.get("type"),
        )
        if not mfa_required:
            self.finalize_login(env)

        if request and request.session is self and request.db == env.registry.db_name:
            request.env = env(user=self.uid, context=self.context)
            request.update_context(lang=get_lang(request.env(user=pre_uid)).code)
            _debug.lifecycle("http.session.request_env_rebound", uid=self.uid)

        return auth_info

    def finalize_login(self, env: Any) -> None:
        login = self.pop("pre_login")
        uid = self.pop("pre_uid")

        env = env(user=uid)
        with _debug.perf(
            "http.session.finalize_login", cr=getattr(env, "cr", None), uid=uid
        ):
            user_context = dict(env["res.users"].context_get())

            self._require_hard_rotation()
            self.update(
                {
                    "db": env.registry.db_name,
                    "login": login,
                    "uid": uid,
                    "context": user_context,
                    "session_token": env.user._get_session_token(self.sid),
                }
            )
        _debug.lifecycle(
            "http.session.login_finalized",
            db=env.registry.db_name,
            uid=uid,
            context_keys=len(user_context),
        )

    def logout(self, keep_db: bool = False) -> None:
        _debug.lifecycle("http.session.logout", uid=self.uid, keep_db=keep_db)
        db = self.db if keep_db else None
        debug = self.debug
        self.clear()
        self.update(prepare_default_session(), db=db, debug=debug)
        context = self.context
        assert context is not None
        context["lang"] = request.get_default_lang() if request else DEFAULT_LANG
        self._require_hard_rotation()

        if request and request.env is not None:
            _debug.lifecycle("http.session.post_logout_hook", db=request.db)
            get_ir_http(request.env)._post_logout()

    def _require_hard_rotation(self) -> None:
        self.should_rotate = True
        _debug.logic(
            "http.session.hard_rotation_required",
            staged=self.rotation is not None,
            staged_soft=self.rotation is not None and self.rotation[1],
        )
        if self.rotation is not None:
            original, soft = self.rotation
            if soft:
                # Leave the old family as well as its cookie. A stale request's
                # family cleanup must not be able to delete the logged-in or
                # logged-out successor of this authentication transition.
                self.sid = self.store.generate_key()
                self.pop("gc_previous_sessions", None)
            self.rotation = (original, False)

    def mark_dirty(self) -> None:
        self.is_dirty = True

    def mark_clean(self) -> None:
        self.is_dirty = False
        self.__baseline = _dumps_bytes(self.__data)

    def has_content_changed(self) -> bool:
        if self.__baseline is None:
            return self.is_dirty
        return _dumps_bytes(self.__data) != self.__baseline

    def is_modified(self) -> bool:
        return self.is_dirty or self.has_content_changed()

    def update_trace(self, request: Any) -> dict[str, Any] | None:
        if self.get("_trace_disable"):
            return None

        user_agent = request.httprequest.user_agent
        platform = user_agent.platform
        browser = user_agent.browser
        ip_address = request.httprequest.remote_addr
        now = int(time.time())
        for trace in self["_trace"]:
            if (
                trace["platform"] == platform
                and trace["browser"] == browser
                and trace["ip_address"] == ip_address
            ):
                if now - trace["last_activity"] >= 3600:
                    trace["last_activity"] = now
                    self.is_dirty = True
                    _debug.lifecycle("http.session.trace_refreshed", browser=browser)
                    return trace
                return None
        new_trace = {
            "platform": platform,
            "browser": browser,
            "ip_address": ip_address,
            "first_activity": now,
            "last_activity": now,
        }
        self["_trace"].append(new_trace)
        if len(self["_trace"]) > _TRACE_MAX_ENTRIES:
            oldest_idx = min(
                range(len(self["_trace"])),
                key=lambda i: self["_trace"][i]["last_activity"],
            )
            del self["_trace"][oldest_idx]
            _debug.lifecycle("http.session.trace_evicted", traces=len(self["_trace"]))
        self.is_dirty = True
        _debug.lifecycle(
            "http.session.trace_added", browser=browser, traces=len(self["_trace"])
        )
        return new_trace

    def _remove_old_sessions(self) -> None:
        if self.store is None:
            return
        self.store.remove_old_sessions(self)
