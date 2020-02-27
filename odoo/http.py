# -*- coding: utf-8 -*-
#----------------------------------------------------------
# Odoo HTTP layer
#----------------------------------------------------------
import ast
import collections
import contextlib
import datetime
import functools
import hashlib
import hmac
import inspect
import logging
import mimetypes
import os
import pprint
import random
import re
import sys
import threading
import time
import traceback
import zlib

import babel.core
import psycopg2
import json
import werkzeug.contrib.sessions
import werkzeug.datastructures
import werkzeug.exceptions
import werkzeug.local
import werkzeug.routing
import werkzeug.wrappers
import werkzeug.wsgi
from werkzeug import urls

try:
    # werkzeug >= 0.15
    from werkzeug.middleware.proxy_fix import ProxyFix as ProxyFix_
    # 0.15 also supports port and prefix, but 0.14 only forwarded for, proto
    # and host so replicate that
    ProxyFix = lambda app: ProxyFix_(app, x_for=1, x_proto=1, x_host=1)
except ImportError:
    # werkzeug < 0.15
    from werkzeug.contrib.fixers import ProxyFix

try:
    import psutil
except ImportError:
    psutil = None

import odoo
from odoo import fields
from .modules.module import module_manifest
from .service.server import memory_info
from .service import security, model as service_model
from .tools.func import lazy_property
from .tools import ustr, consteq, frozendict, pycompat, unique, date_utils
from .tools.mimetypes import guess_mimetype

_logger = logging.getLogger(__name__)
_logger_rpc_request = logging.getLogger(__name__ + '.rpc.request')
_logger_rpc_response = logging.getLogger(__name__ + '.rpc.response')
_logger_rpc_request_flag = _logger_rpc_request.isEnabledFor(logging.DEBUG)
_logger_rpc_response_flag = _logger_rpc_response.isEnabledFor(logging.DEBUG) # should rather be named rpc content

#----------------------------------------------------------
# Constants
#----------------------------------------------------------

# One week cache for static content (static files in apps, library files, ...)
# Safe resources may use what google page speed recommends (1 year)
# (attachments with unique hash in the URL, ...)
STATIC_CACHE = 3600 * 24 * 7
STATIC_CACHE_LONG = 3600 * 24 * 365

# To remove when corrected in Babel
babel.core.LOCALE_ALIASES['nb'] = 'nb_NO'

""" Debug mode is stored in session and should always be a string.
    It can be activated with an URL query string `debug=<mode>` where
    mode is either:
    - 'tests' to load tests assets
    - 'assets' to load assets non minified
    - any other truthy value to enable simple debug mode (to show some
      technical feature, to show complete traceback in frontend error..)
    - any falsy value to disable debug mode

    You can use any truthy/falsy value from `str2bool` (eg: 'on', 'f'..)
    Multiple debug modes can be activated simultaneously, separated with
    a comma (eg: 'tests, assets').
"""
ALLOWED_DEBUG_MODES = ['', '1', 'assets', 'tests']

# don't trigger debugger for those exceptions, they carry user-facing warnings
# and indications, they're not necessarily indicative of anything being
# *broken*
NO_POSTMORTEM = (
    odoo.exceptions.except_orm,
    odoo.exceptions.AccessDenied,
    odoo.exceptions.Warning,
    odoo.exceptions.RedirectWarning,
)

#----------------------------------------------------------
# Helpers
#----------------------------------------------------------
# TODO move to request method as helper ?
def local_redirect(path, query=None, keep_hash=False, code=303):
    # FIXME: drop the `keep_hash` param, now useless
    url = path
    if not query:
        query = {}
    if query:
        url += '?' + urls.url_encode(query)
    return werkzeug.utils.redirect(url, code)

def redirect_with_hash(url, code=303):
    # Section 7.1.2 of RFC 7231 requires preservation of URL fragment through redirects,
    # so we don't need any special handling anymore. This function could be dropped in the future.
    # seealso : http://www.rfc-editor.org/info/rfc7231
    #           https://tools.ietf.org/html/rfc7231#section-7.1.2
    return werkzeug.utils.redirect(url, code)

def serialize_exception(e):
    tmp = {
        "name": type(e).__module__ + "." + type(e).__name__ if type(e).__module__ else type(e).__name__,
        "debug": traceback.format_exc(),
        "message": ustr(e),
        "arguments": e.args,
        "exception_type": "internal_error",
        "context": getattr(e, 'context', {}),
    }
    if isinstance(e, odoo.exceptions.UserError):
        tmp["exception_type"] = "user_error"
    elif isinstance(e, odoo.exceptions.Warning):
        tmp["exception_type"] = "warning"
    elif isinstance(e, odoo.exceptions.RedirectWarning):
        tmp["exception_type"] = "warning"
    elif isinstance(e, odoo.exceptions.AccessError):
        tmp["exception_type"] = "access_error"
    elif isinstance(e, odoo.exceptions.MissingError):
        tmp["exception_type"] = "missing_error"
    elif isinstance(e, odoo.exceptions.AccessDenied):
        tmp["exception_type"] = "access_denied"
    elif isinstance(e, odoo.exceptions.ValidationError):
        tmp["exception_type"] = "validation_error"
    elif isinstance(e, odoo.exceptions.except_orm):
        tmp["exception_type"] = "except_orm"
    return tmp

#----------------------------------------------------------
# Request and Response
#----------------------------------------------------------
# Thread local global request object
_request_stack = werkzeug.local.LocalStack()
request = _request_stack() # global proxy that always redirect to the current request object.

class Response(werkzeug.wrappers.Response):
    """ Response object passed through controller route chain.

    In addition to the :class:`werkzeug.wrappers.Response` parameters, this
    class's constructor can take the following additional parameters
    for QWeb Lazy Rendering.

    :param basestring template: template to render
    :param dict qcontext: Rendering context to use
    :param int uid: User id to use for the ir.ui.view render call,
                    ``None`` to use the request's user (the default)

    these attributes are available as parameters on the Response object and
    can be altered at any time before rendering

    Also exposes all the attributes and methods of
    :class:`werkzeug.wrappers.Response`.
    """
    default_mimetype = 'text/html'
    def __init__(self, *args, **kw):
        template = kw.pop('template', None)
        qcontext = kw.pop('qcontext', None)
        uid = kw.pop('uid', None)
        super(Response, self).__init__(*args, **kw)
        self.set_default(template, qcontext, uid)

    def set_default(self, template=None, qcontext=None, uid=None):
        self.template = template
        self.qcontext = qcontext or dict()
        self.qcontext['response_template'] = self.template
        self.uid = uid
        # Support for Cross-Origin Resource Sharing
        if request.endpoint and 'cors' in request.endpoint.routing:
            self.headers.set('Access-Control-Allow-Origin', request.endpoint.routing['cors'])
            methods = 'GET, POST'
            if request.endpoint.routing['type'] == 'json':
                methods = 'POST'
            elif request.endpoint.routing.get('methods'):
                methods = ', '.join(request.endpoint.routing['methods'])
            self.headers.set('Access-Control-Allow-Methods', methods)

    @property
    def is_qweb(self):
        return self.template is not None

    def render(self):
        """ Renders the Response's template, returns the result
        """
        env = request.env(user=self.uid or request.uid or odoo.SUPERUSER_ID)
        self.qcontext['request'] = request
        return env["ir.ui.view"].render_template(self.template, self.qcontext)

    def flatten(self):
        """ Forces the rendering of the response's template, sets the result
        as response body and unsets :attr:`.template`
        """
        if self.template:
            self.response.append(self.render())
            self.template = None

