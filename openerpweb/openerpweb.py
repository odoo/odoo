#!/usr/bin/python
import datetime
import dateutil.relativedelta
import functools
import optparse
import os
import sys
import tempfile
import time
import traceback
import uuid
import xmlrpclib
import pytz

import cherrypy
import cherrypy.lib.static
import simplejson

import nonliterals
import xmlrpctimeout
import logging

#-----------------------------------------------------------
# Globals
#-----------------------------------------------------------

path_root = os.path.dirname(os.path.dirname(os.path.normpath(__file__)))
path_addons = os.path.join(path_root, 'addons')
cherrypy_root = None

#-----------------------------------------------------------
# Per Database Globals (might move into a pool if needed)
#-----------------------------------------------------------

applicationsession = {}
addons_module = {}
addons_manifest = {}
controllers_class = {}
controllers_object = {}
controllers_path = {}

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
    def __init__(self, session, model):
        self._session = session
        self._model = model

    def __getattr__(self, name):
        return lambda *l:self._session.execute(self._model, name, *l)

class OpenERPSession(object):
    """
    An OpenERP RPC session, a given user can own multiple such sessions
    in a web session.

    .. attribute:: context
    
        The session context, a ``dict``. Can be reloaded by calling
        :meth:`openerpweb.openerpweb.OpenERPSession.get_context`

    .. attribute:: domains_store

        A ``dict`` matching domain keys to evaluable (but non-literal) domains.

        Used to store references to non-literal domains which need to be
        round-tripped to the client browser.
    """
    def __init__(self, server='127.0.0.1', port=8069,
                 model_factory=OpenERPModel):
        self._server = server
        self._port = port
        self._db = False
        self._uid = False
        self._login = False
        self._password = False
        self.model_factory = model_factory
        self._locale = 'en_US'
        self.context = {}
        self.contexts_store = {}
        self.domains_store = {}
        self._lang = {}
        self.remote_timezone = 'utc'
        self.client_timezone = False

    def proxy(self, service):
        s = xmlrpctimeout.TimeoutServerProxy('http://%s:%s/xmlrpc/%s' % (self._server, self._port, service), timeout=5)
        return s

    def bind(self, db, uid, password):
        self._db = db
        self._uid = uid
        self._password = password

    def login(self, db, login, password):
        uid = self.proxy('common').login(db, login, password)
        self.bind(db, uid, password)
        self._login = login
        
        if uid: self.get_context()
        return uid

    def execute(self, model, func, *l, **d):
        if not (self._db and self._uid and self._password):
            raise OpenERPUnboundException()
        r = self.proxy('object').execute(self._db, self._uid, self._password, model, func, *l, **d)
        return r

    def model(self, model):
        """ Get an RPC proxy for the object ``model``, bound to this session.

        :param model: an OpenERP model name
        :type model: str
        :rtype: :class:`openerpweb.openerpweb.OpenERPModel`
        """
        return self.model_factory(self, model)

    def get_context(self):
        """ Re-initializes the current user's session context (based on
        his preferences) by calling res.users.get_context() with the old
        context

        :returns: the new context
        """
        assert self._uid, "The user needs to be logged-in to initialize his context"
        self.context = self.model('res.users').context_get(self.context)
        
        self.client_timezone = self.context.get("tz", False)
        if self.client_timezone:
            self.remote_timezone = self.execute('common', 'timezone_get')
            
        self._locale = self.context.get('lang','en_US')
        lang_ids = self.execute('res.lang','search', [('code', '=', self._locale)])
        if lang_ids:
            self._lang = self.execute('res.lang', 'read',lang_ids[0], [])
        return self.context

    @property
    def base_eval_context(self):
        """ Default evaluation context for the session.

        Used to evaluate contexts and domains.
        """
        base = dict(
            uid=self._uid,
            current_date=datetime.date.today().strftime('%Y-%m-%d'),
            time=time,
            datetime=datetime,
            relativedelta=dateutil.relativedelta.relativedelta
        )
        base.update(self.context)
        return base

    def evaluation_context(self, context=None):
        """ Returns the session's evaluation context, augmented with the
        provided context if any.

        :param dict context: to add merge in the session's base eval context
        :returns: the augmented context
        :rtype: dict
        """
        d = {}
        d.update(self.base_eval_context)
        if context:
            d.update(context)
        return d

    def eval_context(self, context_to_eval, context=None):
        """ Evaluates the provided context_to_eval in the context (haha) of
        the context.

        :param context_to_eval: a context to evaluate. Must be a dict or a
                                non-literal context. If it's a dict, will be
                                returned as-is
        :type context_to_eval: openerpweb.nonliterals.Context
        :returns: the evaluated context
        :rtype: dict

        :raises: ``TypeError`` if ``context_to_eval`` is neither a dict nor
                 a Context
        """
        if not isinstance(context_to_eval, (dict, nonliterals.Domain)):
            raise TypeError("Context %r is not a dict or a nonliteral Context",
                             context_to_eval)

        if isinstance(context_to_eval, dict):
            return context_to_eval

        ctx = dict(context or {})
        ctx['context'] = ctx

        # if the domain was unpacked from JSON, it needs the current
        # OpenERPSession for its data retrieval
        context_to_eval.session = self
        return context_to_eval.evaluate(ctx)

    def eval_contexts(self, contexts, context=None):
        """ Evaluates a sequence of contexts to build a single final result

        :param list contexts: a list of Context or dict contexts
        :param dict context: a base context, if needed
        :returns: the final combination of all provided contexts
        :rtype: dict
        """
        # This is the context we use to evaluate stuff
        current_context = dict(
            self.base_eval_context,
            **(context or {}))
        # this is our result, it should not contain the values
        # of the base context above
        final_context = {}
        for ctx in contexts:
            # evaluate the current context in the sequence, merge it into
            # the result
            final_context.update(
                self.eval_context(
                    ctx, current_context))
            # update the current evaluation context so that future
            # evaluations can use the results we just gathered
            current_context.update(final_context)
        return final_context

    def eval_domain(self, domain, context=None):
        """ Evaluates the provided domain using the provided context
        (merged with the session's evaluation context)

        :param domain: an OpenERP domain as a list or as a
                       :class:`openerpweb.nonliterals.Domain` instance

                       In the second case, it will be evaluated and returned.
        :type domain: openerpweb.nonliterals.Domain
        :param dict context: the context to use in the evaluation, if any.
        :returns: the evaluated domain
        :rtype: list

        :raises: ``TypeError`` if ``domain`` is neither a list nor a Domain
        """
        if not isinstance(domain, (list, nonliterals.Domain)):
            raise TypeError("Domain %r is not a list or a nonliteral Domain",
                             domain)

        if isinstance(domain, list):
            return domain

        ctx = dict(context or {})
        ctx['context'] = ctx

        # if the domain was unpacked from JSON, it needs the current
        # OpenERPSession for its data retrieval
        domain.session = self
        return domain.evaluate(ctx)

    def eval_domains(self, domains, context=None):
        """ Evaluates and concatenates the provided domains using the
        provided context for all of them.

        Returns the final, concatenated result.

        :param list domains: a list of Domain or list domains
        :param dict context: the context in which the domains
                             should be evaluated (if evaluations need
                             to happen)
        :returns: the final combination of all domains in the sequence
        :rtype: list
        """
        final_domain = []
        for domain in domains:
            final_domain.extend(
                self.eval_domain(domain, context))
        return final_domain

