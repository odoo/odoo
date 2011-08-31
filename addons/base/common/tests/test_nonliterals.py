# -*- coding: utf-8 -*-
import mock
import simplejson
import unittest2

from openerpweb.nonliterals import Domain, Context
import openerpweb.nonliterals
import openerpweb.openerpweb

class NonLiteralDomainTest(unittest2.TestCase):
    def setUp(self):
        self.session = mock.Mock(spec=openerpweb.openerpweb.OpenERPSession)
        self.session.domains_store = {}
    def test_store_domain(self):
        d = Domain(self.session, "some arbitrary string")

        self.assertEqual(
            self.session.domains_store[d.key],
            "some arbitrary string")

    def test_get_domain_back(self):
        d = Domain(self.session, "some arbitrary string")

        self.assertEqual(
            d.get_domain_string(),
            "some arbitrary string")
    def test_retrieve_second_domain(self):
        """ A different domain should be able to retrieve the nonliteral set
        previously
        """
        key = Domain(self.session, "some arbitrary string").key

        self.assertEqual(
            Domain(self.session, key=key).get_domain_string(),
            "some arbitrary string")

    def test_key_and_string(self):
        self.assertRaises(
            ValueError, Domain, None, domain_string="a", key="b")

    def test_eval(self):
        self.session.evaluation_context.return_value = {'foo': 3}
        result = Domain(self.session, "[('a', '=', foo)]").evaluate({'foo': 3})
        self.assertEqual(
            result, [('a', '=', 3)])

    def test_own_values(self):
        self.session.evaluation_context.return_value = {}
        domain = Domain(self.session, "[('a', '=', self)]")
        domain.own = {'self': 3}
        result = domain.evaluate()
        self.assertEqual(
            result, [('a', '=', 3)])

class NonLiteralContextTest(unittest2.TestCase):
    def setUp(self):
        self.session = mock.Mock(spec=openerpweb.openerpweb.OpenERPSession)
        self.session.contexts_store = {}
    def test_store_domain(self):
        c = Context(self.session, "some arbitrary string")

        self.assertEqual(
            self.session.contexts_store[c.key],
            "some arbitrary string")

    def test_get_domain_back(self):
        c = Context(self.session, "some arbitrary string")

        self.assertEqual(
            c.get_context_string(),
            "some arbitrary string")
    def test_retrieve_second_domain(self):
        """ A different domain should be able to retrieve the nonliteral set
        previously
        """
        key = Context(self.session, "some arbitrary string").key

        self.assertEqual(
            Context(self.session, key=key).get_context_string(),
            "some arbitrary string")

    def test_key_and_string(self):
        self.assertRaises(
            ValueError, Context, None, context_string="a", key="b")

    def test_eval(self):
        self.session.evaluation_context.return_value = {'foo': 3}
        result = Context(self.session, "[('a', '=', foo)]")\
            .evaluate({'foo': 3})
        self.assertEqual(
            result, [('a', '=', 3)])

    def test_own_values(self):
        self.session.evaluation_context.return_value = {}
        context = Context(self.session, "{'a': self}")
        context.own = {'self': 3}
        result = context.evaluate()
        self.assertEqual(
            result, {'a': 3})

class NonLiteralJSON(unittest2.TestCase):
    def setUp(self):
        self.session = mock.Mock(spec=openerpweb.openerpweb.OpenERPSession)
        self.session.domains_store = {}
        self.session.contexts_store = {}

    def test_encode_domain(self):
        d = Domain(self.session, "some arbitrary string")
        self.assertEqual(
            simplejson.dumps(d, cls=openerpweb.nonliterals.NonLiteralEncoder),
            simplejson.dumps({'__ref': 'domain', '__id': d.key}))

    def test_decode_domain(self):
        encoded = simplejson.dumps(
            Domain(self.session, "some arbitrary string"),
            cls=openerpweb.nonliterals.NonLiteralEncoder)

        domain = simplejson.loads(
            encoded, object_hook=openerpweb.nonliterals.non_literal_decoder)
        domain.session = self.session

        self.assertEqual(
            domain.get_domain_string(),
            "some arbitrary string"
        )

    def test_encode_context(self):
        c = Context(self.session, "some arbitrary string")
        self.assertEqual(
            simplejson.dumps(c, cls=openerpweb.nonliterals.NonLiteralEncoder),
            simplejson.dumps({'__ref': 'context', '__id': c.key}))

    def test_decode_context(self):
        encoded = simplejson.dumps(
            Context(self.session, "some arbitrary string"),
            cls=openerpweb.nonliterals.NonLiteralEncoder)

        context = simplejson.loads(
            encoded, object_hook=openerpweb.nonliterals.non_literal_decoder)
        context.session = self.session

        self.assertEqual(
            context.get_context_string(),
            "some arbitrary string"
        )