class WebRequest(object):
    """ Odoo Web request.

    :param httprequest: a wrapped werkzeug Request object
    :type httprequest: :class:`werkzeug.wrappers.BaseRequest`

    .. attribute:: httprequest

        the original :class:`werkzeug.wrappers.Request` object provided to the
        request

    .. attribute:: params

        :class:`~collections.Mapping` of request parameters, also provided
        directly to the handler method as keyword arguments
    """
    def __init__(self, httprequest):
        self.httprequest = httprequest
        self.httpresponse = None
        self.disable_db = False
        self.endpoint = None
        self.endpoint_arguments = None
        self.auth_method = None
        self._request_type = None
        self._cr = None
        self._uid = None
        self._context = None
        self._env = None

        # prevents transaction commit, use when you catch an exception during handling
        self._failed = None

        # set db/uid trackers - they're cleaned up at the WSGI
        # dispatching phase in odoo.http.application
        if self.db:
            threading.current_thread().dbname = self.db
        if self.session.uid:
            threading.current_thread().uid = self.session.uid

    @property
    def cr(self):
        """ :class:`~odoo.sql_db.Cursor` initialized for the current method call.

        Accessing the cursor when the current request uses the ``none``
        authentication will raise an exception.
        """
        # can not be a lazy_property because manual rollback in _call_function
        # if already set (?)
        if not self.db:
            raise RuntimeError('request not bound to a database')
        if not self._cr:
            self._cr = self.registry.cursor()
        return self._cr

    @property
    def uid(self):
        return self._uid

    @uid.setter
    def uid(self, val):
        self._uid = val
        self._env = None

    @property
    def context(self):
        """ :class:`~collections.Mapping` of context values for the current request """
        if self._context is None:
            self._context = frozendict(self.session.context)
        return self._context

    @context.setter
    def context(self, val):
        self._context = frozendict(val)
        self._env = None

    @property
    def db(self):
        """
        The database linked to this request. Can be ``None``
        if the current request uses the ``none`` authentication.
        """
        return self.session.db if not self.disable_db else None

    @property
    def registry(self):
        """
        The registry to the database linked to this request. Can be ``None``
        if the current request uses the ``none`` authentication.

        .. deprecated:: 8.0

            use :attr:`.env`
        """
        return odoo.registry(self.db)

    @property
    def env(self):
        """ The :class:`~odoo.api.Environment` bound to current request. """
        if self._env is None:
            self._env = odoo.api.Environment(self.cr, self.uid, self.context)
        return self._env

    @lazy_property
    def session(self):
        """ :class:`OpenERPSession` holding the HTTP session data for the
        current http session
        """
        return self.httprequest.session

    def __enter__(self):
        _request_stack.push(self)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        _request_stack.pop()

        if self._cr:
            try:
                if exc_type is None and not self._failed:
                    self._cr.commit()
                    if self.registry:
                        self.registry.signal_changes()
                elif self.registry:
                    self.registry.reset_changes()
            finally:
                self._cr.close()
        # just to be sure no one tries to re-use the request
        self.disable_db = True
        self.uid = None

    #------------------------------------------------------
    # Common helpers
    #------------------------------------------------------
    def _call_function(self, *args, **kwargs):
        request = self
        if self.endpoint.routing['type'] != self._request_type:
            msg = "%s, %s: Function declared as capable of handling request of type '%s' but called with a request of type '%s'"
            params = (self.endpoint.original, self.httprequest.path, self.endpoint.routing['type'], self._request_type)
            _logger.info(msg, *params)
            raise werkzeug.exceptions.BadRequest(msg % params)

        if self.endpoint_arguments:
            kwargs.update(self.endpoint_arguments)

        # Backward for 7.0
        if self.endpoint.first_arg_is_req:
            args = (request,) + args

        first_time = True

        # Correct exception handling and concurency retry
        @service_model.check
        def checked_call(___dbname, *a, **kw):
            nonlocal first_time
            # The decorator can call us more than once if there is an database error. In this
            # case, the request cursor is unusable. Rollback transaction to create a new one.
            if self._cr and not first_time:
                self._cr.rollback()
                self.env.clear()
            first_time = False
            result = self.endpoint(*a, **kw)
            if isinstance(result, Response) and result.is_qweb:
                # Early rendering of lazy responses to benefit from @service_model.check protection
                result.flatten()
            return result

        if self.db:
            return checked_call(self.db, *args, **kwargs)
        return self.endpoint(*args, **kwargs)

    def _handle_exception(self, exception):
        """Called within an except block to allow converting exceptions
           to abitrary responses. Anything returned (except None) will
           be used as response."""
        self._failed = exception  # prevent tx commit
        if not isinstance(exception, NO_POSTMORTEM) and not isinstance(exception, werkzeug.exceptions.HTTPException):
            odoo.tools.debugger.post_mortem( odoo.tools.config, sys.exc_info())

        # WARNING: do not inline or it breaks: raise...from evaluates strictly
        # LTR so would first remove traceback then copy lack of traceback
        new_cause = Exception().with_traceback(exception.__traceback__)
        # tries to provide good chained tracebacks, just re-raising exception
        # generates a weird message as stacks just get concatenated, exceptions
        # not guaranteed to copy.copy cleanly & we want `exception` as leaf (for
        # callers to check & look at)
        raise exception.with_traceback(None) from new_cause

        # HTTP
        """Called within an except block to allow converting exceptions
           to abitrary responses. Anything returned (except None) will
           be used as response."""
        try:
            return super(HttpRequest, self)._handle_exception(exception)
        except SessionExpiredException:
            if not request.params.get('noredirect'):
                query = werkzeug.urls.url_encode({ 'redirect': self.httprequest.url, })
                return werkzeug.utils.redirect('/web/login?%s' % query)

        except werkzeug.exceptions.HTTPException as e:
            return e
        # JSON

        """Called within an except block to allow converting exceptions
           to arbitrary responses. Anything returned (except None) will
           be used as response."""
        try:
            return super(JsonRequest, self)._handle_exception(exception)
        except Exception:
            if not isinstance(exception, SessionExpiredException):
                if exception.args and exception.args[0] == "bus.Bus not available in test mode":
                    _logger.info(exception)
                elif isinstance(exception, (odoo.exceptions.Warning, odoo.exceptions.except_orm,
                                          werkzeug.exceptions.NotFound)):
                    _logger.warning(exception)
                else:
                    _logger.exception("Exception during JSON request handling.")
            error = {
                'code': 200,
                'message': "Odoo Server Error",
                'data': serialize_exception(exception),
            }
            if isinstance(exception, werkzeug.exceptions.NotFound):
                error['http_status'] = 404
                error['code'] = 404
                error['message'] = "404: Not Found"
            if isinstance(exception, AuthenticationError):
                error['code'] = 100
                error['message'] = "Odoo Session Invalid"
            if isinstance(exception, SessionExpiredException):
                error['code'] = 100
                error['message'] = "Odoo Session Expired"
            return self._json_response(error=error)

    def rpc_debug_pre(self, params, model=None, method=None):
        # For Odoo service RPC params is a list or a tuple, for call_kw style it is a dict
        if _logger_rpc_request_flag or _logger_rpc_response_flag:
            endpoint = self.endpoint.method.__name__
            model = model or params.get('model')
            method = method or params.get('method')

            # For Odoo service RPC call password is always 3rd argument in a
            # request, we replace it in logs so it's easier to forward logs for
            # diagnostics/debugging purposes...
            if isinstance(params, (tuple, list)):
                if len(params) > 2:
                    log_params = list(params)
                    log_params[2] = '*'

            start_time = time.time()
            start_memory = 0
            if psutil:
                start_memory = memory_info(psutil.Process(os.getpid()))
            _logger_rpc_request.debug('%s: request %s.%s: %s', endpoint, model, method, pprint.pformat(params))
            return (endpoint, model, method, start_time, start_memory)

    def rpc_debug_post(self, t0, result):
        if _logger_rpc_request_flag or _logger_rpc_response_flag:
            endpoint, model, method, start_time, start_memory = t0
            end_time = time.time()
            end_memory = 0
            if psutil:
                end_memory = memory_info(psutil.Process(os.getpid()))
            logline = '%s: response %s.%s: time:%.3fs mem: %sk -> %sk (diff: %sk)' % (name, model, method, end_time - start_time, start_memory / 1024, end_memory / 1024, (end_memory - start_memory)/1024)
            if _logger_rpc_response_flag:
                rpc_response.debug('%s, response: %s', logline, pprint.pformat(result))
            else:
                rpc_request.debug(logline)

    def rpc_service(service_name, method, args):
        """ Handle an Odoo Service RPC call.  """
        try:
            threading.current_thread().uid = None
            threading.current_thread().dbname = None

            t0 = self.rpc_debug_pre(args, service_name, method)

            result = False
            if service_name == 'common':
                result = odoo.service.common.dispatch(method, args)
            elif service_name == 'db':
                result = odoo.service.db.dispatch(method, args)
            elif service_name == 'object':
                result = odoo.service.model.dispatch(method, args)

            t0 = self.rpc_debug_post(t0, result)

            return result
        except NO_POSTMORTEM:
            raise
        except odoo.exceptions.DeferredException as e:
            _logger.exception(odoo.tools.exception_to_unicode(e))
            odoo.tools.debugger.post_mortem(odoo.tools.config, e.traceback)
            raise
        except Exception as e:
            _logger.exception(odoo.tools.exception_to_unicode(e))
            odoo.tools.debugger.post_mortem(odoo.tools.config, sys.exc_info())
            raise

    #------------------------------------------------------
    # Plain HTTP Helpers and Handler
    #------------------------------------------------------
    def render(self, template, qcontext=None, lazy=True, **kw):
        """ Lazy render of a QWeb template.

        The actual rendering of the given template will occur at then end of
        the dispatching. Meanwhile, the template and/or qcontext can be
        altered or even replaced by a static response.

        :param basestring template: template to render
        :param dict qcontext: Rendering context to use
        :param bool lazy: whether the template rendering should be deferred
                          until the last possible moment
        :param kw: forwarded to werkzeug's Response object
        """
        response = Response(template=template, qcontext=qcontext, **kw)
        if not lazy:
            return response.render()
        return response

    def not_found(self, description=None):
        """ Shortcut for a `HTTP 404
        <http://tools.ietf.org/html/rfc7231#section-6.5.4>`_ (Not Found)
        response
        """
        return werkzeug.exceptions.NotFound(description)

    def make_response(self, data, headers=None, cookies=None):
        """ Helper for non-HTML responses, or HTML responses with custom
        response headers or cookies.

        While handlers can just return the HTML markup of a page they want to
        send as a string if non-HTML data is returned they need to create a
        complete response object, or the returned data will not be correctly
        interpreted by the clients.

        :param basestring data: response body
        :param headers: HTTP headers to set on the response
        :type headers: ``[(name, value)]``
        :param collections.Mapping cookies: cookies to set on the client
        """
        response = Response(data, headers=headers)
        if cookies:
            for k, v in cookies.items():
                response.set_cookie(k, v)
        return response

    def csrf_token(self, time_limit=3600):
        """ Generates and returns a CSRF token for the current session

        :param time_limit: the CSRF token should only be valid for the
                           specified duration (in second), by default 1h,
                           ``None`` for the token to be valid as long as the
                           current user's session is.
        :type time_limit: int | None
        :returns: ASCII token string
        """
        token = self.session.sid
        max_ts = '' if not time_limit else int(time.time() + time_limit)
        msg = '%s%s' % (token, max_ts)
        secret = self.env['ir.config_parameter'].sudo().get_param('database.secret')
        assert secret, "CSRF protection requires a configured database secret"
        hm = hmac.new(secret.encode('ascii'), msg.encode('utf-8'), hashlib.sha1).hexdigest()
        return '%so%s' % (hm, max_ts)

    def validate_csrf(self, csrf):
        if not csrf:
            return False

        try:
            hm, _, max_ts = str(csrf).rpartition('o')
        except UnicodeEncodeError:
            return False

        if max_ts:
            try:
                if int(max_ts) < int(time.time()):
                    return False
            except ValueError:
                return False

        token = self.session.sid

        msg = '%s%s' % (token, max_ts)
        secret = self.env['ir.config_parameter'].sudo().get_param('database.secret')
        assert secret, "CSRF protection requires a configured database secret"
        hm_expected = hmac.new(secret.encode('ascii'), msg.encode('utf-8'), hashlib.sha1).hexdigest()
        return consteq(hm, hm_expected)

    def handle_http(self):
        """ Handle ``http`` request type.

        Matched routing arguments, query string and form parameters (including
        files) are passed to the handler method as keyword arguments. In case
        of name conflict, routing parameters have priority.

        The handler method's result can be:

        * a falsy value, in which case the HTTP response will be an `HTTP 204`_ (No Content)
        * a werkzeug Response object, which is returned as-is
        * a ``str`` or ``unicode``, will be wrapped in a Response object and returned as HTML
        """

        # TODO why not use .values ?
        params = collections.OrderedDict(self.httprequest.args)
        params.update(self.httprequest.form)
        params.update(self.httprequest.files)

        params.pop('session_id', None)
        self.params = params

        # Reply to CORS requests
        if request.httprequest.method == 'OPTIONS' and request.endpoint and request.endpoint.routing.get('cors'):
            headers = {
                'Access-Control-Max-Age': 60 * 60 * 24,
                'Access-Control-Allow-Headers': 'Origin, X-Requested-With, Content-Type, Accept'
            }
            return Response(status=200, headers=headers)

        # Check for CSRF token for relevent requests
        if request.httprequest.method not in ('GET', 'HEAD', 'OPTIONS', 'TRACE') and request.endpoint.routing.get('csrf', True):
            token = self.params.pop('csrf_token', None)
            if not self.validate_csrf(token):
                if token is not None:
                    _logger.warning("CSRF validation failed on path '%s'", request.httprequest.path)
                else:
                    _logger.warning("""No CSRF token provided for path '%s' https://www.odoo.com/documentation/13.0/reference/http.html#csrf for more details.""", request.httprequest.path)
                raise werkzeug.exceptions.BadRequest('Session expired (invalid CSRF token)')

        # Handle normal requests
        r = self._call_function(**self.params)
        if not r:
            r = Response(status=204)  # no content
        return r

    #------------------------------------------------------
    # JSON-RPC2
    #------------------------------------------------------
    def _json_response(self, result=None, error=None):
        response = { 'jsonrpc': '2.0', 'id': self.request_id }
        if error is not None:
            response['error'] = error
        if result is not None:
            response['result'] = result

        body = json.dumps(response, default=date_utils.json_default)

        return Response(
            body, status=error and error.pop('http_status', 200) or 200,
            headers=[('Content-Type', 'application/json'), ('Content-Length', len(body))]
        )

    def handle_json(self):
        """ Parser handler for `JSON-RPC 2 <http://www.jsonrpc.org/specification>`_ over HTTP

        * ``method`` is ignored
        * ``params`` must be a JSON object (not an array) and is passed as keyword arguments to the handler method
        * the handler method's result is returned as JSON-RPC ``result`` and wrapped in the `JSON-RPC Response <http://www.jsonrpc.org/specification#response_object>`_

        Sucessful request::

          --> {"jsonrpc": "2.0", "method": "call", "params": {"context": {}, "arg1": "val1" }, "id": null}

          <-- {"jsonrpc": "2.0", "result": { "res1": "val1" }, "id": null}

        Request producing a error::

          --> {"jsonrpc": "2.0", "method": "call", "params": {"context": {}, "arg1": "val1" }, "id": null}

          <-- {"jsonrpc": "2.0", "error": {"code": 1, "message": "End user error message.", "data": {"code": "codestring", "debug": "traceback" } }, "id": null}

        """
        # Fake JSON-RPC2 where id and params are www-form encoded instead of plain JSON
        # TODO decide yes or not ? because it is a CSRF security issue
        if self.httprequest.content_type == "application/x-www-form-urlencoded":
            self.request_id = self.httprequest.values.get('id')
            try:
                www_form_params = self.httprequest.values.get('params')
                params = json.loads(www_form_params)
            except ValueError:
                _logger.info('%s: JSON-RPC www-form error parsing params: %r', self.httprequest.path, www_form_params)
                raise werkzeug.exceptions.BadRequest()

        # Regular JSON-RPC2
        else:
            json_request = self.httprequest.get_data().decode(self.httprequest.charset)
            try:
                self.jsonrequest = json.loads(json_request)
            except ValueError:
                _logger.info('%s: Invalid JSON data: %r', self.httprequest.path, json_request)
                raise werkzeug.exceptions.BadRequest()
            self.request_id = self.jsonrequest.get("id")
            params = dict(self.jsonrequest.get("params", {}))

        self.params = params
        self.context = self.params.pop('context', dict(self.session.context))

        # Call the endpoint
        t0 = self.rpc_debug_pre(self.params)
        result = self._call_function(**self.params)
        self.rpc_debug_post(t0, result)

        return self._json_response(result)

    #------------------------------------------------------
    # Entry point
    #------------------------------------------------------
    def dispatch(self, endpoint, args, auth='none'):
        self.endpoint = endpoint
        self.endpoint_arguments = args
        self.auth_method = auth

        # Plain HTTP endpoint
        if self.endpoint.routing_type == 'http':
            return self.handle_http()

        # JSON-RPC2 endpoint
        elif self.endpoint.routing_type == 'json':
            return self.handle_json()

