import contextlib
import functools
import logging
import math
import threading
import time
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any
from urllib.parse import urlencode, urlparse

import werkzeug.routing
from werkzeug.exceptions import (
    HTTPException,
    InternalServerError,
    MethodNotAllowed,
    NotFound,
    ServiceUnavailable,
)
from werkzeug.middleware.proxy_fix import ProxyFix as ProxyFix_
from werkzeug.wrappers import Response as WerkzeugResponse
from werkzeug.wsgi import ClosingIterator

from odoo.exceptions import AccessDenied, AccessError, UserError
from odoo.libs.debug_log import DebugLog
from odoo.libs.worker_thread import current_worker_thread, forget_request
from odoo.modules import module as module_manager
from odoo.tools import file_path
from odoo.tools.misc import real_time

from ._dbfilter import filter_dbs_served, get_dbs_served
from ._protocols import get_ir_http
from ._session_store import (
    FilesystemSessionStore,
    MemorySessionStore,
    PostgresSessionStore,
    prepare_session_dir,
)
from .constants import (
    REGISTRY_RETRY_AFTER,
    REJECTED_HTTP_METHODS,
    STATIC_ALLOWED_METHODS,
    is_select_db_path,
    prepare_allow_header,
)
from .core import _request_stack, request
from .dispatcher import (
    get_dispatcher_for_unmatched_route,
    is_debugger_handover_required,
)
from .exceptions import (
    RegistryError,
    SessionExpiredException,
    get_error_response,
    set_error_response,
)
from .geoip import geoip2, maxminddb
from .request_class import Request
from .routing import SignedIntConverter, _generate_routing_rules, prepare_routing_map
from .session import Session
from .settings import current as current_settings
from .wrappers import (
    HTTPRequest,
    Response,
    prepare_exception_response,
    prepare_no_content_response,
)

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)


def _noop_start_response(status: str, headers: list[tuple[str, str]]) -> None:
    pass


@functools.lru_cache(maxsize=4)
def _prepare_proxy_fix(hops: int) -> ProxyFix_:
    return ProxyFix_(
        lambda environ, start_response: [],
        x_for=hops,
        x_proto=hops,
        x_host=hops,
    )


_UNSET = object()


@functools.lru_cache(maxsize=4096)
def _get_static_resource_path(static_path: str, resource: str) -> str:
    resolved = file_path(f"{static_path}/{resource}")
    if not Path(resolved).resolve().is_relative_to(Path(static_path).resolve()):
        _debug.logic(
            "http.static.rejected", reason="escapes_static_dir", resource=resource
        )
        raise FileNotFoundError(resolved)
    _debug.lifecycle("http.static.resolved", resource=resource)
    return resolved


class _locked_cached_property(functools.cached_property):
    def __init__(self, func: Callable) -> None:
        super().__init__(func)
        self.lock = threading.Lock()

    def __get__(self, instance: object, owner: type | None = None) -> Any:
        if instance is None:
            return self
        if self.attrname is None:
            return super().__get__(instance, owner)
        cache = instance.__dict__
        val = cache.get(self.attrname, _UNSET)
        if val is _UNSET:
            with self.lock:
                val = cache.get(self.attrname, _UNSET)
                if val is _UNSET:
                    val = self.func(instance)
                    cache[self.attrname] = val
        return val


class _GeoIPReaderSlot:
    # The MaxMind files are refreshed in place (geoipupdate): look again at
    # most this often, and reopen when the path, inode or mtime moved.
    RECHECK_SECONDS = 60.0

    def __init__(self, kind: str) -> None:
        self.kind = kind
        self._lock = threading.Lock()
        self._reader: Any = None
        self._identity: tuple[Any, ...] | None = None
        self._checked_at = -math.inf

    def get(self, app: Application, path: str) -> Any:
        now = time.monotonic()
        identity = self._identity
        if (
            identity is not None
            and identity[0] == path
            and now - self._checked_at < self.RECHECK_SECONDS
        ):
            return self._reader
        with self._lock:
            try:
                st = Path(path).stat()
            except OSError:
                current: tuple[Any, ...] = (path,)
            else:
                current = (path, st.st_ino, st.st_mtime_ns)
            if current != self._identity:
                _debug.lifecycle(
                    "http.geoip.reader_reloaded",
                    db=self.kind,
                    first=self._identity is None,
                )
                # The previous reader is left to the garbage collector: a
                # lookup running in another thread may still hold it.
                self._reader = app._open_geoip_reader(self.kind, path)
                self._identity = current
            self._checked_at = now
            return self._reader


