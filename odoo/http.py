# Part of Odoo. See LICENSE file for full copyright and licensing details.
r"""\
Odoo HTTP layer / WSGI application

The main duty of this module is to prepare and dispatch all http
requests to their corresponding controllers: from a raw http request
arriving on the WSGI entrypoint to a :class:`~http.Request`: arriving at
a module controller with a fully setup ORM available.

Application developers mostly know this module thanks to the
:class:`~odoo.http.Controller`: class and its companion the
:func:`~odoo.http.route`: method decorator. Together they are used to
register methods responsible of delivering web content to matching URLS.

Those two are only the tip of the iceberg, below is an ascii graph that
shows the various processing layers each request passes through before
ending at the @route decorated endpoint. Hopefully, this graph and the
attached function descriptions will help you understand this module.

Here be dragons:

    Application.__call__
        +-> Request._serve_static
        |
        +-> Request._serve_nodb
        |   -> App.nodb_routing_map.match
        |   -> Dispatcher.pre_dispatch
        |   -> Dispatcher.dispatch
        |      -> route_wrapper
        |         -> endpoint
        |   -> Dispatcher.post_dispatch
        |
        +-> Request._serve_db
            -> model.retrying
               -> Request._serve_ir_http
                  -> env['ir.http']._match
                  -> env['ir.http']._authenticate
                  -> env['ir.http']._pre_dispatch
                     -> Dispatcher.pre_dispatch
                  -> Dispatcher.dispatch
                     -> env['ir.http']._dispatch
                        -> route_wrapper
                           -> endpoint
                  -> env['ir.http']._post_dispatch
                     -> Dispatcher.post_dispatch

Application.__call__
  WSGI entry point, it sanitizes the request, it wraps it in a werkzeug
  request and itself in an Odoo http request. The Odoo http request is
  exposed at ``http.request`` then it is forwarded to either
  ``_serve_static``, ``_serve_nodb`` or ``_serve_db`` depending on the
  request path and the presence of a database. It is also responsible of
  ensuring any error is properly logged and encapsuled in a HTTP error
  response.

Request._serve_static
  Handle all requests to ``/<module>/static/<asset>`` paths, open the
  underlying file on the filesystem and stream it via
  :meth:``Request.send_file``

Request._serve_nodb
  Handle requests to ``@route(auth='none')`` endpoints when the user is
  not connected to a database. It performs limited operations, just
  matching the auth='none' endpoint using the request path and then it
  delegates to Dispatcher.

Request._serve_db
  Handle all requests that are not static when it is possible to connect
  to a database. It opens a session and initializes the ORM before
  forwarding the request to ``retrying`` and ``_serve_ir_http``.

service.model.retrying
  Protect against SQL serialisation errors (when two different
  transactions write on the same record), when such an error occurs this
  function resets the session and the environment then re-dispatches the
  request.

Request._serve_ir_http
  Delegate most of the effort to the ``ir.http`` abstract model which
  itself calls RequestDispatch back. ``ir.http`` grants modularity in
  the http stack. The notable difference with nodb is that there is an
  authentication layer and a mechanism to serve pages that are not
  accessible through controllers.

ir.http._authenticate
  Ensure the user on the current environment fulfill the requirement of
  ``@route(auth=...)``. Using the ORM outside of abstract models is
  unsafe prior of calling this function.

ir.http._pre_dispatch/Dispatcher.pre_dispatch
  Prepare the system the handle the current request, often used to save
  some extra query-string parameters in the session (e.g. ?debug=1)

ir.http._dispatch/Dispatcher.dispatch
  Deserialize the HTTP request body into ``request.params`` according to
  @route(type=...), call the controller endpoint, serialize its return
  value into an HTTP Response object.

ir.http._post_dispatch/Dispatcher.post_dispatch
  Post process the response returned by the controller endpoint. Used to
  inject various headers such as Content-Security-Policy.

route_wrapper, closure of the http.route decorator
  Sanitize the request parameters, call the route endpoint and
  optionally coerce the endpoint result.

endpoint
  The @route(...) decorated controller method.
"""

import base64
import cgi
import collections
import collections.abc
import contextlib
import functools
import glob
import hashlib
import hmac
import inspect
import json
import logging
import mimetypes
import os
import re
import threading
import time
import traceback
import warnings
import zlib
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from io import BytesIO
from os.path import join as opj
from pathlib import Path
from urllib.parse import urlparse
from zlib import adler32

import babel.core

try:
    import geoip2.database
    import geoip2.models
    import geoip2.errors
except ImportError:
    geoip2 = None

try:
    import maxminddb
except ImportError:
    maxminddb = None

import psycopg2
import werkzeug.datastructures
import werkzeug.exceptions
import werkzeug.local
import werkzeug.routing
import werkzeug.security
import werkzeug.wrappers
import werkzeug.wsgi
from werkzeug.urls import URL, url_parse, url_encode, url_quote
from werkzeug.exceptions import (HTTPException, BadRequest, Forbidden,
                                 NotFound, InternalServerError)
try:
    from werkzeug.middleware.proxy_fix import ProxyFix as ProxyFix_
    ProxyFix = functools.partial(ProxyFix_, x_for=1, x_proto=1, x_host=1)
except ImportError:
    from werkzeug.contrib.fixers import ProxyFix

try:
    from werkzeug.utils import send_file as _send_file
except ImportError:
    from .tools._vendor.send_file import send_file as _send_file

import odoo
from .exceptions import UserError, AccessError, AccessDenied
from .modules.module import get_manifest
from .modules.registry import Registry
from .service import security, model as service_model
from .tools import (config, consteq, date_utils, file_path, parse_version,
                    profiler, submap, unique, ustr,)
from .tools.func import filter_kwargs, lazy_property
from .tools.mimetypes import guess_mimetype
from .tools.misc import pickle
from .tools._vendor import sessions
from .tools._vendor.useragents import UserAgent


_logger = logging.getLogger(__name__)


# =========================================================
# Lib fixes
# =========================================================

# Add potentially missing (older ubuntu) font mime types
mimetypes.add_type('application/font-woff', '.woff')
mimetypes.add_type('application/vnd.ms-fontobject', '.eot')
mimetypes.add_type('application/x-font-ttf', '.ttf')
mimetypes.add_type('image/webp', '.webp')
# Add potentially wrong (detected on windows) svg mime types
mimetypes.add_type('image/svg+xml', '.svg')
# this one can be present on windows with the value 'text/plain' which
# breaks loading js files from an addon's static folder
mimetypes.add_type('text/javascript', '.js')

# To remove when corrected in Babel
babel.core.LOCALE_ALIASES['nb'] = 'nb_NO'


# =========================================================
# Const
# =========================================================

# The validity duration of a preflight response, one day.
CORS_MAX_AGE = 60 * 60 * 24

# The HTTP methods that do not require a CSRF validation.
CSRF_FREE_METHODS = ('GET', 'HEAD', 'OPTIONS', 'TRACE')

# The default csrf token lifetime, a salt against BREACH, one year
CSRF_TOKEN_SALT = 60 * 60 * 24 * 365

# The default lang to use when the browser doesn't specify it
DEFAULT_LANG = 'en_US'

# The dictionary to initialise a new session with.
def get_default_session():
    return {
        'context': {},  # 'lang': request.default_lang()  # must be set at runtime
        'db': None,
        'debug': '',
        'login': None,
        'uid': None,
        'session_token': None,
    }

DEFAULT_MAX_CONTENT_LENGTH = 128 * 1024 * 1024  # 128MiB

# Two empty objects used when the geolocalization failed. They have the
# sames attributes as real countries/cities except that accessing them
# evaluates to None.
if geoip2:
    GEOIP_EMPTY_COUNTRY = geoip2.models.Country({})
    GEOIP_EMPTY_CITY = geoip2.models.City({})

# The request mimetypes that transport JSON in their body.
JSON_MIMETYPES = ('application/json', 'application/json-rpc')

MISSING_CSRF_WARNING = """\
No CSRF validation token provided for path %r

Odoo URLs are CSRF-protected by default (when accessed with unsafe
HTTP methods). See
https://www.odoo.com/documentation/17.0/developer/reference/addons/http.html#csrf
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

# The @route arguments to propagate from the decorated method to the
# routing rule.
ROUTING_KEYS = {
    'defaults', 'subdomain', 'build_only', 'strict_slashes', 'redirect_to',
    'alias', 'host', 'methods',
}

if parse_version(werkzeug.__version__) >= parse_version('2.0.2'):
    # Werkzeug 2.0.2 adds the websocket option. If a websocket request
    # (ws/wss) is trying to access an HTTP route, a WebsocketMismatch
    # exception is raised. On the other hand, Werkzeug 0.16 does not
    # support the websocket routing key. In order to bypass this issue,
    # let's add the websocket key only when appropriate.
    ROUTING_KEYS.add('websocket')

# The default duration of a user session cookie. Inactive sessions are reaped
# server-side as well with a threshold that can be set via an optional
# config parameter `sessions.max_inactivity_seconds` (default: SESSION_LIFETIME)
SESSION_LIFETIME = 60 * 60 * 24 * 7

# The cache duration for static content from the filesystem, one week.
STATIC_CACHE = 60 * 60 * 24 * 7

# The cache duration for content where the url uniquely identifies the
# content (usually using a hash), one year.
STATIC_CACHE_LONG = 60 * 60 * 24 * 365


# =========================================================
# Helpers
# =========================================================

class SessionExpiredException(Exception):
    pass

def content_disposition(filename):
    return "attachment; filename*=UTF-8''{}".format(
        url_quote(filename, safe='', unsafe='()<>@,;:"/[]?={}\\*\'%') # RFC6266
    )

def db_list(force=False, host=None):
    """
    Get the list of available databases.

    :param bool force: See :func:`~odoo.service.db.list_dbs`:
    :param host: The Host used to replace %h and %d in the dbfilters
        regexp. Taken from the current request when omitted.
    :returns: the list of available databases
    :rtype: List[str]
    """
    try:
        dbs = odoo.service.db.list_dbs(force)
    except psycopg2.OperationalError:
        return []
    return db_filter(dbs, host)

def db_filter(dbs, host=None):
    """
    Return the subset of ``dbs`` that match the dbfilter or the dbname
    server configuration. In case neither are configured, return ``dbs``
    as-is.

    :param Iterable[str] dbs: The list of database names to filter.
    :param host: The Host used to replace %h and %d in the dbfilters
        regexp. Taken from the current request when omitted.
    :returns: The original list filtered.
    :rtype: List[str]
    """

    if config['dbfilter']:
        #        host
        #     -----------
        # www.example.com:80
        #     -------
        #     domain
        if host is None:
            host = request.httprequest.environ.get('HTTP_HOST', '')
        host = host.partition(':')[0]
        if host.startswith('www.'):
            host = host[4:]
        domain = host.partition('.')[0]

        dbfilter_re = re.compile(
            config["dbfilter"].replace("%h", re.escape(host))
                              .replace("%d", re.escape(domain)))
        return [db for db in dbs if dbfilter_re.match(db)]

    if config['db_name']:
        # In case --db-filter is not provided and --database is passed, Odoo will
        # use the value of --database as a comma separated list of exposed databases.
        exposed_dbs = {db.strip() for db in config['db_name'].split(',')}
        return sorted(exposed_dbs.intersection(dbs))

    return list(dbs)


def dispatch_rpc(service_name, method, params):
    """
    Perform a RPC call.

    :param str service_name: either "common", "db" or "object".
    :param str method: the method name of the given service to execute
    :param Mapping params: the keyword arguments for method call
    :return: the return value of the called method
    :rtype: Any
    """
    rpc_dispatchers = {
        'common': odoo.service.common.dispatch,
        'db': odoo.service.db.dispatch,
        'object': odoo.service.model.dispatch,
    }

    with borrow_request():
        threading.current_thread().uid = None
        threading.current_thread().dbname = None

        dispatch = rpc_dispatchers[service_name]
        return dispatch(method, params)


def is_cors_preflight(request, endpoint):
    return request.httprequest.method == 'OPTIONS' and endpoint.routing.get('cors', False)


def serialize_exception(exception):
    name = type(exception).__name__
    module = type(exception).__module__

    return {
        'name': f'{module}.{name}' if module else name,
        'debug': traceback.format_exc(),
        'message': ustr(exception),
        'arguments': exception.args,
        'context': getattr(exception, 'context', {}),
    }


# =========================================================
# File Streaming
# =========================================================

def send_file(filepath_or_fp, mimetype=None, as_attachment=False, filename=None, mtime=None,
              add_etags=True, cache_timeout=STATIC_CACHE, conditional=True):
    warnings.warn('odoo.http.send_file is deprecated, please use odoo.http.Stream instead.', DeprecationWarning, stacklevel=2)
    return _send_file(
        filepath_or_fp,
        request.httprequest.environ,
        mimetype=mimetype,
        as_attachment=as_attachment,
        download_name=filename,
        last_modified=mtime,
        etag=add_etags,
        max_age=cache_timeout,
        response_class=Response,
        conditional=conditional
    )


class Stream:
    """
    Send the content of a file, an attachment or a binary field via HTTP

    This utility is safe, cache-aware and uses the best available
    streaming strategy. Works best with the --x-sendfile cli option.

    Create a Stream via one of the constructors: :meth:`~from_path`:,
    :meth:`~from_attachment`: or :meth:`~from_binary_field`:, generate
    the corresponding HTTP response object via :meth:`~get_response`:.

    Instantiating a Stream object manually without using one of the
    dedicated constructors is discouraged.
    """

    type: str = ''  # 'data' or 'path' or 'url'
    data = None
    path = None
    url = None

    mimetype = None
    as_attachment = False
    download_name = None
    conditional = True
    etag = True
    last_modified = None
    max_age = None
    immutable = False
    size = None

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    @classmethod
    def from_path(cls, path, filter_ext=('',)):
        """ Create a :class:`~Stream`: from an addon resource. """
        path = file_path(path, filter_ext)
        check = adler32(path.encode())
        stat = os.stat(path)
        return cls(
            type='path',
            path=path,
            download_name=os.path.basename(path),
            etag=f'{int(stat.st_mtime)}-{stat.st_size}-{check}',
            last_modified=stat.st_mtime,
            size=stat.st_size,
        )

    @classmethod
    def from_attachment(cls, attachment):
        """ Create a :class:`~Stream`: from an ir.attachment record. """
        attachment.ensure_one()

        self = cls(
            mimetype=attachment.mimetype,
            download_name=attachment.name,
            conditional=True,
            etag=attachment.checksum,
        )

        if attachment.store_fname:
            self.type = 'path'
            self.path = werkzeug.security.safe_join(
                os.path.abspath(config.filestore(request.db)),
                attachment.store_fname
            )
            stat = os.stat(self.path)
            self.last_modified = stat.st_mtime
            self.size = stat.st_size

        elif attachment.db_datas:
            self.type = 'data'
            self.data = attachment.raw
            self.last_modified = attachment.write_date
            self.size = len(self.data)

        elif attachment.url:
            # When the URL targets a file located in an addon, assume it
            # is a path to the resource. It saves an indirection and
            # stream the file right away.
            static_path = root.get_static_file(
                attachment.url,
                host=request.httprequest.environ.get('HTTP_HOST', '')
            )
            if static_path:
                self = cls.from_path(static_path)
            else:
                self.type = 'url'
                self.url = attachment.url

        else:
            self.type = 'data'
            self.data = b''
            self.size = 0

        return self

    @classmethod
    def from_binary_field(cls, record, field_name):
        """ Create a :class:`~Stream`: from a binary field. """
        data_b64 = record[field_name]
        data = base64.b64decode(data_b64) if data_b64 else b''
        return cls(
            type='data',
            data=data,
            etag=request.env['ir.attachment']._compute_checksum(data),
            last_modified=record.write_date if record._log_access else None,
            size=len(data),
        )

    def read(self):
        """ Get the stream content as bytes. """
        if self.type == 'url':
            raise ValueError("Cannot read an URL")

        if self.type == 'data':
            return self.data

        with open(self.path, 'rb') as file:
            return file.read()

    def get_response(self, as_attachment=None, immutable=None, **send_file_kwargs):
        """
        Create the corresponding :class:`~Response` for the current stream.

        :param bool as_attachment: Indicate to the browser that it
            should offer to save the file instead of displaying it.
        :param bool immutable: Add the ``immutable`` directive to the
            ``Cache-Control`` response header, allowing intermediary
            proxies to aggressively cache the response. This option
            also set the ``max-age`` directive to 1 year.
        :param send_file_kwargs: Other keyword arguments to send to
            :func:`odoo.tools._vendor.send_file.send_file` instead of
            the stream sensitive values. Discouraged.
        """
        assert self.type in ('url', 'data', 'path'), "Invalid type: {self.type!r}, should be 'url', 'data' or 'path'."
        assert getattr(self, self.type) is not None, "There is nothing to stream, missing {self.type!r} attribute."

        if self.type == 'url':
            return request.redirect(self.url, code=301, local=False)

        if as_attachment is None:
            as_attachment = self.as_attachment
        if immutable is None:
            immutable = self.immutable

        send_file_kwargs = {
            'mimetype': self.mimetype,
            'as_attachment': as_attachment,
            'download_name': self.download_name,
            'conditional': self.conditional,
            'etag': self.etag,
            'last_modified': self.last_modified,
            'max_age': STATIC_CACHE_LONG if immutable else self.max_age,
            'environ': request.httprequest.environ,
            'response_class': Response,
            **send_file_kwargs,
        }

        if self.type == 'data':
            return _send_file(BytesIO(self.data), **send_file_kwargs)

        # self.type == 'path'
        send_file_kwargs['use_x_sendfile'] = False
        if config['x_sendfile']:
            with contextlib.suppress(ValueError):  # outside of the filestore
                fspath = Path(self.path).relative_to(opj(config['data_dir'], 'filestore'))
                x_accel_redirect = f'/web/filestore/{fspath}'
                send_file_kwargs['use_x_sendfile'] = True

        res = _send_file(self.path, **send_file_kwargs)

        if immutable and res.cache_control:
            res.cache_control["immutable"] = None  # None sets the directive

        if 'X-Sendfile' in res.headers:
            res.headers['X-Accel-Redirect'] = x_accel_redirect

            # In case of X-Sendfile/X-Accel-Redirect, the body is empty,
            # yet werkzeug gives the length of the file. This makes
            # NGINX wait for content that'll never arrive.
            res.headers['Content-Length'] = '0'

        return res


# =========================================================
# Controller and routes
# =========================================================

class Controller:
    """
    Class mixin that provide module controllers the ability to serve
    content over http and to be extended in child modules.

    Each class :ref:`inheriting <python:tut-inheritance>` from
    :class:`~odoo.http.Controller` can use the :func:`~odoo.http.route`:
    decorator to route matching incoming web requests to decorated
    methods.

    Like models, controllers can be extended by other modules. The
    extension mechanism is different because controllers can work in a
    database-free environment and therefore cannot use
    :class:~odoo.api.Registry:.

    To *override* a controller, :ref:`inherit <python:tut-inheritance>`
    from its class, override relevant methods and re-expose them with
    :func:`~odoo.http.route`:. Please note that the decorators of all
    methods are combined, if the overriding method’s decorator has no
    argument all previous ones will be kept, any provided argument will
    override previously defined ones.

    .. code-block:

        class GreetingController(odoo.http.Controller):
            @route('/greet', type='http', auth='public')
            def greeting(self):
                return 'Hello'

        class UserGreetingController(GreetingController):
            @route(auth='user')  # override auth, keep path and type
            def greeting(self):
                return super().handler()
    """
    children_classes = collections.defaultdict(list)  # indexed by module

    @classmethod
    def __init_subclass__(cls):
        super().__init_subclass__()
        if Controller in cls.__bases__:
            path = cls.__module__.split('.')
            module = path[2] if path[:2] == ['odoo', 'addons'] else ''
            Controller.children_classes[module].append(cls)


def route(route=None, **routing):
    """
    Decorate a controller method in order to route incoming requests
    matching the given URL and options to the decorated method.

    .. warning::
        It is mandatory to re-decorate any method that is overridden in
        controller extensions but the arguments can be omitted. See
        :class:`~odoo.http.Controller` for more details.

    :param Union[str, Iterable[str]] route: The paths that the decorated
        method is serving. Incoming HTTP request paths matching this
        route will be routed to this decorated method. See `werkzeug
        routing documentation <http://werkzeug.pocoo.org/docs/routing/>`_
        for the format of route expressions.
    :param str type: The type of request, either ``'json'`` or
        ``'http'``. It describes where to find the request parameters
        and how to serialize the response.
    :param str auth: The authentication method, one of the following:

        * ``'user'``: The user must be authenticated and the current
          request will be executed using the rights of the user.
        * ``'public'``: The user may or may not be authenticated. If he
          isn't, the current request will be executed using the shared
          Public user.
        * ``'none'``: The method is always active, even if there is no
          database. Mainly used by the framework and authentication
          modules. The request code will not have any facilities to
          access the current user.
    :param Iterable[str] methods: A list of http methods (verbs) this
        route applies to. If not specified, all methods are allowed.
    :param str cors: The Access-Control-Allow-Origin cors directive value.
    :param bool csrf: Whether CSRF protection should be enabled for the
        route. Enabled by default for ``'http'``-type requests, disabled
        by default for ``'json'``-type requests.
    :param Callable[[Exception], Response] handle_params_access_error:
        Implement a custom behavior if an error occurred when retrieving the record
        from the URL parameters (access error or missing error).
    """
    def decorator(endpoint):
        fname = f"<function {endpoint.__module__}.{endpoint.__name__}>"

        # Sanitize the routing
        assert routing.get('type', 'http') in _dispatchers.keys()
        if route:
            routing['routes'] = route if isinstance(route, list) else [route]
        wrong = routing.pop('method', None)
        if wrong is not None:
            _logger.warning("%s defined with invalid routing parameter 'method', assuming 'methods'", fname)
            routing['methods'] = wrong

        @functools.wraps(endpoint)
        def route_wrapper(self, *args, **params):
            params_ok = filter_kwargs(endpoint, params)
            params_ko = set(params) - set(params_ok)
            if params_ko:
                _logger.warning("%s called ignoring args %s", fname, params_ko)

            result = endpoint(self, *args, **params_ok)
            if routing['type'] == 'http':  # _generate_routing_rules() ensures type is set
                return Response.load(result)
            return result

        route_wrapper.original_routing = routing
        route_wrapper.original_endpoint = endpoint
        return route_wrapper
    return decorator

def _generate_routing_rules(modules, nodb_only, converters=None):
    """
    Two-fold algorithm used to (1) determine which method in the
    controller inheritance tree should bind to what URL with respect to
    the list of installed modules and (2) merge the various @route
    arguments of said method with the @route arguments of the method it
    overrides.
    """
    def is_valid(cls):
        """ Determine if the class is defined in an addon. """
        path = cls.__module__.split('.')
        return path[:2] == ['odoo', 'addons'] and path[2] in modules

    def get_leaf_classes(cls):
        """
        Find the classes that have no child and that have ``cls`` as
        ancestor.
        """
        result = []
        for subcls in cls.__subclasses__():
            if is_valid(subcls):
                result.extend(get_leaf_classes(subcls))
        if not result and is_valid(cls):
            result.append(cls)
        return result

    def build_controllers():
        """
        Create dummy controllers that inherit only from the controllers
        defined at the given ``modules`` (often system wide modules or
        installed modules). Modules in this context are Odoo addons.
        """
        # Controllers defined outside of odoo addons are outside of the
        # controller inheritance/extension mechanism.
        yield from (ctrl() for ctrl in Controller.children_classes.get('', []))

        # Controllers defined inside of odoo addons can be extended in
        # other installed addons. Rebuild the class inheritance here.
        highest_controllers = []
        for module in modules:
            highest_controllers.extend(Controller.children_classes.get(module, []))

        for top_ctrl in highest_controllers:
            leaf_controllers = list(unique(get_leaf_classes(top_ctrl)))

            name = top_ctrl.__name__
            if leaf_controllers != [top_ctrl]:
                name += ' (extended by %s)' %  ', '.join(
                    bot_ctrl.__name__
                    for bot_ctrl in leaf_controllers
                    if bot_ctrl is not top_ctrl
                )

            Ctrl = type(name, tuple(reversed(leaf_controllers)), {})
            yield Ctrl()

    for ctrl in build_controllers():
        for method_name, method in inspect.getmembers(ctrl, inspect.ismethod):

            # Skip this method if it is not @route decorated anywhere in
            # the hierarchy
            def is_method_a_route(cls):
                return getattr(getattr(cls, method_name, None), 'original_routing', None) is not None
            if not any(map(is_method_a_route, type(ctrl).mro())):
                continue

            merged_routing = {
                # 'type': 'http',  # set below
                'auth': 'user',
                'methods': None,
                'routes': [],
                'readonly': False,
            }

            for cls in unique(reversed(type(ctrl).mro()[:-2])):  # ancestors first
                if method_name not in cls.__dict__:
                    continue
                submethod = getattr(cls, method_name)

                if not hasattr(submethod, 'original_routing'):
                    _logger.warning("The endpoint %s is not decorated by @route(), decorating it myself.", f'{cls.__module__}.{cls.__name__}.{method_name}')
                    submethod = route()(submethod)

                _check_and_complete_route_definition(cls, submethod, merged_routing)

                merged_routing.update(submethod.original_routing)

            if not merged_routing['routes']:
                _logger.warning("%s is a controller endpoint without any route, skipping.", f'{cls.__module__}.{cls.__name__}.{method_name}')
                continue

            if nodb_only and merged_routing['auth'] != "none":
                continue

            for url in merged_routing['routes']:
                # duplicates the function (partial) with a copy of the
                # original __dict__ (update_wrapper) to keep a reference
                # to `original_routing` and `original_endpoint`, assign
                # the merged routing ONLY on the duplicated function to
                # ensure method's immutability.
                endpoint = functools.partial(method)
                functools.update_wrapper(endpoint, method)
                endpoint.routing = merged_routing

                yield (url, endpoint)


def _check_and_complete_route_definition(controller_cls, submethod, merged_routing):
    """Verify and complete the route definition.

    * Ensure 'type' is defined on each method's own routing.
    * also ensure overrides don't change the routing type.

    :param submethod: route method
    :param dict merged_routing: accumulated routing values (defaults + submethod ancestor methods)
    """
    default_type = submethod.original_routing.get('type', 'http')
    routing_type = merged_routing.setdefault('type', default_type)
    if submethod.original_routing.get('type') not in (None, routing_type):
        _logger.warning(
            "The endpoint %s changes the route type, using the original type: %r.",
            f'{controller_cls.__module__}.{controller_cls.__name__}.{submethod.__name__}',
            routing_type)
    submethod.original_routing['type'] = routing_type

# =========================================================
# Session
# =========================================================

class FilesystemSessionStore(sessions.FilesystemSessionStore):
    """ Place where to load and save session objects. """
    def get_session_filename(self, sid):
        # scatter sessions across 256 directories
        sha_dir = sid[:2]
        dirname = os.path.join(self.path, sha_dir)
        session_path = os.path.join(dirname, sid)
        return session_path

    def save(self, session):
        session_path = self.get_session_filename(session.sid)
        dirname = os.path.dirname(session_path)
        if not os.path.isdir(dirname):
            with contextlib.suppress(OSError):
                os.mkdir(dirname, 0o0755)
        super().save(session)

    def get(self, sid):
        # retro compatibility
        old_path = super().get_session_filename(sid)
        session_path = self.get_session_filename(sid)
        if os.path.isfile(old_path) and not os.path.isfile(session_path):
            dirname = os.path.dirname(session_path)
            if not os.path.isdir(dirname):
                with contextlib.suppress(OSError):
                    os.mkdir(dirname, 0o0755)
            with contextlib.suppress(OSError):
                os.rename(old_path, session_path)
        return super().get(sid)

    def rotate(self, session, env):
        self.delete(session)
        session.sid = self.generate_key()
        if session.uid and env:
            session.session_token = security.compute_session_token(session, env)
        session.should_rotate = False
        self.save(session)

    def vacuum(self, max_lifetime=SESSION_LIFETIME):
        threshold = time.time() - max_lifetime
        for fname in glob.iglob(os.path.join(root.session_store.path, '*', '*')):
            path = os.path.join(root.session_store.path, fname)
            with contextlib.suppress(OSError):
                if os.path.getmtime(path) < threshold:
                    os.unlink(path)


class Session(collections.abc.MutableMapping):
    """ Structure containing data persisted across requests. """
    __slots__ = ('can_save', '_Session__data', 'is_dirty', 'is_explicit', 'is_new',
                 'should_rotate', 'sid')

    def __init__(self, data, sid, new=False):
        self.can_save = True
        self.__data = {}
        self.update(data)
        self.is_dirty = False
        self.is_explicit = False
        self.is_new = new
        self.should_rotate = False
        self.sid = sid

    #
    # MutableMapping implementation with DocDict-like extension
    #
    def __getitem__(self, item):
        if item == 'geoip':
            warnings.warn('request.session.geoip have been moved to request.geoip', DeprecationWarning)
            return request.geoip if request else {}
        return self.__data[item]

    def __setitem__(self, item, value):
        value = pickle.loads(pickle.dumps(value))
        if item not in self.__data or self.__data[item] != value:
            self.is_dirty = True
        self.__data[item] = value

    def __delitem__(self, item):
        del self.__data[item]
        self.is_dirty = True

    def __len__(self):
        return len(self.__data)

    def __iter__(self):
        return iter(self.__data)

    def __getattr__(self, attr):
        return self.get(attr, None)

    def __setattr__(self, key, val):
        if key in self.__slots__:
            super().__setattr__(key, val)
        else:
            self[key] = val

    def clear(self):
        self.__data.clear()
        self.is_dirty = True

    #
    # Session methods
    #
    def authenticate(self, dbname, login=None, password=None):
        """
        Authenticate the current user with the given db, login and
        password. If successful, store the authentication parameters in
        the current session, unless multi-factor-auth (MFA) is
        activated. In that case, that last part will be done by
        :ref:`finalize`.

        .. versionchanged:: saas-15.3
           The current request is no longer updated using the user and
           context of the session when the authentication is done using
           a database different than request.db. It is up to the caller
           to open a new cursor/registry/env on the given database.
        """
        wsgienv = {
            'interactive': True,
            'base_location': request.httprequest.url_root.rstrip('/'),
            'HTTP_HOST': request.httprequest.environ['HTTP_HOST'],
            'REMOTE_ADDR': request.httprequest.environ['REMOTE_ADDR'],
        }

        registry = Registry(dbname)
        pre_uid = registry['res.users'].authenticate(dbname, login, password, wsgienv)

        self.uid = None
        self.pre_login = login
        self.pre_uid = pre_uid

        with registry.cursor() as cr:
            env = odoo.api.Environment(cr, pre_uid, {})

            # if 2FA is disabled we finalize immediately
            user = env['res.users'].browse(pre_uid)
            if not user._mfa_url():
                self.finalize(env)

        if request and request.session is self and request.db == dbname:
            # Like update_env(user=request.session.uid) but works when uid is None
            request.env = odoo.api.Environment(request.env.cr, self.uid, self.context)
            request.update_context(**self.context)
            # request env needs to be able to access the latest changes from the auth layers
            request.env.cr.commit()

        return pre_uid

    def finalize(self, env):
        """
        Finalizes a partial session, should be called on MFA validation
        to convert a partial / pre-session into a logged-in one.
        """
        login = self.pop('pre_login')
        uid = self.pop('pre_uid')

        env = env(user=uid)
        user_context = dict(env['res.users'].context_get())

        self.should_rotate = True
        self.update({
            'db': env.registry.db_name,
            'login': login,
            'uid': uid,
            'context': user_context,
            'session_token': env.user._compute_session_token(self.sid),
        })

    def logout(self, keep_db=False):
        db = self.db if keep_db else get_default_session()['db']  # None
        debug = self.debug
        self.clear()
        self.update(get_default_session(), db=db, debug=debug)
        self.context['lang'] = request.default_lang() if request else DEFAULT_LANG
        self.should_rotate = True

        if request and request.env:
            request.env['ir.http']._post_logout()

    def touch(self):
        self.is_dirty = True



# =========================================================
# GeoIP
# =========================================================

class GeoIP(collections.abc.Mapping):
    """
    Ip Geolocalization utility, determine information such as the
    country or the timezone of the user based on their IP Address.

    The instances share the same API as `:class:`geoip2.models.City`
    <https://geoip2.readthedocs.io/en/latest/#geoip2.models.City>`_.

    When the IP couldn't be geolocalized (missing database, bad address)
    then an empty object is returned. This empty object can be used like
    a regular one with the exception that all info are set None.

    :param str ip: The IP Address to geo-localize

    .. note:

        The geoip info the the current request are available at
        :attr:`~odoo.http.request.geoip`.

    .. code-block:

        >>> GeoIP('127.0.0.1').country.iso_code
        >>> odoo_ip = socket.gethostbyname('odoo.com')
        >>> GeoIP(odoo_ip).country.iso_code
        'FR'
    """

    def __init__(self, ip):
        self.ip = ip

    @lazy_property
    def _city_record(self):
        try:
            return root.geoip_city_db.city(self.ip)
        except (OSError, maxminddb.InvalidDatabaseError):
            return GEOIP_EMPTY_CITY
        except geoip2.errors.AddressNotFoundError:
            return GEOIP_EMPTY_CITY

    @lazy_property
    def _country_record(self):
        if '_city_record' in vars(self):
            # the City class inherits from the Country class and the
            # city record is in cache already, save a geolocalization
            return self._city_record
        try:
            return root.geoip_country_db.country(self.ip)
        except (OSError, maxminddb.InvalidDatabaseError):
            return self._city_record
        except geoip2.errors.AddressNotFoundError:
            return GEOIP_EMPTY_COUNTRY

    @property
    def country_name(self):
        return self.country.name or self.continent.name

    @property
    def country_code(self):
        return self.country.iso_code or self.continent.code

    def __getattr__(self, attr):
        # Be smart and determine whether the attribute exists on the
        # country object or on the city object.
        if hasattr(GEOIP_EMPTY_COUNTRY, attr):
            return getattr(self._country_record, attr)
        if hasattr(GEOIP_EMPTY_CITY, attr):
            return getattr(self._city_record, attr)
        raise AttributeError(f"{self} has no attribute {attr!r}")

    def __bool__(self):
        return self.country_name is not None

    # Old dict API, undocumented for now, will be deprecated some day
    def __getitem__(self, item):
        if item == 'country_name':
            return self.country_name

        if item == 'country_code':
            return self.country_code

        if item == 'city':
            return self.city.name

        if item == 'latitude':
            return self.location.latitude

        if item == 'longitude':
            return self.location.longitude

        if item == 'region':
            return self.subdivisions[0].iso_code if self.subdivisions else None

        if item == 'time_zone':
            return self.location.time_zone

        raise KeyError(item)

    def __iter__(self):
        raise NotImplementedError("The dictionnary GeoIP API is deprecated.")

    def __len__(self):
        raise NotImplementedError("The dictionnary GeoIP API is deprecated.")

# =========================================================
# Request and Response
# =========================================================

# Thread local global request object
_request_stack = werkzeug.local.LocalStack()
request = _request_stack()

@contextlib.contextmanager
def borrow_request():
    """ Get the current request and unexpose it from the local stack. """
    req = _request_stack.pop()
    try:
        yield req
    finally:
        _request_stack.push(req)


def make_request_wrap_methods(attr):
    def getter(self):
        return getattr(self._HTTPRequest__wrapped, attr)

    def setter(self, value):
        return setattr(self._HTTPRequest__wrapped, attr, value)

    return getter, setter


class HTTPRequest:
    def __init__(self, environ):
        httprequest = werkzeug.wrappers.Request(environ)
        httprequest.user_agent_class = UserAgent  # use vendored userAgent since it will be removed in 2.1
        httprequest.parameter_storage_class = werkzeug.datastructures.ImmutableOrderedMultiDict
        httprequest.max_content_length = DEFAULT_MAX_CONTENT_LENGTH

        self.__wrapped = httprequest
        self.__environ = self.__wrapped.environ
        self.environ = {
            key: value
            for key, value in self.__environ.items()
            if (not key.startswith(('werkzeug.', 'wsgi.', 'socket')) or key in ['wsgi.url_scheme'])
        }

    def __enter__(self):
        return self


HTTPREQUEST_ATTRIBUTES = [
    '__str__', '__repr__', '__exit__',
    'accept_charsets', 'accept_languages', 'accept_mimetypes', 'access_route', 'args', 'authorization', 'base_url',
    'charset', 'content_encoding', 'content_length', 'content_md5', 'content_type', 'cookies', 'data', 'date',
    'encoding_errors', 'files', 'form', 'full_path', 'get_data', 'get_json', 'headers', 'host', 'host_url', 'if_match',
    'if_modified_since', 'if_none_match', 'if_range', 'if_unmodified_since', 'is_json', 'is_secure', 'json',
    'max_content_length', 'method', 'mimetype', 'mimetype_params', 'origin', 'path', 'pragma', 'query_string', 'range',
    'referrer', 'remote_addr', 'remote_user', 'root_path', 'root_url', 'scheme', 'script_root', 'server', 'session',
    'trusted_hosts', 'url', 'url_charset', 'url_root', 'user_agent', 'values',
]
for attr in HTTPREQUEST_ATTRIBUTES:
    setattr(HTTPRequest, attr, property(*make_request_wrap_methods(attr)))


class Response(werkzeug.wrappers.Response):
    """
    Outgoing HTTP response with body, status, headers and qweb support.
    In addition to the :class:`werkzeug.wrappers.Response` parameters,
    this class's constructor can take the following additional
    parameters for QWeb Lazy Rendering.

    :param str template: template to render
    :param dict qcontext: Rendering context to use
    :param int uid: User id to use for the ir.ui.view render call,
        ``None`` to use the request's user (the default)

    these attributes are available as parameters on the Response object
    and can be altered at any time before rendering

    Also exposes all the attributes and methods of
    :class:`werkzeug.wrappers.Response`.
    """
    default_mimetype = 'text/html'

    def __init__(self, *args, **kw):
        template = kw.pop('template', None)
        qcontext = kw.pop('qcontext', None)
        uid = kw.pop('uid', None)
        super().__init__(*args, **kw)
        self.set_default(template, qcontext, uid)

    @classmethod
    def load(cls, result, fname="<function>"):
        """
        Convert the return value of an endpoint into a Response.

        :param result: The endpoint return value to load the Response from.
        :type result: Union[Response, werkzeug.wrappers.BaseResponse,
            werkzeug.exceptions.HTTPException, str, bytes, NoneType]
        :param str fname: The endpoint function name wherefrom the
            result emanated, used for logging.
        :returns: The created :class:`~odoo.http.Response`.
        :rtype: Response
        :raises TypeError: When ``result`` type is none of the above-
            mentioned type.
        """
        if isinstance(result, Response):
            return result

        if isinstance(result, werkzeug.exceptions.HTTPException):
            _logger.warning("%s returns an HTTPException instead of raising it.", fname)
            raise result

        if isinstance(result, werkzeug.wrappers.Response):
            response = cls.force_type(result)
            response.set_default()
            return response

        if isinstance(result, (bytes, str, type(None))):
            return cls(result)

        raise TypeError(f"{fname} returns an invalid value: {result}")

    def set_default(self, template=None, qcontext=None, uid=None):
        self.template = template
        self.qcontext = qcontext or dict()
        self.qcontext['response_template'] = self.template
        self.uid = uid

    @property
    def is_qweb(self):
        return self.template is not None

    def render(self):
        """ Renders the Response's template, returns the result. """
        self.qcontext['request'] = request
        return request.env["ir.ui.view"]._render_template(self.template, self.qcontext)

    def flatten(self):
        """
        Forces the rendering of the response's template, sets the result
        as response body and unsets :attr:`.template`
        """
        if self.template:
            self.response.append(self.render())
            self.template = None

    def set_cookie(self, key, value='', max_age=None, expires=-1, path='/', domain=None, secure=False, httponly=False, samesite=None, cookie_type='required'):
        """
        The default expires in Werkzeug is None, which means a session cookie.
        We want to continue to support the session cookie, but not by default.
        Now the default is arbitrary 1 year.
        So if you want a cookie of session, you have to explicitly pass expires=None.
        """
        if expires == -1:  # not provided value -> default value -> 1 year
            expires = datetime.now() + timedelta(days=365)

        if request.db and not request.env['ir.http']._is_allowed_cookie(cookie_type):
            max_age = 0
        super().set_cookie(key, value=value, max_age=max_age, expires=expires, path=path, domain=domain, secure=secure, httponly=httponly, samesite=samesite)