#----------------------------------------------------------
# Controller and routes
#----------------------------------------------------------
addons_manifest = {}
controllers_per_module = collections.defaultdict(list)

def route(route=None, **kw):
    """Decorator marking the decorated method as being a handler for
    requests. The method must be part of a subclass of ``Controller``.

    :param route: string or array. The route part that will determine which
                  http requests will match the decorated method. Can be a
                  single string or an array of strings. See werkzeug's routing
                  documentation for the format of route expression (
                  http://werkzeug.pocoo.org/docs/routing/ ).
    :param type: The type of request, can be ``'http'`` or ``'json'``.
    :param auth: The type of authentication method, can on of the following:

                 * ``user``: The user must be authenticated and the current request
                   will perform using the rights of the user.
                 * ``public``: The user may or may not be authenticated. If she isn't,
                   the current request will perform using the shared Public user.
                 * ``none``: The method is always active, even if there is no
                   database. Mainly used by the framework and authentication
                   modules. There request code will not have any facilities to access
                   the database nor have any configuration indicating the current
                   database nor the current user.
    :param methods: A sequence of http methods this route applies to. If not
                    specified, all methods are allowed.
    :param cors: The Access-Control-Allow-Origin cors directive value.
    :param bool csrf: Whether CSRF protection should be enabled for the route.
                      Defaults to ``True``. See :ref:`CSRF Protection
                      <csrf>` for more.

    .. _csrf:

    .. admonition:: CSRF Protection
        :class: alert-warning

        .. versionadded:: 9.0

        Odoo implements token-based `CSRF protection
        <https://en.wikipedia.org/wiki/CSRF>`_.

        CSRF protection is enabled by default and applies to *UNSAFE*
        HTTP methods as defined by :rfc:`7231` (all methods other than
        ``GET``, ``HEAD``, ``TRACE`` and ``OPTIONS``).

        CSRF protection is implemented by checking requests using
        unsafe methods for a value called ``csrf_token`` as part of
        the request's form data. That value is removed from the form
        as part of the validation and does not have to be taken in
        account by your own form processing.

        When adding a new controller for an unsafe method (mostly POST
        for e.g. forms):

        * if the form is generated in Python, a csrf token is
          available via :meth:`request.csrf_token()
          <odoo.http.WebRequest.csrf_token`, the
          :data:`~odoo.http.request` object is available by default
          in QWeb (python) templates, it may have to be added
          explicitly if you are not using QWeb.

        * if the form is generated in Javascript, the CSRF token is
          added by default to the QWeb (js) rendering context as
          ``csrf_token`` and is otherwise available as ``csrf_token``
          on the ``web.core`` module:

          .. code-block:: javascript

              require('web.core').csrf_token

        * if the endpoint can be called by external parties (not from
          Odoo) as e.g. it is a REST API or a `webhook
          <https://en.wikipedia.org/wiki/Webhook>`_, CSRF protection
          must be disabled on the endpoint. If possible, you may want
          to implement other methods of request validation (to ensure
          it is not called by an unrelated third-party).

    """
    routing = kw.copy()
    assert 'type' not in routing or routing['type'] in ("http", "json")
    def decorator(f):
        if route:
            if isinstance(route, list):
                routes = route
            else:
                routes = [route]
            routing['routes'] = routes

        @functools.wraps(f)
        def response_wrap(*args, **kw):
            # if controller cannot be called with extra args (utm, debug, ...), call endpoint ignoring them
            params = inspect.signature(f).parameters.values()
            is_kwargs = lambda p: p.kind == inspect.Parameter.VAR_KEYWORD
            if not any(is_kwargs(p) for p in params):  # missing **kw
                is_keyword_compatible = lambda p: p.kind in (
                    inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    inspect.Parameter.KEYWORD_ONLY)
                fargs = {p.name for p in params if is_keyword_compatible(p)}
                ignored = ['<%s=%s>' % (k, kw.pop(k)) for k in list(kw) if k not in fargs]
                if ignored:
                    _logger.info("<function %s.%s> called ignoring args %s" % (f.__module__, f.__name__, ', '.join(ignored)))

            response = f(*args, **kw)
            if isinstance(response, Response) or f.routing_type == 'json':
                return response

            if isinstance(response, (bytes, str)):
                return Response(response)

            if isinstance(response, werkzeug.exceptions.HTTPException):
                response = response.get_response(request.httprequest.environ)
            if isinstance(response, werkzeug.wrappers.BaseResponse):
                response = Response.force_type(response)
                response.set_default()
                return response

            _logger.warning("<function %s.%s> returns an invalid response type for an http request" % (f.__module__, f.__name__))
            return response
        response_wrap.routing = routing
        response_wrap.original_func = f
        return response_wrap
    return decorator

