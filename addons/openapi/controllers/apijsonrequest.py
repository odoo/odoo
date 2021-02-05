import functools
import json
import logging
import os
import pprint
import time

import werkzeug.wrappers

import odoo
from odoo.http import (
    AuthenticationError,
    Response,
    Root,
    SessionExpiredException,
    WebRequest,
    request,
    rpc_request,
    rpc_response,
    serialize_exception,
)
from odoo.service.server import memory_info
from odoo.tools import date_utils

try:
    import psutil
except ImportError:
    psutil = None


_logger = logging.getLogger(__name__)


class ApiJsonRequest(WebRequest):
    _request_type = "apijson"

    def __init__(self, *args):
        super(ApiJsonRequest, self).__init__(*args)

        self.jsonp_handler = None
        self.params = {}

        args = self.httprequest.args
        jsonp = args.get("jsonp")
        self.jsonp = jsonp
        request = None
        request_id = args.get("id")

        if jsonp and self.httprequest.method == "POST":
            # jsonp 2 steps step1 POST: save call
            def handler():
                self.session[
                    "jsonp_request_{}".format(request_id)
                ] = self.httprequest.form["rb"]
                self.session.modified = True
                headers = [("Content-Type", "text/plain; charset=utf-8")]
                r = werkzeug.wrappers.Response(request_id, headers=headers)
                return r

            self.jsonp_handler = handler
            return
        elif jsonp and args.get("rb"):
            # jsonp method GET
            request = args.get("rb")
        elif jsonp and request_id:
            # jsonp 2 steps step2 GET: run and return result
            request = self.session.pop("jsonp_request_{}".format(request_id), "{}")
        else:
            # regular jsonrpc2
            request = self.httprequest.get_data().decode(self.httprequest.charset)

        # Read POST content or POST Form Data named "request"
        try:
            self.ApiJsonRequest = json.loads(request)
        except ValueError:
            msg = "Invalid JSON data: {!r}".format(request)
            _logger.info("%s: %s", self.httprequest.path, msg)
            raise werkzeug.exceptions.BadRequest(msg)

        self.params = dict(self.ApiJsonRequest or {})
        self.context = self.params.pop("context", dict(self.session.context))

    def _json_response(self, result=None, error=None):

        response = {}
        if error is not None:
            response["error"] = error

        mime = "application/json"
        status = error and error.pop("code") or result.status_code
        body = (
            response
            and json.dumps(response, default=date_utils.json_default)
            or result.data
        )

        return Response(
            body,
            status=status,
            headers=[("Content-Type", mime), ("Content-Length", len(body))],
        )

    def _handle_exception(self, exception):
        """Called within an except block to allow converting exceptions
           to arbitrary responses. Anything returned (except None) will
           be used as response."""
        try:
            return super(ApiJsonRequest, self)._handle_exception(exception)
        except Exception:
            if not isinstance(
                exception,
                (
                    odoo.exceptions.Warning,
                    SessionExpiredException,
                    odoo.exceptions.except_orm,
                    werkzeug.exceptions.NotFound,
                ),
            ):
                _logger.exception("Exception during JSON request handling.")
            error = {
                "code": exception.response.status_code,
                "message": "Odoo Server Error",
                "data": serialize_exception(exception),
                "openapi_message": json.loads(exception.response.response[0]),
            }
            if isinstance(exception, werkzeug.exceptions.NotFound):
                error["http_status"] = 404
                error["code"] = 404
                error["message"] = "404: Not Found"
            if isinstance(exception, AuthenticationError):
                error["code"] = 100
                error["message"] = "Odoo Session Invalid"
            if isinstance(exception, SessionExpiredException):
                error["code"] = 100
                error["message"] = "Odoo Session Expired"
            return self._json_response(error=error)

    def dispatch(self):
        if self.jsonp_handler:
            return self.jsonp_handler()
        try:
            rpc_request_flag = rpc_request.isEnabledFor(logging.DEBUG)
            rpc_response_flag = rpc_response.isEnabledFor(logging.DEBUG)
            if rpc_request_flag or rpc_response_flag:
                endpoint = self.endpoint.method.__name__
                model = self.params.get("model")
                method = self.params.get("method")
                args = self.params.get("args", [])

                start_time = time.time()
                start_memory = 0
                if psutil:
                    start_memory = memory_info(psutil.Process(os.getpid()))
                if rpc_request and rpc_response_flag:
                    rpc_request.debug(
                        "%s: %s %s, %s", endpoint, model, method, pprint.pformat(args)
                    )

            result = self._call_function(**self.params)

            if rpc_request_flag or rpc_response_flag:
                end_time = time.time()
                end_memory = 0
                if psutil:
                    end_memory = memory_info(psutil.Process(os.getpid()))
                logline = "{}: {} {}: time:{:.3f}s mem: {}k -> {}k (diff: {}k)".format(
                    endpoint,
                    model,
                    method,
                    end_time - start_time,
                    start_memory / 1024,
                    end_memory / 1024,
                    (end_memory - start_memory) / 1024,
                )
                if rpc_response_flag:
                    rpc_response.debug("%s, %s", logline, pprint.pformat(result))
                else:
                    rpc_request.debug(logline)
            return self._json_response(result)
        except Exception as e:
            return self._handle_exception(e)


# Copy of http.route adding routing 'type':'api'
def api_route(route=None, **kw):

    routing = kw.copy()
    assert "type" not in routing or routing["type"] in ("http", "json", "apijson")

    def decorator(f):
        if route:
            if isinstance(route, list):
                routes = route
            else:
                routes = [route]
            routing["routes"] = routes

        @functools.wraps(f)
        def response_wrap(*args, **kw):
            response = f(*args, **kw)
            if isinstance(response, Response) or f.routing_type in ("apijson", "json"):
                return response

            if isinstance(response, (bytes, str)):
                return Response(response)

            if isinstance(response, werkzeug.exceptions.HTTPException):
                response = response.get_response(request.httprequest.environ)
            if isinstance(response, werkzeug.wrappers.BaseResponse):
                response = Response.force_type(response)
                response.set_default()
                return response

            _logger.warn(
                "<function %s.%s> returns an invalid response type for an http request"
                % (f.__module__, f.__name__)
            )
            return response

        response_wrap.routing = routing
        response_wrap.original_func = f
        return response_wrap

    return decorator


get_request_original = Root.get_request


def api_get_request(self, httprequest):
    # deduce type of request

    if (
        "authorization" in httprequest.headers
        and httprequest.headers.get("content-type", "") == "application/json"
    ):
        return ApiJsonRequest(httprequest)

    return get_request_original(self, httprequest)


Root.get_request = api_get_request