#----------------------------------------------------------
# OpenERP Web RequestHandler
#----------------------------------------------------------
class JsonRequest(object):
    """ JSON-RPC2 over HTTP POST using non standard POST encoding.
    Difference with the standard:

    * the json string is passed as a form parameter named "request"
    * method is currently ignored

    Sucessful request:
    --> {"jsonrpc": "2.0", "method": "call", "params": {"session_id": "SID", "context": {}, "arg1": "val1" }, "id": null}
    <-- {"jsonrpc": "2.0", "result": { "res1": "val1" }, "id": null}

    Request producing a error:
    --> {"jsonrpc": "2.0", "method": "call", "params": {"session_id": "SID", "context": {}, "arg1": "val1" }, "id": null}
    <-- {"jsonrpc": "2.0", "error": {"code": 1, "message": "End user error message.", "data": {"code": "codestring", "debug": "traceback" } }, "id": null}

    """

    def parse(self, request):
        self.request = request
        self.params = request.get("params", {})
        self.applicationsession = applicationsession
        self.httpsession_id = "cookieid"
        self.httpsession = cherrypy.session
        self.session_id = self.params.pop("session_id", None) or uuid.uuid4().hex
        self.session = self.httpsession.setdefault(self.session_id, OpenERPSession())
        self.context = self.params.pop('context', None)
        return self.params

    def dispatch(self, controller, method, requestf=None, request=None):
        ''' Calls the method asked for by the JSON-RPC2 request

        :param controller: the instance of the controller which received the request
        :type controller: type
        :param method: the method which received the request
        :type method: callable
        :param requestf: a file-like object containing an encoded JSON-RPC2 request
        :type requestf: <read() -> bytes>
        :param request: an encoded JSON-RPC2 request
        :type request: bytes

        :returns: a string-encoded JSON-RPC2 reply
        :rtype: bytes
        '''
        # Read POST content or POST Form Data named "request"
        if requestf:
            request = simplejson.load(requestf, object_hook=nonliterals.non_literal_decoder)
        else:
            request = simplejson.loads(request, object_hook=nonliterals.non_literal_decoder)
        try:
            print "--> %s.%s %s" % (controller.__class__.__name__, method.__name__, request)
            error = None
            self.parse(request)
            result = method(controller, self, **self.params)
        except OpenERPUnboundException:
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
        response = {"jsonrpc": "2.0", "id": request.get('id')}
        if error:
            response["error"] = error
        else:
            response["result"] = result

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

