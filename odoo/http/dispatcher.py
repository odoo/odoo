from __future__ import annotations

import logging
import traceback
import typing
import weakref
from abc import ABC, abstractmethod
from http import HTTPStatus

from werkzeug.exceptions import (
    BadRequest,
    HTTPException,
    InternalServerError,
    NotFound,
    UnprocessableEntity,
    abort,
)
from werkzeug.exceptions import default_exceptions as werkzeug_default_exceptions

from odoo.exceptions import UserError
from odoo.tools import exception_to_unicode

if typing.TYPE_CHECKING:
    from collections.abc import Collection

    import werkzeug.routing

    from .requestlib import Request
    from .routing_map import Endpoint

_logger = logging.getLogger('odoo.http')

CORS_MAX_AGE = 60 * 60 * 24  # 1 day
""" The validity duration of a preflight response. """

SAFE_HTTP_METHODS = ('GET', 'HEAD', 'OPTIONS', 'TRACE')
""" The HTTP methods that do not require a CSRF validation. """

MISSING_CSRF_WARNING = """\
No CSRF validation token provided for path %r

Odoo URLs are CSRF-protected by default (when accessed with unsafe
HTTP methods). See
https://www.odoo.com/documentation/master/developer/reference/addons/http.html#csrf
for more details.

* if this endpoint is accessed through Odoo via py-QWeb form, embed a CSRF
  token in the form, Tokens are available via `request.csrf_token()`
  can be provided through a hidden input and must be POST-ed named
  `csrf_token` e.g. in your form add:
      <input type="hidden" name="csrf_token" t-att-value="request.csrf_token()"/>

* if the form is generated or posted in javascript, the token value is
  available as `csrf_token` on `web.core` and as the `csrf_token`
  value in the default js-qweb execution context

* if the form is accessed by an external third party (e.g. REST API
  endpoint, payment gateway callback) you will need to disable CSRF
  protection (and implement your own protection if necessary) by
  passing the `csrf=False` parameter to the `route` decorator.
"""


def serialize_exception(exception: Exception, *, message: str | None = None, arguments=None) -> dict[str, typing.Any]:
    name = type(exception).__name__
    module = type(exception).__module__

    return {
        'name': f'{module}.{name}' if module else name,
        'message': exception_to_unicode(exception) if message is None else message,
        'arguments': exception.args if arguments is None else arguments,
        'context': getattr(exception, 'context', {}),
        'debug': ''.join(traceback.format_exception(exception)),
    }


_dispatchers: dict[str, type[Dispatcher]] = {}


class Dispatcher(ABC):
    routing_type: str
    mimetypes: Collection[str] = ()

    @classmethod
    def __init_subclass__(cls):
        super().__init_subclass__()
        _dispatchers[cls.routing_type] = cls

    def __init__(self, request: Request):
        # use a weak reference to break the cycle between the dispatcher and
        # the Request object so they can be collected by the GC
        self._request = weakref.ref(request)

    @property
    def request(self) -> Request:
        return self._request()

    @classmethod
    @abstractmethod
    def is_compatible_with(cls, request: Request) -> bool:
        """
        Determine if the current request is compatible with this
        dispatcher.
        """

    def pre_dispatch(self, rule: werkzeug.routing.Rule, args):
        """
        Prepare the system before dispatching the request to its
        controller. This method is often overridden in ir.http to
        extract some info from the request query-string or headers and
        to save them in the session or in the context.
        """
        routing = rule.endpoint.routing
        self.request.session.can_save &= routing.get('save_session', True)

        set_header = self.request.future_response.headers.set
        cors = routing.get('cors')
        if cors:
            set_header('Access-Control-Allow-Origin', cors)
            set_header('Access-Control-Allow-Methods', (
                'POST' if routing['type'] == JsonRPCDispatcher.routing_type
                else ', '.join(routing['methods'] or ['GET', 'POST'])
            ))

        if cors and self.request.httprequest.method == 'OPTIONS':
            set_header('Access-Control-Max-Age', str(CORS_MAX_AGE))
            set_header('Access-Control-Allow-Headers',
                       'Origin, X-Requested-With, Content-Type, Accept, Authorization')
            abort(Response(status=204))

        if 'max_content_length' in routing:
            max_content_length = routing['max_content_length']
            if callable(max_content_length):
                max_content_length = max_content_length(rule.endpoint.func.__self__)
            self.request.httprequest.max_content_length = max_content_length

    @abstractmethod
    def dispatch(self, endpoint: Endpoint, args) -> Response:
        """
        Extract the params from the request's body and call the
        endpoint. While it is preferred to override ir.http._pre_dispatch
        and ir.http._post_dispatch, this method can be override to have
        a tight control over the dispatching.
        """

    def post_dispatch(self, response: Response):
        """
        Manipulate the HTTP response to inject various headers, also
        save the session when it is dirty.
        """
        save_session(self.request)
        self.request._inject_future_response(response)
        root.set_csp(response)

    @abstractmethod
    def handle_error(self, exc: Exception) -> Response | HTTPException:
        """
        Transform the exception into a valid HTTP response. Called upon
        any exception while serving a request.
        """


