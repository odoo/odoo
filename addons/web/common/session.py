#!/usr/bin/python
import datetime
import babel
import dateutil.relativedelta
import logging
import time
import openerplib

from . import nonliterals

_logger = logging.getLogger(__name__)

#----------------------------------------------------------
# openerplib local connector
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

#----------------------------------------------------------
# OpenERPSession RPC openerp backend access
#----------------------------------------------------------
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
    def __init__(self):
        self._creation_time = time.time()
        self.config = None
        self._db = False
        self._uid = False
        self._login = False
        self._password = False
        self._suicide = False
        self.context = {}
        self.contexts_store = {}
        self.domains_store = {}
        self.jsonp_requests = {}     # FIXME use a LRU
        
    def __getstate__(self):
        state = dict(self.__dict__)
        if "config" in state:
            del state['config']
        return state

    def openerp_entreprise(self):
        if not self._uid:
            return False
        else:
            return self.model('publisher_warranty.contract').status()['status'] == 'full'

    def build_connection(self):
        conn = openerplib.Connection(self.config.connector, database=self._db, login=self._login,
                   user_id=self._uid, password=self._password)
        return conn

    def proxy(self, service):
        return self.build_connection().get_service(service)

    def bind(self, db, uid, login, password):
        self._db = db
        self._uid = uid
        self._login = login
        self._password = password

    def authenticate(self, db, login, password, env=None):
        # TODO use the openerplib API once it exposes authenticate()
        uid = self.proxy('common').authenticate(db, login, password, env)
        self.bind(db, uid, login, password)
        
        if uid: self.get_context()
        return uid

    def assert_valid(self, force=False):
        """
        Ensures this session is valid (logged into the openerp server)
        """
        self.build_connection().check_login(force)

    def ensure_valid(self):
        if self._uid:
            try:
                self.assert_valid(True)
            except Exception:
                self._uid = None

    def execute(self, model, func, *l, **d):
        self.assert_valid()
        model = self.build_connection().get_model(model)
        r = getattr(model, func)(*l, **d)
        return r

    def exec_workflow(self, model, id, signal):
        self.assert_valid()
        r = self.proxy('object').exec_workflow(self._db, self._uid, self._password, model, signal, id)
        return r

    def model(self, model):
        """ Get an RPC proxy for the object ``model``, bound to this session.

        :param model: an OpenERP model name
        :type model: str
        :rtype: a model object
        """
        return self.build_connection().get_model(model)

    def get_context(self):
        """ Re-initializes the current user's session context (based on
        his preferences) by calling res.users.get_context() with the old
        context

        :returns: the new context
        """
        assert self._uid, "The user needs to be logged-in to initialize his context"
        self.context = self.build_connection().get_user_context() or {}
        self.context['uid'] = self._uid
        self._fix_lang(self.context)
        return self.context

    def _fix_lang(self, context):
        """ OpenERP provides languages which may not make sense and/or may not
        be understood by the web client's libraries.

        Fix those here.

        :param dict context: context to fix
        """
        lang = context['lang']

        # inane OpenERP locale
        if lang == 'ar_AR':
            lang = 'ar'

        # lang to lang_REGION (datejs only handles lang_REGION, no bare langs)
        if lang in babel.core.LOCALE_ALIASES:
            lang = babel.core.LOCALE_ALIASES[lang]

        context['lang'] = lang

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
        d = dict(self.base_eval_context)
        if context:
            d.update(context)
        d['context'] = d
        return d

    def eval_context(self, context_to_eval, context=None):
        """ Evaluates the provided context_to_eval in the context (haha) of
        the context. Also merges the evaluated context with the session's context.

        :param context_to_eval: a context to evaluate. Must be a dict or a
                                non-literal context. If it's a dict, will be
                                returned as-is
        :type context_to_eval: openerpweb.nonliterals.Context
        :returns: the evaluated context
        :rtype: dict

        :raises: ``TypeError`` if ``context_to_eval`` is neither a dict nor
                 a Context
        """
        ctx = dict(
            self.base_eval_context,
            **(context or {}))
        
        # adding the context of the session to send to the openerp server
        ccontext = nonliterals.CompoundContext(self.context, context_to_eval or {})
        ccontext.session = self
        return ccontext.evaluate(ctx)

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
        if isinstance(domain, list):
            return domain

        cdomain = nonliterals.CompoundDomain(domain)
        cdomain.session = self
        return cdomain.evaluate(context or {})

# vim:et:ts=4:sw=4:
