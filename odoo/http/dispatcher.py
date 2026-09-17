from __future__ import annotations

import collections.abc
import logging
from abc import ABC, abstractmethod
from http import HTTPStatus
from typing import TYPE_CHECKING, Any

import werkzeug.exceptions
import werkzeug.wrappers
from werkzeug.exceptions import (
    HTTPException,
    InternalServerError,
    NotFound,
    UnprocessableEntity,
)
from werkzeug.exceptions import (
    default_exceptions as werkzeug_default_exceptions,
)

from odoo.exceptions import UserError
from odoo.libs.debug_log import DebugLog

from ._cors import is_cors_preflight, stage_cors_headers, stage_preflight_headers
from ._error_serialization import serialize_exception
from ._params import coerce_params
from ._protocols import get_ir_http
from .constants import (
    MISSING_CSRF_WARNING,
    SAFE_HTTP_METHODS,
    prepare_allow_header,
)
from .exceptions import ParameterError, SessionExpiredException
from .wrappers import Response, prepare_no_content_response

if TYPE_CHECKING:
    from ._protocols import Endpoint, RequestState

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)

_dispatchers: dict[str, type[Dispatcher]] = {}

PROBLEM_JSON_MIMETYPE = "application/problem+json; charset=utf-8"


def _prepare_problem_details(
    body: dict[str, Any], status: int, generic: bool
) -> dict[str, Any]:
    # RFC 9457 members first, Odoo's own after them, so a client that knows
    # one shape or the other reads what it expects.
    try:
        title = HTTPStatus(status).phrase
    except ValueError:
        title = "Error"
    return {
        "type": "about:blank" if generic else f"urn:odoo:exception:{body['name']}",
        "title": title,
        "status": status,
        "detail": body["message"],
        **body,
    }


def get_dispatcher_for_unmatched_route(request: RequestState) -> type[Dispatcher]:
    mimetype = request.httprequest.mimetype
    for routing_type in ("json2", "jsonrpc"):
        dispatcher = _dispatchers.get(routing_type)
        if dispatcher is not None and mimetype in dispatcher.mimetypes:
            _debug.logic(
                "http.dispatcher.inferred", mimetype=mimetype, routing_type=routing_type
            )
            return dispatcher
    _debug.logic("http.dispatcher.inferred", mimetype=mimetype, routing_type="http")
    return _dispatchers["http"]


class Dispatcher(ABC):
    routing_type: str
    mimetypes: collections.abc.Collection[str] = ()

    cors_allowed_methods: collections.abc.Collection[str] | None = None

    serializes_errors_in_dev_mode: bool = False

    statement_timeout: float | None = None

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        routing_type = getattr(cls, "routing_type", None)
        if routing_type is None:
            return
        existing = _dispatchers.get(routing_type)
        if existing is not None and existing is not cls:
            deliberate = issubclass(cls, existing)
            _logger.log(
                logging.DEBUG if deliberate else logging.WARNING,
                "Dispatcher routing_type=%r was %s; %s %s it.",
                routing_type,
                existing.__name__,
                cls.__name__,
                "extends" if deliberate else "unrelatedly replaces",
            )
        _dispatchers[routing_type] = cls
        _debug.lifecycle(
            "http.dispatcher.registered",
            routing_type=routing_type,
            cls=cls.__qualname__,
            replaced=None if existing is None else existing.__qualname__,
        )

    def __init__(self, request: RequestState) -> None:
        self.request = request

    @classmethod
    @abstractmethod
    def is_compatible_with_request(cls, request: RequestState) -> bool:
        pass

    def pre_dispatch(self, rule: Any, args: dict[str, Any]) -> None:
        routing = rule.endpoint.routing
        self.request.session.can_save &= routing.get("save_session", True)

        is_preflight = is_cors_preflight(self.request, rule.endpoint)
        vary = stage_cors_headers(self.request, routing, self.cors_allowed_methods)
        if is_preflight:
            vary += stage_preflight_headers(self.request, routing)
        if vary:
            self.request.future_response.headers.set("Vary", ", ".join(vary))

        _debug.pipeline(
            "http.dispatch.pre",
            dispatcher=self.routing_type,
            preflight=is_preflight,
            cors=bool(routing.get("cors")),
            vary=len(vary),
            save_session=self.request.session.can_save,
        )
        self._answer_options_request(routing, is_preflight)
        self._apply_max_content_length(rule, routing)
        self._apply_statement_timeout(routing)

    def _answer_options_request(
        self, routing: collections.abc.Mapping[str, Any], is_preflight: bool
    ) -> None:
        if self.request.httprequest.method == "OPTIONS" and (
            is_preflight or "OPTIONS" not in (routing.get("methods") or ())
        ):
            _debug.logic("http.dispatch.options_answered", preflight=is_preflight)
            werkzeug.exceptions.abort(
                prepare_no_content_response(
                    headers=[("Allow", prepare_allow_header(routing.get("methods")))]
                )
            )

    def _apply_max_content_length(
        self, rule: Any, routing: collections.abc.Mapping[str, Any]
    ) -> None:
        if "max_content_length" in routing:
            max_content_length = routing["max_content_length"]
            if callable(max_content_length):
                max_content_length = max_content_length(rule.endpoint.func.__self__)
            self.request.httprequest.max_content_length = max_content_length
            _debug.logic(
                "http.dispatch.max_content_length",
                limit=max_content_length,
                resolved=callable(routing["max_content_length"]),
            )

    def _apply_statement_timeout(
        self, routing: collections.abc.Mapping[str, Any]
    ) -> None:
        seconds = routing.get("statement_timeout", self.statement_timeout)
        if seconds is None:
            return
        env = getattr(self.request, "env", None)
        if env is None or env.cr.closed:
            return
        # The cursor remembers the budget and re-arms it (SET LOCAL) before the
        # first statement of every transaction it runs, so a mid-request commit,
        # a savepoint rollback or the promotion replay keep it; it ends with
        # the cursor, i.e. with the request.
        env.cr.set_statement_timeout(seconds)
        _debug.logic(
            "http.dispatch.statement_timeout",
            seconds=seconds,
            source="route" if "statement_timeout" in routing else self.routing_type,
        )

    @abstractmethod
    def dispatch(self, endpoint: Endpoint, args: dict[str, Any]) -> Any:
        pass

    def post_dispatch(self, response: Response) -> None:
        root = self.request.app

        self.request._save_session()
        self.request._session_response = response
        self.request._update_response_from_future(response)
        root.update_standard_headers(response)
        _debug.pipeline(
            "http.dispatch.post",
            dispatcher=self.routing_type,
            status=getattr(response, "status_code", None),
        )

    def _call_endpoint(self, endpoint: Endpoint) -> Any:
        specs = getattr(endpoint, "_param_specs", None)
        _debug.pipeline(
            "http.dispatch.call",
            dispatcher=self.routing_type,
            endpoint=getattr(endpoint, "__qualname__", None),
            params=len(self.request.params),
            typed=bool(specs),
        )
        if specs:
            self.request.params = coerce_params(self.request.params, specs)
        if self.request.db:
            registry = self.request.registry
            if registry is None:
                raise RuntimeError("a database-bound request has a registry")
            with _debug.perf(
                "http.dispatch.endpoint",
                cr=getattr(getattr(self.request, "env", None), "cr", None),
                endpoint=getattr(endpoint, "__qualname__", None),
                via="ir.http",
            ):
                return get_ir_http(registry)._dispatch(endpoint)
        with _debug.perf(
            "http.dispatch.endpoint",
            endpoint=getattr(endpoint, "__qualname__", None),
            via="direct",
        ):
            return endpoint(**self.request.params)

    @abstractmethod
    def prepare_error_response(self, exc: Exception) -> Response | HTTPException:
        pass


class HttpDispatcher(Dispatcher):
    routing_type = "http"

    mimetypes = (
        "application/x-www-form-urlencoded",
        "multipart/form-data",
        "*/*",
    )

    @classmethod
    def is_compatible_with_request(cls, request: RequestState) -> bool:
        return True

    def dispatch(self, endpoint: Endpoint, args: dict[str, Any]) -> Any:
        self.request.params = self.request.get_http_params() | args

        list_params = getattr(endpoint, "typed_list_params", None)
        if list_params:
            httprequest = self.request.httprequest
            for name in list_params:
                if name in args:
                    continue
                values = (
                    httprequest.args.getlist(name)
                    + httprequest.form.getlist(name)
                    + httprequest.files.getlist(name)
                )
                if len(values) > 1:
                    self.request.params[name] = values
                    _debug.logic(
                        "http.dispatch.list_param", param=name, values=len(values)
                    )

        if self.request.httprequest.method not in SAFE_HTTP_METHODS:
            csrf_required = endpoint.routing.get("csrf", True)
            if _debug.logic.enabled:
                _debug.logic(
                    "http.csrf",
                    by="route_exempt"
                    if not csrf_required
                    else "redirect_nodb"
                    if not self.request.db
                    else "checked",
                    method=self.request.httprequest.method,
                    path=getattr(self.request.httprequest, "path", None),
                )
            if csrf_required:
                if not self.request.db:
                    return self.request.redirect("/web/database/selector")
                self._check_csrf_token()

        return self._call_endpoint(endpoint)

    def _check_csrf_token(self) -> None:
        path = self.request.httprequest.path
        token = self.request.params.pop("csrf_token", None)
        if not self.request.is_valid_csrf(token):
            _debug.logic(
                "http.csrf.rejected", path=path, token_present=token is not None
            )
            if token is not None:
                _logger.warning("CSRF validation failed on path '%s'", path)
            else:
                _logger.warning(MISSING_CSRF_WARNING, path)
            msg = "Session expired (invalid CSRF token)"
            raise werkzeug.exceptions.BadRequest(msg)
        _debug.logic("http.csrf.accepted", path=path)

    def prepare_error_response(self, exc: Exception) -> Response | HTTPException:
        if isinstance(exc, SessionExpiredException):
            session = self.request.session
            was_connected = session.uid is not None
            session.logout(keep_db=True)
            if not was_connected:
                session.should_rotate = False
            _debug.logic("http.error.session_expired", was_connected=was_connected)
            return self.request.redirect_query(
                "/web/login", {"redirect": self.request.httprequest.full_path}
            )

        if isinstance(exc, HTTPException):
            _debug.logic(
                "http.error.http_exception",
                error=type(exc).__name__,
                status=exc.code,
                explicit_response=exc.response is not None,
            )
            return exc

        if isinstance(exc, UserError):
            description = exc.args[0] if exc.args else str(exc) or None
            status = exc.http_status
            exc_cls = werkzeug_default_exceptions.get(status)
            _debug.logic(
                "http.error.user_error_mapped",
                error=type(exc).__name__,
                status=status,
                known_status=exc_cls is not None,
            )
            if exc_cls is not None:
                return exc_cls(description)
            return UnprocessableEntity(description)

        _debug.logic("http.error.internal", error=type(exc).__name__)
        return InternalServerError()


class JsonRPCDispatcher(Dispatcher):
    routing_type = "jsonrpc"
    mimetypes = ("application/json", "application/json-rpc")
    cors_allowed_methods = ("POST",)
    serializes_errors_in_dev_mode = True

    def __init__(self, request: RequestState) -> None:
        super().__init__(request)
        self.jsonrequest: dict[str, Any] = {}
        self.request_id: Any = None

    @classmethod
    def is_compatible_with_request(cls, request: RequestState) -> bool:
        return request.httprequest.mimetype in cls.mimetypes

    def dispatch(self, endpoint: Endpoint, args: dict[str, Any]) -> Any:
        try:
            self.jsonrequest = self.request.get_json_data()
        except ValueError as exc:
            _debug.logic(
                "http.jsonrpc.invalid", reason="json", error=type(exc).__name__
            )
            raise self._prepare_bad_request_error("Invalid JSON data") from exc

        if not isinstance(self.jsonrequest, dict):
            _debug.logic("http.jsonrpc.invalid", reason="not_object")
            raise self._prepare_bad_request_error("Invalid JSON-RPC data")

        self.request_id = self.jsonrequest.get("id")
        params = self.jsonrequest.get("params", {})
        if not isinstance(params, dict):
            _debug.logic("http.jsonrpc.invalid", reason="params_not_object")
            raise self._prepare_bad_request_error(
                f"JSON-RPC params must be an object (got {type(params).__name__!r})"
            )
        self.request.params = params | args
        _debug.pipeline(
            "http.jsonrpc.request",
            id=self.request_id,
            method=self.jsonrequest.get("method"),
            params=len(params),
        )

        result = self._call_endpoint(endpoint)
        return self._prepare_jsonrpc_response(result)

    def prepare_error_response(self, exc: Exception) -> Response:
        if isinstance(exc, ParameterError):
            _debug.logic(
                "http.jsonrpc.error",
                code=400,
                error="ParameterError",
                id=self.request_id,
            )
            return self._prepare_bad_request_response(exc.description or "Bad Request")
        error = {
            "code": 0,
            "message": "Odoo Server Error",
            "data": serialize_exception(exc),
        }
        if isinstance(exc, NotFound):
            error["code"] = 404
            error["message"] = "404: Not Found"
        elif isinstance(exc, SessionExpiredException):
            error["code"] = 100
            error["message"] = "Odoo Session Expired"

        _debug.logic(
            "http.jsonrpc.error",
            code=error["code"],
            error=type(exc).__name__,
            id=self.request_id,
        )
        return self._prepare_jsonrpc_response(error=error)

    def _prepare_bad_request_error(self, message: str) -> HTTPException:
        return HTTPException(response=self._prepare_bad_request_response(message))

    def _prepare_bad_request_response(self, message: str) -> Response:
        body = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "error": {"code": 400, "message": message, "data": {}},
        }
        return self.request.prepare_json_response(body, status=400)

    def _prepare_jsonrpc_response(
        self, result: Any = None, error: dict[str, Any] | None = None
    ) -> Response:
        response: dict[str, Any] = {"jsonrpc": "2.0", "id": self.request_id}
        if error is not None:
            response["error"] = error
        else:
            response["result"] = result
            version = getattr(self.request, "_response_version", None)
            if version is not None:
                response["version"] = version

        _debug.pipeline(
            "http.jsonrpc.response",
            id=self.request_id,
            error=error is not None,
            versioned="version" in response,
        )
        return self.request.prepare_json_response(response)