class HttpDispatcher(Dispatcher):
    routing_type = 'http'

    mimetypes = ('application/x-www-form-urlencoded', 'multipart/form-data', '*/*')

    @classmethod
    def is_compatible_with(cls, request):
        return True

    def dispatch(self, endpoint, args):
        """
        Perform http-related actions such as deserializing the request
        body and query-string and checking cors/csrf while dispatching a
        request to a ``type='http'`` route.

        See :meth:`~odoo.http.Response.load` method for the compatible
        endpoint return types.
        """
        self.request.params = dict(self.request.get_http_params(), **args)

        # Check for CSRF token for relevant requests
        is_http_method_safe = self.request.httprequest.method in SAFE_HTTP_METHODS
        if not is_http_method_safe and endpoint.routing.get('csrf', True):
            if not self.request.db:
                return self.request.redirect('/web/database/selector')

            token = self.request.params.pop('csrf_token', None)
            if not self.request.validate_csrf(token):
                if token is not None:
                    _logger.warning(
                        "CSRF validation failed on path '%s'",
                        self.request.httprequest.path)
                else:
                    _logger.warning(MISSING_CSRF_WARNING, self.request.httprequest.path)
                e = "Session expired (invalid CSRF token)"
                raise BadRequest(e)

        if self.request.db:
            response = self.request.registry['ir.http']._dispatch(endpoint)
        else:
            response = endpoint(**self.request.params)
        return response

    def handle_error(self, exc):
        """
        Handle any exception that occurred while dispatching a request
        to a `type='http'` route. Also handle exceptions that occurred
        when no route matched the request path, when no fallback page
        could be delivered and that the request ``Content-Type`` was not
        json.

        :param Exception exc: the exception that occurred.
        :returns: a WSGI response
        """
        if isinstance(exc, SessionExpiredException):
            if isinstance(exc, CheckIdentityException):
                # The user is redirected to the identity confirmation page.
                # This ensures that re-authentication can be completed before
                # redirecting to the original request.
                return self.request.redirect_query('/web/session/identity', {
                    'redirect': self.request.httprequest.full_path,
                })
            session = self.request.session
            was_connected = session.uid is not None
            logout(session, keep_db=True)
            response = self.request.redirect_query('/web/login', {
                'redirect': self.request.httprequest.full_path})
            if was_connected:
                root.session_store.rotate(session, self.request.env)
                response.set_cookie(
                    'session_id',
                    session.sid,
                    max_age=get_session_max_inactivity(self.request.env),
                    httponly=True,
                )
            return response

        if isinstance(exc, HTTPException):
            return exc

        if isinstance(exc, UserError):
            try:
                return werkzeug_default_exceptions[exc.http_status](exc.args[0])
            except (KeyError, AttributeError):
                return UnprocessableEntity(exc.args[0])

        return InternalServerError()


