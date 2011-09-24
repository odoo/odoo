#!/usr/bin/python
import datetime
import dateutil.relativedelta
import time
import openerplib

import nonliterals
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
    def __init__(self, config):
        self.config = config
        self._db = False
        self._uid = False
        self._login = False
        self._password = False
        self._locale = 'en_US'
        self.context = {}
        self.contexts_store = {}
        self.domains_store = {}
        self._lang = {}
        self.remote_timezone = 'utc'
        self.client_timezone = False
        
    def build_connection(self):
        return openerplib.get_connection(hostname=self.config.server_host, port=self.config.server_port,
                                         database=self._db, login=self._login,
                                         user_id=self._uid, password=self._password)

    def proxy(self, service):
        return self.build_connection().get_service(service)

    def bind(self, db, uid, login, password):
        self._db = db
        self._uid = uid
        self._login = login
        self._password = password

    def login(self, db, login, password):
        uid = self.proxy('common').login(db, login, password)
        self.bind(db, uid, login, password)
        
        if uid: self.get_context()
        return uid

    def assert_valid(self, force=False):
        """
        Ensures this session is valid (logged into the openerp server)
        """
        self.build_connection().check_login(force)

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
        self.context = self.model('res.users').context_get(self.context)
        self.context = self.context or {}

        self.client_timezone = self.context.get("tz", False)
        # invalid code, anyway we decided the server will be in UTC
        #if self.client_timezone:
        #    self.remote_timezone = self.execute('common', 'timezone_get')

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