class FutureResponse:
    """
    werkzeug.Response mock class that only serves as placeholder for
    headers to be injected in the final response.
    """
    # used by werkzeug.Response.set_cookie
    charset = 'utf-8'
    max_cookie_size = 4093

    def __init__(self):
        self.headers = werkzeug.datastructures.Headers()

    @property
    def _charset(self):
        return self.charset

    @functools.wraps(werkzeug.Response.set_cookie)
    def set_cookie(self, key, value='', max_age=None, expires=-1, path='/', domain=None, secure=False, httponly=False, samesite=None, cookie_type='required'):
        if expires == -1:  # not forced value -> default value -> 1 year
            expires = datetime.now() + timedelta(days=365)

        if request.db and not request.env['ir.http']._is_allowed_cookie(cookie_type):
            max_age = 0
        werkzeug.Response.set_cookie(self, key, value=value, max_age=max_age, expires=expires, path=path, domain=domain, secure=secure, httponly=httponly, samesite=samesite)


class Request:
    """
    Wrapper around the incoming HTTP request with deserialized request
    parameters, session utilities and request dispatching logic.
    """

    def __init__(self, httprequest):
        self.httprequest = httprequest
        self.future_response = FutureResponse()
        self.dispatcher = _dispatchers['http'](self)  # until we match
        #self.params = {}  # set by the Dispatcher

        self.geoip = GeoIP(httprequest.remote_addr)
        self.registry = None
        self.env = None

    def _post_init(self):
        self.session, self.db = self._get_session_and_dbname()

    def _get_session_and_dbname(self):
        # The session is explicit when it comes from the query-string or
        # the header. It is implicit when it comes from the cookie or
        # that is does not exist yet. The explicit session should be
        # used in this request only, it should not be saved on the
        # response cookie.
        sid = (self.httprequest.args.get('session_id')
            or self.httprequest.headers.get("X-Openerp-Session-Id"))
        if sid:
            is_explicit = True
        else:
            sid = self.httprequest.cookies.get('session_id')
            is_explicit = False

        if sid is None:
            session = root.session_store.new()
        else:
            session = root.session_store.get(sid)
            session.sid = sid  # in case the session was not persisted
        session.is_explicit = is_explicit

        for key, val in get_default_session().items():
            session.setdefault(key, val)
        if not session.context.get('lang'):
            session.context['lang'] = self.default_lang()

        dbname = None
        host = self.httprequest.environ['HTTP_HOST']
        if session.db and db_filter([session.db], host=host):
            dbname = session.db
        else:
            all_dbs = db_list(force=True, host=host)
            if len(all_dbs) == 1:
                dbname = all_dbs[0]  # monodb

        if session.db != dbname:
            if session.db:
                _logger.warning("Logged into database %r, but dbfilter rejects it; logging session out.", session.db)
                session.logout(keep_db=False)
            session.db = dbname

        session.is_dirty = False
        return session, dbname

    # =====================================================
    # Getters and setters
    # =====================================================
    def update_env(self, user=None, context=None, su=None):
        """ Update the environment of the current request.

        :param user: optional user/user id to change the current user
        :type user: int or :class:`res.users record<~odoo.addons.base.models.res_users.Users>`
        :param dict context: optional context dictionary to change the current context
        :param bool su: optional boolean to change the superuser mode
        """
        cr = None  # None is a sentinel, it keeps the same cursor
        self.env = self.env(cr, user, context, su)
        threading.current_thread().uid = self.env.uid

    def update_context(self, **overrides):
        """
        Override the environment context of the current request with the
        values of ``overrides``. To replace the entire context, please
        use :meth:`~update_env` instead.
        """
        self.update_env(context=dict(self.env.context, **overrides))

    @property
    def context(self):
        return self.env.context

    @context.setter
    def context(self, value):
        raise NotImplementedError("Use request.update_context instead.")

    @property
    def uid(self):
        return self.env.uid

    @uid.setter
    def uid(self, value):
        raise NotImplementedError("Use request.update_env instead.")

    @property
    def cr(self):
        return self.env.cr

    @cr.setter
    def cr(self, value):
        if value is None:
            raise NotImplementedError("Close the cursor instead.")
        raise ValueError("You cannot replace the cursor attached to the current request.")

    _cr = cr

    @lazy_property
    def best_lang(self):
        lang = self.httprequest.accept_languages.best
        if not lang:
            return None

        try:
            code, territory, _, _ = babel.core.parse_locale(lang, sep='-')
            if territory:
                lang = f'{code}_{territory}'
            else:
                lang = babel.core.LOCALE_ALIASES[code]
            return lang
        except (ValueError, KeyError):
            return None

    # =====================================================
    # Helpers
    # =====================================================
    def csrf_token(self, time_limit=None):
        """
        Generates and returns a CSRF token for the current session

        :param Optional[int] time_limit: the CSRF token should only be
            valid for the specified duration (in second), by default
            48h, ``None`` for the token to be valid as long as the
            current user's session is.
        :returns: ASCII token string
        :rtype: str
        """
        secret = self.env['ir.config_parameter'].sudo().get_param('database.secret')
        if not secret:
            raise ValueError("CSRF protection requires a configured database secret")

        # if no `time_limit` => distant 1y expiry so max_ts acts as salt, e.g. vs BREACH
        max_ts = int(time.time() + (time_limit or CSRF_TOKEN_SALT))
        msg = f'{self.session.sid}{max_ts}'.encode('utf-8')

        hm = hmac.new(secret.encode('ascii'), msg, hashlib.sha1).hexdigest()
        return f'{hm}o{max_ts}'

    def validate_csrf(self, csrf):
        """
        Is the given csrf token valid ?

        :param str csrf: The token to validate.
        :returns: ``True`` when valid, ``False`` when not.
        :rtype: bool
        """
        if not csrf:
            return False

        secret = self.env['ir.config_parameter'].sudo().get_param('database.secret')
        if not secret:
            raise ValueError("CSRF protection requires a configured database secret")

        hm, _, max_ts = csrf.rpartition('o')
        msg = f'{self.session.sid}{max_ts}'.encode('utf-8')

        if max_ts:
            try:
                if int(max_ts) < int(time.time()):
                    return False
            except ValueError:
                return False

        hm_expected = hmac.new(secret.encode('ascii'), msg, hashlib.sha1).hexdigest()
        return consteq(hm, hm_expected)

    def default_context(self):
        return dict(get_default_session()['context'], lang=self.default_lang())

    def default_lang(self):
        """Returns default user language according to request specification

        :returns: Preferred language if specified or 'en_US'
        :rtype: str
        """
        return self.best_lang or DEFAULT_LANG

    def get_http_params(self):
        """
        Extract key=value pairs from the query string and the forms
        present in the body (both application/x-www-form-urlencoded and
        multipart/form-data).

        :returns: The merged key-value pairs.
        :rtype: dict
        """
        params = {
            **self.httprequest.args,
            **self.httprequest.form,
            **self.httprequest.files
        }
        params.pop('session_id', None)
        return params

    def get_json_data(self):
        return json.loads(self.httprequest.get_data(as_text=True))

    def _get_profiler_context_manager(self):
        """
        Get a profiler when the profiling is enabled and the requested
        URL is profile-safe. Otherwise, get a context-manager that does
        nothing.
        """
        if self.session.profile_session and self.db:
            if self.session.profile_expiration < str(datetime.now()):
                # avoid having session profiling for too long if user forgets to disable profiling
                self.session.profile_session = None
                _logger.warning("Profiling expiration reached, disabling profiling")
            elif 'set_profiling' in self.httprequest.path:
                _logger.debug("Profiling disabled on set_profiling route")
            elif self.httprequest.path.startswith('/websocket'):
                _logger.debug("Profiling disabled for websocket")
            elif odoo.evented:
                # only longpolling should be in a evented server, but this is an additional safety
                _logger.debug("Profiling disabled for evented server")
            else:
                try:
                    return profiler.Profiler(
                        db=self.db,
                        description=self.httprequest.full_path,
                        profile_session=self.session.profile_session,
                        collectors=self.session.profile_collectors,
                        params=self.session.profile_params,
                    )
                except Exception:
                    _logger.exception("Failure during Profiler creation")
                    self.session.profile_session = None

        return contextlib.nullcontext()

    def _inject_future_response(self, response):
        response.headers.extend(self.future_response.headers)
        return response

    def make_response(self, data, headers=None, cookies=None, status=200):
        """ Helper for non-HTML responses, or HTML responses with custom
        response headers or cookies.

        While handlers can just return the HTML markup of a page they want to
        send as a string if non-HTML data is returned they need to create a
        complete response object, or the returned data will not be correctly
        interpreted by the clients.

        :param str data: response body
        :param int status: http status code
        :param headers: HTTP headers to set on the response
        :type headers: ``[(name, value)]``
        :param collections.abc.Mapping cookies: cookies to set on the client
        :returns: a response object.
        :rtype: :class:`~odoo.http.Response`
        """
        response = Response(data, status=status, headers=headers)
        if cookies:
            for k, v in cookies.items():
                response.set_cookie(k, v)
        return response

    def make_json_response(self, data, headers=None, cookies=None, status=200):
        """ Helper for JSON responses, it json-serializes ``data`` and
        sets the Content-Type header accordingly if none is provided.

        :param data: the data that will be json-serialized into the response body
        :param int status: http status code
        :param List[(str, str)] headers: HTTP headers to set on the response
        :param collections.abc.Mapping cookies: cookies to set on the client
        :rtype: :class:`~odoo.http.Response`
        """
        data = json.dumps(data, ensure_ascii=False, default=date_utils.json_default)

        headers = werkzeug.datastructures.Headers(headers)
        headers['Content-Length'] = len(data)
        if 'Content-Type' not in headers:
            headers['Content-Type'] = 'application/json; charset=utf-8'

        return self.make_response(data, headers.to_wsgi_list(), cookies, status)

    def not_found(self, description=None):
        """ Shortcut for a `HTTP 404
        <http://tools.ietf.org/html/rfc7231#section-6.5.4>`_ (Not Found)
        response
        """
        return NotFound(description)

    def redirect(self, location, code=303, local=True):
        # compatibility, Werkzeug support URL as location
        if isinstance(location, URL):
            location = location.to_url()
        if local:
            location = '/' + url_parse(location).replace(scheme='', netloc='').to_url().lstrip('/')
        if self.db:
            return self.env['ir.http']._redirect(location, code)
        return werkzeug.utils.redirect(location, code, Response=Response)

    def redirect_query(self, location, query=None, code=303, local=True):
        if query:
            location += '?' + url_encode(query)
        return self.redirect(location, code=code, local=local)

    def render(self, template, qcontext=None, lazy=True, **kw):
        """ Lazy render of a QWeb template.

        The actual rendering of the given template will occur at then end of
        the dispatching. Meanwhile, the template and/or qcontext can be
        altered or even replaced by a static response.

        :param str template: template to render
        :param dict qcontext: Rendering context to use
        :param bool lazy: whether the template rendering should be deferred
                          until the last possible moment
        :param dict kw: forwarded to werkzeug's Response object
        """
        response = Response(template=template, qcontext=qcontext, **kw)
        if not lazy:
            return response.render()
        return response

    def _save_session(self):
        """ Save a modified session on disk. """
        sess = self.session

        if not sess.can_save:
            return

        if sess.should_rotate:
            root.session_store.rotate(sess, self.env)  # it saves
        elif sess.is_dirty:
            root.session_store.save(sess)

        # We must not set the cookie if the session id was specified
        # using a http header or a GET parameter.
        # There are two reasons to this:
        # - When using one of those two means we consider that we are
        #   overriding the cookie, which means creating a new session on
        #   top of an already existing session and we don't want to
        #   create a mess with the 'normal' session (the one using the
        #   cookie). That is a special feature of the Javascript Session.
        # - It could allow session fixation attacks.
        cookie_sid = self.httprequest.cookies.get('session_id')
        if not sess.is_explicit and (sess.is_dirty or cookie_sid != sess.sid):
            self.future_response.set_cookie('session_id', sess.sid, max_age=SESSION_LIFETIME, httponly=True)

    def _set_request_dispatcher(self, rule):
        routing = rule.endpoint.routing
        dispatcher_cls = _dispatchers[routing['type']]
        if (not is_cors_preflight(self, rule.endpoint)
            and not dispatcher_cls.is_compatible_with(self)):
            compatible_dispatchers = [
                disp.routing_type
                for disp in _dispatchers.values()
                if disp.is_compatible_with(self)
            ]
            raise BadRequest(f"Request inferred type is compatible with {compatible_dispatchers} but {routing['routes'][0]!r} is type={routing['type']!r}.")
        self.dispatcher = dispatcher_cls(self)

    # =====================================================
    # Routing
    # =====================================================
    def _serve_static(self):
        """ Serve a static file from the file system. """
        module, _, path = self.httprequest.path[1:].partition('/static/')
        try:
            directory = root.statics[module]
            filepath = werkzeug.security.safe_join(directory, path)
            res = Stream.from_path(filepath).get_response(
                max_age=0 if 'assets' in self.session.debug else STATIC_CACHE,
            )
            root.set_csp(res)
            return res
        except KeyError:
            raise NotFound(f'Module "{module}" not found.\n')
        except OSError:  # cover both missing file and invalid permissions
            raise NotFound(f'File "{path}" not found in module {module}.\n')

    def _serve_nodb(self):
        """
        Dispatch the request to its matching controller in a
        database-free environment.
        """
        router = root.nodb_routing_map.bind_to_environ(self.httprequest.environ)
        rule, args = router.match(return_rule=True)
        self._set_request_dispatcher(rule)
        self.dispatcher.pre_dispatch(rule, args)
        response = self.dispatcher.dispatch(rule.endpoint, args)
        self.dispatcher.post_dispatch(response)
        return response

    def _serve_db(self):
        """
        Prepare the user session and load the ORM before forwarding the
        request to ``_serve_ir_http``.
        """
        try:
            self.registry = Registry(self.db).check_signaling()
        except (AttributeError, psycopg2.OperationalError, psycopg2.ProgrammingError):
            # psycopg2 error or attribute error while constructing
            # the registry. That means either
            #  - the database probably does not exists anymore, or
            #  - the database is corrupted, or
            #  - the database version doesn't match the server version.
            # So remove the database from the cookie
            self.db = None
            self.session.db = None
            root.session_store.save(self.session)
            if request.httprequest.path == '/web':
                # Internal Server Error
                raise
            else:
                return self._serve_nodb()

        with contextlib.closing(self.registry.cursor()) as cr:
            self.env = odoo.api.Environment(cr, self.session.uid, self.session.context)
            threading.current_thread().uid = self.env.uid
            try:
                return service_model.retrying(self._serve_ir_http, self.env)
            except Exception as exc:
                if isinstance(exc, HTTPException) and exc.code is None:
                    raise  # bubble up to odoo.http.Application.__call__
                exc.error_response = self.registry['ir.http']._handle_error(exc)
                raise

    def _serve_ir_http(self):
        """
        Delegate most of the processing to the ir.http model that is
        extensible by applications.
        """
        ir_http = self.registry['ir.http']

        try:
            rule, args = ir_http._match(self.httprequest.path)
        except NotFound:
            self.params = self.get_http_params()
            response = ir_http._serve_fallback()
            if response:
                self.dispatcher.post_dispatch(response)
                return response
            raise

        self._set_request_dispatcher(rule)
        ir_http._authenticate(rule.endpoint)
        ir_http._pre_dispatch(rule, args)
        response = self.dispatcher.dispatch(rule.endpoint, args)
        # the registry can have been reniewed by dispatch
        self.registry['ir.http']._post_dispatch(response)
        return response