class JsonRPCDispatcher(Dispatcher):
    routing_type = 'jsonrpc'
    mimetypes = ('application/json', 'application/json-rpc')

    def __init__(self, request):
        super().__init__(request)
        self.jsonrequest = {}
        self.request_id = None

    @classmethod
    def is_compatible_with(cls, request):
        return request.httprequest.mimetype in cls.mimetypes

    def dispatch(self, endpoint, args):
        """
        `JSON-RPC 2 <http://www.jsonrpc.org/specification>`_ over HTTP.

        Our implementation differs from the specification on two points:

        1. The ``method`` member of the JSON-RPC request payload is
           ignored as the HTTP path is already used to route the request
           to the controller.
        2. We only support parameter structures by-name, i.e. the
           ``params`` member of the JSON-RPC request payload MUST be a
           JSON Object and not a JSON Array.

        In addition, it is possible to pass a context that replaces
        the session context via a special ``context`` argument that is
        removed prior to calling the endpoint.

        Successful request::

          --> {"jsonrpc": "2.0", "method": "call", "params": {"arg1": "val1" }, "id": null}

          <-- {"jsonrpc": "2.0", "result": { "res1": "val1" }, "id": null}

        Request producing a error::

          --> {"jsonrpc": "2.0", "method": "call", "params": {"arg1": "val1" }, "id": null}

          <-- {"jsonrpc": "2.0", "error": {"code": 1, "message": "End user error message.", "data": {"code": "codestring", "debug": "traceback" } }, "id": null}

        """
        try:
            self.jsonrequest = self.request.get_json_data()
            self.request_id = self.jsonrequest.get('id')
        except ValueError:
            # must use abort+Response to bypass handle_error
            abort(Response("Invalid JSON data", status=400))
        except AttributeError:
            # must use abort+Response to bypass handle_error
            abort(Response("Invalid JSON-RPC data", status=400))

        self.request.params = dict(self.jsonrequest.get('params', {}), **args)

        if self.request.db:
            result = self.request.registry['ir.http']._dispatch(endpoint)
        else:
            result = endpoint(**self.request.params)
        return self._response(result)

    def handle_error(self, exc):
        """
        Handle any exception that occurred while dispatching a request to
        a `type='jsonrpc'` route. Also handle exceptions that occurred when
        no route matched the request path, that no fallback page could
        be delivered and that the request ``Content-Type`` was json.

        :param exc: the exception that occurred.
        :returns: a WSGI application
        """
        error = {
            'code': 0,  # we don't care of this code
            'message': "Odoo Server Error",
            'data': serialize_exception(exc),
        }
        if isinstance(exc, NotFound):
            error['code'] = 404
            error['message'] = "404: Not Found"
        elif isinstance(exc, SessionExpiredException):
            error['code'] = 100
            error['message'] = "Odoo Session Expired"

        return self._response(error=error)

    def _response(self, result=None, error=None):
        response = {'jsonrpc': '2.0', 'id': self.request_id}
        if error is not None:
            response['error'] = error
        if result is not None:
            response['result'] = result

        return self.request.make_json_response(response)


class Json2Dispatcher(Dispatcher):
    routing_type = 'json2'
    mimetypes = ('application/json',)

    def __init__(self, request):
        super().__init__(request)
        self.jsonrequest = None

    @classmethod
    def is_compatible_with(cls, request):
        return (
            request.httprequest.mimetype in cls.mimetypes
            or not request.httprequest.content_length
        )

    def dispatch(self, endpoint, args):
        # "args" are the path parameters, "id" in /web/image/<id>
        if self.request.httprequest.content_length:
            try:
                self.jsonrequest = self.request.get_json_data()
            except ValueError as exc:
                e = f"could not parse the body as json: {exc.args[0]}"
                raise BadRequest(e) from exc
        try:
            self.request.params = self.jsonrequest | args
        except TypeError:
            self.request.params = dict(args)  # make a copy

        if self.request.db:
            result = self.request.registry['ir.http']._dispatch(endpoint)
        else:
            result = endpoint(**self.request.params)
        if isinstance(result, Response):
            return result
        return self.request.make_json_response(result)

    def handle_error(self, exc):
        if isinstance(exc, HTTPException) and exc.response:
            return exc.response

        headers = None
        if isinstance(exc, (UserError, SessionExpiredException)):
            status = exc.http_status
            body = serialize_exception(exc)
        elif isinstance(exc, HTTPException):
            status = exc.code
            body = serialize_exception(
                exc,
                message=exc.description,
                arguments=(exc.description, exc.code),
            )
            # strip Content-Type but keep the remaining headers
            ct, *headers = exc.get_headers()
            assert ct == ('Content-Type', 'text/html; charset=utf-8')
        else:
            status = HTTPStatus.INTERNAL_SERVER_ERROR
            body = serialize_exception(exc)

        return self.request.make_json_response(body, headers=headers, status=status)


# ruff: noqa: E402
from .response import Response
from .router import root
from .session import (
    CheckIdentityException,
    SessionExpiredException,
    get_session_max_inactivity,
    logout,
    save_session,
)