class Application:
    def __init__(self) -> None:
        self._geoip_city = _GeoIPReaderSlot("city")
        self._geoip_country = _GeoIPReaderSlot("country")

    def initialize(self) -> None:
        module_manager.initialize_sys_path()
        from odoo.service.server import load_server_wide_modules

        load_server_wide_modules()
        _debug.lifecycle(
            "http.application.initialized",
            server_wide_modules=len(current_settings().server_wide_modules),
        )

    def get_dbs_served(self, host: str | None = None) -> list[str]:
        return get_dbs_served(force=True, host=host)

    def filter_dbs_served(self, dbs: list[str], host: str | None = None) -> list[str]:
        return filter_dbs_served(dbs, host=host)

    def get_static_path(self, module_name: str) -> str | None:
        manifest = module_manager.Manifest.for_addon(module_name, display_warning=False)
        return manifest.static_path if manifest is not None else None

    def get_static_file_path(self, url: str, host: str = "") -> str | None:

        try:
            netloc, path = urlparse(url)[1:3]
        except ValueError:
            return None
        try:
            leading_segment, module, static, resource = path.split("/", 3)
        except ValueError:
            return None

        host = host.lower()
        if netloc and netloc.lower() != host:
            _debug.logic("http.static.rejected", reason="netloc", netloc=netloc)
            return None

        if not netloc and leading_segment and leading_segment.lower() != host:
            return None

        if not (static == "static" and resource):
            return None

        static_path = self.get_static_path(module)
        if not static_path:
            _debug.logic("http.static.rejected", reason="no_static_dir", module=module)
            return None

        try:
            return _get_static_resource_path(static_path, resource)
        except FileNotFoundError, ValueError:
            _debug.logic("http.static.rejected", reason="unresolved", module=module)
            return None

    @_locked_cached_property
    def nodb_routing_map(self):
        with _debug.perf(
            "http.nodb_routing_map",
            modules=len(current_settings().server_wide_modules),
        ):
            return prepare_routing_map(
                _generate_routing_rules(
                    ["", *current_settings().server_wide_modules], nodb_only=True
                ),
                converters={"int": SignedIntConverter},
            )

    @_locked_cached_property
    def session_store(self):
        settings = current_settings()
        if settings.session_store == "postgres":
            _debug.lifecycle("http.session_store.opened", backend="postgres")
            return PostgresSessionStore(settings.session_db, session_class=Session)
        if settings.session_store == "memory":
            _debug.lifecycle("http.session_store.opened", backend="memory")
            return MemorySessionStore(Session)
        path = prepare_session_dir(settings.session_dir)
        _logger.debug("HTTP sessions stored in: %s", path)
        _debug.lifecycle("http.session_store.opened", backend="filesystem", path=path)
        return FilesystemSessionStore(path, session_class=Session)

    def get_routing_map(self, db: str | None, env: Any = None) -> werkzeug.routing.Map:
        if not db:
            _debug.logic("http.routing_map.selected", db=None, source="nodb")
            return self.nodb_routing_map
        router_env = env if env is not None else request.env
        if router_env is None:
            raise RuntimeError("a database router needs a bound environment")
        _debug.logic("http.routing_map.selected", db=db, source="ir.http")
        return get_ir_http(router_env).routing_map()

    def _open_geoip_reader(self, kind: str, path: str) -> Any:
        if geoip2 is None:
            _debug.logic("http.geoip.db_unavailable", db=kind, reason="no_geoip2")
            return None
        try:
            reader = geoip2.database.Reader(path)
        except (OSError, maxminddb.InvalidDatabaseError) as exc:
            _logger.debug(
                "Couldn't load the GeoIP %s file at %s (%s); lookups against it "
                "answer nothing.",
                kind,
                path,
                exc,
            )
            _debug.logic(
                "http.geoip.db_unavailable",
                db=kind,
                reason=type(exc).__name__,
                path=path,
            )
            return None
        _debug.lifecycle("http.geoip.db_opened", db=kind, path=path)
        return reader

    @property
    def geoip_city_db(self) -> Any:
        return self._geoip_city.get(self, current_settings().geoip_city_db)

    @property
    def geoip_country_db(self) -> Any:
        return self._geoip_country.get(self, current_settings().geoip_country_db)

    def update_standard_headers(self, response: WerkzeugResponse | Response) -> None:
        headers = response.headers
        if "X-Content-Type-Options" not in headers:
            headers["X-Content-Type-Options"] = "nosniff"
        if request and "X-Request-Id" not in headers:
            headers["X-Request-Id"] = request.id

        if "Content-Security-Policy" in headers:
            return

        if not headers.get("Content-Type", "").startswith("image/"):
            return

        _debug.logic("http.security_headers.image_csp", status=response.status_code)
        headers["Content-Security-Policy"] = "default-src 'none'"

    def _clear_thread_state(self) -> None:
        forget_request()
        current_thread = current_worker_thread()
        current_thread.query_count = 0
        current_thread.query_time = 0
        current_thread.perf_t0 = real_time()
        current_thread.cursor_mode = None

    def _apply_proxy_fix(self, environ: dict[str, object]) -> None:
        settings = current_settings()
        if settings.proxy_mode and (
            environ.get("HTTP_X_FORWARDED_FOR")
            or environ.get("HTTP_X_FORWARDED_PROTO")
            or environ.get("HTTP_X_FORWARDED_HOST")
        ):
            hops = settings.proxy_hops
            _prepare_proxy_fix(hops)(environ, _noop_start_response)
            _debug.logic(
                "http.proxy_fix.applied",
                hops=hops,
                remote_addr=environ.get("REMOTE_ADDR"),
                scheme=environ.get("wsgi.url_scheme"),
            )
        if (
            _debug.logic.enabled
            and not settings.proxy_mode
            and environ.get("HTTP_X_FORWARDED_FOR")
        ):
            _debug.logic(
                "http.proxy_fix.skipped",
                reason="proxy_mode_off",
                remote_addr=environ.get("REMOTE_ADDR"),
            )

    def _recover_from_registry_error(
        self, request: Request, httprequest: HTTPRequest, exc: RegistryError
    ) -> Any:
        durable = exc.db_absent is True or (
            exc.db_absent is False and not exc.transient
        )
        _debug.logic(
            "http.registry_error.recover",
            path=httprequest.path,
            db_absent=exc.db_absent,
            transient=exc.transient,
            durable=durable,
            select_db_path=is_select_db_path(httprequest.path),
        )
        if not durable:
            # The database is there but out of reach for now (pool exhausted,
            # server restarting): say so and when to retry, keep the session.
            # Serving the database-free router instead answered "database not
            # found" or the selector for a database that exists.
            _logger.warning(
                "Database %r unreachable for now; answering 503",
                request.db,
                exc_info=exc.__cause__,
            )
            request.dispatcher = get_dispatcher_for_unmatched_route(request)(request)
            raise ServiceUnavailable(
                "The database is temporarily unavailable. Try again shortly.",
                retry_after=REGISTRY_RETRY_AFTER,
            ) from exc
        _logger.warning(
            "Database %r is gone; serving without a database",
            request.db,
            exc_info=exc.__cause__,
        )
        request.db = None
        request.session.logout()
        if is_select_db_path(httprequest.path):
            args_nodb = request.httprequest.args.copy()
            args_nodb.pop("db", None)
            request.reroute(
                httprequest.path,
                urlencode(list(args_nodb.items(multi=True))),
            )
        return request._serve_nodb()

    def _serve_static_file(self, request: Request, static_file: str) -> Any:
        method = request.httprequest.method
        if method in STATIC_ALLOWED_METHODS:
            return request._serve_static(static_file)

        allow = prepare_allow_header(STATIC_ALLOWED_METHODS)
        _debug.logic("http.static.method_rejected", method=method, allow=allow)
        if method == "OPTIONS":
            response = prepare_no_content_response(headers=[("Allow", allow)])
            self.update_standard_headers(response)
            return response
        raise MethodNotAllowed(valid_methods=allow.split(", "))

    def _log_request_exception(self, exc: Exception) -> None:
        _debug.logic(
            "http.request.exception_logged",
            error=type(exc).__name__,
            custom_level=hasattr(exc, "loglevel"),
            http_status=getattr(exc, "code", None),
        )
        if hasattr(exc, "loglevel"):
            _logger.log(
                exc.loglevel,
                exc,
                exc_info=getattr(exc, "exc_info", None),
            )
        elif isinstance(exc, HTTPException):
            pass
        elif isinstance(exc, SessionExpiredException):
            _logger.info(exc)
        elif isinstance(exc, AccessError):
            _logger.warning(exc, exc_info="access" in current_settings().dev_mode)
        elif isinstance(exc, UserError):
            _logger.warning(exc)
        else:
            _logger.error("Exception during request handling.", exc_info=exc)

    def _get_or_create_error_response(
        self, exc: Exception, request: Request | None
    ) -> Any:
        existing = get_error_response(exc)
        if existing is not None:
            _debug.logic("http.error_response.reused", error=type(exc).__name__)
            return existing
        if isinstance(exc, AccessDenied):
            exc.suppress_traceback()
        via = "no_request"  # debuglog
        if request is None:
            response: Any = InternalServerError()
        else:
            try:
                response = request.dispatcher.prepare_error_response(exc)
                via = "dispatcher"  # debuglog
            except Exception:
                _logger.exception("The dispatcher could not build an error response")
                response = InternalServerError()
                via = "dispatcher_failed"  # debuglog
        set_error_response(exc, response)
        _debug.logic(
            "http.error_response.built",
            error=type(exc).__name__,
            via=via,
            status=getattr(response, "code", None),
        )
        return response

    def _finalize_error_response(
        self, exc: Exception, request: Request | None, response: Any
    ) -> Any:
        if request is None:
            _debug.logic("http.error_response.unfinalized", error=type(exc).__name__)
            return response
        try:
            if isinstance(response, HTTPException):
                response = prepare_exception_response(
                    response, request.httprequest.environ
                )
            if request._post_init_done:
                request.dispatcher.post_dispatch(response)
            else:
                self.update_standard_headers(response)
            set_error_response(exc, response)
            _debug.pipeline(
                "http.error_response.finalized",
                error=type(exc).__name__,
                status=getattr(response, "status_code", None),
                post_dispatched=request._post_init_done,
            )
        except Exception:
            _logger.warning(
                "Could not post-process the error response; "
                "CORS/session headers may be missing.",
                exc_info=True,
            )
            _debug.logic(
                "http.error_response.finalize_failed", error=type(exc).__name__
            )
        return response

    def __call__(
        self, environ: dict[str, object], start_response: Callable
    ) -> Iterable[bytes]:
        self._clear_thread_state()
        self._apply_proxy_fix(environ)

        httprequest = HTTPRequest(environ)
        with contextlib.ExitStack() as request_guard:
            # The WSGI iterable is consumed after __call__ returns, so a
            # return path must NOT close the request here (a streamed body
            # may read a request-owned resource, e.g. an uploaded file);
            # ownership of close() moves into the returned ClosingIterator.
            # Paths that exit without returning an iterable close it now.
            request_guard.callback(httprequest.close)
            request: Request | None = None
            pushed = False
            try:
                request = Request(httprequest, app=self)
                _request_stack.push(request)
                pushed = True
                current_worker_thread().url = httprequest.url
                current_worker_thread().request_id = request.id

                if httprequest.method in REJECTED_HTTP_METHODS:
                    _debug.logic(
                        "http.request.method_rejected", method=httprequest.method
                    )
                    raise MethodNotAllowed(
                        valid_methods=prepare_allow_header().split(", ")
                    )

                if "\x00" in httprequest.path:
                    _debug.logic("http.request.path_rejected", reason="nul_byte")
                    raise NotFound

                with _debug.perf(
                    "http.request", method=httprequest.method, path=httprequest.path
                ) as span:
                    request._post_init()
                    _debug.pipeline(
                        "http.request.begin",
                        request_id=request.id,
                        method=httprequest.method,
                        path=httprequest.path,
                        db=request.db,
                        uid=request.session.uid,
                        session_new=request.session.is_new,
                    )
                    static_file = self.get_static_file_path(httprequest.path)
                    span.set(
                        kind="static" if static_file else "db" if request.db else "nodb"
                    )
                    if static_file:
                        response = self._serve_static_file(request, static_file)
                    elif request.db:
                        try:
                            with request._profile_request():
                                response = request._serve_db()
                        except RegistryError as exc:
                            response = self._recover_from_registry_error(
                                request, httprequest, exc
                            )
                    else:
                        response = request._serve_nodb()
                    span.set(
                        status=getattr(response, "status_code", None),
                        queries=current_worker_thread().query_count,
                        query_ms=current_worker_thread().query_time * 1000.0,
                    )
                iterable = response(environ, start_response)
                request_guard.pop_all()
                return ClosingIterator(iterable, httprequest.close)

            except Exception as exc:
                self._log_request_exception(exc)
                _debug.pipeline(
                    "http.request.failed",
                    method=httprequest.method,
                    path=httprequest.path,
                    error=type(exc).__name__,
                    status=getattr(exc, "code", None),
                )
                if is_debugger_handover_required(
                    None if request is None else request.dispatcher, exc
                ):
                    _debug.logic(
                        "http.request.debugger_handover", error=type(exc).__name__
                    )
                    raise
                error_response = self._finalize_error_response(
                    exc, request, self._get_or_create_error_response(exc, request)
                )
                iterable = error_response(environ, start_response)
                request_guard.pop_all()
                return ClosingIterator(iterable, httprequest.close)

            finally:
                if pushed:
                    _request_stack.pop()
                if request is not None and request.httprequest is not httprequest:
                    _debug.lifecycle(
                        "http.request.rerouted_closed", path=httprequest.path
                    )
                    with contextlib.suppress(Exception):
                        request.httprequest.close()


root = Application()
