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
from .tools.func import filter_kwargs, lazy_property
from .tools.mimetypes import guess_mimetype
from .tools._vendor import sessions


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

# The default lang to use when the browser doesn't specify it
DEFAULT_LANG = 'en_US'

# The dictionnary to initialise a new session with.
DEFAULT_SESSION = {
    'context': {
        #'lang': request.default_lang()  # must be set at runtime
    },
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

...

# The @route arguments to propagate from the decorated method to the
# routing rule.
ROUTING_KEYS = {
    'defaults', 'subdomain', 'build_only', 'strict_slashes', 'redirect_to',
    'alias', 'host', 'methods',
}

...

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

...

def db_list(force=False, host=None):
    """
    Get the list of available databases.

    :param bool force: See :func:`~odoo.service.db.list_dbs`:
    :param host: The Host used to replace %h and %d in the dbfilters
        regexp. Taken from the current request when omitted.
    :returns: the list of available databases
    :rtype: List[str]
    """
    dbs = odoo.service.db.list_dbs(force)
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

...

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

...


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
           modules. There request code will not have any facilities to
           access the current user.
    :param Iterable[str] methods: A list of http methods (verbs) this
        route applies to. If not specified, all methods are allowed.
    :param str cors: The Access-Control-Allow-Origin cors directive value.
    :param bool csrf: Whether CSRF protection should be enabled for the
        route. Enabled by default for ``'http'``-type requests, disabled
        by default for ``'json'``-type requests. See
        :ref:`CSRF Protection <csrf>` for more.
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
            ...
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
        highest_controllers = []
        for module in modules:
            highest_controllers.extend(Controller.children_classes.get(module, []))

        for top_ctrl in highest_controllers:
            leaf_controllers = list(unique(get_leaf_classes(top_ctrl)))
            name = '{} (extended by {})'.format(
                top_ctrl.__name__,
                ', '.join(bot_ctrl.__name__ for bot_ctrl in leaf_controllers),
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


class Session(dict):
    """ Structure containing data persisted across requests. """
    __slots__ = ('can_save', 'is_explicit', 'json_data', 'new', 'should_rotate', 'sid')

    def __init__(self, data, sid, new=False):
        super().__init__(data)
        object.__setattr__(self, 'can_save', True)
        object.__setattr__(self, 'is_explicit', False)
        object.__setattr__(self, 'json_data', json.dumps(data))
        object.__setattr__(self, 'new', new)
        object.__setattr__(self, 'should_rotate', False)
        object.__setattr__(self, 'sid', sid)

    def __getattr__(self, attr):
        return self.get(attr, None)

    def __setattr__(self, key, val):
        if key in self.__slots__:
            object.__setattr__(self, key, val)
        else:
            self[key] = val

    ...

    def logout(self, keep_db=False):
        db = self.db if keep_db else DEFAULT_SESSION['db']  # None
        debug = self.debug
        self.clear()
        self.update(DEFAULT_SESSION, db=db, debug=debug)
        self.context['lang'] = request.default_lang() if request else DEFAULT_LANG
        self.should_rotate = True


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
    """
    ...


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
        ...

        self.session = self._get_session()
        self.db = self._get_dbname()
        self.registry = None
        self.env = None

        if self.session.db != self.db:
            if self.session.db:
                _logger.warning("Logged into database %r, but dbfilter rejects it; logging session out.", self.session.db)
                self.session.logout(keep_db=False)
            self.session.db = self.db

    def _get_session(self):
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

        session.is_explicit = is_explicit
        for key, val in DEFAULT_SESSION.items():
            session.setdefault(key, val)
        if not session.context.get('lang'):
            session.context['lang'] = self.default_lang()

        return session

    def _get_dbname(self):
        if self.session.db and db_filter([self.session.db], host=self.httprequest.environ['HTTP_HOST']):
            return self.session.db

        # monodb
        all_dbs = db_list(force=True, host=self.httprequest.environ['HTTP_HOST'])
        if len(all_dbs) == 1:
            return all_dbs[0]

        # nodb
        return None

    # =====================================================
    # Getters and setters
    # =====================================================
    ...

    # =====================================================
    # Helpers
    # =====================================================
    ...

    def default_lang(self):
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

    ...

    def _inject_future_response(self, response):
        response.headers.extend(self.future_response.headers)
        return response

    ...

    def _save_session(self):
        """ Save a modified session on disk. """
        if not self.session.can_save:
            return

        if self.session.should_rotate:
            root.session_store.rotate(self.session, self.env)  # it saves
        elif json.dumps(self.session) != self.session.json_data:
            root.session_store.save(self.session)

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
        if (cookie_sid != self.session.sid and not self.session.is_explicit):
            self.future_response.set_cookie('session_id', self.session.sid, max_age=SESSION_LIFETIME, httponly=True)

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
        ...


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
    ...


class JsonRPCDispatcher(Dispatcher):
    routing_type = 'json'
    ...


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
        ...

        httprequest = werkzeug.wrappers.Request(environ)
        ...
        request = Request(httprequest)
        _request_stack.push(request)
        ...

        try:
            segments = httprequest.path.split('/')
            if len(segments) >= 4 and segments[2] == 'static':
                with contextlib.suppress(NotFound):
                    response = request._serve_static()
                    return response(environ, start_response)

            if request.db:
                ...
                response = request._serve_db()
            else:
                response = request._serve_nodb()
            return response(environ, start_response)

        except Exception as exc:
            ...

        finally:
            _request_stack.pop()


root = Application()