# =========================================================
# Core type-specialized dispatchers
# =========================================================

_dispatchers = {}

class Dispatcher(ABC):
    routing_type: str

    @classmethod
    def __init_subclass__(cls):
        super().__init_subclass__()
        _dispatchers[cls.routing_type] = cls

    def __init__(self, request):
        self.request = request

    @classmethod
    @abstractmethod
    def is_compatible_with(cls, request):
        """
        Determine if the current request is compatible with this
        dispatcher.
        """

    def pre_dispatch(self, rule, args):
        """
        Prepare the system before dispatching the request to its
        controller. This method is often overridden in ir.http to
        extract some info from the request query-string or headers and
        to save them in the session or in the context.
        """
        routing = rule.endpoint.routing
        self.request.session.can_save = routing.get('save_session', True)

        set_header = self.request.future_response.headers.set
        cors = routing.get('cors')
        if cors:
            set_header('Access-Control-Allow-Origin', cors)
            set_header('Access-Control-Allow-Methods', (
                'POST' if routing['type'] == 'json'
                else ', '.join(routing['methods'] or ['GET', 'POST'])
            ))

        if cors and self.request.httprequest.method == 'OPTIONS':
            set_header('Access-Control-Max-Age', CORS_MAX_AGE)
            set_header('Access-Control-Allow-Headers',
                       'Origin, X-Requested-With, Content-Type, Accept, Authorization')
            werkzeug.exceptions.abort(Response(status=204))

        if 'max_content_length' in routing:
            self.request.httprequest.max_content_length = routing['max_content_length']

    @abstractmethod
    def dispatch(self, endpoint, args):
        """
        Extract the params from the request's body and call the
        endpoint. While it is preferred to override ir.http._pre_dispatch
        and ir.http._post_dispatch, this method can be override to have
        a tight control over the dispatching.
        """

    def post_dispatch(self, response):
        """
        Manipulate the HTTP response to inject various headers, also
        save the session when it is dirty.
        """
        self.request._save_session()
        self.request._inject_future_response(response)
        root.set_csp(response)

    @abstractmethod
    def handle_error(self, exc: Exception) -> collections.abc.Callable:
        """
        Transform the exception into a valid HTTP response. Called upon
        any exception while serving a request.
        """