class ControllerType(type):
    def __init__(cls, name, bases, attrs):
        super(ControllerType, cls).__init__(name, bases, attrs)

        # flag old-style methods with req as first argument
        for k, v in attrs.items():
            if inspect.isfunction(v) and hasattr(v, 'original_func'):
                # Set routing type on original functions
                routing_type = v.routing.get('type')
                parent = [claz for claz in bases if isinstance(claz, ControllerType) and hasattr(claz, k)]
                parent_routing_type = getattr(parent[0], k).original_func.routing_type if parent else routing_type or 'http'
                if routing_type is not None and routing_type is not parent_routing_type:
                    routing_type = parent_routing_type
                    _logger.warning("Subclass re-defines <function %s.%s.%s> with different type than original."
                                    " Will use original type: %r" % (cls.__module__, cls.__name__, k, parent_routing_type))
                v.original_func.routing_type = routing_type or parent_routing_type

                sign = inspect.signature(v.original_func)
                first_arg = list(sign.parameters)[1] if len(sign.parameters) >= 2 else None
                if first_arg in ["req", "request"]:
                    v._first_arg_is_req = True

        # store the controller in the controllers list
        name_class = ("%s.%s" % (cls.__module__, cls.__name__), cls)
        class_path = name_class[0].split(".")
        if not class_path[:2] == ["odoo", "addons"]:
            module = ""
        else:
            # we want to know all modules that have controllers
            module = class_path[2]
        # but we only store controllers directly inheriting from Controller
        if not "Controller" in globals() or not Controller in bases:
            return
        controllers_per_module[module].append(name_class)

