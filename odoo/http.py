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

...


# The cache duration for static content from the filesystem, one week.
STATIC_CACHE = 60 * 60 * 24 * 7

# The cache duration for content where the url uniquely identifies the
# content (usually using a hash), one year.
STATIC_CACHE_LONG = 60 * 60 * 24 * 365

# =========================================================
# Helpers
# =========================================================

...

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
    """


def route(route=None, **routing):
    """
    Decorate a controller method in order to route incoming requests
    matching the given URL and options to the decorated method.
    """

def _generate_routing_rules(modules, nodb_only, converters=None):
    """
    Two-fold algorithm used to (1) determine which method in the
    controller inheritance tree should bind to what URL with respect to
    the list of installed modules and (2) merge the various @route
    arguments of said method with the @route arguments of the method it
    overrides.
    """
    ...


# =========================================================
# Session
# =========================================================

class FilesystemSessionStore(sessions.FilesystemSessionStore):
    """ Place where to load and save session objects. """


class Session(sessions.Session):
    """ Structure containing data persisted across requests. """


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
    ...


class Request:
    """
    Wrapper around the incomming HTTP request with deserialized request
    parameters, session utilities and request dispatching logic.
    """

    def __init__(self, httprequest):
        self.httprequest = httprequest
        ...

    ...

    # =====================================================
    # Getters and setters
    # =====================================================
    ...

    # =====================================================
    # Helpers
    # =====================================================
    ...

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
        ...

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

    ...


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

            ...

        except Exception as exc:
            ...

        finally:
            _request_stack.pop()


root = Application()
