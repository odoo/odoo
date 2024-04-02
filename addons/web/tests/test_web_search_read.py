# -*- coding: utf-8 -*-
from odoo.tests import common
from unittest.mock import patch


@common.tagged('post_install', '-at_install')
class TestWebSearchRead(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.ResCurrency = cls.env['res.currency'].with_context(active_test=False)
        cls.max = cls.ResCurrency.search_count([])
        cls.env.cr.execute("ANALYZE res_currency")

    def assert_web_search_read(self, expected_length, expected_records_length, expected_search_count_called=True,
                               **kwargs):
        with patch.object(type(self.ResCurrency), '_estimate_count', wraps=self.ResCurrency._estimate_count) as patched_count:
            results = self.ResCurrency.web_search_read(domain=[], specification={'id':{}}, **kwargs)

        self.assertEqual(results['length'], expected_length)
        self.assertEqual(len(results['records']), expected_records_length)
        self.assertEqual(patched_count.called, expected_search_count_called)

    def test_unity_web_search_read(self):
        self.assert_web_search_read(self.max, self.max, expected_search_count_called=False)
        self.assert_web_search_read(self.max, 2, limit=2)
        self.assert_web_search_read(self.max, 2, limit=2, offset=10)