class HttpDispatcher(Dispatcher):
    routing_type = 'http'

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
        if self.request.httprequest.method not in CSRF_FREE_METHODS and endpoint.routing.get('csrf', True):
            if not self.request.db:
                return self.request.redirect('/web/database/selector')

            token = self.request.params.pop('csrf_token', None)
            if not self.request.validate_csrf(token):
                if token is not None:
                    _logger.warning("CSRF validation failed on path '%s'", self.request.httprequest.path)
                else:
                    _logger.warning(MISSING_CSRF_WARNING, request.httprequest.path)
                raise werkzeug.exceptions.BadRequest('Session expired (invalid CSRF token)')

        if self.request.db:
            return self.request.registry['ir.http']._dispatch(endpoint)
        else:
            return endpoint(**self.request.params)

    def handle_error(self, exc: Exception) -> collections.abc.Callable:
        """
        Handle any exception that occurred while dispatching a request
        to a `type='http'` route. Also handle exceptions that occurred
        when no route matched the request path, when no fallback page
        could be delivered and that the request ``Content-Type`` was not
        json.

        :param Exception exc: the exception that occurred.
        :returns: a WSGI application
        """
        if isinstance(exc, SessionExpiredException):
            session = self.request.session
            was_connected = session.uid is not None
            session.logout(keep_db=True)
            response = self.request.redirect_query('/web/login', {'redirect': self.request.httprequest.full_path})
            if not session.is_explicit and was_connected:
                root.session_store.rotate(session, self.request.env)
                response.set_cookie('session_id', session.sid, max_age=SESSION_LIFETIME, httponly=True)
            return response

        return (exc if isinstance(exc, HTTPException)
           else Forbidden(exc.args[0]) if isinstance(exc, (AccessDenied, AccessError))
           else BadRequest(exc.args[0]) if isinstance(exc, UserError)
           else InternalServerError()  # hide the real error
        )


