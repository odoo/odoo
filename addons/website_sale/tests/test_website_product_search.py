# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged
from odoo.addons.base.tests.common import TransactionCase


@tagged('post_install', '-at_install')
class TestWebsiteProductSearch(TransactionCase):

    def _search_products(self, search):
        current_website = self.env['website'].get_current_website()
        options = {
            'displayDescription': False,
            'displayDetail': False,
            'displayExtraLink': False,
            'displayImage': False,
            'display_currency': current_website.get_current_pricelist().currency_id,
        }
        product_count, details, _ = current_website._search_with_fuzzy("products_only", search,
            limit=None, order='', options=options)
        return product_count, details[0].get('results')

    def setUp(self):
        super(TestWebsiteProductSearch, self).setUp()

        self.env['product.product'].create({
            'name': 'My Wonderful MAC - M1',
            'default_code': 'MAC0001',
            'list_price': 1400.0,
            'website_published': True,
        })
        self.env['product.product'].create({
            'name': 'My Wonderful MAC - Vanilla',
            'default_code': 'MAC0002',
            'list_price': 1000.0,
            'website_published': True,
        })

    def test_01_search_by_reference(self):
        """Test to make sure that search works with references"""
        product_count, products = self._search_products('MAC0001')
        self.assertEqual(product_count, 1)
        self.assertEqual(products[0].name, 'My Wonderful MAC - M1')

    def test_02_search_by_name(self):
        """Test to make sure that search works with name"""
        product_count, products = self._search_products('My Wonderful MAC -')
        self.assertEqual(product_count, 2)
        self.assertEqual(products[0].name, 'My Wonderful MAC - M1')
        self.assertEqual(products[1].name, 'My Wonderful MAC - Vanilla')
