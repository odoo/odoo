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
  optionaly coerce the endpoint result.

endpoint
  The @route(...) decorated controller method.
"""

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
from datetime import datetime
from os.path import join as opj

import babel.core
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

import odoo
from .exceptions import UserError, AccessError, AccessDenied
from .modules.module import get_manifest
from .modules.registry import Registry
from .service import security, model as service_model
from .tools import (config, consteq, date_utils, profiler, resolve_attr,
                    submap, unique, ustr,)
from .tools.geoipresolver import GeoIPResolver
from .tools.func import filter_kwargs, lazy_property
from .tools.mimetypes import guess_mimetype
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
# Add potentially wrong (detected on windows) svg mime types
mimetypes.add_type('image/svg+xml', '.svg')

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

# The dictionnary to initialise a new session with.
def get_default_session():
    return {
        'context': {},  # 'lang': request.default_lang()  # must be set at runtime
        'db': None,
        'debug': '',
        'login': None,
        'uid': None,
        'session_token': None,
        # profiling
        'profile_session': None,
        'profile_collectors': None,
        'profile_params': None,
    }

# The request mimetypes that transport JSON in their body.
JSON_MIMETYPES = ('application/json', 'application/json-rpc')

MISSING_CSRF_WARNING = """\
No CSRF validation token provided for path %r

Odoo URLs are CSRF-protected by default (when accessed with unsafe
HTTP methods). See
https://www.odoo.com/documentation/saas-15.3/developer/reference/addons/http.html#csrf
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

# The mimetypes of safe image types
SAFE_IMAGE_MIMETYPES = {'image/jpeg', 'image/png', 'image/gif', 'image/x-icon'}

# The duration of a user session before it is considered expired,
# three months.
SESSION_LIFETIME = 60 * 60 * 24 * 90

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
        url_quote(filename, safe='')
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

def is_cors_preflight(request, endpoint):
    return request.httprequest.method == 'OPTIONS' and endpoint.routing.get('cors', False)

def send_file(filepath_or_fp, filename=None, mimetype=None, mtime=None,
              as_attachment=False, cache_timeout=STATIC_CACHE):
    """
    Fle streaming utility with mime and cache handling, it takes a
    file-object or immediately the content as bytes/str.

    Sends the content of a file to the client. This will use the most
    efficient method available and configured. By default it will try to
    use the WSGI server's file_wrapper support.

    If filename of file.name is provided it will try to guess the
    mimetype for you, but you can also explicitly provide one.

    For extra security you probably want to send certain files as
    attachment (e.g. HTML).

    :param Union[os.PathLike,io.FileIO] filepath_or_fp: the filename of
        the file to send.  Alternatively a file object might be provided
        in which case `X-Sendfile` might not work and fall back to the
        traditional method. Make sure that the file pointer is position-
        ed at the start of data to send before calling :func:`send_file`
    :param str filename: optional if file has a 'name' attribute, used
        for attachment name and mimetype guess.
    :param str mimetype: the mimetype of the file if provided, otherwise
        auto detection happens based on the name.
    :param datetime mtime: optional if file has a 'name' attribute, last
        modification time used for conditional response.
    :param bool as_attachment: set to `True` if you want to send this
        file with a ``Content-Disposition: attachment`` header.
    :param int cache_timeout: set to `False` to disable etags and
        conditional response handling (last modified and etags)
    :returns: the HTTP response that streams the file.
    """
    if isinstance(filepath_or_fp, str):
        if not filename:
            filename = os.path.basename(filepath_or_fp)
        file = open(filepath_or_fp, 'rb')
    else:
        file = filepath_or_fp
        if not filename:
            filename = getattr(file, 'name', None)

    # Only used when filename or mtime argument is not provided
    path = getattr(file, 'name', 'file.bin')

    if not filename:
        filename = os.path.basename(path)

    if not mimetype:
        mimetype = mimetypes.guess_type(filename)[0] or 'application/octet-stream'

    file.seek(0, 2)
    size = file.tell()
    file.seek(0)

    data = werkzeug.wsgi.wrap_file(request.httprequest.environ, file)

    res = werkzeug.wrappers.Response(data, mimetype=mimetype, direct_passthrough=True)
    res.content_length = size

    if as_attachment:
        res.headers.add('Content-Disposition', 'attachment', filename=filename)

    if cache_timeout:
        if not mtime:
            with contextlib.suppress(FileNotFoundError):
                mtime = datetime.fromtimestamp(os.path.getmtime(path))
        if mtime:
            res.last_modified = mtime
        crc = zlib.adler32(filename.encode('utf-8') if isinstance(filename, str) else filename) & 0xffffffff
        etag = f'odoo-{mtime}-{size}-{crc}'
        if not werkzeug.http.is_resource_modified(request.httprequest.environ, etag, last_modified=mtime):
            res = werkzeug.wrappers.Response(status=304)
        else:
            res.cache_control.public = True
            res.cache_control.max_age = cache_timeout
            res.set_etag(etag)
    return res

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

