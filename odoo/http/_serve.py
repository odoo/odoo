from __future__ import annotations

import functools
import logging
from typing import Any

import psycopg
import psycopg.errors
from werkzeug.exceptions import (
    HTTPException,
    NotFound,
    RequestEntityTooLarge,
    UnsupportedMediaType,
)

import odoo.api
from odoo.db import PoolError, close_db
from odoo.exceptions import AccessDenied
from odoo.libs.debug_log import DebugLog
from odoo.libs.worker_thread import current_worker_thread
from odoo.modules.registry import Registry
from odoo.service.db import list_dbs
from odoo.service.transaction import retrying

from ._cors import is_cors_preflight
from ._protocols import RequestState, get_ir_http
from ._retry import RequestRetryParticipant, rewind_uploaded_files
from .constants import NOT_FOUND_NODB, NOT_FOUND_NODB_TEXT, STATIC_CACHE
from .core import borrow_request
from .dispatcher import _dispatchers, get_dispatcher_for_unmatched_route
from .exceptions import (
    RegistryError,
    get_error_response,
    is_http_answer,
    set_error_response,
)
from .settings import current as current_settings
from .stream import Stream
from .wrappers import Response, prepare_exception_response

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)

_PROMOTE = object()
"""What `_serve_transaction` answers when the handler must be replayed read/write."""


