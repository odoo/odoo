#!/usr/bin/python
from __future__ import with_statement

import functools
import logging
import os
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
import backendrpc as backend

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
    def __init__(self, request, config):
        self.applicationsession = applicationsession
        self.httprequest = request
        self.httpresponse = None
        self.httpsession = request.session
        self.config = config
        # Request attributes
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
            if self.debug or 1:
                print "--> %s.%s %s" % (controller.__class__.__name__, method.__name__, self.jsonrequest)
            response['id'] = self.jsonrequest.get('id')
            response["result"] = method(controller, self, **self.params)
        except backend.OpenERPUnboundException:
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
            logging.getLogger('openerp.JSONRequest.dispatch').exception\
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

        if self.debug or 1:
            print "<--", response
            print

        content = simplejson.dumps(response, cls=nonliterals.NonLiteralEncoder)
        return werkzeug.wrappers.Response(
            content, headers=[('Content-Type', 'application/json'),
                              ('Content-Length', len(content))])

def jsonrequest(f):
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
        self.init(self.httprequest.args)
        akw = {}
        for key, value in self.httprequest.args.iteritems():
            if isinstance(value, basestring) and len(value) < 1024:
                akw[key] = value
            else:
                akw[key] = type(value)
        if self.debug or 1:
            print "%s --> %s.%s %r" % (self.httprequest.method, controller.__class__.__name__, method.__name__, akw)
        r = method(controller, self, **self.params)
        if self.debug or 1:
            if isinstance(r, werkzeug.wrappers.BaseResponse):
                print '<--', r
            else:
                print "<--", 'size:', len(r)
            print
        return r

    def make_response(self, data, headers=None, cookies=None):
        response = werkzeug.wrappers.Response(data, headers=headers)
        if cookies:
            for k, v in cookies.iteritems():
                response.set_cookie(k, v)
        return response

    def not_found(self, description=None):
        return werkzeug.exceptions.NotFound(description)

def httprequest(f):
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
    def __init__(self, options):
        self.root = werkzeug.urls.Href('/base/webclient/home')
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
        return self.dispatch(environ, start_response)

    def dispatch(self, environ, start_response):
        request = werkzeug.wrappers.Request(environ)
        request.parameter_storage_class = werkzeug.datastructures.ImmutableDict

        if request.path == '/':
            return werkzeug.utils.redirect(
                self.root(request.args), 301)(
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

                if isinstance(result, werkzeug.wrappers.Response):
                    response = result
                else:
                    response = werkzeug.wrappers.Response(
                        result, headers=[('Content-Type', 'text/html; charset=utf-8'),
                                         ('Content-Length', len(result))])

                response.set_cookie(self.session_cookie, session.sid)

        return response(environ, start_response)

    def _load_addons(self):
        statics = {}
        addons_path = self.config.addons_path
        if addons_path not in sys.path:
            sys.path.insert(0, addons_path)
        for module in os.listdir(addons_path):
            if module not in addons_module:
                manifest_path = os.path.join(addons_path, module, '__openerp__.py')
                if os.path.isfile(manifest_path):
                    manifest = ast.literal_eval(open(manifest_path).read())
                    print "Loading", module
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
        if len(l) > 1:
            for i in range(len(l), 1, -1):
                ps = "/" + "/".join(l[0:i])
                if ps in controllers_path:
                    c = controllers_path[ps]
                    rest = l[i:] or ['index']
                    meth = rest[0]
                    m = getattr(c, meth)
                    if getattr(m, 'exposed', False):
                        print "Dispatching to", ps, c, meth, m
                        return m
        return None