class JsonRPCDispatcher(Dispatcher):
    routing_type = 'json'

    def __init__(self, request):
        super().__init__(request)
        self.jsonrequest = {}
        self.request_id = None

    @classmethod
    def is_compatible_with(cls, request):
        return request.httprequest.mimetype in JSON_MIMETYPES

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
        except ValueError as exc:
            # must use abort+Response to bypass handle_error
            werkzeug.exceptions.abort(Response("Invalid JSON data", status=400))
        except AttributeError as exc:
            # must use abort+Response to bypass handle_error
            werkzeug.exceptions.abort(Response("Invalid JSON-RPC data", status=400))

        self.request.params = dict(self.jsonrequest.get('params', {}), **args)

        if self.request.db:
            result = self.request.registry['ir.http']._dispatch(endpoint)
        else:
            result = endpoint(**self.request.params)
        return self._response(result)

    def handle_error(self, exc: Exception) -> collections.abc.Callable:
        """
        Handle any exception that occurred while dispatching a request to
        a `type='json'` route. Also handle exceptions that occurred when
        no route matched the request path, that no fallback page could
        be delivered and that the request ``Content-Type`` was json.

        :param exc: the exception that occurred.
        :returns: a WSGI application
        """
        error = {
            'code': 200,  # this code is the JSON-RPC level code, it is
                          # distinct from the HTTP status code. This
                          # code is ignored and the value 200 (while
                          # misleading) is totally arbitrary.
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


# =========================================================
# WSGI Entry Point
# =========================================================

class Application:
    """ Odoo WSGI application """
    # See also: https://www.python.org/dev/peps/pep-3333

    @lazy_property
    def statics(self):
        """
        Map module names to their absolute ``static`` path on the file
        system.
        """
        mod2path = {}
        for addons_path in odoo.addons.__path__:
            for module in os.listdir(addons_path):
                manifest = get_manifest(module)
                static_path = opj(addons_path, module, 'static')
                if (manifest
                        and (manifest['installable'] or manifest['assets'])
                        and os.path.isdir(static_path)):
                    mod2path[module] = static_path
        return mod2path

    def get_static_file(self, url, host=''):
        """
        Get the full-path of the file if the url resolves to a local
        static file, otherwise return None.

        Without the second host parameters, ``url`` must be an absolute
        path, others URLs are considered faulty.

        With the second host parameters, ``url`` can also be a full URI
        and the authority found in the URL (if any) is validated against
        the given ``host``.
        """

        netloc, path = urlparse(url)[1:3]
        try:
            path_netloc, module, static, resource = path.split('/', 3)
        except ValueError:
            return None

        if ((netloc and netloc != host) or (path_netloc and path_netloc != host)):
            return None

        if (module not in self.statics or static != 'static' or not resource):
            return None

        try:
            return file_path(f'{module}/static/{resource}')
        except FileNotFoundError:
            return None

    @lazy_property
    def nodb_routing_map(self):
        nodb_routing_map = werkzeug.routing.Map(strict_slashes=False, converters=None)
        for url, endpoint in _generate_routing_rules([''] + odoo.conf.server_wide_modules, nodb_only=True):
            routing = submap(endpoint.routing, ROUTING_KEYS)
            if routing['methods'] is not None and 'OPTIONS' not in routing['methods']:
                routing['methods'] = routing['methods'] + ['OPTIONS']
            rule = werkzeug.routing.Rule(url, endpoint=endpoint, **routing)
            rule.merge_slashes = False
            nodb_routing_map.add(rule)

        return nodb_routing_map

    @lazy_property
    def session_store(self):
        path = odoo.tools.config.session_dir
        _logger.debug('HTTP sessions stored in: %s', path)
        return FilesystemSessionStore(path, session_class=Session, renew_missing=True)

    def get_db_router(self, db):
        if not db:
            return self.nodb_routing_map
        return request.env['ir.http'].routing_map()

    @lazy_property
    def geoip_city_db(self):
        try:
            return geoip2.database.Reader(config['geoip_city_db'])
        except (OSError, maxminddb.InvalidDatabaseError):
            _logger.debug(
                "Couldn't load Geoip City file at %s. IP Resolver disabled.",
                config['geoip_city_db'], exc_info=True
            )
            raise

    @lazy_property
    def geoip_country_db(self):
        try:
            return geoip2.database.Reader(config['geoip_country_db'])
        except (OSError, maxminddb.InvalidDatabaseError) as exc:
            _logger.debug("Couldn't load Geoip Country file (%s). Fallbacks on Geoip City.", exc,)
            raise

    def set_csp(self, response):
        headers = response.headers
        headers['X-Content-Type-Options'] = 'nosniff'

        if 'Content-Security-Policy' in headers:
            return

        mime, _params = cgi.parse_header(headers.get('Content-Type', ''))
        if not mime.startswith('image/'):
            return

        headers['Content-Security-Policy'] = "default-src 'none'"

    def __call__(self, environ, start_response):
        """
        WSGI application entry point.

        :param dict environ: container for CGI environment variables
            such as the request HTTP headers, the source IP address and
            the body as an io file.
        :param callable start_response: function provided by the WSGI
            server that this application must call in order to send the
            HTTP response status line and the response headers.
        """
        current_thread = threading.current_thread()
        current_thread.query_count = 0
        current_thread.query_time = 0
        current_thread.perf_t0 = time.time()
        if hasattr(current_thread, 'dbname'):
            del current_thread.dbname
        if hasattr(current_thread, 'uid'):
            del current_thread.uid

        if odoo.tools.config['proxy_mode'] and environ.get("HTTP_X_FORWARDED_HOST"):
            # The ProxyFix middleware has a side effect of updating the
            # environ, see https://github.com/pallets/werkzeug/pull/2184
            def fake_app(environ, start_response):
                return []
            def fake_start_response(status, headers):
                return
            ProxyFix(fake_app)(environ, fake_start_response)

        with HTTPRequest(environ) as httprequest:
            request = Request(httprequest)
            _request_stack.push(request)

            try:
                request._post_init()
                current_thread.url = httprequest.url

                if self.get_static_file(httprequest.path):
                    response = request._serve_static()
                elif request.db:
                    with request._get_profiler_context_manager():
                        response = request._serve_db()
                else:
                    response = request._serve_nodb()
                return response(environ, start_response)

            except Exception as exc:
                # Valid (2xx/3xx) response returned via werkzeug.exceptions.abort.
                if isinstance(exc, HTTPException) and exc.code is None:
                    response = exc.get_response()
                    HttpDispatcher(request).post_dispatch(response)
                    return response(environ, start_response)

                # Logs the error here so the traceback starts with ``__call__``.
                if hasattr(exc, 'loglevel'):
                    _logger.log(exc.loglevel, exc, exc_info=getattr(exc, 'exc_info', None))
                elif isinstance(exc, HTTPException):
                    pass
                elif isinstance(exc, SessionExpiredException):
                    _logger.info(exc)
                elif isinstance(exc, (UserError, AccessError)):
                    _logger.warning(exc)
                else:
                    _logger.error("Exception during request handling.", exc_info=True)

                # Ensure there is always a WSGI handler attached to the exception.
                if not hasattr(exc, 'error_response'):
                    exc.error_response = request.dispatcher.handle_error(exc)

                return exc.error_response(environ, start_response)

            finally:
                _request_stack.pop()


root = Application()
