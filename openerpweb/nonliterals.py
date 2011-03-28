# -*- coding: utf-8 -*-
""" Manages the storage and lifecycle of non-literal domains and contexts
(and potentially other structures) which have to be evaluated with client data,
but still need to be safely round-tripped to and from the browser (and thus
can't be sent there themselves).
"""
import binascii
import hashlib
import simplejson.decoder
import simplejson.encoder

__all__ = ['Domain', 'Context', 'NonLiteralEncoder, non_literal_decoder']

#: 48 bits should be sufficient to have almost no chance of collision
#: with a million hashes, according to hg@67081329d49a
SHORT_HASH_BYTES_SIZE = 6

class NonLiteralEncoder(simplejson.encoder.JSONEncoder):
    def default(self, object):
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
        return super(NonLiteralEncoder, self).default(object)

def non_literal_decoder(dct):
    if '__ref' in dct:
        if dct['__ref'] == 'domain':
            return Domain(None, key=dct['__id'])
        elif dct['__ref'] == 'context':
            return Context(None, key=dct['__id'])
    return dct

class Domain(object):
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
        if domain_string:
            self.key = binascii.hexlify(
                hashlib.sha256(domain_string).digest()[:SHORT_HASH_BYTES_SIZE])
            self.session.domains_store[self.key] = domain_string
        elif key:
            self.key = key

    def get_domain_string(self):
        """ Retrieves the domain string linked to this non-literal domain in
        the provided session.

        :param session: the OpenERP Session used to store the domain string in
                        the first place.
        :type session: openerpweb.openerpweb.OpenERPSession
        """
        return self.session.domains_store[self.key]

    def evaluate(self, context=None):
        """ Forces the evaluation of the linked domain, using the provided
        context (as well as the session's base context), and returns the
        evaluated result.
        """
        return eval(self.get_domain_string(),
            self.session.evaluation_context(context))

class Context(object):
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
        if context_string:
            self.key = binascii.hexlify(
                hashlib.sha256(context_string).digest()[:SHORT_HASH_BYTES_SIZE])
            self.session.domains_store[self.key] = context_string
        elif key:
            self.key = key

    def get_context_string(self):
        """ Retrieves the context string linked to this non-literal context in
        the provided session.

        :param session: the OpenERP Session used to store the context string in
                        the first place.
        :type session: openerpweb.openerpweb.OpenERPSession
        """
        return self.session.domains_store[self.key]

    def evaluate(self, context=None):
        """ Forces the evaluation of the linked context, using the provided
        context (as well as the session's base context), and returns the
        evaluated result.
        """
        return eval(self.get_context_string(),
            self.session.evaluation_context(context))
