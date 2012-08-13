# -*- coding: utf-8 -*-
#----------------------------------------------------------
# OpenERP Web HTTP layer
#----------------------------------------------------------
import ast
import cgi
import contextlib
import functools
import logging
import os
import pprint
import sys
import threading
import time
import traceback
import urllib
import uuid
import xmlrpclib

import simplejson
import werkzeug.contrib.sessions
import werkzeug.datastructures
import werkzeug.exceptions
import werkzeug.utils
import werkzeug.wrappers
import werkzeug.wsgi

from . import nonliterals
from . import session
from . import openerplib
import urlparse

__all__ = ['Root', 'jsonrequest', 'httprequest', 'Controller',
           'WebRequest', 'JsonRequest', 'HttpRequest']

_logger = logging.getLogger(__name__)

#----------------------------------------------------------
# OpenERP Web RequestHandler
#----------------------------------------------------------
class WebRequest(object):
    """ Parent class for all OpenERP Web request types, mostly deals with
    initialization and setup of the request object (the dispatching itself has
    to be handled by the subclasses)

    :param request: a wrapped werkzeug Request object
    :type request: :class:`werkzeug.wrappers.BaseRequest`
    :param config: configuration object

    .. attribute:: httprequest

        the original :class:`werkzeug.wrappers.Request` object provided to the
        request

    .. attribute:: httpsession

        a :class:`~collections.Mapping` holding the HTTP session data for the
        current http session

    .. attribute:: config

        config parameter provided to the request object

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
    def __init__(self, request, config):
        self.httprequest = request
        self.httpresponse = None
        self.httpsession = request.session
        self.config = config

    def init(self, params):
        self.params = dict(params)
        # OpenERP session setup
        self.session_id = self.params.pop("session_id", None) or uuid.uuid4().hex
        self.session = self.httpsession.get(self.session_id)
        if not self.session:
            self.httpsession[self.session_id] = self.session = session.OpenERPSession()
        self.session.config = self.config
        self.context = self.params.pop('context', None)
        self.debug = self.params.pop('debug', False) != False

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
    def dispatch(self, controller, method):
        """ Calls the method asked for by the JSON-RPC2 or JSONP request

        :param controller: the instance of the controller which received the request
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
                self.jsonrequest = simplejson.load(requestf, object_hook=nonliterals.non_literal_decoder)
            else:
                self.jsonrequest = simplejson.loads(request, object_hook=nonliterals.non_literal_decoder)
            self.init(self.jsonrequest.get("params", {}))
            if _logger.isEnabledFor(logging.DEBUG):
                _logger.debug("--> %s.%s\n%s", controller.__class__.__name__, method.__name__, pprint.pformat(self.jsonrequest))
            response['id'] = self.jsonrequest.get('id')
            response["result"] = method(controller, self, **self.params)
        except openerplib.AuthenticationError:
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
            mime = 'application/javascript'
            body = "%s(%s);" % (jsonp, simplejson.dumps(response, cls=nonliterals.NonLiteralEncoder),)
        else:
            mime = 'application/json'
            body = simplejson.dumps(response, cls=nonliterals.NonLiteralEncoder)

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
    @functools.wraps(f)
    def json_handler(controller, request, config):
        return JsonRequest(request, config).dispatch(controller, f)
    json_handler.exposed = True
    return json_handler

class HttpRequest(WebRequest):
    """ Regular GET/POST request
    """
    def dispatch(self, controller, method):
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
        _logger.debug("%s --> %s.%s %r", self.httprequest.method, controller.__class__.__name__, method.__name__, akw)
        try:
            r = method(controller, self, **self.params)
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
    @functools.wraps(f)
    def http_handler(controller, request, config):
        return HttpRequest(request, config).dispatch(controller, f)
    http_handler.exposed = True
    return http_handler

#----------------------------------------------------------
# OpenERP Web Session context manager
#----------------------------------------------------------
STORES = {}

@contextlib.contextmanager
def session_context(request, storage_path, session_cookie='sessionid'):
    session_store, session_lock = STORES.get(storage_path, (None, None))
    if not session_store:
        session_store = werkzeug.contrib.sessions.FilesystemSessionStore( storage_path)
        session_lock = threading.Lock()
        STORES[storage_path] = session_store, session_lock

    sid = request.cookies.get(session_cookie)
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
                        v.contexts_store.update(stored.contexts_store)
                        v.domains_store.update(stored.domains_store)
                        if not hasattr(v, 'jsonp_requests'):
                            v.jsonp_requests = {}
                        v.jsonp_requests.update(getattr(
                            stored, 'jsonp_requests', {}))

                # add missing keys
                for k, v in in_store.iteritems():
                    if k not in request.session and k not in removed_sessions:
                        request.session[k] = v

            session_store.save(request.session)

#----------------------------------------------------------
# OpenERP Web Controller registration with a metaclass
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
# OpenERP Web WSGI Application
#----------------------------------------------------------

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

class Root(object):
    """Root WSGI application for the OpenERP Web Client.

    :param options: mandatory initialization options object, must provide
                    the following attributes:

                    ``server_host`` (``str``)
                      hostname of the OpenERP server to dispatch RPC to
                    ``server_port`` (``int``)
                      RPC port of the OpenERP server
                    ``serve_static`` (``bool | None``)
                      whether this application should serve the various
                      addons's static files
                    ``storage_path`` (``str``)
                      filesystem path where HTTP session data will be stored
                    ``dbfilter`` (``str``)
                      only used in case the list of databases is requested
                      by the server, will be filtered by this pattern
    """
    def __init__(self, options, openerp_addons_namespace=True):
        self.config = options

        if not hasattr(self.config, 'connector'):
            if self.config.backend == 'local':
                self.config.connector = LocalConnector()
            else:
                self.config.connector = openerplib.get_connector(
                    hostname=self.config.server_host, port=self.config.server_port)

        self.httpsession_cookie = 'httpsessionid'
        self.addons = {}

        static_dirs = self._load_addons(openerp_addons_namespace)
        if options.serve_static:
            app = werkzeug.wsgi.SharedDataMiddleware( self.dispatch, static_dirs)
            self.dispatch = DisableCacheMiddleware(app)

        if options.session_storage:
            if not os.path.exists(options.session_storage):
                os.mkdir(options.session_storage, 0700)
            self.session_storage = options.session_storage
        _logger.debug('HTTP sessions stored in: %s', self.session_storage)

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
            with session_context(request, self.session_storage, self.httpsession_cookie) as session:
                result = handler( request, self.config)

                if isinstance(result, basestring):
                    headers=[('Content-Type', 'text/html; charset=utf-8'), ('Content-Length', len(result))]
                    response = werkzeug.wrappers.Response(result, headers=headers)
                else:
                    response = result

                if hasattr(response, 'set_cookie'):
                    response.set_cookie(self.httpsession_cookie, session.sid)

        return response(environ, start_response)

    def _load_addons(self, openerp_addons_namespace=True):
        """
        Loads all addons at the specified addons path, returns a mapping of
        static URLs to the corresponding directories
        """
        statics = {}
        for addons_path in self.config.addons_path:
            for module in os.listdir(addons_path):
                if module not in addons_module:
                    manifest_path = os.path.join(addons_path, module, '__openerp__.py')
                    path_static = os.path.join(addons_path, module, 'static')
                    if os.path.isfile(manifest_path) and os.path.isdir(path_static):
                        manifest = ast.literal_eval(open(manifest_path).read())
                        manifest['addons_path'] = addons_path
                        _logger.debug("Loading %s", module)
                        if openerp_addons_namespace:
                            m = __import__('openerp.addons.' + module)
                        else:
                            m = __import__(module)
                        addons_module[module] = m
                        addons_manifest[module] = manifest
                        statics['/%s/static' % module] = path_static
        for k, v in controllers_class:
            if k not in controllers_object:
                o = v()
                controllers_object[k] = o
                if hasattr(o, '_cp_path'):
                    controllers_path[o._cp_path] = o
        return statics

    def find_handler(self, *l):
        """
        Tries to discover the controller handling the request for the path
        specified by the provided parameters

        :param l: path sections to a controller or controller method
        :returns: a callable matching the path sections, or ``None``
        :rtype: ``Controller | None``
        """
        if l:
            ps = '/' + '/'.join(l)
            meth = 'index'
            while ps:
                c = controllers_path.get(ps)
                if c:
                    m = getattr(c, meth)
                    if getattr(m, 'exposed', False):
                        _logger.debug("Dispatching to %s %s %s", ps, c, meth)
                        return m
                ps, _slash, meth = ps.rpartition('/')
                if not ps and meth:
                    ps = '/'
        return None

#----------------------------------------------------------
# OpenERP Web Client lib
#----------------------------------------------------------

class LibException(Exception):
    """ Base of all client lib exceptions """
    def __init__(self,code=None,message=None):
        self.code = code
        self.message = message

class ApplicationError(LibException):
    """ maps to code: 1, server side: Exception or openerp.exceptions.DeferredException"""

class Warning(LibException):
    """ maps to code: 2, server side: openerp.exceptions.Warning"""

class AccessError(LibException):
    """ maps to code: 3, server side:  openerp.exceptions.AccessError"""

class AccessDenied(LibException):
    """ maps to code: 4, server side: openerp.exceptions.AccessDenied"""

class LocalConnector(openerplib.Connector):
    """
    A type of connector that uses the XMLRPC protocol.
    """
    PROTOCOL = 'local'

    def __init__(self):
        pass

    def send(self, service_name, method, *args):
        import openerp
        import traceback
        import xmlrpclib
        code_string = "warning -- %s\n\n%s"
        try:
            return openerp.netsvc.dispatch_rpc(service_name, method, args)
        except openerp.osv.osv.except_osv, e:
        # TODO change the except to raise LibException instead of their emulated xmlrpc fault
            raise xmlrpclib.Fault(code_string % (e.name, e.value), '')
        except openerp.exceptions.Warning, e:
            raise xmlrpclib.Fault(code_string % ("Warning", e), '')
        except openerp.exceptions.AccessError, e:
            raise xmlrpclib.Fault(code_string % ("AccessError", e), '')
        except openerp.exceptions.AccessDenied, e:
            raise xmlrpclib.Fault('AccessDenied', str(e))
        except openerp.exceptions.DeferredException, e:
            formatted_info = "".join(traceback.format_exception(*e.traceback))
            raise xmlrpclib.Fault(openerp.tools.ustr(e.message), formatted_info)
        except Exception, e:
            formatted_info = "".join(traceback.format_exception(*(sys.exc_info())))
            raise xmlrpclib.Fault(openerp.tools.exception_to_unicode(e), formatted_info)

# vim:et:
