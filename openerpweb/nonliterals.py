# -*- coding: utf-8 -*-
""" Manages the storage and lifecycle of non-literal domains and contexts
(and potentially other structures) which have to be evaluated with client data,
but still need to be safely round-tripped to and from the browser (and thus
can't be sent there themselves).
"""
import binascii
import hashlib
import simplejson.encoder

__all__ = ['Domain', 'Context', 'NonLiteralEncoder, non_literal_decoder']

#: 48 bits should be sufficient to have almost no chance of collision
#: with a million hashes, according to hg@67081329d49a
SHORT_HASH_BYTES_SIZE = 6

class NonLiteralEncoder(simplejson.encoder.JSONEncoder):
    def default(self, object):
        if not isinstance(object, (BaseDomain, BaseContext)):
            return super(NonLiteralEncoder, self).default(object)
        if isinstance(object, Domain):
            return {
                '__ref': 'domain',
                '__id': object.key
            }
        elif isinstance(object, Context):
            return {
                '__ref': 'context',
                '__id': object.key
            }
        elif isinstance(object, CompoundDomain):
            return {
                '__ref': 'compound_domain',
                '__domains': object.domains
            }
        elif isinstance(object, CompoundContext):
            return {
                '__ref': 'compound_context',
                '__contexts': object.contexts
            }
        raise TypeError('Could not encode unknown non-literal %s' % object)

def non_literal_decoder(dct):
    """ Decodes JSON dicts into :class:`Domain` and :class:`Context` based on
    magic attribute tags.

    Also handles private context section for the domain or section via the
    ``own_values`` dict key.
    """
    if '__ref' in dct:
        if dct['__ref'] == 'domain':
            domain = Domain(None, key=dct['__id'])
            if 'own_values' in dct:
                domain.own = dct['own_values']
            return domain
        elif dct['__ref'] == 'context':
            context = Context(None, key=dct['__id'])
            if 'own_values' in dct:
                context.own = dct['own_values']
            return context
        elif dct["__ref"] == "compound_domain":
            cdomain = CompoundDomain()
            for el in dct["__domains"]:
                cdomain.domains.append(non_literal_decoder(el))
            return cdomain
        elif dct["__ref"] == "compound_context":
            ccontext = CompoundContext()
            for el in dct["__contexts"]:
                ccontext.contexts.append(non_literal_decoder(el))
            return ccontext
    return dct

# TODO: use abstract base classes if 2.6+?
class BaseDomain(object):
    def evaluate(self, context=None):
        raise NotImplementedError('Non literals must implement evaluate()')

class BaseContext(object):
    def evaluate(self, context=None):
        raise NotImplementedError('Non literals must implement evaluate()')

class Domain(BaseDomain):
    def __init__(self, session, domain_string=None, key=None):
        """ Uses session information to store the domain string and map it to a
        domain key, which can be safely round-tripped to the client.

        If initialized with a domain string, will generate a key for that
        string and store the domain string out of the way. When initialized
        with a key, considers this key is a reference to an existing domain
        string.

        :param session: the OpenERP Session to use when evaluating the domain
        :type session: openerpweb.openerpweb.OpenERPSession
        :param str domain_string: a non-literal domain in string form
        :param str key: key used to retrieve the domain string
        """
        if domain_string and key:
            raise ValueError("A nonliteral domain can not take both a key "
                             "and a domain string")

        self.session = session
        self.own = {}
        if domain_string:
            self.key = binascii.hexlify(
                hashlib.sha256(domain_string).digest()[:SHORT_HASH_BYTES_SIZE])
            self.session.domains_store[self.key] = domain_string
        elif key:
            self.key = key

    def get_domain_string(self):
        """ Retrieves the domain string linked to this non-literal domain in
        the provided session.
        """
        return self.session.domains_store[self.key]

    def evaluate(self, context=None):
        """ Forces the evaluation of the linked domain, using the provided
        context (as well as the session's base context), and returns the
        evaluated result.
        """
        ctx = self.session.evaluation_context(context)
        if self.own:
            ctx.update(self.own)
        return eval(self.get_domain_string(), ctx)

class Context(BaseContext):
    def __init__(self, session, context_string=None, key=None):
        """ Uses session information to store the context string and map it to
        a key (stored in a secret location under a secret mountain), which can
        be safely round-tripped to the client.

        If initialized with a context string, will generate a key for that
        string and store the context string out of the way. When initialized
        with a key, considers this key is a reference to an existing context
        string.

        :param session: the OpenERP Session to use when evaluating the context
        :type session: openerpweb.openerpweb.OpenERPSession
        :param str context_string: a non-literal context in string form
        :param str key: key used to retrieve the context string
        """
        if context_string and key:
            raise ValueError("A nonliteral domain can not take both a key "
                             "and a domain string")

        self.session = session
        self.own = {}
        if context_string:
            self.key = binascii.hexlify(
                hashlib.sha256(context_string).digest()[:SHORT_HASH_BYTES_SIZE])
            self.session.contexts_store[self.key] = context_string
        elif key:
            self.key = key

    def get_context_string(self):
        """ Retrieves the context string linked to this non-literal context in
        the provided session.
        """
        return self.session.contexts_store[self.key]

    def evaluate(self, context=None):
        """ Forces the evaluation of the linked context, using the provided
        context (as well as the session's base context), and returns the
        evaluated result.
        """
        ctx = self.session.evaluation_context(context)
        if self.own:
            ctx.update(self.own)
        return eval(self.get_context_string(),
                    ctx)

class CompoundDomain(BaseDomain):
    def __init__(self, *domains):
        self.domains = []
        self.session = None
        for domain in domains:
            self.add(domain)
        
    def evaluate(self, context=None):
        final_domain = []
        for domain in self.domains:
            if not isinstance(domain, (list, BaseDomain)):
                raise TypeError("Domain %r is not a list or a nonliteral Domain",
                                 domain)
                
            if isinstance(domain, list):
                final_domain.extend(domain)
                continue
            
            ctx = dict(context or {})
            ctx['context'] = ctx
            
            domain.session = self.session
            final_domain.extend(domain.evaluate(ctx))
        return final_domain
    
    def add(self, domain):
        self.domains.append(domain)
        return self

class CompoundContext(BaseContext):
    def __init__(self, *contexts):
        self.contexts = []
        self.session = None
        for context in contexts:
            self.add(context)
    
    def evaluate(self, context=None):
        ctx = dict(context or {})
        final_context = {}
        for context_to_eval in self.contexts:
            if not isinstance(context_to_eval, (dict, BaseContext)):
                raise TypeError("Context %r is not a dict or a nonliteral Context",
                                 context_to_eval)
    
            if isinstance(context_to_eval, dict):
                final_context.update(context_to_eval)
                continue
            
            ctx.update(final_context)
            ctx["context"] = ctx
            
            context_to_eval.session = self.session
            final_context.update(context_to_eval.evaluate(ctx))
        return final_context
            
    def add(self, context):
        self.contexts.append(context)
        return self
        
