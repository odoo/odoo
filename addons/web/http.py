# -*- coding: utf-8 -*-
#----------------------------------------------------------
# OpenERP Web HTTP layer
#----------------------------------------------------------
import ast
import cgi
import contextlib
import functools
import getpass
import logging
import mimetypes
import os
import pprint
import random
import sys
import tempfile
import threading
import time
import traceback
import urlparse
import uuid
import xmlrpclib

import babel.core
import simplejson
import werkzeug.contrib.sessions
import werkzeug.datastructures
import werkzeug.exceptions
import werkzeug.utils
import werkzeug.wrappers
import werkzeug.wsgi

import openerp

import session

_logger = logging.getLogger(__name__)

#----------------------------------------------------------
# RequestHandler
#----------------------------------------------------------
class WebRequest(object):
    """ Parent class for all OpenERP Web request types, mostly deals with
    initialization and setup of the request object (the dispatching itself has
    to be handled by the subclasses)

    :param request: a wrapped werkzeug Request object
    :type request: :class:`werkzeug.wrappers.BaseRequest`

    .. attribute:: httprequest

        the original :class:`werkzeug.wrappers.Request` object provided to the
        request

    .. attribute:: httpsession

        a :class:`~collections.Mapping` holding the HTTP session data for the
        current http session

    .. attribute:: params

        :class:`~collections.Mapping` of request parameters, not generally
        useful as they're provided directly to the handler method as keyword
        arguments

    .. attribute:: session_id

        opaque identifier for the :class:`session.OpenERPSession` instance of
        the current request

    .. attribute:: session

        :class:`~session.OpenERPSession` instance for the current request

    .. attribute:: context

        :class:`~collections.Mapping` of context values for the current request

    .. attribute:: debug

        ``bool``, indicates whether the debug mode is active on the client
    """
    def __init__(self, request):
        self.httprequest = request
        self.httpresponse = None
        self.httpsession = request.session

    def init(self, params):
        self.params = dict(params)
        # OpenERP session setup
        self.session_id = self.params.pop("session_id", None) or uuid.uuid4().hex
        self.session = self.httpsession.get(self.session_id)
        if not self.session:
            self.session = session.OpenERPSession()
            self.httpsession[self.session_id] = self.session

        # set db/uid trackers - they're cleaned up at the WSGI
        # dispatching phase in openerp.service.wsgi_server.application
        if self.session._db:
            threading.current_thread().dbname = self.session._db
        if self.session._uid:
            threading.current_thread().uid = self.session._uid

        self.context = self.params.pop('context', {})
        self.debug = self.params.pop('debug', False) is not False
        # Determine self.lang
        lang = self.params.get('lang', None)
        if lang is None:
            lang = self.context.get('lang')
        if lang is None:
            lang = self.httprequest.cookies.get('lang')
        if lang is None:
            lang = self.httprequest.accept_languages.best
        if not lang:
            lang = 'en_US'
        # tranform 2 letters lang like 'en' into 5 letters like 'en_US'
        lang = babel.core.LOCALE_ALIASES.get(lang, lang)
        # we use _ as seprator where RFC2616 uses '-'
        self.lang = lang.replace('-', '_')

def reject_nonliteral(dct):
    if '__ref' in dct:
        raise ValueError(
            "Non literal contexts can not be sent to the server anymore (%r)" % (dct,))
    return dct

class JsonRequest(WebRequest):
    """ JSON-RPC2 over HTTP.

    Sucessful request::

      --> {"jsonrpc": "2.0",
           "method": "call",
           "params": {"session_id": "SID",
                      "context": {},
                      "arg1": "val1" },
           "id": null}

      <-- {"jsonrpc": "2.0",
           "result": { "res1": "val1" },
           "id": null}

    Request producing a error::

      --> {"jsonrpc": "2.0",
           "method": "call",
           "params": {"session_id": "SID",
                      "context": {},
                      "arg1": "val1" },
           "id": null}

      <-- {"jsonrpc": "2.0",
           "error": {"code": 1,
                     "message": "End user error message.",
                     "data": {"code": "codestring",
                              "debug": "traceback" } },
           "id": null}

    """
    def dispatch(self, method):
        """ Calls the method asked for by the JSON-RPC2 or JSONP request

        :param method: the method which received the request

        :returns: an utf8 encoded JSON-RPC2 or JSONP reply
        """
        args = self.httprequest.args
        jsonp = args.get('jsonp')
        requestf = None
        request = None
        request_id = args.get('id')

        if jsonp and self.httprequest.method == 'POST':
            # jsonp 2 steps step1 POST: save call
            self.init(args)
            self.session.jsonp_requests[request_id] = self.httprequest.form['r']
            headers=[('Content-Type', 'text/plain; charset=utf-8')]
            r = werkzeug.wrappers.Response(request_id, headers=headers)
            return r
        elif jsonp and args.get('r'):
            # jsonp method GET
            request = args.get('r')
        elif jsonp and request_id:
            # jsonp 2 steps step2 GET: run and return result
            self.init(args)
            request = self.session.jsonp_requests.pop(request_id, "")
        else:
            # regular jsonrpc2
            requestf = self.httprequest.stream

        response = {"jsonrpc": "2.0" }
        error = None
        try:
            # Read POST content or POST Form Data named "request"
            if requestf:
                self.jsonrequest = simplejson.load(requestf, object_hook=reject_nonliteral)
            else:
                self.jsonrequest = simplejson.loads(request, object_hook=reject_nonliteral)
            self.init(self.jsonrequest.get("params", {}))
            if _logger.isEnabledFor(logging.DEBUG):
                _logger.debug("--> %s.%s\n%s", method.im_class.__name__, method.__name__, pprint.pformat(self.jsonrequest))
            response['id'] = self.jsonrequest.get('id')
            response["result"] = method(self, **self.params)
        except session.AuthenticationError:
            error = {
                'code': 100,
                'message': "OpenERP Session Invalid",
                'data': {
                    'type': 'session_invalid',
                    'debug': traceback.format_exc()
                }
            }
        except xmlrpclib.Fault, e:
            error = {
                'code': 200,
                'message': "OpenERP Server Error",
                'data': {
                    'type': 'server_exception',
                    'fault_code': e.faultCode,
                    'debug': "Client %s\nServer %s" % (
                    "".join(traceback.format_exception("", None, sys.exc_traceback)), e.faultString)
                }
            }
        except Exception:
            logging.getLogger(__name__ + '.JSONRequest.dispatch').exception\
                ("An error occured while handling a json request")
            error = {
                'code': 300,
                'message': "OpenERP WebClient Error",
                'data': {
                    'type': 'client_exception',
                    'debug': "Client %s" % traceback.format_exc()
                }
            }
        if error:
            response["error"] = error

        if _logger.isEnabledFor(logging.DEBUG):
            _logger.debug("<--\n%s", pprint.pformat(response))

        if jsonp:
            # If we use jsonp, that's mean we are called from another host
            # Some browser (IE and Safari) do no allow third party cookies
            # We need then to manage http sessions manually.
            response['httpsessionid'] = self.httpsession.sid
            mime = 'application/javascript'
            body = "%s(%s);" % (jsonp, simplejson.dumps(response),)
        else:
            mime = 'application/json'
            body = simplejson.dumps(response)

        r = werkzeug.wrappers.Response(body, headers=[('Content-Type', mime), ('Content-Length', len(body))])
        return r

def jsonrequest(f):
    """ Decorator marking the decorated method as being a handler for a
    JSON-RPC request (the exact request path is specified via the
    ``$(Controller._cp_path)/$methodname`` combination.

    If the method is called, it will be provided with a :class:`JsonRequest`
    instance and all ``params`` sent during the JSON-RPC request, apart from
    the ``session_id``, ``context`` and ``debug`` keys (which are stripped out
    beforehand)
    """
    f.exposed = 'json'
    return f

class HttpRequest(WebRequest):
    """ Regular GET/POST request
    """
    def dispatch(self, method):
        params = dict(self.httprequest.args)
        params.update(self.httprequest.form)
        params.update(self.httprequest.files)
        self.init(params)
        akw = {}
        for key, value in self.httprequest.args.iteritems():
            if isinstance(value, basestring) and len(value) < 1024:
                akw[key] = value
            else:
                akw[key] = type(value)
        _logger.debug("%s --> %s.%s %r", self.httprequest.method, method.im_class.__name__, method.__name__, akw)
        try:
            r = method(self, **self.params)
        except xmlrpclib.Fault, e:
            r = werkzeug.exceptions.InternalServerError(cgi.escape(simplejson.dumps({
                'code': 200,
                'message': "OpenERP Server Error",
                'data': {
                    'type': 'server_exception',
                    'fault_code': e.faultCode,
                    'debug': "Server %s\nClient %s" % (
                        e.faultString, traceback.format_exc())
                }
            })))
        except Exception:
            logging.getLogger(__name__ + '.HttpRequest.dispatch').exception(
                    "An error occurred while handling a json request")
            r = werkzeug.exceptions.InternalServerError(cgi.escape(simplejson.dumps({
                'code': 300,
                'message': "OpenERP WebClient Error",
                'data': {
                    'type': 'client_exception',
                    'debug': "Client %s" % traceback.format_exc()
                }
            })))
        if self.debug or 1:
            if isinstance(r, (werkzeug.wrappers.BaseResponse, werkzeug.exceptions.HTTPException)):
                _logger.debug('<-- %s', r)
            else:
                _logger.debug("<-- size: %s", len(r))
        return r

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
        response = werkzeug.wrappers.Response(data, headers=headers)
        if cookies:
            for k, v in cookies.iteritems():
                response.set_cookie(k, v)
        return response

    def not_found(self, description=None):
        """ Helper for 404 response, return its result from the method
        """
        return werkzeug.exceptions.NotFound(description)

def httprequest(f):
    """ Decorator marking the decorated method as being a handler for a
    normal HTTP request (the exact request path is specified via the
    ``$(Controller._cp_path)/$methodname`` combination.

    If the method is called, it will be provided with a :class:`HttpRequest`
    instance and all ``params`` sent during the request (``GET`` and ``POST``
    merged in the same dictionary), apart from the ``session_id``, ``context``
    and ``debug`` keys (which are stripped out beforehand)
    """
    f.exposed = 'http'
    return f

#----------------------------------------------------------
# Controller registration with a metaclass
#----------------------------------------------------------
addons_module = {}
addons_manifest = {}
controllers_class = []
controllers_object = {}
controllers_path = {}

class ControllerType(type):
    def __init__(cls, name, bases, attrs):
        super(ControllerType, cls).__init__(name, bases, attrs)
        controllers_class.append(("%s.%s" % (cls.__module__, cls.__name__), cls))

class Controller(object):
    __metaclass__ = ControllerType

#----------------------------------------------------------
# Session context manager
#----------------------------------------------------------
@contextlib.contextmanager
def session_context(request, session_store, session_lock, sid):
    with session_lock:
        if sid:
            request.session = session_store.get(sid)
        else:
            request.session = session_store.new()
    try:
        yield request.session
    finally:
        # Remove all OpenERPSession instances with no uid, they're generated
        # either by login process or by HTTP requests without an OpenERP
        # session id, and are generally noise
        removed_sessions = set()
        for key, value in request.session.items():
            if not isinstance(value, session.OpenERPSession):
                continue
            if getattr(value, '_suicide', False) or (
                        not value._uid
                    and not value.jsonp_requests
                    # FIXME do not use a fixed value
                    and value._creation_time + (60*5) < time.time()):
                _logger.debug('remove session %s', key)
                removed_sessions.add(key)
                del request.session[key]

        with session_lock:
            if sid:
                # Re-load sessions from storage and merge non-literal
                # contexts and domains (they're indexed by hash of the
                # content so conflicts should auto-resolve), otherwise if
                # two requests alter those concurrently the last to finish
                # will overwrite the previous one, leading to loss of data
                # (a non-literal is lost even though it was sent to the
                # client and client errors)
                #
                # note that domains_store and contexts_store are append-only (we
                # only ever add items to them), so we can just update one with the
                # other to get the right result, if we want to merge the
                # ``context`` dict we'll need something smarter
                in_store = session_store.get(sid)
                for k, v in request.session.iteritems():
                    stored = in_store.get(k)
                    if stored and isinstance(v, session.OpenERPSession):
                        if hasattr(v, 'contexts_store'):
                            del v.contexts_store
                        if hasattr(v, 'domains_store'):
                            del v.domains_store
                        if not hasattr(v, 'jsonp_requests'):
                            v.jsonp_requests = {}
                        v.jsonp_requests.update(getattr(
                            stored, 'jsonp_requests', {}))

                # add missing keys
                for k, v in in_store.iteritems():
                    if k not in request.session and k not in removed_sessions:
                        request.session[k] = v

            session_store.save(request.session)

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
# WSGI Application
#----------------------------------------------------------
# Add potentially missing (older ubuntu) font mime types
mimetypes.add_type('application/font-woff', '.woff')
mimetypes.add_type('application/vnd.ms-fontobject', '.eot')
mimetypes.add_type('application/x-font-ttf', '.ttf')

