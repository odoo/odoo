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

        result = self.env["res.partner"].web_name_search("", {"display_name": {}, "street": {}})[0]
        self.assertTrue("display_name" in result)
        self.assertTrue("street" in result)
        self.assertTrue("__formatted_display_name" in result)

        result = self.env["res.partner"].web_name_search("", {"street": {}})[0]
        self.assertTrue("display_name" not in result)
        self.assertTrue("street" in result)
        self.assertTrue("__formatted_display_name" not in result)

    def _create_order_prefix_partners(self):
        marker = 'ZQXW_ORDER_PREFIX'
        Partner = self.env['res.partner']
        Partner.search([('name', '=like', f'{marker}%')]).unlink()
        # 'ref' is the field floated by order_prefix. It is independent of the
        # model _order, so the prefix demonstrably changes the result, and it is
        # a plain stored field, so the values are not altered by other modules.
        return marker, Partner.create([
            {'name': f'{marker} AAA', 'ref': 'AA'},
            {'name': f'{marker} BBB', 'ref': 'ZZ'},
            {'name': f'{marker} CCC', 'ref': 'AA'},
            {'name': f'{marker} DDD', 'ref': 'ZZ'},
        ])

    def test_web_search_read_order_prefix(self):
        """ order_prefix layers on top of the model _order for the view only;
        it never affects search()/the API. """
        Partner = self.env['res.partner']
        marker, partners = self._create_order_prefix_partners()
        domain = [('name', '=like', f'{marker}%')]
        ref_by_id = {p.id: p.ref for p in partners}

        baseline = [r['id'] for r in Partner.web_search_read(domain, {'id': {}})['records']]
        # web_search_read without a prefix matches the model _order, like search()
        self.assertEqual(baseline, Partner.search(domain).ids)

        prefixed = [r['id'] for r in Partner.web_search_read(
            domain, {'id': {}}, order_prefix='ref desc')['records']]
        zz = [i for i in baseline if ref_by_id[i] == 'ZZ']
        aa = [i for i in baseline if ref_by_id[i] == 'AA']
        # 'ZZ' refs float to the top, each block keeping its _order
        self.assertEqual(prefixed, zz + aa)
        # the data actually exercises a reordering (guard against a trivial pass)
        self.assertNotEqual(prefixed, baseline)
        # the prefix is presentation-only: search() stays untouched
        self.assertEqual(Partner.search(domain).ids, baseline)

    def test_web_read_group_order_prefix(self):
        """ order_prefix floats records to the top inside each unfolded group,
        without affecting the order of the groups themselves. """
        Partner = self.env['res.partner']
        marker, partners = self._create_order_prefix_partners()
        partners.write({'function': f'{marker}_ROLE'})
        domain = [('name', '=like', f'{marker}%')]
        spec = {'id': {}, 'ref': {}}

        plain = Partner.web_read_group(domain, ['function'], auto_unfold=True,
                                       unfold_read_specification=spec)
        self.assertEqual(len(plain['groups']), 1)
        plain_records = plain['groups'][0]['__records']
        plain_ids = [r['id'] for r in plain_records]

        prefixed = Partner.web_read_group(domain, ['function'], auto_unfold=True,
                                          unfold_read_specification=spec,
                                          order_prefix='ref desc')
        prefixed_ids = [r['id'] for r in prefixed['groups'][0]['__records']]
        zz = [r['id'] for r in plain_records if r['ref'] == 'ZZ']
        aa = [r['id'] for r in plain_records if r['ref'] == 'AA']
        self.assertEqual(prefixed_ids, zz + aa)
        self.assertNotEqual(prefixed_ids, plain_ids)
