# -*- coding: utf-8 -*-
""" Manages the storage and lifecycle of non-literal domains and contexts
(and potentially other structures) which have to be evaluated with client data,
but still need to be safely round-tripped to and from the browser (and thus
can't be sent there themselves).
"""
import simplejson.encoder

__all__ = ['Domain', 'Context', 'NonLiteralEncoder', 'non_literal_decoder', 'CompoundDomain', 'CompoundContext']

class NonLiteralEncoder(simplejson.encoder.JSONEncoder):
    def default(self, object):
        if not isinstance(object, (BaseDomain, BaseContext)):
            return super(NonLiteralEncoder, self).default(object)
        if isinstance(object, Domain):
            return {
                '__ref': 'domain',
                '__debug': object.domain_string
            }
        elif isinstance(object, Context):
            return {
                '__ref': 'context',
                '__debug': object.context_string
            }
        raise TypeError('Could not encode unknown non-literal %s' % object)

def non_literal_decoder(dct):
    if '__ref' in dct:
        raise ValueError(
            "Non literal contexts can not be sent to the server anymore (%r)" % (dct,))
    return dct

# TODO: use abstract base classes if 2.6+?
class BaseDomain(object):
    def evaluate(self, context=None):
        raise NotImplementedError('Non literals must implement evaluate()')

class BaseContext(object):
    def evaluate(self, context=None):
        raise NotImplementedError('Non literals must implement evaluate()')

class Domain(BaseDomain):
    def __init__(self, session, domain_string):
        """ Uses session information to store the domain string and map it to a
        domain key, which can be safely round-tripped to the client.

        If initialized with a domain string, will generate a key for that
        string and store the domain string out of the way. When initialized
        with a key, considers this key is a reference to an existing domain
        string.

        :param session: the OpenERP Session to use when evaluating the domain
        :type session: web.common.session.OpenERPSession
        :param str domain_string: a non-literal domain in string form
        """
        self.session = session
        self.domain_string = domain_string

    def evaluate(self, context=None):
        """ Forces the evaluation of the linked domain, using the provided
        context (as well as the session's base context), and returns the
        evaluated result.
        """
        ctx = self.session.evaluation_context(context)

        try:
            return eval(self.domain_string, SuperDict(ctx))
        except NameError as e:
            raise ValueError('Error during evaluation of this domain: "%s", message: "%s"' % (self.domain_string, e.message))

class Context(BaseContext):
    def __init__(self, session, context_string):
        """ Uses session information to store the context string and map it to
        a key (stored in a secret location under a secret mountain), which can
        be safely round-tripped to the client.

        If initialized with a context string, will generate a key for that
        string and store the context string out of the way. When initialized
        with a key, considers this key is a reference to an existing context
        string.

        :param session: the OpenERP Session to use when evaluating the context
        :type session: web.common.session.OpenERPSession
        :param str context_string: a non-literal context in string form
        """
        self.session = session
        self.context_string = context_string

    def evaluate(self, context=None):
        """ Forces the evaluation of the linked context, using the provided
        context (as well as the session's base context), and returns the
        evaluated result.
        """
        ctx = self.session.evaluation_context(context)

        try:
            return eval(self.context_string, SuperDict(ctx))
        except NameError as e:
            raise ValueError('Error during evaluation of this context: "%s", message: "%s"' % (self.context_string, e.message))

class SuperDict(dict):
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)
    def __getitem__(self, key):
        tmp = super(SuperDict, self).__getitem__(key)
        if isinstance(tmp, dict):
            return SuperDict(tmp)
        return tmp