class HttpRequest(object):
    """ Regular GET/POST request
    """
    def dispatch(self, controller, f, request, **kw):
        self.request = request
        self.applicationsession = applicationsession
        self.httpsession_id = "cookieid"
        self.httpsession = cherrypy.session
        self.result = ""
        print "GET/POST --> %s.%s %s %r" % (controller.__class__.__name__, f.__name__, request, kw)
        r = f(controller, self, **kw)
        print "<--", r
        print
        return r

def httprequest(f):
    # check cleaner wrapping:
    # functools.wraps(f)(lambda x: JsonRequest().dispatch(x, f))
    def http_handler(self,*l, **kw):
        return HttpRequest().dispatch(self, f, cherrypy.request, **kw)
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
            if i not in sys.modules:
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
        #print "default",l,kw
        # handle static files
        if len(l) > 2 and l[1] == 'static':
            # sanitize path
            p = os.path.normpath(os.path.join(*l))
            return cherrypy.lib.static.serve_file(os.path.join(path_addons, p))
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
        else:
            raise cherrypy.HTTPRedirect('/base/static/src/base.html', 301)
    default.exposed = True

def main(argv):
    # Parse config
    op = optparse.OptionParser()
    op.add_option("-p", "--port", dest="socket_port", help="listening port", metavar="NUMBER", default=8002)
    op.add_option("-s", "--session-path", dest="storage_path",
                  help="directory used for session storage", metavar="DIR",
                  default=os.path.join(tempfile.gettempdir(), "cpsessions"))
    (o, args) = op.parse_args(argv[1:])

    # Prepare cherrypy config from options
    if not os.path.exists(o.storage_path):
        os.mkdir(o.storage_path, 0700)
    config = {
        'server.socket_port': int(o.socket_port),
        'server.socket_host': '0.0.0.0',
        #'server.thread_pool' = 10,
        'tools.sessions.on': True,
        'tools.sessions.storage_type': 'file',
        'tools.sessions.storage_path': o.storage_path,
        'tools.sessions.timeout': 60
    }

    # Setup and run cherrypy
    cherrypy.tree.mount(Root())
    cherrypy.config.update(config)
    cherrypy.server.subscribe()
    cherrypy.engine.start()
    cherrypy.engine.block()