def set_safe_image_headers(headers, content):
    """Return new headers based on `headers` but with `Content-Length` and
    `Content-Type` set appropriately depending on the given `content` only if it
    is safe to do, as well as `X-Content-Type-Options: nosniff` so that if the
    file is of an unsafe type, it is not interpreted as that type if the
    `Content-type` header was already set to a different mimetype
    """
    headers = werkzeug.datastructures.Headers(headers)
    content_type = guess_mimetype(content)
    if content_type in SAFE_IMAGE_MIMETYPES:
        headers['Content-Type'] = content_type
    headers['X-Content-Type-Options'] = 'nosniff'
    headers['Content-Length'] = len(content)
    return list(headers)


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
                return resolve_attr(cls, f'{method_name}.original_routing', None) is not None
            if not any(map(is_method_a_route, type(ctrl).mro())):
                continue

            merged_routing = {
                # 'type': 'http',  # set below
                'auth': 'user',
                'methods': None,
                'routes': [],
                'readonly': False,
            }

            for cls in unique(reversed(type(ctrl).mro())):  # ancestors first
                submethod = getattr(cls, method_name, None)
                if submethod is None:
                    continue

                if not hasattr(submethod, 'original_routing'):
                    _logger.warning("The endpoint %s is not decorated by @route(), decorating it myself.", f'{cls.__module__}.{cls.__name__}.{method_name}')
                    submethod = route()(submethod)

                # Ensure "type" is defined on each method's own routing,
                # also ensure overrides don't change the routing type.
                default_type = submethod.original_routing.get('type', 'http')
                routing_type = merged_routing.setdefault('type', default_type)
                if submethod.original_routing.get('type') not in (None, routing_type):
                    _logger.warning("The endpoint %s changes the route type, using the original type: %r.", f'{cls.__module__}.{cls.__name__}.{method_name}', routing_type)
                submethod.original_routing['type'] = routing_type

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
        self.save(session)

    def vacuum(self):
        threshold = time.time() - SESSION_LIFETIME
        for fname in glob.iglob(os.path.join(root.session_store.path, '*', '*')):
            path = os.path.join(root.session_store.path, fname)
            with contextlib.suppress(OSError):
                if os.path.getmtime(path) < threshold:
                    os.unlink(path)


class Session(collections.abc.MutableMapping):
    """ Structure containing data persisted across requests. """
    __slots__ = ('can_save', 'data', 'is_dirty', 'is_explicit', 'is_new',
                 'should_rotate', 'sid')

    def __init__(self, data, sid, new=False):
        self.can_save = True
        self.data = data
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
        return self.data[item]

    def __setitem__(self, item, value):
        if item not in self.data or self.data[item] != value:
            self.is_dirty = True
        self.data[item] = value

    def __delitem__(self, item):
        del self.data[item]
        self.is_dirty = True

    def __len__(self):
        return len(self.data)

    def __iter__(self):
        return iter(self.data)

    def __getattr__(self, attr):
        return self.get(attr, None)

    def __setattr__(self, key, val):
        if key in self.__slots__:
            super().__setattr__(key, val)
        else:
            self[key] = val

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

    def touch(self):
        self.is_dirty = True


# =========================================================
# Request and Response
# =========================================================

# Thread local global request object
_request_stack = werkzeug.local.LocalStack()
request = _request_stack()


class Response(werkzeug.wrappers.Response):
    """
    Outgoing HTTP response with body, status, headers and qweb support.
    In addition to the :class:`werkzeug.wrappers.Response` parameters,
    this class's constructor can take the following additional
    parameters for QWeb Lazy Rendering.

    :param basestring template: template to render
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

    @functools.wraps(werkzeug.Response.set_cookie)
    def set_cookie(self, *args, **kwargs):
        werkzeug.Response.set_cookie(self, *args, **kwargs)


class Request:
    """
    Wrapper around the incomming HTTP request with deserialized request
    parameters, session utilities and request dispatching logic.
    """

    def __init__(self, httprequest):
        self.httprequest = httprequest
        self.future_response = FutureResponse()
        self.dispatcher = _dispatchers['http'](self)  # until we match
        #self.params = {}  # set by the Dispatcher

        self.session, self.db = self._get_session_and_dbname()
        self.registry = None
        self.env = None

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
        """ Update the environment of the current request. """
        cr = None  # None is a sentinel, it keeps the same cursor
        self.env = self.env(cr, user, context, su)
        threading.current_thread().uid = self.env.uid

    def update_context(self, **overrides):
        """
        Override the environment context of the current request with the
        values of ``overrides``. To replace the entire context, please
        use :meth:`~update_env`: instead.
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

    @property
    def geoip(self):
        """
        Get the remote address geolocalisation.

        When geolocalization is successful, the return value is a
        dictionary whoose format is:

            {'city': str, 'country_code': str, 'country_name': str,
             'latitude': float, 'longitude': float, 'region': str,
             'time_zone': str}

        When geolocalization fails, an empty dict is returned.
        """
        if '_geoip' not in self.session:
            was_dirty = self.session.is_dirty
            self.session._geoip = (self.registry['ir.http']._geoip_resolve()
                                   if self.db else self._geoip_resolve())
            self.session.is_dirty = was_dirty
        return self.session._geoip

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
        lang = self.httprequest.accept_languages.best
        if not lang:
            return DEFAULT_LANG

        try:
            code, territory, _, _ = babel.core.parse_locale(lang, sep='-')
            if territory:
                lang = f'{code}_{territory}'
            else:
                lang = babel.core.LOCALE_ALIASES[code]
            return lang
        except (ValueError, KeyError):
            return DEFAULT_LANG

    def _geoip_resolve(self):
        if not (root.geoip_resolver and self.httprequest.remote_addr):
            return {}
        return root.geoip_resolver.resolve(self.httprequest.remote_addr) or {}

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
            elif self.httprequest.path.startswith('/longpolling'):
                _logger.debug("Profiling disabled for longpolling")
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
        :param collections.abc.Mapping cookies: cookies to set on the client
        """
        response = Response(data, headers=headers)
        if cookies:
            for k, v in cookies.items():
                response.set_cookie(k, v)
        return response

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

    def _save_session(self):
        """ Save a modified session on disk. """
        sess = self.session

        if not sess.can_save:
            return

        if sess.should_rotate:
            sess['_geoip'] = self.geoip
            root.session_store.rotate(sess, self.env)  # it saves
        elif sess.is_dirty:
            sess['_geoip'] = self.geoip
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
            return send_file(filepath)
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
            #  - the database version doesnt match the server version.
            # So remove the database from the cookie
            self.db = None
            self.session.db = None
            root.session_store.save(self.session)
            return self.redirect('/web/database/selector')

        with contextlib.closing(self.registry.cursor()) as cr:
            self.env = odoo.api.Environment(cr, self.session.uid, self.session.context)
            threading.current_thread().uid = self.env.uid
            try:
                return service_model.retrying(self._serve_ir_http, self.env)
            except Exception as exc:
                if isinstance(exc, HTTPException) and exc.code is None:
                    raise  # bubble up to odoo.http.Application.__call__
                if 'werkzeug' in config['dev_mode'] and self.dispatcher.routing_type != 'json':
                    raise  # bubble up to werkzeug.debug.DebuggedApplication
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
        ir_http._post_dispatch(response)
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

    @abstractmethod
    def dispatch(self, endpoint, args):
        """
        Extract the params from the request's body and call the
        endpoint. While it is prefered to override ir.http._pre_dispatch
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
    def handle_error(self, exc):
        """
        Transform the exception into a valid HTTP response. Called upon
        any exception while serving a request.
        """