Controller = ControllerType('Controller', (object,), {})

class EndPoint(object):
    def __init__(self, method, routing):
        self.method = method
        self.original = getattr(method, 'original_func', method)
        self.routing = routing
        self.arguments = {}

    @property
    def first_arg_is_req(self):
        # Backward for 7.0
        return getattr(self.method, '_first_arg_is_req', False)

    def __call__(self, *args, **kw):
        return self.method(*args, **kw)

def _generate_routing_rules(modules, nodb_only, converters=None):
    def get_subclasses(klass):
        def valid(c):
            return c.__module__.startswith('odoo.addons.') and c.__module__.split(".")[2] in modules
        subclasses = klass.__subclasses__()
        result = []
        for subclass in subclasses:
            if valid(subclass):
                result.extend(get_subclasses(subclass))
        if not result and valid(klass):
            result = [klass]
        return result

    for module in modules:
        if module not in controllers_per_module:
            continue

        for _, cls in controllers_per_module[module]:
            subclasses = list(unique(c for c in get_subclasses(cls) if c is not cls))
            if subclasses:
                name = "%s (extended by %s)" % (cls.__name__, ', '.join(sub.__name__ for sub in subclasses))
                cls = type(name, tuple(reversed(subclasses)), {})

            o = cls()
            members = inspect.getmembers(o, inspect.ismethod)
            for _, mv in members:
                if hasattr(mv, 'routing'):
                    routing = dict(type='http', auth='user', methods=None, routes=None)
                    methods_done = list()
                    # update routing attributes from subclasses(auth, methods...)
                    for claz in reversed(mv.__self__.__class__.mro()):
                        fn = getattr(claz, mv.__name__, None)
                        if fn and hasattr(fn, 'routing') and fn not in methods_done:
                            methods_done.append(fn)
                            routing.update(fn.routing)
                    if not nodb_only or routing['auth'] == "none":
                        assert routing['routes'], "Method %r has not route defined" % mv
                        endpoint = EndPoint(mv, routing)
                        for url in routing['routes']:
                            yield (url, endpoint, routing)

#----------------------------------------------------------
# HTTP Sessions
#----------------------------------------------------------
class AuthenticationError(Exception):
    pass

class SessionExpiredException(Exception):
    pass

class OpenERPSession(werkzeug.contrib.sessions.Session):
    def __init__(self, *args, **kwargs):
        self.inited = False
        self.modified = False
        self.rotate = False
        super(OpenERPSession, self).__init__(*args, **kwargs)
        self.inited = True
        self._default_values()
        self.modified = False

    def __getattr__(self, attr):
        return self.get(attr, None)
    def __setattr__(self, k, v):
        if getattr(self, "inited", False):
            try:
                object.__getattribute__(self, k)
            except:
                return self.__setitem__(k, v)
        object.__setattr__(self, k, v)

    def authenticate(self, db, login=None, password=None, uid=None):
        """
        Authenticate the current user with the given db, login and
        password. If successful, store the authentication parameters in the
        current session and request.

        :param uid: If not None, that user id will be used instead the login
                    to authenticate the user.
        """

        if uid is None:
            wsgienv = request.httprequest.environ
            env = dict(
                base_location=request.httprequest.url_root.rstrip('/'),
                HTTP_HOST=wsgienv['HTTP_HOST'],
                REMOTE_ADDR=wsgienv['REMOTE_ADDR'],
            )
            uid = odoo.registry(db)['res.users'].authenticate(db, login, password, env)
        else:
            security.check(db, uid, password)
        self.rotate = True
        self.db = db
        self.uid = uid
        self.login = login
        self.session_token = uid and security.compute_session_token(self, request.env)
        request.uid = uid
        request.disable_db = False

        if uid: self.get_context()
        return uid

    def check_security(self):
        """
        Check the current authentication parameters to know if those are still
        valid. This method should be called at each request. If the
        authentication fails, a :exc:`SessionExpiredException` is raised.
        """
        if not self.db or not self.uid:
            raise SessionExpiredException("Session expired")
        # We create our own environment instead of the request's one.
        # to avoid creating it without the uid since request.uid isn't set yet
        env = odoo.api.Environment(request.cr, self.uid, self.context)
        # here we check if the session is still valid
        if not security.check_session(self, env):
            raise SessionExpiredException("Session expired")

    def logout(self, keep_db=False):
        for k in list(self):
            if not (keep_db and k == 'db') and k != 'debug':
                del self[k]
        self._default_values()
        self.rotate = True

    def _default_values(self):
        self.setdefault("db", None)
        self.setdefault("uid", None)
        self.setdefault("login", None)
        self.setdefault("session_token", None)
        self.setdefault("context", {})
        self.setdefault("debug", '')

    def get_context(self):
        """
        Re-initializes the current user's session context (based on his
        preferences) by calling res.users.get_context() with the old context.

        :returns: the new context
        """
        assert self.uid, "The user needs to be logged-in to initialize his context"
        self.context = dict(request.env['res.users'].context_get() or {})
        self.context['uid'] = self.uid
        self._fix_lang(self.context)
        return self.context

    def _fix_lang(self, context):
        """ OpenERP provides languages which may not make sense and/or may not
        be understood by the web client's libraries.

        Fix those here.

        :param dict context: context to fix
        """
        lang = context.get('lang')

        # inane OpenERP locale
        if lang == 'ar_AR':
            lang = 'ar'

        # lang to lang_REGION (datejs only handles lang_REGION, no bare langs)
        if lang in babel.core.LOCALE_ALIASES:
            lang = babel.core.LOCALE_ALIASES[lang]

        context['lang'] = lang or 'en_US'

    def save_action(self, action):
        """
        This method store an action object in the session and returns an integer
        identifying that action. The method get_action() can be used to get
        back the action.

        :param the_action: The action to save in the session.
        :type the_action: anything
        :return: A key identifying the saved action.
        :rtype: integer
        """
        saved_actions = self.setdefault('saved_actions', {"next": 1, "actions": {}})
        # we don't allow more than 10 stored actions
        if len(saved_actions["actions"]) >= 10:
            del saved_actions["actions"][min(saved_actions["actions"])]
        key = saved_actions["next"]
        saved_actions["actions"][key] = action
        saved_actions["next"] = key + 1
        self.modified = True
        return key

    def get_action(self, key):
        """
        Gets back a previously saved action. This method can return None if the action
        was saved since too much time (this case should be handled in a smart way).

        :param key: The key given by save_action()
        :type key: integer
        :return: The saved action or None.
        :rtype: anything
        """
        saved_actions = self.get('saved_actions', {})
        return saved_actions.get("actions", {}).get(key)

def session_gc(session_store):
    if random.random() < 0.001:
        # we keep session one week
        last_week = time.time() - 60*60*24*7
        for fname in os.listdir(session_store.path):
            path = os.path.join(session_store.path, fname)
            try:
                if os.path.getmtime(path) < last_week:
                    os.unlink(path)
            except OSError:
                pass

#----------------------------------------------------------
# WSGI Layer
#----------------------------------------------------------
# Add potentially missing (older ubuntu) font mime types
mimetypes.add_type('application/font-woff', '.woff')
mimetypes.add_type('application/vnd.ms-fontobject', '.eot')
mimetypes.add_type('application/x-font-ttf', '.ttf')
# Add potentially missing (detected on windows) svg mime types
mimetypes.add_type('image/svg+xml', '.svg')

class DisableCacheMiddleware(object):
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        def start_wrapped(status, headers):
            req = werkzeug.wrappers.Request(environ)
            root.setup_session(req)
            if req.session and req.session.debug and not 'wkhtmltopdf' in req.headers.get('User-Agent'):
                new_headers = [('Cache-Control', 'no-cache')]

                for k, v in headers:
                    if k.lower() != 'cache-control':
                        new_headers.append((k, v))

                start_response(status, new_headers)
            else:
                start_response(status, headers)
        return self.app(environ, start_wrapped)

class Root(object):
    """Root WSGI application for Odoo.  """
    def __init__(self):
        self._loaded = False

    @lazy_property
    def session_store(self):
        # Setup http sessions
        path = odoo.tools.config.session_dir
        _logger.debug('HTTP sessions stored in: %s', path)
        return werkzeug.contrib.sessions.FilesystemSessionStore(
            path, session_class=OpenERPSession, renew_missing=True)

    @lazy_property
    def nodb_routing_map(self):
        _logger.info("Generating nondb routing")
        routing_map = werkzeug.routing.Map(strict_slashes=False, converters=None)
        for url, endpoint, routing in odoo.http._generate_routing_rules([''] + odoo.conf.server_wide_modules, True):
            routing_map.add(werkzeug.routing.Rule(url, endpoint=endpoint, methods=routing['methods']))
        return routing_map

    def load_addons(self):
        """ Load all addons from addons path containing static files and
        controllers and configure them.  """
        # TODO should we move this to ir.http so that only configured modules are served ?
        statics = {}
        for addons_path in odoo.addons.__path__:
            for module in sorted(os.listdir(str(addons_path))):
                if module not in addons_manifest:
                    mod_path = os.path.join(addons_path, module)
                    manifest_path = module_manifest(mod_path)
                    path_static = os.path.join(addons_path, module, 'static')
                    if manifest_path and os.path.isdir(path_static):
                        with open(manifest_path, 'rb') as fd:
                            manifest_data = fd.read()
                        manifest = ast.literal_eval(pycompat.to_text(manifest_data))
                        if not manifest.get('installable', True):
                            continue
                        manifest['addons_path'] = addons_path
                        _logger.debug("Loading %s", module)
                        addons_manifest[module] = manifest
                        statics['/%s/static' % module] = path_static

        if statics:
            _logger.info("HTTP Configuring static files")
        app = werkzeug.wsgi.SharedDataMiddleware(self.dispatch, statics, cache_timeout=STATIC_CACHE)
        self.dispatch = DisableCacheMiddleware(app)

    def setup_session(self, httprequest):
        # recover or create session
        session_gc(self.session_store)

        sid = httprequest.args.get('session_id')
        explicit_session = True
        if not sid:
            sid =  httprequest.headers.get("X-Openerp-Session-Id")
        if not sid:
            sid = httprequest.cookies.get('session_id')
            explicit_session = False
        if sid is None:
            httprequest.session = self.session_store.new()
        else:
            httprequest.session = self.session_store.get(sid)
        return explicit_session

    def setup_db(self, httprequest):
        db = httprequest.session.db
        # Check if session.db is legit
        if db:
            if db not in db_filter([db], httprequest=httprequest):
                _logger.warning("Logged into database '%s', but dbfilter "
                             "rejects it; logging session out.", db)
                httprequest.session.logout()
                db = None

        if not db:
            httprequest.session.db = db_monodb(httprequest)

    def setup_lang(self, httprequest):
        if "lang" not in httprequest.session.context:
            alang = httprequest.accept_languages.best or "en-US"
            try:
                code, territory, _, _ = babel.core.parse_locale(alang, sep='-')
                if territory:
                    lang = '%s_%s' % (code, territory)
                else:
                    lang = babel.core.LOCALE_ALIASES[code]
            except (ValueError, KeyError):
                lang = 'en_US'
            httprequest.session.context["lang"] = lang

    def get_response(self, httprequest, result, explicit_session):
        if isinstance(result, Response) and result.is_qweb:
            try:
                result.flatten()
            except Exception as e:
                if request.db:
                    result = request.registry['ir.http']._handle_exception(e)
                else:
                    raise

        if isinstance(result, (bytes, str)):
            response = Response(result, mimetype='text/html')
        else:
            response = result

        save_session = (not request.endpoint) or request.endpoint.routing.get('save_session', True)
        if not save_session:
            return response

        if httprequest.session.should_save:
            if httprequest.session.rotate:
                self.session_store.delete(httprequest.session)
                httprequest.session.sid = self.session_store.generate_key()
                if httprequest.session.uid:
                    httprequest.session.session_token = security.compute_session_token(httprequest.session, request.env)
                httprequest.session.modified = True
            self.session_store.save(httprequest.session)
        # We must not set the cookie if the session id was specified using a http header or a GET parameter.
        # There are two reasons to this:
        # - When using one of those two means we consider that we are overriding the cookie, which means creating a new
        #   session on top of an already existing session and we don't want to create a mess with the 'normal' session
        #   (the one using the cookie). That is a special feature of the Session Javascript class.
        # - It could allow session fixation attacks.
        if not explicit_session and hasattr(response, 'set_cookie'):
            response.set_cookie(
                'session_id', httprequest.session.sid, max_age=90 * 24 * 60 * 60, httponly=True)

        return response

    def get_db_router(self, db):
        if not db:
            return self.nodb_routing_map
        return request.registry['ir.http'].routing_map()

    def dispatch_nodb(self, request):
        try:
            func, arguments = self.nodb_routing_map.bind_to_environ(request.httprequest.environ).match()
        except werkzeug.exceptions.HTTPException as e:
            return request._handle_exception(e)
        request.set_handler(func, arguments, "none")
        result = request.dispatch()
                return result

    def dispatch(self, environ, start_response):
        """
        Performs the actual WSGI dispatching for the application.
        """
        try:
            httprequest = werkzeug.wrappers.Request(environ)
            httprequest.app = self
            httprequest.parameter_storage_class = werkzeug.datastructures.ImmutableOrderedMultiDict

            current_thread = threading.current_thread()
            current_thread.url = httprequest.url
            current_thread.query_count = 0
            current_thread.query_time = 0
            current_thread.perf_t0 = time.time()

            explicit_session = self.setup_session(httprequest)
            self.setup_db(httprequest)
            self.setup_lang(httprequest)

            request = WebRequest(httprequest)

            with request:
                db = request.session.db
                if db:
                    try:
                        odoo.registry(db).check_signaling()
                        with odoo.tools.mute_logger('odoo.sql_db'):
                            ir_http = request.registry['ir.http']
                    except (AttributeError, psycopg2.OperationalError, psycopg2.ProgrammingError):
                        # psycopg2 error or attribute error while constructing
                        # the registry. That means either
                        # - the database probably does not exists anymore
                        # - the database is corrupted
                        # - the database version doesnt match the server version
                        # Log the user out and fall back to nodb
                        request.session.logout()
                        # If requesting /web this will loop
                        if request.httprequest.path == '/web':
                            result = werkzeug.utils.redirect('/web/database/selector')
                        else:
                            result = self.dispatch_nodb(request)
                    else:
                        result = ir_http._dispatch()
                else:
                    result = self.dispatch_nodb(request)

                response = self.get_response(httprequest, result, explicit_session)
            return response(environ, start_response)

        except werkzeug.exceptions.HTTPException as e:
            return e(environ, start_response)

    def __call__(self, environ, start_response):
        """ WSGI entry point."""
        # cleanup db/uid trackers - they're set in WebRequest or in
        # for servie rpc in odoo.service.*.dispatch().
        # /!\ The cleanup cannot be done at the end of this `application`
        # method because werkzeug still produces relevant logging afterwards
        if hasattr(threading.current_thread(), 'uid'):
            del threading.current_thread().uid
        if hasattr(threading.current_thread(), 'dbname'):
            del threading.current_thread().dbname
        if hasattr(threading.current_thread(), 'url'):
            del threading.current_thread().url

        # Lazy load addons
        if not self._loaded:
            self._loaded = True
            self.load_addons()

        with odoo.api.Environment.manage():
            result = self.dispatch(environ, start_response)
            if result is not None:
                return result

        # We never returned from the loop.
        return werkzeug.exceptions.NotFound("No handler found.\n")(environ, start_response)

#  main wsgi handler
root = Root()

def db_list(force=False, httprequest=None):
    dbs = odoo.service.db.list_dbs(force)
    return db_filter(dbs, httprequest=httprequest)

def db_filter(dbs, httprequest=None):
    httprequest = httprequest or request.httprequest
    h = httprequest.environ.get('HTTP_HOST', '').split(':')[0]
    d, _, r = h.partition('.')
    if d == "www" and r:
        d = r.partition('.')[0]
    if odoo.tools.config['dbfilter']:
        d, h = re.escape(d), re.escape(h)
        r = odoo.tools.config['dbfilter'].replace('%h', h).replace('%d', d)
        dbs = [i for i in dbs if re.match(r, i)]
    elif odoo.tools.config['db_name']:
        # In case --db-filter is not provided and --database is passed, Odoo will
        # use the value of --database as a comma seperated list of exposed databases.
        exposed_dbs = set(db.strip() for db in odoo.tools.config['db_name'].split(','))
        dbs = sorted(exposed_dbs.intersection(dbs))
    return dbs

def db_monodb(httprequest=None):
    """
        Magic function to find the current database.

        Implementation details:

        * Magic
        * More magic

        Returns ``None`` if the magic is not magic enough.
    """
    httprequest = httprequest or request.httprequest

    dbs = db_list(True, httprequest)

    # try the db already in the session
    db_session = httprequest.session.db
    if db_session in dbs:
        return db_session

    # if there is only one possible db, we take that one
    if len(dbs) == 1:
        return dbs[0]
    return None

def send_file(filepath_or_fp, mimetype=None, as_attachment=False, filename=None, mtime=None,
              add_etags=True, cache_timeout=STATIC_CACHE, conditional=True):
    """This is a modified version of Flask's send_file()

    Sends the contents of a file to the client. This will use the
    most efficient method available and configured.  By default it will
    try to use the WSGI server's file_wrapper support.

    By default it will try to guess the mimetype for you, but you can
    also explicitly provide one.  For extra security you probably want
    to send certain files as attachment (HTML for instance).  The mimetype
    guessing requires a `filename` or an `attachment_filename` to be
    provided.

    Please never pass filenames to this function from user sources without
    checking them first.

    :param filepath_or_fp: the filename of the file to send.
                           Alternatively a file object might be provided
                           in which case `X-Sendfile` might not work and
                           fall back to the traditional method.  Make sure
                           that the file pointer is positioned at the start
                           of data to send before calling :func:`send_file`.
    :param mimetype: the mimetype of the file if provided, otherwise
                     auto detection happens.
    :param as_attachment: set to `True` if you want to send this file with
                          a ``Content-Disposition: attachment`` header.
    :param filename: the filename for the attachment if it differs from the file's filename or
                     if using file object without 'name' attribute (eg: E-tags with StringIO).
    :param mtime: last modification time to use for contitional response.
    :param add_etags: set to `False` to disable attaching of etags.
    :param conditional: set to `False` to disable conditional responses.

    :param cache_timeout: the timeout in seconds for the headers.
    """
    if isinstance(filepath_or_fp, str):
        if not filename:
            filename = os.path.basename(filepath_or_fp)
        file = open(filepath_or_fp, 'rb')
        if not mtime:
            mtime = os.path.getmtime(filepath_or_fp)
    else:
        file = filepath_or_fp
        if not filename:
            filename = getattr(file, 'name', None)

    file.seek(0, 2)
    size = file.tell()
    file.seek(0)

    if mimetype is None and filename:
        mimetype = mimetypes.guess_type(filename)[0]
    if mimetype is None:
        mimetype = 'application/octet-stream'

    headers = werkzeug.datastructures.Headers()
    if as_attachment:
        if filename is None:
            raise TypeError('filename unavailable, required for sending as attachment')
        headers.add('Content-Disposition', 'attachment', filename=filename)
        headers['Content-Length'] = size

    data = werkzeug.wsgi.wrap_file(request.httprequest.environ, file)
    rv = Response(data, mimetype=mimetype, headers=headers,
                                    direct_passthrough=True)

    if isinstance(mtime, str):
        try:
            server_format = odoo.tools.misc.DEFAULT_SERVER_DATETIME_FORMAT
            mtime = datetime.datetime.strptime(mtime.split('.')[0], server_format)
        except Exception:
            mtime = None
    if mtime is not None:
        rv.last_modified = mtime

    rv.cache_control.public = True
    if cache_timeout:
        rv.cache_control.max_age = cache_timeout
        rv.expires = int(time.time() + cache_timeout)

    if add_etags and filename and mtime:
        rv.set_etag('odoo-%s-%s-%s' % (
            mtime,
            size,
            zlib.adler32(
                filename.encode('utf-8') if isinstance(filename, str)
                else filename
            ) & 0xffffffff
        ))
        if conditional:
            rv = rv.make_conditional(request.httprequest)
            # make sure we don't send x-sendfile for servers that
            # ignore the 304 status code for x-sendfile.
            if rv.status_code == 304:
                rv.headers.pop('x-sendfile', None)
    return rv

def content_disposition(filename):
    filename = odoo.tools.ustr(filename)
    escaped = urls.url_quote(filename, safe='')

    return "attachment; filename*=UTF-8''%s" % escaped

def set_safe_image_headers(headers, content):
    """Return new headers based on `headers` but with `Content-Length` and
    `Content-Type` set appropriately depending on the given `content` only if it
    is safe to do."""
    content_type = guess_mimetype(content)
    safe_types = ['image/jpeg', 'image/png', 'image/gif', 'image/x-icon']
    if content_type in safe_types:
        headers = set_header_field(headers, 'Content-Type', content_type)
    set_header_field(headers, 'Content-Length', len(content))
    return headers

def set_header_field(headers, name, value):
    """ Return new headers based on `headers` but with `value` set for the
    header field `name`.

    :param headers: the existing headers
    :type headers: list of tuples (name, value)

    :param name: the header field name
    :type name: string

    :param value: the value to set for the `name` header
    :type value: string

    :return: the updated headers
    :rtype: list of tuples (name, value)
    """
    dictheaders = dict(headers)
    dictheaders[name] = value
    return list(dictheaders.items())

def application(environ, start_response):
    # FIXME: is checking for the presence of HTTP_X_FORWARDED_HOST really useful?
    #        we're ignoring the user configuration, and that means we won't
    #        support the standardised Forwarded header once werkzeug supports
    #        it
    if odoo.tools.config['proxy_mode'] and 'HTTP_X_FORWARDED_HOST' in environ:
        return ProxyFix(root)(environ, start_response)
    else:
        return root(environ, start_response)

#
