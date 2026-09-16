import io
import sys
from types import ModuleType
from typing import Any
from unittest import mock

import werkzeug.utils

import odoo.http
from odoo.exceptions import AccessDenied
from odoo.http import Controller, Response, request
from odoo.http._session_store import FilesystemSessionStore
from odoo.http.application import Application
from odoo.http.exceptions import SessionExpiredException
from odoo.http.routing import _generate_routing_rules, prepare_routing_map
from odoo.http.session import Session
from odoo.libs.func import Callbacks

PUBLIC_UID = 3
DB = "wsgi_probe_db"


def environ(
    path: str = "/",
    method: str = "GET",
    *,
    body: bytes = b"",
    content_type: str | None = None,
    cookies: dict[str, str] | None = None,
    headers: dict[str, str] | None = None,
    query: str = "",
) -> dict[str, Any]:
    env: dict[str, Any] = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "QUERY_STRING": query,
        "SERVER_NAME": "localhost",
        "SERVER_PORT": "8069",
        "SERVER_PROTOCOL": "HTTP/1.1",
        "HTTP_HOST": "localhost:8069",
        "REMOTE_ADDR": "127.0.0.1",
        "wsgi.url_scheme": "http",
        "wsgi.input": io.BytesIO(body),
        "wsgi.errors": io.BytesIO(),
        "wsgi.multithread": True,
        "wsgi.multiprocess": False,
        "wsgi.run_once": False,
        "wsgi.version": (1, 0),
    }
    if body or content_type:
        env["CONTENT_LENGTH"] = str(len(body))
        env["CONTENT_TYPE"] = content_type or "application/x-www-form-urlencoded"
    if cookies:
        env["HTTP_COOKIE"] = "; ".join(f"{k}={v}" for k, v in cookies.items())
    for key, value in (headers or {}).items():
        env["HTTP_" + key.upper().replace("-", "_")] = value
    return env


class FakeCursor:
    def __init__(self, readonly: bool = False) -> None:
        self.readonly = readonly
        self.closed = False
        self.commit_count = 0
        self.rollbacks = 0
        self.sql_statement_count = 0
        self.postcommit = Callbacks()
        self.postrollback = Callbacks()
        self.pin_key: object = None
        self.statement_timeouts: list[float | None] = []

    def set_statement_timeout(self, seconds: float | None) -> None:
        self.statement_timeouts.append(seconds)

    def commit(self) -> None:
        self.commit_count += 1
        self.postcommit.run()
        self.postrollback.clear()

    def rollback(self) -> None:
        self.rollbacks += 1
        self.postrollback.run()
        self.postcommit.clear()

    def flush(self) -> None:
        pass

    def close(self) -> None:
        self.closed = True


class FakeTransaction:
    def __init__(self) -> None:
        self.default_env: Any = None
        self.resets = 0

    def reset(self) -> None:
        self.resets += 1


class FakeConfigParameter:
    def __init__(self, params: dict[str, Any]) -> None:
        self._params = params

    def sudo(self) -> FakeConfigParameter:
        return self

    def get_param(self, key: str, default: Any = None) -> Any:
        return self._params.get(key, default)


class FakeUser:
    def __init__(self, uid: int | None) -> None:
        self.id = uid

    def _get_session_token(self, sid: str) -> str:
        return f"token-{self.id}-{sid[:6]}"

    def _is_public(self) -> bool:
        return self.id in (None, PUBLIC_UID)


class FakeUsers:
    def browse(self, uid: int | None) -> FakeUser:
        return FakeUser(uid)


class FakeEnv:
    def __init__(
        self,
        cr: FakeCursor,
        uid: int | None,
        context: dict[str, Any] | None,
        su: bool = False,
        registry: FakeRegistry | None = None,
    ) -> None:
        self.cr = cr
        self.uid = uid
        self.context = dict(context or {})
        self.su = su
        self.registry = registry if registry is not None else FakeRegistry.current
        self.transaction = self.registry.transactions.setdefault(
            id(cr), FakeTransaction()
        )
        self.user = FakeUser(uid)

    def __call__(
        self,
        cr: Any = None,
        user: Any = None,
        context: Any = None,
        su: Any = None,
    ) -> FakeEnv:
        uid = self.uid if user is None else getattr(user, "id", user)
        return FakeEnv(
            cr if cr is not None else self.cr,
            uid,
            self.context if context is None else context,
            self.su if su is None else su,
            self.registry,
        )

    def __getitem__(self, model: str) -> Any:
        return self.registry[model]


class FakeIrHttp:
    def __init__(self, routing_map: Any) -> None:
        self._routing_map = routing_map
        self.errors_handled: list[BaseException] = []

    def routing_map(self, key: str | None = None) -> Any:
        return self._routing_map

    def _match(self, path_info: str) -> Any:
        adapter = self._routing_map.bind_to_environ(request.httprequest.environ)
        return adapter.match(path_info=path_info, return_rule=True)

    def _authenticate(self, endpoint: Any) -> None:
        self._authenticate_explicit(endpoint.routing["auth"])

    def _authenticate_explicit(self, auth: str) -> None:
        if auth == "none":
            request.update_env(anonymous=True)
        elif auth == "public":
            request.update_env(user=request.session.uid or PUBLIC_UID)
        elif auth == "user":
            if not request.session.uid:
                raise SessionExpiredException("Session expired")
            request.update_env(user=request.session.uid)
        else:
            raise AccessDenied(f"unknown auth {auth!r}")

    def _pre_dispatch(self, rule: Any, args: dict[str, Any]) -> None:
        request.dispatcher.pre_dispatch(rule, args)

    def _dispatch(self, endpoint: Any) -> Any:
        result = endpoint(**request.params)
        if isinstance(result, Response) and result.is_qweb:
            result.flatten()
        return result

    def _post_dispatch(self, response: Any) -> None:
        request.dispatcher.post_dispatch(response)

    def _handle_error(self, exception: Exception) -> Any:
        self.errors_handled.append(exception)
        return request.dispatcher.prepare_error_response(exception)

    def _serve_fallback(self) -> Any:
        return None

    def _redirect(self, location: str, code: int = 303) -> Any:
        return werkzeug.utils.redirect(location, code=code, Response=Response)

    def _is_allowed_cookie(self, cookie_type: str) -> bool:
        return True

    def _sanitize_cookies(self, cookies: Any) -> None:
        pass

    def _post_logout(self) -> None:
        pass

    def _apply_max_upload_size(self) -> None:
        pass


class FakeRegistry:
    current: FakeRegistry

    def __init__(self, routing_map: Any, *, replica: bool) -> None:
        self.db_name = DB
        self.replica = replica
        self.cursors: list[FakeCursor] = []
        self.transactions: dict[int, FakeTransaction] = {}
        self.signals = 0
        self.models: dict[str, Any] = {
            "ir.http": FakeIrHttp(routing_map),
            "ir.config_parameter": FakeConfigParameter({"database.secret": "s3cret"}),
            "res.users": FakeUsers(),
        }

    def cursor(self, readonly: bool = False, *, pin_key: object = None) -> FakeCursor:
        cr = FakeCursor(readonly=readonly and self.replica)
        cr.pin_key = pin_key
        self.cursors.append(cr)
        return cr

    def check_signaling(self, cr: Any = None) -> FakeRegistry:
        return self

    def signal_changes(self) -> None:
        self.signals += 1

    def reset_changes(self) -> None:
        pass

    def __getitem__(self, model: str) -> Any:
        return self.models[model]

    @property
    def ir_http(self) -> FakeIrHttp:
        return self.models["ir.http"]


def install_addon(name: str, source: str) -> ModuleType:
    module = ModuleType(f"odoo.addons.{name}")
    module.__dict__["__file__"] = f"<{name}>"
    sys.modules[module.__name__] = module
    exec(compile(source, module.__name__, "exec"), module.__dict__)  # noqa: S102  test controllers defined from source, the same way test_routing_diamond installs its fake addons
    return module


def uninstall_addon(name: str) -> None:
    sys.modules.pop(f"odoo.addons.{name}", None)
    Controller.children_classes.pop(name, None)


class Served:
    def __init__(
        self, status: str, headers: list[tuple[str, str]], body: bytes
    ) -> None:
        self.status = status
        self.status_code = int(status.split(" ", 1)[0])
        self.headers = headers
        self.body = body

    def header(self, name: str) -> str | None:
        for key, value in self.headers:
            if key.lower() == name.lower():
                return value
        return None

    def headers_named(self, name: str) -> list[str]:
        return [v for k, v in self.headers if k.lower() == name.lower()]

    def cookie(self, name: str) -> str | None:
        for value in self.headers_named("Set-Cookie"):
            if value.startswith(f"{name}="):
                return value.split(";", 1)[0].partition("=")[2]
        return None


class Harness:
    def __init__(self, tmp_path: Any, addon: str, *, replica: bool = False) -> None:
        self.addon = addon
        self.app = Application()
        self.store = FilesystemSessionStore(str(tmp_path), session_class=Session)
        self.app.__dict__["session_store"] = self.store
        self.app.__dict__["nodb_routing_map"] = prepare_routing_map(
            _generate_routing_rules([addon], nodb_only=True)
        )
        db_map = prepare_routing_map(_generate_routing_rules([addon], nodb_only=False))
        self.registry = FakeRegistry(db_map, replica=replica)
        FakeRegistry.current = self.registry
        self.served_dbs = [DB]
        self.db_list_calls: list[str | None] = []

    def serve(self, environ: dict[str, Any]) -> Served:
        captured: dict[str, Any] = {}

        def start_response(status, headers, exc_info=None):
            captured["status"] = status
            captured["headers"] = list(headers)

        with (
            mock.patch("odoo.http._serve.Registry", lambda db: self.registry),
            mock.patch("odoo.api.Environment", FakeEnv),
            mock.patch.object(self.app, "get_dbs_served", self._list_served_dbs),
            mock.patch.object(
                self.app,
                "filter_dbs_served",
                lambda dbs, host: [d for d in dbs if d in self.served_dbs],
            ),
            mock.patch.object(self.app, "get_static_file_path", return_value=None),
        ):
            body = b"".join(self.app(environ, start_response))
        return Served(captured["status"], captured["headers"], body)

    def _list_served_dbs(self, host: str | None = None) -> list[str]:
        self.db_list_calls.append(host)
        return list(self.served_dbs)

    @property
    def ir_http(self) -> FakeIrHttp:
        return self.registry.ir_http

    def login(self, uid: int) -> str:
        session = self.store.new()
        session.update(odoo.http.prepare_default_session())
        session.db = DB
        session.uid = uid
        session.login = f"user{uid}"
        session.session_token = FakeUser(uid)._get_session_token(session.sid)
        self.store.save(session)
        return session.sid