class HttpDispatcher(Dispatcher):
    routing_type = 'http'

    @classmethod
    def is_compatible_with(cls, request):
        return request.httprequest.mimetype not in JSON_MIMETYPES

    def dispatch(self, endpoint, args):
        """
        Perform http-related actions such as deserializing the request
        body and query-string and checking cors/csrf while dispatching a
        request to a ``type='http'`` route.

        See :meth:`~odoo.http.Response.load`: method for the compatible
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

    def handle_error(self, exc):
        """
        Handle any exception that occurred while dispatching a request
        to a `type='http'` route. Also handle exceptions that occurred
        when no route matched the request path, when no fallback page
        could be delivered and that the request ``Content-Type`` was not
        json.

        :param exc Exception: the exception that occured.
        :returns: an HTTP error response
        :rtype: werkzeug.wrapper.Response
        """
        if isinstance(exc, SessionExpiredException):
            session = self.request.session
            session.logout(keep_db=True)
            response = self.request.redirect_query('/web/login', {'redirect': self.request.httprequest.full_path})
            if not session.is_explicit:
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

        Sucessful request::

          --> {"jsonrpc": "2.0", "method": "call", "params": {"context": {}, "arg1": "val1" }, "id": null}

          <-- {"jsonrpc": "2.0", "result": { "res1": "val1" }, "id": null}

        Request producing a error::

          --> {"jsonrpc": "2.0", "method": "call", "params": {"context": {}, "arg1": "val1" }, "id": null}

          <-- {"jsonrpc": "2.0", "error": {"code": 1, "message": "End user error message.", "data": {"code": "codestring", "debug": "traceback" } }, "id": null}

        """
        httprequest = self.request.httprequest
        body = httprequest.get_data().decode(httprequest.charset)
        try:
            self.jsonrequest = json.loads(body)
        except ValueError:
            _logger.info('%s: Invalid JSON data\n%s', httprequest.path,
                         body)
            raise werkzeug.exceptions.BadRequest(f"Invalid JSON data:\n{body}")

        self.request.params = dict(self.jsonrequest.get('params', {}), **args)
        ctx = self.request.params.pop('context', None)
        if ctx is not None and self.request.db:
            self.request.update_env(context=ctx)

        if self.request.db:
            result = self.request.registry['ir.http']._dispatch(endpoint)
        else:
            result = endpoint(**self.request.params)
        return self._response(result)

    def handle_error(self, exc):
        """
        Handle any exception that occured while dispatching a request to
        a `type='json'` route. Also handle exceptions that occured when
        no route matched the request path, that no fallback page could
        be delivered and that the request ``Content-Type`` was json.

        :param exc Exception: the exception that occured.
        :returns: an HTTP error response
        :rtype: Response
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
            error['http_status'] = 404
            error['code'] = 404
            error['message'] = "404: Not Found"
        elif isinstance(exc, SessionExpiredException):
            error['code'] = 100
            error['message'] = "Odoo Session Expired"

        return self._response(error=error)

    def _response(self, result=None, error=None):
        request_id = self.jsonrequest.get('id')
        status = 200
        response = {'jsonrpc': '2.0', 'id': request_id}
        if error is not None:
            response['error'] = error
            status = error.pop('http_status', 200)
        if result is not None:
            response['result'] = result

        body = json.dumps(response, default=date_utils.json_default)

        return Response(body, status=status, headers=[
            ('Content-Type', 'application/json'),
            ('Content-Length', len(body)),
        ])


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

    @lazy_property
    def geoip_resolver(self):
        try:
            return GeoIPResolver.open(config.get('geoip_database'))
        except Exception as e:
            _logger.warning('Cannot load GeoIP: %s', e)

    def get_db_router(self, db):
        if not db:
            return self.nodb_routing_map
        return request.registry['ir.http'].routing_map()

    def set_csp(self, response):
        headers = response.headers
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

        if odoo.tools.config['proxy_mode'] and environ.get("HTTP_X_FORWARDED_HOST"):
            # The ProxyFix middleware has a side effect of updating the
            # environ, see https://github.com/pallets/werkzeug/pull/2184
            def fake_app(environ, start_response):
                return []
            def fake_start_response(status, headers):
                return
            ProxyFix(fake_app)(environ, fake_start_response)

        # Some URLs in website are concatened, first url ends with /,
        # second url starts with /, resulting url contains two following
        # slashes that must be merged.
        if environ['REQUEST_METHOD'] == 'GET' and '//' in environ['PATH_INFO']:
            response = werkzeug.utils.redirect(
                environ['PATH_INFO'].replace('//', '/'), 301)
            return response(environ, start_response)

        httprequest = werkzeug.wrappers.Request(environ)
        httprequest.user_agent_class = UserAgent  # use vendored userAgent since it will be removed in 2.1
        httprequest.parameter_storage_class = (
            werkzeug.datastructures.ImmutableOrderedMultiDict)
        request = Request(httprequest)
        _request_stack.push(request)
        current_thread.url = httprequest.url

        try:
            segments = httprequest.path.split('/')
            if len(segments) >= 4 and segments[2] == 'static':
                with contextlib.suppress(NotFound):
                    response = request._serve_static()
                    return response(environ, start_response)

            if request.db:
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
            elif isinstance(exc, (UserError, AccessError, NotFound)):
                _logger.warning(exc)
            else:
                _logger.error("Exception during request handling.", exc_info=True)

            # Server is running with --dev=werkzeug, bubble the error up
            # to werkzeug so he can fire up a debugger.
            if 'werkzeug' in config['dev_mode'] and request.dispatcher.routing_type != 'json':
                raise

            # Ensure there is always a Response attached to the exception.
            if not hasattr(exc, 'error_response'):
                exc.error_response = request.dispatcher.handle_error(exc)

            return exc.error_response(environ, start_response)

        finally:
            _request_stack.pop()


root = Application()
