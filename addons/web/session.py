#!/usr/bin/python
import datetime
import babel
import dateutil.relativedelta
import logging
import time
import traceback
import sys
import xmlrpclib

import openerp

_logger = logging.getLogger(__name__)

#----------------------------------------------------------
# OpenERPSession RPC openerp backend access
#----------------------------------------------------------
class AuthenticationError(Exception):
    pass

class SessionExpiredException(Exception):
    pass

class Service(object):
    def __init__(self, session, service_name):
        self.session = session
        self.service_name = service_name

    def __getattr__(self, method):
        def proxy_method(*args):
            result = self.session.send(self.service_name, method, *args)
            return result
        return proxy_method

class Model(object):
    def __init__(self, session, model):
        self.session = session
        self.model = model
        self.proxy = self.session.proxy('object')

    def __getattr__(self, method):
        def proxy(*args, **kw):
            result = self.proxy.execute_kw(self.session._db, self.session._uid, self.session._password, self.model, method, args, kw)
            # reorder read
            if method == "read":
                if isinstance(result, list) and len(result) > 0 and "id" in result[0]:
                    index = {}
                    for r in result:
                        index[r['id']] = r
                    result = [index[x] for x in args[0] if x in index]
            return result
        return proxy

    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None, context=None):
        record_ids = self.search(domain or [], offset, limit or False, order or False, context or {})
        if not record_ids: return []
        records = self.read(record_ids, fields or [], context or {})
        return records

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
        self._db = False
        self._uid = False
        self._login = False
        self._password = False
        self._suicide = False
        self.context = {}
        self.jsonp_requests = {}     # FIXME use a LRU

    def send(self, service_name, method, *args):
        code_string = u"warning -- %s\n\n%s"
        try:
            return openerp.netsvc.dispatch_rpc(service_name, method, args)
        except openerp.osv.osv.except_osv, e:
            raise xmlrpclib.Fault(code_string % (e.name, e.value), '')
        except openerp.exceptions.Warning, e:
            raise xmlrpclib.Fault(code_string % ("Warning", e), '')
        except openerp.exceptions.AccessError, e:
            raise xmlrpclib.Fault(code_string % ("AccessError", e), '')
        except openerp.exceptions.AccessDenied, e:
            raise xmlrpclib.Fault('AccessDenied', openerp.tools.ustr(e))
        except openerp.exceptions.DeferredException, e:
            formatted_info = "".join(traceback.format_exception(*e.traceback))
            raise xmlrpclib.Fault(openerp.tools.ustr(e), formatted_info)
        except Exception, e:
            formatted_info = "".join(traceback.format_exception(*(sys.exc_info())))
            raise xmlrpclib.Fault(openerp.tools.ustr(e), formatted_info)

    def proxy(self, service):
        return Service(self, service)

    def bind(self, db, uid, login, password):
        self._db = db
        self._uid = uid
        self._login = login
        self._password = password

    def authenticate(self, db, login, password, env=None):
        uid = self.proxy('common').authenticate(db, login, password, env)
        self.bind(db, uid, login, password)

        if uid: self.get_context()
        return uid

    def assert_valid(self, force=False):
        """
        Ensures this session is valid (logged into the openerp server)
        """
        if self._uid and not force:
            return
        # TODO use authenticate instead of login
        uid = self.proxy("common").login(self._db, self._login, self._password)
        if not uid:
            raise AuthenticationError("Authentication failure")

    def ensure_valid(self):
        if self._uid:
            try:
                self.assert_valid(True)
            except Exception:
                self._uid = None

    def execute(self, model, func, *l, **d):
        self.assert_valid()
        model = self.model(model)
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
        if self._db == False:
            raise SessionExpiredException("Session expired")

        return Model(self, model)

    def get_context(self):
        """ Re-initializes the current user's session context (based on
        his preferences) by calling res.users.get_context() with the old
        context

        :returns: the new context
        """
        assert self._uid, "The user needs to be logged-in to initialize his context"
        self.context = self.model('res.users').context_get() or {}
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

        context['lang'] = lang or 'en_US'

# vim:et:ts=4:sw=4:
