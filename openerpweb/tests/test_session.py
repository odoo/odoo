# -*- coding: utf-8 -*-
import unittest2
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
