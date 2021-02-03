# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.sale.tests.test_sale_product_attribute_value_config import TestSaleProductAttributeValueSetup
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestWebsiteSaleProductAttributeValueConfig(TestSaleProductAttributeValueSetup):

    def test_get_combination_info(self):
        current_website = self.env['website'].get_current_website()
        pricelist = current_website.get_current_pricelist()

        self.computer = self.computer.with_context(website_id=current_website.id)

        # make sure the pricelist has a 10% discount
        pricelist.item_ids = self.env['product.pricelist.item'].create({
            'price_discount': 10,
            'compute_price': 'formula',
        })

        discount_rate = 0.9

        # make sure there is a 15% tax on the product
        tax = self.env['account.tax'].create({'name': "Test tax", 'amount': 15})
        self.computer.taxes_id = tax
        tax_ratio = (100 + tax.amount) / 100

        currency_ratio = 2
        pricelist.currency_id = self._setup_currency(currency_ratio)

        # ensure pricelist is set to with_discount
        pricelist.discount_policy = 'with_discount'

        # CASE: B2B setting
        group_tax_included = self.env.ref('account.group_show_line_subtotals_tax_included').with_context(active_test=False)
        group_tax_excluded = self.env.ref('account.group_show_line_subtotals_tax_excluded').with_context(active_test=False)
        group_tax_included.users -= self.env.user
        group_tax_excluded.users |= self.env.user

        combination_info = self.computer._get_combination_info()
        self.assertEqual(combination_info['price'], 2222 * discount_rate * currency_ratio)
        self.assertEqual(combination_info['list_price'], 2222 * discount_rate * currency_ratio)
        self.assertEqual(combination_info['has_discounted_price'], False)

        # CASE: B2C setting
        group_tax_excluded.users -= self.env.user
        group_tax_included.users |= self.env.user

        combination_info = self.computer._get_combination_info()
        self.assertEqual(combination_info['price'], 2222 * discount_rate * currency_ratio * tax_ratio)
        self.assertEqual(combination_info['list_price'], 2222 * discount_rate * currency_ratio * tax_ratio)
        self.assertEqual(combination_info['has_discounted_price'], False)

        # CASE: pricelist 'without_discount'
        pricelist.discount_policy = 'without_discount'

        # ideally we would need to use compare_amounts everywhere, but this is
        # the only rounding where it fails without it
        combination_info = self.computer._get_combination_info()
        self.assertEqual(pricelist.currency_id.compare_amounts(combination_info['price'], 2222 * discount_rate * currency_ratio * tax_ratio), 0)
        self.assertEqual(pricelist.currency_id.compare_amounts(combination_info['list_price'], 2222 * currency_ratio * tax_ratio), 0)
        self.assertEqual(combination_info['has_discounted_price'], True)

    def test_get_combination_info_with_fpos(self):
        self.env.user.partner_id.country_id = False
        current_website = self.env['website'].get_current_website()
        pricelist = current_website.get_current_pricelist()
        (self.env['product.pricelist'].search([]) - pricelist).write({'active': False})

        test_product = self.env['product.template'].create({
            'name': 'Test Product',
            'price': 2000,
        }).with_context(website_id=current_website.id)

        # Add fixed price for pricelist
        pricelist.item_ids = self.env['product.pricelist.item'].create({
            'applied_on': "1_product",
            'base': "list_price",
            'compute_price': "fixed",
            'fixed_price': 500,
            'product_tmpl_id': test_product.id,
        })
        # Add 15% tax on product
        tax15 = self.env['account.tax'].create({'name': "Test tax 15", 'amount': 15})
        tax0 = self.env['account.tax'].create({'name': "Test tax 0", 'amount': 0})
        test_product.taxes_id = tax15

        # Enable tax included
        group_tax_included = self.env.ref('account.group_show_line_subtotals_tax_included').with_context(active_test=False)
        group_tax_excluded = self.env.ref('account.group_show_line_subtotals_tax_excluded').with_context(active_test=False)
        group_tax_excluded.users -= self.env.user
        group_tax_included.users |= self.env.user

        # Create fiscal position for belgium mapping taxes 15% -> 0%
        fpos = self.env['account.fiscal.position'].create({
            'name': 'test',
            'auto_apply': True,
            'country_id': self.env.ref('base.be').id,
        })
        self.env['account.fiscal.position.tax'].create({
            'position_id': fpos.id,
            'tax_src_id': tax15.id,
            'tax_dest_id': tax0.id,
        })

        combination_info = test_product._get_combination_info()
        self.assertEqual(combination_info['price'], 575, "500$ + 15% tax")
        self.assertEqual(combination_info['list_price'], 575, "500$ + 15% tax (2)")

        # Now with fiscal position, taxes should be mapped
        self.env.user.partner_id.country_id = self.env.ref('base.be').id
        combination_info = test_product._get_combination_info()
        self.assertEqual(combination_info['price'], 500, "500% + 0% tax (mapped from fp 15% -> 0% for BE)")
        self.assertEqual(combination_info['list_price'], 500, "500% + 0% tax (mapped from fp 15% -> 0% for BE) (2)")
