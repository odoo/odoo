# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time

from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.product.tests.common import ProductCommon


@tagged('post_install', '-at_install')
class TestProductRounding(ProductCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # test-specific currencies
        cls.currency_jpy = cls.env['res.currency'].create({
            'name': 'JPX',
            'symbol': '¥',
            'rounding': 1.0,
            'rate_ids': [Command.create({'rate': 133.6200, 'name': time.strftime('%Y-%m-%d')})],
        })

        cls.currency_cad = cls.env['res.currency'].create({
            'name': 'CXD',
            'symbol': '$',
            'rounding': 0.01,
            'rate_ids': [Command.create({'rate': 1.338800, 'name': time.strftime('%Y-%m-%d')})],
        })

        cls.pricelist_usd = cls.pricelist

        cls.pricelist_jpy = cls.env['product.pricelist'].create({
            'name': 'Pricelist Testing JPY',
            'currency_id': cls.currency_jpy.id,
        })

        cls.pricelist_cad = cls.env['product.pricelist'].create({
            'name': 'Pricelist Testing CAD',
            'currency_id': cls.currency_cad.id,
        })

        cls.product_1_dollar = cls.env['product.product'].create({
            'name': 'Test Product $1',
            'list_price': 1.00,
            'categ_id': cls.product_category.id,
        })

        cls.product_100_dollars = cls.env['product.product'].create({
            'name': 'Test Product $100',
            'list_price': 100.00,
            'categ_id': cls.product_category.id,
        })

    def test_no_discount_1_dollar_product(self):
        """Ensure that no discount is applied when there shouldn't be, even for very small amounts."""
        product = self.product_1_dollar

        product_in_jpy = product.with_context(pricelist=self.pricelist_jpy.id)
        discount_jpy = product_in_jpy._get_contextual_discount()
        self.assertAlmostEqual(discount_jpy, 0.0, places=6, msg="No discount should be applied for $1 product in Testing JPY.")

        product_in_usd = product.with_context(pricelist=self.pricelist_usd.id)
        discount_usd = product_in_usd._get_contextual_discount()
        self.assertAlmostEqual(discount_usd, 0.0, places=6, msg="No discount should be applied for $1 product in USD.")

        product_in_cad = product.with_context(pricelist=self.pricelist_cad.id)
        discount_cad = product_in_cad._get_contextual_discount()
        self.assertAlmostEqual(discount_cad, 0.0, places=6, msg="No discount should be applied for $1 product in Testing CAD.")

    def test_no_discount_100_dollars_product(self):
        """Ensure that no discount is applied when there shouldn't be, even for very small amounts."""
        product = self.product_100_dollars

        product_in_jpy = product.with_context(pricelist=self.pricelist_jpy.id)
        discount_jpy = product_in_jpy._get_contextual_discount()
        self.assertAlmostEqual(discount_jpy, 0.0, places=6, msg="No discount should be applied for $100 product in Testing JPY.")

        product_in_usd = product.with_context(pricelist=self.pricelist_usd.id)
        discount_usd = product_in_usd._get_contextual_discount()
        self.assertAlmostEqual(discount_usd, 0.0, places=6, msg="No discount should be applied for $100 product in USD.")

        product_in_cad = product.with_context(pricelist=self.pricelist_cad.id)
        discount_cad = product_in_cad._get_contextual_discount()
        self.assertAlmostEqual(discount_cad, 0.0, places=6, msg="No discount should be applied for $100 product in Testing CAD.")