class _RequestServeMixin(RequestState):
    def _require_env(self) -> odoo.api.Environment:
        env = self.env
        if env is None:
            raise RuntimeError("a database-bound request has an environment")
        return env

    @property
    def _debug_cr(self) -> Any:
        env = self.env
        return None if env is None else env.cr

    def _update_dispatcher(self, rule: Any) -> None:
        routing = rule.endpoint.routing
        dispatcher_cls = _dispatchers[routing["type"]]
        if not is_cors_preflight(
            self, rule.endpoint
        ) and not dispatcher_cls.is_compatible_with_request(self):
            compatible_dispatchers = [
                disp.routing_type
                for disp in _dispatchers.values()
                if disp.is_compatible_with_request(self)
            ]
            _debug.logic(
                "http.dispatcher.incompatible",
                routing_type=routing["type"],
                mimetype=getattr(self.httprequest, "mimetype", None),
                compatible=",".join(compatible_dispatchers) or None,
            )
            e = (
                f"Request inferred type is compatible with {compatible_dispatchers} "
                f"but {routing['routes'][0]!r} is type={routing['type']!r}.\n\n"
                "Please verify the Content-Type request header and try again."
            )
            res = prepare_exception_response(UnsupportedMediaType(e))
            res.headers["Accept"] = ", ".join(dispatcher_cls.mimetypes)
            raise UnsupportedMediaType(response=res)
        self.dispatcher = dispatcher_cls(self)
        _debug.logic(
            "http.dispatcher.selected",
            routing_type=routing["type"],
            mimetype=getattr(self.httprequest, "mimetype", None),
        )

    def _serve_static(self, filepath: str) -> Response:
        root = self.app

        with _debug.perf(
            "http.serve.static", path=getattr(self.httprequest, "path", None)
        ) as span:
            try:
                stream = Stream._from_trusted_path(filepath, public=True)
                debug = "assets" in self.session.debug
                res = stream.prepare_response(
                    max_age=0 if debug else STATIC_CACHE,
                    content_security_policy=None,
                )
                root.update_standard_headers(res)
                span.set(size=stream.size, status=res.status_code, debug_assets=debug)
                return res
            except OSError:
                module, _, path = self.httprequest.path[1:].partition("/static/")
                _debug.logic("http.static.missing", module=module, path=path)
                raise NotFound(
                    f'File "{path}" not found in module {module}.\n'
                ) from None

    def _serve_aborted(self, exc: HTTPException) -> Response:
        _debug.logic(
            "http.serve.aborted",
            path=getattr(self.httprequest, "path", None),
            status=exc.code,
            explicit_response=exc.response is not None,
        )
        if exc.response is not None:
            response = prepare_exception_response(exc)
        else:
            _logger.error(
                "Aborted with a status-less HTTPException while serving %s",
                self.httprequest.path,
                exc_info=exc,
            )
            response = self._prepare_dispatcher_error_response(exc)
        self.dispatcher.post_dispatch(response)
        return response

    def _prepare_dispatcher_error_response(self, exc: HTTPException) -> Response:
        handled = self.dispatcher.prepare_error_response(exc)
        if isinstance(handled, HTTPException):
            return prepare_exception_response(handled)
        return handled

    def _serve_nodb(self) -> Response:
        root = self.app

        try:
            router = root.nodb_routing_map.bind_to_environ(self.httprequest.environ)
            try:
                rule, args = router.match(return_rule=True)
            except NotFound as exc:
                _debug.logic(
                    "http.route.unmatched", path=self.httprequest.path, db=None
                )
                self.dispatcher = get_dispatcher_for_unmatched_route(self)(self)
                set_error_response(exc, self._prepare_nodb_not_found_response(exc))
                raise
            _debug.pipeline(
                "http.route.matched",
                db=None,
                endpoint=getattr(rule.endpoint, "__qualname__", None),
                type=rule.endpoint.routing["type"],
            )
            self._update_dispatcher(rule)
            self.dispatcher.pre_dispatch(rule, args)
            with _debug.perf(
                "http.serve.handler",
                db=None,
                endpoint=getattr(rule.endpoint, "__qualname__", None),
            ) as span:
                response = self.dispatcher.dispatch(rule.endpoint, args)
                span.set(status=getattr(response, "status_code", None))
            _debug.pipeline(
                "http.serve.dispatched",
                db=None,
                endpoint=getattr(rule.endpoint, "__qualname__", None),
                status=getattr(response, "status_code", None),
            )
            self.dispatcher.post_dispatch(response)
            return response
        except HTTPException as exc:
            if exc.code is not None:
                raise
            return self._serve_aborted(exc)

    def _prepare_nodb_not_found_response(self, exc: NotFound) -> Response:
        _debug.logic(
            "http.nodb.not_found",
            path=getattr(self.httprequest, "path", None),
            routing_type=self.dispatcher.routing_type,
        )
        if self.dispatcher.routing_type == "http":
            return Response(
                NOT_FOUND_NODB,
                status=exc.code,
                headers=[("Content-Type", "text/html; charset=utf-8")],
            )
        exc.description = NOT_FOUND_NODB_TEXT
        return self._prepare_dispatcher_error_response(exc)

    def _acquire_registry_cursor(self) -> Any:
        db = self.db
        if not db:
            raise RuntimeError("a database-bound request needs a database name")
        cr = None
        try:
            with _debug.perf("http.registry.acquire", db=db) as span:
                with _debug.perf("http.registry.lookup", db=db):
                    with borrow_request():
                        registry = Registry(db)
                with _debug.perf("http.registry.cursor", db=db):
                    cr = registry.cursor(readonly=True, pin_key=self.session.sid)
                with _debug.perf("http.registry.signaling", cr=cr, db=db):
                    self.registry = registry.check_signaling(cr)
                span.set(reloaded=self.registry is not registry)
            _debug.pipeline(
                "http.registry.acquired",
                db=db,
                readonly_cursor=getattr(cr, "readonly", None),
                reloaded=self.registry is not registry,
            )
            return cr
        except (
            PoolError,
            psycopg.OperationalError,
            psycopg.ProgrammingError,
        ) as e:
            db_absent = None
            try:
                db_absent = db not in list_dbs(force=True)
                if db_absent:
                    Registry.clear_database_state(db)
                    close_db(db)
                    _debug.lifecycle("http.registry.stale_cleared", db=db)
            except Exception:
                _logger.debug(
                    "Stale-registry cleanup after RegistryError failed",
                    exc_info=True,
                )
            finally:
                if cr is not None:
                    cr.close()
            err = RegistryError(
                f"Cannot get registry {db}",
                db_absent=db_absent,
                transient=not isinstance(e, psycopg.ProgrammingError),
            )
            _debug.logic(
                "http.registry.unavailable",
                db=db,
                error=type(e).__name__,
                db_absent=db_absent,
                transient=err.transient,
            )
            raise err from e
        except BaseException:
            if cr is not None:
                cr.close()
            raise

    def _select_serve_target_and_mode(self, registry: Registry) -> tuple[Any, bool]:
        try:
            with _debug.perf("http.route.match", db=registry.db_name):
                rule, args = get_ir_http(registry)._match(self.httprequest.path)
        except NotFound as not_found_exc:
            _debug.logic(
                "http.route.unmatched", path=self.httprequest.path, db=registry.db_name
            )
            self.dispatcher = get_dispatcher_for_unmatched_route(self)(self)
            return functools.partial(self._serve_ir_http_fallback, not_found_exc), True

        self._update_dispatcher(rule)
        readonly = rule.endpoint.routing["readonly"]
        if callable(readonly):
            readonly = readonly(rule.endpoint.func.__self__, rule, args)
        _debug.pipeline(
            "http.route.matched",
            db=registry.db_name,
            endpoint=getattr(rule.endpoint, "__qualname__", None),
            type=rule.endpoint.routing["type"],
            auth=rule.endpoint.routing.get("auth"),
            readonly=bool(readonly),
            readonly_resolver=callable(rule.endpoint.routing["readonly"]),
        )
        return functools.partial(self._serve_ir_http, rule, args), bool(readonly)

    def _serve_transaction(
        self,
        serve_func: Any,
        participant: RequestRetryParticipant,
        *,
        readonly: bool,
    ) -> Any:
        mode = "ro" if readonly else "rw"
        env = self._require_env()
        self._bind_session_transaction(env.cr)
        commits_before = env.cr.commit_count
        try:
            response = retrying(
                functools.partial(self._serve_transaction_target, serve_func),
                env=env,
                participant=participant,
            )
        except Exception as exc:
            settled = env.cr.closed or env.cr.commit_count != commits_before
            if (
                readonly
                and not settled
                and isinstance(exc, psycopg.errors.ReadOnlySqlTransaction)
            ):
                self._prepare_promotion(participant, exc)
                return _PROMOTE
            _debug.logic(
                "http.serve.transaction_failed",
                mode=mode,
                error=type(exc).__name__,
                committed=env.cr.commit_count != commits_before,
                cursor_closed=env.cr.closed,
            )
            if not settled:
                env.cr.rollback()
            self._update_served_exception(exc)
            raise
        _debug.pipeline(
            "http.serve.transaction",
            mode=mode,
            commits=env.cr.commit_count - commits_before,
            cursor_closed=env.cr.closed,
            status=getattr(response, "status_code", None),
        )
        if not env.cr.closed:
            self._flush_session()
        return response

    def _prepare_promotion(
        self, participant: RequestRetryParticipant, exc: BaseException
    ) -> None:
        _logger.warning(
            "%s, retrying with a read/write cursor — readonly route "
            "%s %s attempted a write, so its handler runs a second "
            "time; keep non-transactional side effects (emails, "
            "outbound calls, token burns) out until the first write",
            exc.args[0].rstrip(),
            self.httprequest.method,
            self.httprequest.path,
            exc_info=exc,
        )
        current_worker_thread().cursor_mode = "ro->rw"
        participant.on_rollback(exc)
        rewind_uploaded_files(self.httprequest, cause=exc)
        _debug.logic(
            "http.serve.promoted_to_rw",
            method=self.httprequest.method,
            path=self.httprequest.path,
        )

    def _serve_transaction_target(self, serve_func: Any) -> Response:
        try:
            return serve_func()
        except HTTPException as exc:
            if exc.code is not None:
                raise
            # An explicit response is successful control flow (e.g. ensure_db
            # redirect). Let retrying commit its session changes normally.
            return self._serve_aborted(exc)

    def _open_read_write_cursor(self, cr: Any) -> Any:
        env = self._require_env()
        with _debug.perf("http.serve.cursor_ready", replaced=cr.readonly):
            if cr.readonly:
                _debug.lifecycle("http.serve.cursor_replaced", db=env.registry.db_name)
                cr.close()
                cr = env.registry.cursor(pin_key=self.session.sid)
            else:
                cr.rollback()
                _debug.lifecycle("http.serve.cursor_reused", db=env.registry.db_name)
        if cr.readonly:
            _debug.logic("http.serve.cursor_still_readonly", db=env.registry.db_name)
            # The caller's variable still names the cursor this method was
            # handed; close the replacement here or its connection leaks.
            cr.close()
            e = (
                f"{self.httprequest.method} {self.httprequest.path} needs a "
                f"read/write cursor and the registry handed back a read-only "
                f"one; refusing to run the handler against it."
            )
            raise RuntimeError(e)
        return cr

    def _serve_db(self) -> Response:
        cr: Any = None
        try:
            cr = self._acquire_registry_cursor()
            registry = self.registry
            if registry is None:
                raise RuntimeError("ir.http is only reachable with a registry")
            current_worker_thread().dbname = registry.db_name

            self.env = odoo.api.Environment(
                cr, self.session.uid, self.session.context or {}
            )
            serve_func, readonly = self._select_serve_target_and_mode(registry)
            participant = RequestRetryParticipant(self)

            promoted = False
            _debug.pipeline(
                "http.serve.db",
                db=registry.db_name,
                uid=self.session.uid,
                readonly_route=readonly,
                readonly_cursor=getattr(cr, "readonly", None),
            )
            if readonly and cr.readonly:
                current_worker_thread().cursor_mode = "ro"
                served = self._serve_transaction(serve_func, participant, readonly=True)
                if served is not _PROMOTE:
                    return served
                promoted = True
            else:
                thread = current_worker_thread()
                # The registry stamps the speculative read-only acquisition
                # ("ro", or "ro->rw" when the session is pinned). Only a
                # readonly route whose cursor came back on the primary keeps
                # that reading; a write route ran read/write whatever the
                # router chose first.
                if not readonly or getattr(thread, "cursor_mode", None) is None:
                    thread.cursor_mode = "rw"

            env = self._require_env()
            cr = self._open_read_write_cursor(cr)
            if promoted:
                _debug.pipeline(
                    "http.serve.replay",
                    db=registry.db_name,
                    method=getattr(self.httprequest, "method", None),
                    path=getattr(self.httprequest, "path", None),
                )
                self._reset_for_replay(cr)
            else:
                self.env = env(cr=cr)
            return self._serve_transaction(serve_func, participant, readonly=False)
        except HTTPException as exc:
            if exc.code is not None:
                raise
            return self._serve_aborted(exc)
        finally:
            self.env = None
            if cr is not None:
                cr.close()
            _debug.lifecycle(
                "http.serve.db_released",
                db=self.db,
                cursor_mode=getattr(current_worker_thread(), "cursor_mode", None),
                had_cursor=cr is not None,
            )

    def _update_served_exception(self, exc: Exception) -> None:
        if isinstance(exc, HTTPException) and exc.code is None:
            _debug.logic(
                "http.serve.error_passthrough",
                error=type(exc).__name__,
                explicit_response=exc.response is not None,
            )
            return
        if (
            "werkzeug" in current_settings().dev_mode
            and not self.dispatcher.serializes_errors_in_dev_mode
            and not is_http_answer(exc)
        ):
            _debug.logic(
                "http.serve.error_left_to_debugger",
                error=type(exc).__name__,
                dispatcher=self.dispatcher.routing_type,
            )
            return
        if get_error_response(exc) is None:
            if isinstance(exc, AccessDenied):
                exc.suppress_traceback()
            registry = self._get_bound_registry()
            set_error_response(exc, get_ir_http(registry)._handle_error(exc))
            _debug.logic(
                "http.serve.error_handled",
                error=type(exc).__name__,
                dispatcher=self.dispatcher.routing_type,
            )

    def _get_bound_registry(self) -> Registry:
        registry = self.registry
        if registry is None:
            raise RuntimeError("ir.http is only reachable with a registry")
        return registry

    def _check_body_size(self) -> None:
        limit = self.httprequest.max_content_length
        length = self.httprequest.content_length
        if limit is not None and length is not None and length > limit:
            _debug.logic("http.body.too_large", length=length, limit=limit)
            raise RequestEntityTooLarge

    def _serve_ir_http_fallback(self, not_found: NotFound) -> Response:
        ir_http = get_ir_http(self._get_bound_registry())
        ir_http._apply_max_upload_size()
        self._check_body_size()
        self._params_source = self.get_http_params
        with _debug.perf(
            "http.serve.authenticate",
            cr=self._debug_cr,
            auth="public",
        ):
            ir_http._authenticate_explicit("public")
        with _debug.perf(
            "http.serve.fallback_lookup",
            cr=self._debug_cr,
            path=getattr(self.httprequest, "path", None),
        ) as span:
            response = ir_http._serve_fallback()
            span.set(served=bool(response))
        _debug.pipeline(
            "http.serve.fallback",
            path=getattr(self.httprequest, "path", None),
            served=bool(response),
            status=getattr(response, "status_code", None),
        )
        if response:
            with _debug.perf(
                "http.serve.post_dispatch",
                cr=self._debug_cr,
            ):
                ir_http._post_dispatch(response)
            return response

        no_fallback = NotFound()
        no_fallback.__context__ = not_found
        raise no_fallback

    def _serve_ir_http(self, rule: Any, args: dict[str, Any]) -> Response:
        registry = self._get_bound_registry()
        ir_http = get_ir_http(registry)
        with _debug.perf(
            "http.serve.authenticate",
            cr=self._debug_cr,
            auth=rule.endpoint.routing.get("auth"),
        ):
            ir_http._authenticate(rule.endpoint)
        _debug.pipeline(
            "http.serve.authenticated",
            endpoint=getattr(rule.endpoint, "__qualname__", None),
            uid=None if self.env is None else self.env.uid,
        )
        with _debug.perf(
            "http.serve.pre_dispatch",
            cr=self._debug_cr,
            endpoint=getattr(rule.endpoint, "__qualname__", None),
        ):
            ir_http._pre_dispatch(rule, args)
        with _debug.perf(
            "http.serve.handler",
            cr=self._debug_cr,
            db=registry.db_name,
            endpoint=getattr(rule.endpoint, "__qualname__", None),
        ) as span:
            response = self.dispatcher.dispatch(rule.endpoint, args)
            span.set(status=getattr(response, "status_code", None))
        _debug.pipeline(
            "http.serve.dispatched",
            endpoint=getattr(rule.endpoint, "__qualname__", None),
            status=getattr(response, "status_code", None),
        )
        with _debug.perf(
            "http.serve.post_dispatch",
            cr=self._debug_cr,
            status=getattr(response, "status_code", None),
        ):
            ir_http._post_dispatch(response)
        return response
