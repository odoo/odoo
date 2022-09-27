# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.sale.tests.test_sale_product_attribute_value_config import TestSaleProductAttributeValueCommon
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo import Command
from odoo.tests import tagged
from odoo.addons.website.tools import MockRequest


@tagged('post_install', '-at_install', 'product_attribute')
class TestWebsiteSaleProductAttributeValueConfig(AccountTestInvoicingCommon, TestSaleProductAttributeValueCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        # Use the testing environment.
        cls.computer = cls.computer.with_env(cls.env)

    def test_get_combination_info(self):
        # Setup pricelist: make sure the pricelist has a 10% discount
        pricelist = self.env['product.pricelist'].create({
            'name': "test_get_combination_info",
            'currency_id': self.currency_data['currency'].id,
            'discount_policy': 'with_discount',
            'company_id': self.env.company.id,
            'item_ids': [Command.create({
                'price_discount': 10,
                'compute_price': 'formula',
            })],
        })

        # Setup website.
        website = self.env['website'].create({
            'name': "Test website",
            'company_id': self.env.company.id,
            'user_id': self.env.user.id,
            'pricelist_ids': [Command.set(pricelist.ids)],
        })

        # Setup product with 15% tax.
        product_template = self.computer.with_context(website_id=website.id)
        product_template.write({
            'taxes_id': [Command.set(self.company_data['default_tax_sale'].ids)],
            'company_id': self.env.company.id,
        })

        tax_ratio = 1.15
        discount_rate = 0.9
        currency_ratio = 2

        # CASE: B2B setting (default)
        combination_info = product_template._get_combination_info(pricelist=pricelist)
        self.assertEqual(combination_info['price'], 2222 * discount_rate * currency_ratio)
        self.assertEqual(combination_info['list_price'], 2222 * discount_rate * currency_ratio)
        self.assertEqual(combination_info['price_extra'], 222 * currency_ratio)
        self.assertEqual(combination_info['has_discounted_price'], False)

        # CASE: B2C setting
        group_tax_included = self.env.ref('account.group_show_line_subtotals_tax_included').with_context(active_test=False)
        group_tax_excluded = self.env.ref('account.group_show_line_subtotals_tax_excluded').with_context(active_test=False)
        group_tax_excluded.users -= self.env.user
        group_tax_included.users |= self.env.user

        combination_info = product_template._get_combination_info(pricelist=pricelist)
        self.assertEqual(combination_info['price'], 2222 * discount_rate * currency_ratio * tax_ratio)
        self.assertEqual(combination_info['list_price'], 2222 * discount_rate * currency_ratio * tax_ratio)
        self.assertEqual(combination_info['price_extra'], round(222 * currency_ratio * tax_ratio, 2))
        self.assertEqual(combination_info['has_discounted_price'], False)

        # CASE: pricelist 'without_discount'
        pricelist.discount_policy = 'without_discount'

        combination_info = product_template._get_combination_info(pricelist=pricelist)
        self.assertEqual(combination_info['price'], pricelist.currency_id.round(2222 * discount_rate * currency_ratio * tax_ratio), 0)
        self.assertEqual(combination_info['list_price'], pricelist.currency_id.round(2222 * currency_ratio * tax_ratio), 0)
        self.assertEqual(combination_info['price_extra'], pricelist.currency_id.round(222 * currency_ratio * tax_ratio), 0)
        self.assertEqual(combination_info['has_discounted_price'], True)

    def test_get_combination_info_with_fpos(self):
        # Setup product.
        product = self.env['product.template'].create({
            'name': 'Test Product',
            'list_price': 2000,
            'taxes_id': [Command.set(self.company_data['default_tax_sale'].ids)],
            'company_id': self.env.company.id,
        })

        # Setup pricelist: make sure the pricelist has a 10% discount
        pricelist = self.env['product.pricelist'].create({
            'name': "test_get_combination_info",
            'company_id': self.env.company.id,
            'item_ids': [Command.create({
                'applied_on': "1_product",
                'base': "list_price",
                'compute_price': "fixed",
                'fixed_price': 500,
                'product_tmpl_id': product.id,
            })],
        })

        # Setup website.
        website = self.env['website'].create({
            'name': "Test website",
            'company_id': self.env.company.id,
            'user_id': self.env.user.id,
            'pricelist_ids': [Command.set(pricelist.ids)],
        })

        product = product.with_context(website_id=website.id)

        # Setup product attributes.
        computer_ssd_attribute_lines = self.env['product.template.attribute.line'].create({
            'product_tmpl_id': product.id,
            'attribute_id': self.ssd_attribute.id,
            'value_ids': [(6, 0, [self.ssd_256.id])],
        })
        computer_ssd_attribute_lines.product_template_value_ids[0].price_extra = 200

        # Enable tax included
        group_tax_included = self.env.ref('account.group_show_line_subtotals_tax_included').with_context(active_test=False)
        group_tax_excluded = self.env.ref('account.group_show_line_subtotals_tax_excluded').with_context(active_test=False)
        group_tax_excluded.users -= self.env.user
        group_tax_included.users |= self.env.user

        combination_info = product._get_combination_info(pricelist=pricelist)
        self.assertEqual(combination_info['price'], 575, "500$ + 15% tax")
        self.assertEqual(combination_info['list_price'], 575, "500$ + 15% tax (2)")
        self.assertEqual(combination_info['price_extra'], 230, "200$ + 15% tax")

        # Setup fiscal position 15% => 0%.
        us_country = self.env.ref('base.us')
        tax0 = self.env['account.tax'].create({'name': "Test tax 0", 'amount': 0})
        self.env['account.fiscal.position'].create({
            'name': "test_get_combination_info_with_fpos",
            'auto_apply': True,
            'country_id': us_country.id,
            'tax_ids': [Command.create({
                'tax_src_id': self.company_data['default_tax_sale'].id,
                'tax_dest_id': tax0.id,
            })],
        })

        # Now with fiscal position, taxes should be mapped
        self.env.user.partner_id.country_id = us_country
        combination_info = product._get_combination_info(pricelist=pricelist)
        self.assertEqual(combination_info['price'], 500, "500% + 0% tax (mapped from fp 15% -> 0%)")
        self.assertEqual(combination_info['list_price'], 500, "500% + 0% tax (mapped from fp 15% -> 0%)")
        self.assertEqual(combination_info['price_extra'], 200, "200% + 0% tax (mapped from fp 15% -> 0%)")

        # Try same flow with tax included
        self.company_data['default_tax_sale'].price_include = True

        # Reset / Safety check
        self.env.user.partner_id.country_id = None
        combination_info = product._get_combination_info(pricelist=pricelist)
        self.assertEqual(combination_info['price'], 500, "434.78$ + 15% tax")
        self.assertEqual(combination_info['list_price'], 500, "434.78$ + 15% tax (2)")
        self.assertEqual(combination_info['price_extra'], 200, "173.91$ + 15% tax")

        # Now with fiscal position, taxes should be mapped
        self.env.user.partner_id.country_id = us_country.id
        combination_info = product._get_combination_info(pricelist=pricelist)
        self.assertEqual(round(combination_info['price'], 2), 434.78, "434.78$ + 0% tax (mapped from fp 15% -> 0%)")
        self.assertEqual(round(combination_info['list_price'], 2), 434.78, "434.78$ + 0% tax (mapped from fp 15% -> 0%)")
        self.assertEqual(combination_info['price_extra'], 173.91, "173.91$ + 0% tax (mapped from fp 15% -> 0%)")


@tagged('post_install', '-at_install', 'product_pricelist')
class TestWebsiteSaleProductPricelist(AccountTestInvoicingCommon, TestSaleProductAttributeValueCommon):
    def test_cart_update_with_fpos(self):
        # We will test that the mapping of an 10% included tax by a 6% by a fiscal position is taken into account when updating the cart
        self.env.user.partner_id.country_id = False
        current_website = self.env['website'].get_current_website()
        pricelist = current_website.get_current_pricelist()
        (self.env['product.pricelist'].search([]) - pricelist).write({'active': False})
        # Add 10% tax on product
        tax10 = self.env['account.tax'].create({'name': "Test tax 10", 'amount': 10, 'price_include': True, 'amount_type': 'percent'})
        tax6 = self.env['account.tax'].create({'name': "Test tax 6", 'amount': 6, 'price_include': True, 'amount_type': 'percent'})

        test_product = self.env['product.template'].create({
            'name': 'Test Product',
            'list_price': 110,
            'taxes_id': [(6, 0, [tax10.id])],
        }).with_context(website_id=current_website.id)

        # Add discout of 50% for pricelist
        pricelist.item_ids = self.env['product.pricelist.item'].create({
            'applied_on': "1_product",
            'base': "list_price",
            'compute_price': "percentage",
            'percent_price': 50,
            'product_tmpl_id': test_product.id,
        })

        pricelist.discount_policy = 'without_discount'

        # Create fiscal position mapping taxes 10% -> 6%
        fpos = self.env['account.fiscal.position'].create({
            'name': 'test',
        })
        self.env['account.fiscal.position.tax'].create({
            'position_id': fpos.id,
            'tax_src_id': tax10.id,
            'tax_dest_id': tax6.id,
        })
        so = self.env['sale.order'].create({
            'partner_id': self.env.user.partner_id.id,
        })
        sol = self.env['sale.order.line'].create({
            'product_id': test_product.product_variant_id.id,
            'order_id': so.id,
        })
        self.assertEqual(round(sol.price_total), 55.0, "110$ with 50% discount 10% included tax")
        self.assertEqual(round(sol.price_tax), 5.0, "110$ with 50% discount 10% included tax")
        so.pricelist_id = pricelist
        so.fiscal_position_id = fpos
        sol._compute_tax_id()
        with MockRequest(self.env, website=current_website, sale_order_id=so.id):
            so._cart_update(product_id=test_product.product_variant_id.id, line_id=sol.id, set_qty=2)
        self.assertEqual(round(sol.price_total), 106, "2 units @ 100$ with 50% discount + 6% tax (mapped from fp 10% -> 6%)")

    def test_cart_update_with_fpos_no_variant_product(self):
        # We will test that the mapping of an 10% included tax by a 0% by a fiscal position is taken into account when updating the cart for no_variant product
        self.env.user.partner_id.country_id = False
        current_website = self.env['website'].get_current_website()
        pricelist = current_website.get_current_pricelist()
        (self.env['product.pricelist'].search([]) - pricelist).write({'active': False})
        # Add 10% tax on product
        tax10 = self.env['account.tax'].create({'name': "Test tax 10", 'amount': 10, 'price_include': True, 'amount_type': 'percent', 'type_tax_use': 'sale'})
        tax0 = self.env['account.tax'].create({'name': "Test tax 0", 'amount': 0, 'price_include': True, 'amount_type': 'percent', 'type_tax_use': 'sale'})

        # Create fiscal position mapping taxes 10% -> 0%
        fpos = self.env['account.fiscal.position'].create({
            'name': 'test',
        })
        self.env['account.fiscal.position.tax'].create({
            'position_id': fpos.id,
            'tax_src_id': tax10.id,
            'tax_dest_id': tax0.id,
        })

        product = self.env['product.product'].create({
            'name': 'prod_no_variant',
            'list_price': 110,
            'taxes_id': [(6, 0, [tax10.id])],
            'type': 'consu',
        })

        # create an attribute with one variant
        product_attribute = self.env['product.attribute'].create({
            'name': 'test_attr',
            'display_type': 'radio',
            'create_variant': 'no_variant',
        })

        # create attribute value
        a1 = self.env['product.attribute.value'].create({
            'name': 'pa_value',
            'attribute_id': product_attribute.id,
            'sequence': 1,
        })

        # set variant value to product template
        product_template = self.env['product.template'].search(
            [('name', '=', 'prod_no_variant')], limit=1)

        product_template.attribute_line_ids = [(0, 0, {
            'attribute_id': product_attribute.id,
            'value_ids': [(6, 0, [a1.id])],
        })]

        # publish the product on website
        product_template.is_published = True

        # create a so for user using the fiscal position

        so = self.env['sale.order'].create({
            'partner_id': self.env.user.partner_id.id,
        })
        sol = self.env['sale.order.line'].create({
            'name': product_template.name,
            'product_id': product.id,
            'product_uom_qty': 1,
            'product_uom': product_template.uom_id.id,
            'price_unit': product_template.list_price,
            'order_id': so.id,
            'tax_id': [(6, 0, [tax10.id])],
        })
        self.assertEqual(round(sol.price_total), 110.0, "110$ with 10% included tax")
        so.pricelist_id = pricelist
        so.fiscal_position_id = fpos
        sol._compute_tax_id()
        with MockRequest(self.env, website=current_website, sale_order_id=so.id):
            so._cart_update(product_id=product.id, line_id=sol.id, set_qty=2)
        self.assertEqual(round(sol.price_total), 200, "200$ with public price+ 0% tax (mapped from fp 10% -> 0%)")
