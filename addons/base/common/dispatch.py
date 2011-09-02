#!/usr/bin/python
import urllib
import functools
import logging
import os
import sys
import traceback
import uuid
import xmlrpclib

import cherrypy
import cherrypy.lib.static
import simplejson

import nonliterals
# import backendlocal as backend
import backendrpc as backend

#-----------------------------------------------------------
# Globals
#-----------------------------------------------------------

import __main__

path_root = __main__.path_root
path_addons = __main__.path_addons
cherrypy_root = None

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
class CherryPyRequest(object):
    """ CherryPy request handling
    """
    def init(self,params):
        self.params = params
        # Move cherrypy thread local objects to attributes
        self.applicationsession = applicationsession
        self.httprequest = cherrypy.request
        self.httpresponse = cherrypy.response
        self.httpsession = cherrypy.session
        self.httpsession_id = "cookieid"
        # OpenERP session setup
        self.session_id = self.params.pop("session_id", None) or uuid.uuid4().hex
        host = cherrypy.config['openerp.server.host']
        port = cherrypy.config['openerp.server.port']
        self.session = self.httpsession.setdefault(self.session_id, backend.OpenERPSession(host, port))
        # Request attributes
        self.context = self.params.pop('context', None)
        self.debug = self.params.pop('debug',False) != False

class JsonRequest(CherryPyRequest):
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
            cherrypy.log("An error occured while handling a json request",
                         severity=logging.ERROR, traceback=True)
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
        cherrypy.response.headers['Content-Type'] = 'application/json'
        cherrypy.response.headers['Content-Length'] = len(content)
        return content

def jsonrequest(f):
    @cherrypy.expose
    @functools.wraps(f)
    def json_handler(controller):
        return JsonRequest().dispatch(controller, f, requestf=cherrypy.request.body)
    return json_handler

class HttpRequest(CherryPyRequest):
    """ Regular GET/POST request
    """
    def dispatch(self, controller, method, **kw):
        self.init(kw)
        akw = {}
        for key in kw.keys():
            if isinstance(kw[key], basestring) and len(kw[key]) < 1024:
                akw[key] = kw[key]
            else:
                akw[key] = type(kw[key])
        if self.debug or 1:
            print "%s --> %s.%s %r" % (self.httprequest.method, controller.__class__.__name__, method.__name__, akw)
        r = method(controller, self, **kw)
        if self.debug or 1:
            print "<--", 'size:', len(r)
            print
        return r

def httprequest(f):
    # check cleaner wrapping:
    # functools.wraps(f)(lambda x: JsonRequest().dispatch(x, f))
    def http_handler(controller,*l, **kw):
        return HttpRequest().dispatch(controller, f, **kw)
    http_handler.exposed = 1
    return http_handler

#-----------------------------------------------------------
# Cherrypy stuff
#-----------------------------------------------------------

class ControllerType(type):
    def __init__(cls, name, bases, attrs):
        super(ControllerType, cls).__init__(name, bases, attrs)
        controllers_class["%s.%s" % (cls.__module__, cls.__name__)] = cls

class Controller(object):
    __metaclass__ = ControllerType

class Root(object):
    def __init__(self):
        self.addons = {}
        self._load_addons()

    def _load_addons(self):
        if path_addons not in sys.path:
            sys.path.insert(0, path_addons)
        for i in os.listdir(path_addons):
            if i not in addons_module:
                manifest_path = os.path.join(path_addons, i, '__openerp__.py')
                if os.path.isfile(manifest_path):
                    manifest = eval(open(manifest_path).read())
                    print "Loading", i
                    m = __import__(i)
                    addons_module[i] = m
                    addons_manifest[i] = manifest
        for k, v in controllers_class.items():
            if k not in controllers_object:
                o = v()
                controllers_object[k] = o
                if hasattr(o, '_cp_path'):
                    controllers_path[o._cp_path] = o

    def default(self, *l, **kw):
        print "default",l,kw
        # handle static files
        if len(l) > 2 and l[1] == 'static':
            # sanitize path
            p = os.path.normpath(os.path.join(*l))
            p2 = os.path.join(path_addons, p)
            print "p",p
            print "p2",p2

            return cherrypy.lib.static.serve_file(p2)
        elif len(l) > 1:
            for i in range(len(l), 1, -1):
                ps = "/" + "/".join(l[0:i])
                if ps in controllers_path:
                    c = controllers_path[ps]
                    rest = l[i:] or ['index']
                    meth = rest[0]
                    m = getattr(c, meth)
                    if getattr(m, 'exposed', 0):
                        print "Calling", ps, c, meth, m
                        return m(**kw)
            raise cherrypy.NotFound('/' + '/'.join(l))
        elif l and l[0] == 'mobile':
            #for the mobile web client we are supposed to use a different url to just add '/mobile'
            raise cherrypy.HTTPRedirect('/web_mobile/static/src/web_mobile.html', 301)
        else:
            if kw:
                qs = '?' + urllib.urlencode(kw)
            else:
                qs = ''
            raise cherrypy.HTTPRedirect('/base/webclient/home' + qs, 301)
    default.exposed = True

#
