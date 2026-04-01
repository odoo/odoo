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

    def assert_web_search_read(self, expected_length, expected_records_length, expected_search_count_called=True,
                               **kwargs):
        original_search_count = self.ResCurrency.search_count
        search_count_called = [False]

        def search_count(obj, *method_args, **method_kwargs):
            search_count_called[0] = True
            return original_search_count(*method_args, **method_kwargs)

        with patch('odoo.addons.base.models.res_currency.ResCurrency.search_count', new=search_count):
            results = self.ResCurrency.web_search_read(domain=[], specification={'id':{}}, **kwargs)

        self.assertEqual(results['length'], expected_length)
        self.assertEqual(len(results['records']), expected_records_length)
        self.assertEqual(search_count_called[0], expected_search_count_called)

    def test_unity_web_search_read(self):
        self.assert_web_search_read(self.max, self.max, expected_search_count_called=False)
        self.assert_web_search_read(self.max, 2, limit=2)
        self.assert_web_search_read(self.max, 2, limit=2, offset=10)
        self.assert_web_search_read(2, 2, limit=2, count_limit=2, expected_search_count_called=False)
        self.assert_web_search_read(20, 2, limit=2, offset=10, count_limit=20)
        self.assert_web_search_read(12, 2, limit=2, offset=10, count_limit=12, expected_search_count_called=False)

    def test_web_name_search(self):
        result = self.env["res.partner"].web_name_search("", {"display_name": {}})[0]
        self.assertTrue("display_name" in result)
        self.assertTrue("__formatted_display_name" in result)