class Json2Dispatcher(Dispatcher):
    routing_type = "json2"
    mimetypes = ("application/json",)
    serializes_errors_in_dev_mode = True

    def __init__(self, request: RequestState) -> None:
        super().__init__(request)
        self.jsonrequest: dict[str, Any] | None = None

    @classmethod
    def is_compatible_with_request(cls, request: RequestState) -> bool:
        return (
            request.httprequest.mimetype in cls.mimetypes
            or not request.httprequest.content_length
        )

    def dispatch(self, endpoint: Endpoint, args: dict[str, Any]) -> Any:
        httprequest = self.request.httprequest
        if (
            httprequest.method not in SAFE_HTTP_METHODS
            and httprequest.mimetype not in self.mimetypes
            and endpoint.routing.get("csrf", True)
        ):
            _debug.logic(
                "http.json2.csrf_rejected",
                method=httprequest.method,
                mimetype=httprequest.mimetype,
            )
            raise werkzeug.exceptions.BadRequest(
                "State-changing json2 requests must use the 'application/json' "
                "Content-Type (CSRF protection)."
            )
        if httprequest.get_data(cache=True):
            try:
                self.jsonrequest = self.request.get_json_data()
            except ValueError as exc:
                _debug.logic(
                    "http.json2.invalid", reason="json", error=type(exc).__name__
                )
                e = f"could not parse the body as json: {exc.args[0]}"
                raise werkzeug.exceptions.BadRequest(e) from exc
            if self.jsonrequest is not None and not isinstance(self.jsonrequest, dict):
                _debug.logic(
                    "http.json2.invalid",
                    reason="not_object",
                    got=type(self.jsonrequest).__name__,
                )
                e = (
                    "JSON request body must be an object (got "
                    f"{type(self.jsonrequest).__name__!r})."
                )
                raise werkzeug.exceptions.BadRequest(e)
        self.request.params = {
            **httprequest.args,
            **(self.jsonrequest or {}),
            **args,
        }
        _debug.pipeline(
            "http.json2.request",
            method=httprequest.method,
            body=self.jsonrequest is not None,
            params=len(self.request.params),
        )

        result = self._call_endpoint(endpoint)
        if isinstance(result, Response):
            _debug.logic("http.json2.result", kind="response")
            return result
        if isinstance(result, werkzeug.wrappers.Response):
            _debug.logic("http.json2.result", kind="werkzeug_response")
            return Response(result)
        _debug.logic("http.json2.result", kind="json")
        return self.request.prepare_json_response(result)

    def prepare_error_response(self, exc: Exception) -> Response:
        if isinstance(exc, HTTPException) and exc.response:
            _debug.logic(
                "http.json2.error",
                status=getattr(exc.response, "status_code", None),
                error=type(exc).__name__,
                kind="explicit_response",
            )
            return Response(exc.response)

        headers = None
        kind = "internal"  # debuglog
        if isinstance(exc, (UserError, SessionExpiredException)):
            status = exc.http_status
            body = serialize_exception(exc)
            kind = "user_error"  # debuglog
        elif isinstance(exc, HTTPException):
            status = exc.code or HTTPStatus.INTERNAL_SERVER_ERROR
            body = serialize_exception(
                exc,
                message=exc.description,
                arguments=(exc.description, status),
            )
            headers = [(k, v) for k, v in exc.get_headers() if k != "Content-Type"]
            kind = "http_exception"  # debuglog
        else:
            status = HTTPStatus.INTERNAL_SERVER_ERROR
            body = serialize_exception(exc)

        _debug.logic(
            "http.json2.error", status=int(status), error=type(exc).__name__, kind=kind
        )
        return self.request.prepare_json_response(
            _prepare_problem_details(body, int(status), kind == "http_exception"),
            headers=[*(headers or []), ("Content-Type", PROBLEM_JSON_MIMETYPE)],
            status=status,
        )
