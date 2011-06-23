# -*- coding: utf-8 -*-
import unittest2
from openerpweb.nonliterals import Domain, Context, CompoundDomain, CompoundContext
import openerpweb.openerpweb

class TestOpenERPSession(unittest2.TestCase):
    def setUp(self):
        self.module = object()
        self.session = openerpweb.openerpweb.OpenERPSession()
        self.session._uid = -1
        self.session.context = {
            'current_date': '1945-08-05',
            'date': self.module,
            'time': self.module,
            'datetime': self.module,
            'relativedelta': self.module
        }
    def test_base_eval_context(self):
        self.assertEqual(type(self.session.base_eval_context), dict)
        self.assertEqual(
            self.session.base_eval_context,
            {'uid': -1, 'current_date': '1945-08-05',
             'date': self.module, 'datetime': self.module, 'time': self.module,
             'relativedelta': self.module}
        )

    def test_evaluation_context_nocontext(self):
        self.assertEqual(
            type(self.session.evaluation_context()),
            dict
        )
        self.assertEqual(
            self.session.evaluation_context(),
            self.session.base_eval_context
        )

    def test_evaluation_context(self):
        ctx = self.session.evaluation_context({'foo': 3})
        self.assertEqual(
            type(ctx),
            dict
        )
        self.assertIn('foo', ctx)

    def test_eval_with_context(self):
        self.assertEqual(
            eval('current_date', self.session.evaluation_context()),
            '1945-08-05')

        self.assertEqual(
            eval('foo + 3', self.session.evaluation_context({'foo': 4})),
            7)

    def test_eval_domain_typeerror(self):
        self.assertRaises(
            TypeError, self.session.eval_domain, "foo")

    def test_eval_domain_list(self):
        self.assertEqual(
            self.session.eval_domain([]),
            [])

    def test_eval_nonliteral_domain(self):
        d = Domain(self.session, "[('foo', 'is', 3)]")
        self.assertEqual(
            self.session.eval_domain(d),
            [('foo', 'is', 3)])

    def test_eval_nonliteral_domain_bykey(self):
        key = Domain(
            self.session, "[('foo', 'is', 3)]").key

        d = Domain(None, key=key)
        self.assertEqual(
            self.session.eval_domain(d),
            [('foo', 'is', 3)])

    def test_eval_empty_domains(self):
        self.assertEqual(
            self.session.eval_domain(CompoundDomain()),
            [])

    def test_eval_literal_domains(self):
        domains = [
            [('a', 'is', 3)],
            [('b', 'ilike', 'foo')],
            ['|',
             ('c', '=', False),
             ('c', 'in', ['a', 'b', 'c'])]
        ]
        self.assertEqual(
            self.session.eval_domain(CompoundDomain(*domains)),
            [
                ('a', 'is', 3),
                ('b', 'ilike', 'foo'),
                '|',
                ('c', '=', False),
                ('c', 'in', ['a', 'b', 'c'])
            ])
    def test_eval_nonliteral_domains(self):
        domains = [
            Domain(self.session, "[('uid', '=', uid)]"),
            Domain(self.session,
                   "['|', ('date', '<', current_date),"
                        " ('date', '>', current_date)]")]
        self.assertEqual(
            self.session.eval_domain(CompoundDomain(*domains)),
            [('uid', '=', -1),
             '|', ('date', '<', '1945-08-05'), ('date', '>', '1945-08-05')]
        )