class DisableCacheMiddleware(object):
    def __init__(self, app):
        self.app = app
    def __call__(self, environ, start_response):
        def start_wrapped(status, headers):
            referer = environ.get('HTTP_REFERER', '')
            parsed = urlparse.urlparse(referer)
            debug = parsed.query.count('debug') >= 1

            new_headers = []
            unwanted_keys = ['Last-Modified']
            if debug:
                new_headers = [('Cache-Control', 'no-cache')]
                unwanted_keys += ['Expires', 'Etag', 'Cache-Control']

            for k, v in headers:
                if k not in unwanted_keys:
                    new_headers.append((k, v))

            start_response(status, new_headers)
        return self.app(environ, start_wrapped)

def session_path():
    try:
        username = getpass.getuser()
    except Exception:
        username = "unknown"
    path = os.path.join(tempfile.gettempdir(), "oe-sessions-" + username)
    if not os.path.exists(path):
        os.mkdir(path, 0700)
    return path

class Root(object):
    """Root WSGI application for the OpenERP Web Client.
    """
    def __init__(self):
        self.addons = {}
        self.statics = {}

        self.load_addons()

        # Setup http sessions
        path = session_path()
        self.session_store = werkzeug.contrib.sessions.FilesystemSessionStore(path)
        self.session_lock = threading.Lock()
        _logger.debug('HTTP sessions stored in: %s', path)

    def __call__(self, environ, start_response):
        """ Handle a WSGI request
        """
        return self.dispatch(environ, start_response)

    def dispatch(self, environ, start_response):
        """
        Performs the actual WSGI dispatching for the application, may be
        wrapped during the initialization of the object.

        Call the object directly.
        """
        request = werkzeug.wrappers.Request(environ)
        request.parameter_storage_class = werkzeug.datastructures.ImmutableDict
        request.app = self

        handler = self.find_handler(*(request.path.split('/')[1:]))

        if not handler:
            response = werkzeug.exceptions.NotFound()
        else:
            sid = request.cookies.get('sid')
            if not sid:
                sid = request.args.get('sid')

            session_gc(self.session_store)

            with session_context(request, self.session_store, self.session_lock, sid) as session:
                result = handler(request)

                if isinstance(result, basestring):
                    headers=[('Content-Type', 'text/html; charset=utf-8'), ('Content-Length', len(result))]
                    response = werkzeug.wrappers.Response(result, headers=headers)
                else:
                    response = result

                if hasattr(response, 'set_cookie'):
                    response.set_cookie('sid', session.sid)

        return response(environ, start_response)

    def load_addons(self):
        """ Load all addons from addons patch containg static files and
        controllers and configure them.  """

        for addons_path in openerp.modules.module.ad_paths:
            for module in sorted(os.listdir(addons_path)):
                if module not in addons_module:
                    manifest_path = os.path.join(addons_path, module, '__openerp__.py')
                    path_static = os.path.join(addons_path, module, 'static')
                    if os.path.isfile(manifest_path) and os.path.isdir(path_static):
                        manifest = ast.literal_eval(open(manifest_path).read())
                        manifest['addons_path'] = addons_path
                        _logger.debug("Loading %s", module)
                        if 'openerp.addons' in sys.modules:
                            m = __import__('openerp.addons.' + module)
                        else:
                            m = __import__(module)
                        addons_module[module] = m
                        addons_manifest[module] = manifest
                        self.statics['/%s/static' % module] = path_static

        for k, v in controllers_class:
            if k not in controllers_object:
                o = v()
                controllers_object[k] = o
                if hasattr(o, '_cp_path'):
                    controllers_path[o._cp_path] = o

        app = werkzeug.wsgi.SharedDataMiddleware(self.dispatch, self.statics)
        self.dispatch = DisableCacheMiddleware(app)

    def find_handler(self, *l):
        """
        Tries to discover the controller handling the request for the path
        specified by the provided parameters

        :param l: path sections to a controller or controller method
        :returns: a callable matching the path sections, or ``None``
        :rtype: ``Controller | None``
        """
        if l:
            ps = '/' + '/'.join(filter(None, l))
            method_name = 'index'
            while ps:
                c = controllers_path.get(ps)
                if c:
                    method = getattr(c, method_name, None)
                    if method:
                        exposed = getattr(method, 'exposed', False)
                        if exposed == 'json':
                            _logger.debug("Dispatch json to %s %s %s", ps, c, method_name)
                            return lambda request: JsonRequest(request).dispatch(method)
                        elif exposed == 'http':
                            _logger.debug("Dispatch http to %s %s %s", ps, c, method_name)
                            return lambda request: HttpRequest(request).dispatch(method)
                ps, _slash, method_name = ps.rpartition('/')
                if not ps and method_name:
                    ps = '/'
        return None

def wsgi_postload():
    openerp.wsgi.register_wsgi_handler(Root())

# vim:et:ts=4:sw=4:
