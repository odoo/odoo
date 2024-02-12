# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase
from odoo.tools.tsquery import TSQuery


class TestTSQuery(TransactionCase):
    def test_tsquery_check_operator_and(self):
        """ Checks that the user can do a "and" between two query vectors. """
        q1 = TSQuery('english', 'hello')
        q2 = TSQuery('english', 'world')
        q3 = q1 & q2
        (q1_query, q1_query_param) = q1.to_sql()
        self.assertEqual(q1_query, 'websearch_to_tsquery(%s::regconfig, %s)')
        self.assertEqual(q1_query_param, ['english', 'hello'])
        (q2_query, q2_query_param) = q2.to_sql()
        self.assertEqual(q2_query, 'websearch_to_tsquery(%s::regconfig, %s)')
        self.assertEqual(q2_query_param, ['english', 'world'])
        (q3_query, q3_query_param) = q3.to_sql()
        self.assertEqual(q3_query, '(websearch_to_tsquery(%s::regconfig, %s) && websearch_to_tsquery(%s::regconfig, %s))')
        self.assertEqual(q3_query_param, ['english', 'hello', 'english', 'world'])

    def test_tsquery_check_operator_or(self):
        """ Checks that the user can do a "or" between two query vectors. """
        q1 = TSQuery('english', 'hello')
        q2 = TSQuery('english', 'world')
        q3 = q1 | q2
        (q1_query, q1_query_param) = q1.to_sql()
        self.assertEqual(q1_query, 'websearch_to_tsquery(%s::regconfig, %s)')
        self.assertEqual(q1_query_param, ['english', 'hello'])
        (q2_query, q2_query_param) = q2.to_sql()
        self.assertEqual(q2_query, 'websearch_to_tsquery(%s::regconfig, %s)')
        self.assertEqual(q2_query_param, ['english', 'world'])
        (q3_query, q3_query_param) = q3.to_sql()
        self.assertEqual(q3_query, '(websearch_to_tsquery(%s::regconfig, %s) || websearch_to_tsquery(%s::regconfig, %s))')
        self.assertEqual(q3_query_param, ['english', 'hello', 'english', 'world'])
