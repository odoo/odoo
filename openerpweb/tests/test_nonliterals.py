# -*- coding: utf-8 -*-
import mock
import unittest2

from openerpweb.nonliterals import Domain
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
