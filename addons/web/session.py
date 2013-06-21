#!/usr/bin/python
import datetime
import babel
import dateutil.relativedelta
import logging
import time
import traceback
import sys

import openerp
import http

_logger = logging.getLogger(__name__)

#----------------------------------------------------------
# OpenERPSession RPC openerp backend access
#----------------------------------------------------------
class AuthenticationError(Exception):
    pass

class SessionExpiredException(Exception):
    pass

class Service(object):
    """
        .. deprecated:: 8.0
        Use ``openerp.netsvc.dispatch_rpc()`` instead.
    """
    def __init__(self, session, service_name):
        self.session = session
        self.service_name = service_name

    def __getattr__(self, method):
        def proxy_method(*args):
            result = openerp.netsvc.dispatch_rpc(self.service_name, method, args)
            return result
        return proxy_method

class Model(object):
    """
        .. deprecated:: 8.0
        Use the resistry and cursor in ``openerp.addons.web.http.request`` instead.
    """
    def __init__(self, session, model):
        self.session = session
        self.model = model
        self.proxy = self.session.proxy('object')

    def __getattr__(self, method):
        self.session.assert_valid()
        def proxy(*args, **kw):
            # Can't provide any retro-compatibility for this case, so we check it and raise an Exception
            # to tell the programmer to adapt his code
            if not http.request.db or not http.request.uid or self.session._db != http.request.db \
                or self.session._uid != http.request.uid:
                raise Exception("Trying to use Model with badly configured database or user.")
                
            mod = http.request.registry.get(self.model)
            meth = getattr(mod, method)
            cr = http.request.cr
            result = meth(cr, http.request.uid, *args, **kw)
            # reorder read
            if method == "read":
                if isinstance(result, list) and len(result) > 0 and "id" in result[0]:
                    index = {}
                    for r in result:
                        index[r['id']] = r
                    result = [index[x] for x in args[0] if x in index]
            return result
        return proxy

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

    def authenticate(self, db, login, password, env=None):
        """
        Authenticate the current user with the given db, login and password. If successful, store
        the authentication parameters in the current session and request.
        """
        uid = openerp.netsvc.dispatch_rpc('common', 'authenticate', [db, login, password, env])
        self._db = db
        self._uid = uid
        self._login = login
        self._password = password
        http.request.db = db
        http.request.uid = uid

        if uid: self.get_context()
        return uid

    def check_security(self):
        """
        Chech the current authentication parameters to know if those are still valid. This method
        should be called at each request. If the authentication fails, a ``SessionExpiredException``
        is raised.
        """
        if not self._db or not self._uid:
            raise SessionExpiredException("Session expired")
        import openerp.service.security as security
        security.check(self._db, self._uid, self._password)

    def get_context(self):
        """
        Re-initializes the current user's session context (based on
        his preferences) by calling res.users.get_context() with the old
        context.

        :returns: the new context
        """
        assert self._uid, "The user needs to be logged-in to initialize his context"
        self.context = http.request.registry.get('res.users').context_get(http.request.cr, http.request.uid) or {}
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

    def send(self, service_name, method, *args):
        """
        .. deprecated:: 8.0
        Use ``openerp.netsvc.dispatch_rpc()`` instead.
        """
        return openerp.netsvc.dispatch_rpc(service_name, method, args)

    def proxy(self, service):
        """
        .. deprecated:: 8.0
        Use ``openerp.netsvc.dispatch_rpc()`` instead.
        """
        return Service(self, service)

    def assert_valid(self, force=False):
        """
        .. deprecated:: 8.0
        Use ``check_security()`` instead.

        Ensures this session is valid (logged into the openerp server)
        """
        if self._uid and not force:
            return
        # TODO use authenticate instead of login
        self._uid = self.proxy("common").login(self._db, self._login, self._password)
        if not self._uid:
            raise AuthenticationError("Authentication failure")

    def ensure_valid(self):
        """
        .. deprecated:: 8.0
        Use ``check_security()`` instead.
        """
        if self._uid:
            try:
                self.assert_valid(True)
            except Exception:
                self._uid = None

    def execute(self, model, func, *l, **d):
        """
        .. deprecated:: 8.0
        Use the resistry and cursor in ``openerp.addons.web.http.request`` instead.
        """
        model = self.model(model)
        r = getattr(model, func)(*l, **d)
        return r

    def exec_workflow(self, model, id, signal):
        """
        .. deprecated:: 8.0
        Use the resistry and cursor in ``openerp.addons.web.http.request`` instead.
        """
        self.assert_valid()
        r = self.proxy('object').exec_workflow(self._db, self._uid, self._password, model, signal, id)
        return r

    def model(self, model):
        """
        .. deprecated:: 8.0
        Use the resistry and cursor in ``openerp.addons.web.http.request`` instead.

        Get an RPC proxy for the object ``model``, bound to this session.

        :param model: an OpenERP model name
        :type model: str
        :rtype: a model object
        """
        if self._db == False:
            raise SessionExpiredException("Session expired")

        return Model(self, model)

# vim:et:ts=4:sw=4:
