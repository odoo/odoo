#!/usr/bin/python
from __future__ import with_statement

import functools
import logging
import os
import pprint
import sys
import traceback
import uuid
import xmlrpclib

import simplejson
import werkzeug.datastructures
import werkzeug.exceptions
import werkzeug.urls
import werkzeug.utils
import werkzeug.wrappers
import werkzeug.wsgi

import ast
import nonliterals
import http
# import backendlocal as backend
import session as backend
import openerplib

__all__ = ['Root', 'jsonrequest', 'httprequest', 'Controller',
           'WebRequest', 'JsonRequest', 'HttpRequest']

_logger = logging.getLogger(__name__)

#-----------------------------------------------------------
# Globals (wont move into a pool)
#-----------------------------------------------------------

applicationsession = {}
addons_module = {}
addons_manifest = {}
controllers_class = {}
controllers_object = {}
controllers_path = {}

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

    .. attribute:: applicationsession

        an application-wide :class:`~collections.Mapping`

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

        opaque identifier for the :class:`backend.OpenERPSession` instance of
        the current request

    .. attribute:: session

        :class:`~backend.OpenERPSession` instance for the current request

    .. attribute:: context

        :class:`~collections.Mapping` of context values for the current request

    .. attribute:: debug

        ``bool``, indicates whether the debug mode is active on the client
    """
    def __init__(self, request, config):
        self.applicationsession = applicationsession
        self.httprequest = request
        self.httpresponse = None
        self.httpsession = request.session
        self.config = config
    def init(self, params):
        self.params = dict(params)
        # OpenERP session setup
        self.session_id = self.params.pop("session_id", None) or uuid.uuid4().hex
        self.session = self.httpsession.setdefault(
            self.session_id, backend.OpenERPSession(
                self.config.server_host, self.config.server_port))
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

    def dispatch(self, controller, method, requestf=None, request=None):
        """ Calls the method asked for by the JSON-RPC2 request

        :param controller: the instance of the controller which received the request
        :param method: the method which received the request
        :param requestf: a file-like object containing an encoded JSON-RPC2 request
        :param request: a JSON-RPC2 request

        :returns: an utf8 encoded JSON-RPC2 reply
        """
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
        except openerplib.AuthentificationError:
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
        content = simplejson.dumps(response, cls=nonliterals.NonLiteralEncoder)
        return werkzeug.wrappers.Response(
            content, headers=[('Content-Type', 'application/json'),
                              ('Content-Length', len(content))])

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
        return JsonRequest(request, config).dispatch(
            controller, f, requestf=request.stream)
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
        r = method(controller, self, **self.params)
        if self.debug or 1:
            if isinstance(r, werkzeug.wrappers.BaseResponse):
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

class ControllerType(type):
    def __init__(cls, name, bases, attrs):
        super(ControllerType, cls).__init__(name, bases, attrs)
        controllers_class["%s.%s" % (cls.__module__, cls.__name__)] = cls

class Controller(object):
    __metaclass__ = ControllerType

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
    def __init__(self, options):
        self.root = werkzeug.urls.Href('/web/webclient/home')
        self.config = options

        self.session_cookie = 'sessionid'
        self.addons = {}

        static_dirs = self._load_addons()
        if options.serve_static:
            self.dispatch = werkzeug.wsgi.SharedDataMiddleware(
                self.dispatch, static_dirs)

        if options.session_storage:
            if not os.path.exists(options.session_storage):
                os.mkdir(options.session_storage, 0700)
            self.session_storage = options.session_storage

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

        if request.path == '/':
            return werkzeug.utils.redirect(
                self.root(dict(request.args, debug='')), 301)(
                    environ, start_response)
        elif request.path == '/mobile':
            return werkzeug.utils.redirect(
                '/web_mobile/static/src/web_mobile.html', 301)(
                environ, start_response)

        handler = self.find_handler(*(request.path.split('/')[1:]))

        if not handler:
            response = werkzeug.exceptions.NotFound()
        else:
            with http.session(request, self.session_storage, self.session_cookie) as session:
                result = handler(
                    request, self.config)

                if isinstance(result, basestring):
                    response = werkzeug.wrappers.Response(
                        result, headers=[('Content-Type', 'text/html; charset=utf-8'),
                                         ('Content-Length', len(result))])
                else:
                    response = result

                response.set_cookie(self.session_cookie, session.sid)

        return response(environ, start_response)

    def _load_addons(self):
        """
        Loads all addons at the specified addons path, returns a mapping of
        static URLs to the corresponding directories
        """
        statics = {}
        addons_path = self.config.addons_path
        if addons_path not in sys.path:
            sys.path.insert(0, addons_path)
        for module in os.listdir(addons_path):
            if module not in addons_module:
                manifest_path = os.path.join(addons_path, module, '__openerp__.py')
                if os.path.isfile(manifest_path):
                    manifest = ast.literal_eval(open(manifest_path).read())
                    _logger.info("Loading %s", module)
                    m = __import__(module)
                    addons_module[module] = m
                    addons_manifest[module] = manifest

                    statics['/%s/static' % module] = \
                        os.path.join(addons_path, module, 'static')
        for k, v in controllers_class.items():
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
        if len(l) > 1:
            for i in range(len(l), 1, -1):
                ps = "/" + "/".join(l[0:i])
                if ps in controllers_path:
                    c = controllers_path[ps]
                    rest = l[i:] or ['index']
                    meth = rest[0]
                    m = getattr(c, meth)
                    if getattr(m, 'exposed', False):
                        _logger.debug("Dispatching to %s %s %s", ps, c, meth)
                        return m
        return None
