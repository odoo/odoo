#!/usr/bin/python

import os,re,sys,traceback,xmlrpclib

import cherrypy,cherrypy.lib.static

import simplejson as json

import xmlrpctimeout

#----------------------------------------------------------
# OpenERP Client Library
#----------------------------------------------------------
class OpenERPUnboundException(Exception):
    pass

class OpenERPConnector(object):
    pass

class OpenERPAuth(object):
    pass

class OpenERPModel(object):
    def __init__(self,session,model):
        self._session = session
        self._model = model
    def __getattr__(self,name):
        return lambda *l:self._session.execute(self._model,name,*l)

class OpenERPSession(object):
    def __init__(self, server='127.0.0.1', port=8069):
        self._server = server
        self._port = port
        self._db = False
        self._uid = False
        self._login = False
        self._password = False

    def proxy(self, service):
        s = xmlrpctimeout.TimeoutServerProxy('http://%s:%s/xmlrpc/%s'%(self._server, self._port, service), timeout=5)
        return s

    def bind(self, db, uid, password):
        self._db = db
        self._uid = uid
        self._password = password

    def login(self, db, login, password):
        uid = self.proxy('common').login(db, login, password)
        self.bind(db, uid, password)
        self._login = login
        return uid

    def execute(self,model,func,*l,**d):
        if not (self._db and self._uid and self._password):
            raise OpenERPUnboundException()
        r = self.proxy('object').execute(self._db, self._uid, self._password, model, func, *l, **d)
        return r

    def model(self,model):
        return OpenERPModel(self,model)

#----------------------------------------------------------
# OpenERP Web RequestHandler
#----------------------------------------------------------
session_store = {}

class JsonRequest(object):
    """ JSON-RPC2 over HTTP POST using non standard POST encoding.
    Difference with the standard:
       - the json string is passed as a form parameter named "request"
       - method is currently ignored

    Sucessful request:
    --> {"jsonrpc": "2.0", "method": "call", "params": {"session_id": "SID", "context": {}, "arg1": "val1" }, "id": null}
    <-- {"jsonrpc": "2.0", "result": { "res1": "val1" }, "id": null}

    Request producing a error:
    --> {"jsonrpc": "2.0", "method": "call", "params": {"session_id": "SID", "context": {}, "arg1": "val1" }, "id": null}
    <-- {"jsonrpc": "2.0", "error": {"code": 1, "message": "End user error message.", "data": {"code": "codestring", "debug": "traceback" } }, "id": null}

    """
    def __init__(self):
        # result may be filled, it's content will be updated by the return
        # value of the dispatched function if it's a dict
        self.result = {}
        self.error_type = ""
        self.error_message = ""
        self.error_debug = ""

    def parse(self, request):
        self.cherrypy_request = None
        self.cherrypy_session = None
        d=json.loads(request)
        self.params = d.get("params",{})
        self.session_id = self.params.pop("session_id", None) or "random.random"
        self.session = session_store.setdefault(self.session_id, OpenERPSession())
        self.context = self.params.pop("context", {})

    def dispatch(self, controller, f, request):
        try:
            print "--> %s.%s %s"%(controller.__class__.__name__,f.__name__,request)
            self.parse(request)
            r=f(controller, self, **self.params)
            if isinstance(r, dict):
                self.result.update(r)
        except OpenERPUnboundException,e:
            self.error_type = "session_invalid"
            self.error_message = "OpenERP Session Invalid"
            self.error_debug = traceback.format_exc()
        except xmlrpclib.Fault, e:
            tb = "".join(traceback.format_exception("", None, sys.exc_traceback))
            self.error_type = "server_exception"
            self.error_message = "OpenERP Server Error: %s"%e.faultCode
            self.error_debug = "Client %s\nServer %s"%(tb,e.faultString)
        except Exception,e:
            self.error_type = "client_exception"
            self.error_message = "OpenERP WebClient Error: %r"%e
            self.error_debug = "Client %s"%traceback.format_exc()
        r = {"jsonrpc": "2.0",  "id": None}
        if self.error_type:
            r["error"] = {"code": 1, "message": self.error_message, "data": { "type":self.error_type, "debug": self.error_debug } }
        else:
            r["result"] = self.result
        print "<--",r
        print
        #import pprint
        #pprint.pprint(r)
        return json.dumps(r)

def jsonrequest(f):
    # check cleaner wrapping:
    # functools.wraps(f)(lambda x: JsonRequest().dispatch(x, f))
    l=lambda self, request: JsonRequest().dispatch(self, f, request)
    l.exposed=1
    return l

class BasicRequest(object):
    """ Regular GET/POST request
    """
    def __init__(self):
        # result may be filled, it's content will be updated by the return
        # value of the dispatched function if it's a dict
        self.result = ""

    def dispatch(self, controller, f, request):
        print "GET/POST --> %s.%s %s"%(controller.__class__.__name__,f.__name__,request)
        r=f(controller, self, request)
        return r

def basicrequest(f):
    # check cleaner wrapping:
    # functools.wraps(f)(lambda x: JsonRequest().dispatch(x, f))
    l=lambda self, request: BasicRequest().dispatch(self, f, request)
    l.exposed=1
    return l

#-----------------------------------------------------------
# Cherrypy stuff
#-----------------------------------------------------------

path_root = os.path.dirname(os.path.dirname(os.path.normpath(__file__)))
path_addons = os.path.join(path_root,'addons')
cherrypy_root = None
openerp_addons = {}
openerp_controllers_class = {}
openerp_controllers_object = {}
openerp_controllers_path = {}

class ControllerType(type):
    def __init__(cls, name, bases, attrs):
        super(ControllerType, cls).__init__(name, bases, attrs)
        # TODO forgive me this hack and find me a clean way to get the absolute name of a class
        cls.fullname = re.search("'(.+)'",repr(cls)).group(1)
        openerp_controllers_class[cls.fullname] = cls

class Controller(object):
    __metaclass__ = ControllerType

class Root(object):
    def __init__(self):
        self.addons = {}
        self._load_addons()
    def _load_addons(self):
        if path_addons not in sys.path:
            sys.path.insert(0,path_addons)
        for i in os.listdir(path_addons):
            if i not in sys.modules:
                print "Loading",i
                m = __import__(i)
                openerp_addons[i] = m
        for k,v in openerp_controllers_class.items():
            if k not in openerp_controllers_object:
                o = v()
                openerp_controllers_object[k] = o
                if hasattr(o,'_cp_path'):
                    openerp_controllers_path[o._cp_path] = o

    def default(self, *l, **kw):
        #print "default",l,kw
        # handle static files
        if len(l) > 2 and l[1]=='static':
            # sanitize path
            p = os.path.normpath(os.path.join(*l))
            return cherrypy.lib.static.serve_file(os.path.join(path_addons,p))
        elif len(l) > 1:
            for i in range(1,len(l)+1):
                ps = "/" + "/".join(l[0:i])
                if ps in openerp_controllers_path:
                    c = openerp_controllers_path[ps]
                    rest = l[i:] or ['index']
                    meth = rest[0]
                    m = getattr(c,meth)
                    print "Calling",ps,c,meth,m
                    return m(**kw)

        else:
            return '<a href="/base/static/openerp/base.html">/base/static/openerp/base.html</a>'
    default.exposed = True

def main(argv):
    config = {
        'server.socket_port': 8002,
        #'server.socket_host': '64.72.221.48',
        #'server.thread_pool' = 10,
        'tools.sessions.on': True,
    }
    cherrypy.config.update(config)
    cherrypy_root = Root()
    cherrypy.quickstart(cherrypy_root,'',{'/':{}})

# vim:
