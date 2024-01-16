# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.sale.tests.test_sale_product_attribute_value_config import TestSaleProductAttributeValueCommon


class TestSaleCouponCommon(TestSaleProductAttributeValueCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        # set currency to not rely on demo data and avoid possible race condition
        cls.currency_ratio = 1.0
        cls.pricelist = cls.env.ref('product.list0')
        cls.pricelist.currency_id = cls._setup_currency(cls.currency_ratio)

        # Set all the existing programs to active=False to avoid interference
        cls.env['coupon.program'].search([]).write({'active': False})

        # create partner for sale order.
        cls.steve = cls.env['res.partner'].create({
            'name': 'Steve Bucknor',
            'email': 'steve.bucknor@example.com',
            'property_product_pricelist': cls.pricelist.id,
        })

        cls.empty_order = cls.env['sale.order'].create({
            'partner_id': cls.steve.id
        })

        cls.uom_unit = cls.env.ref('uom.product_uom_unit')

        # Taxes
        cls.tax_15pc_excl = cls.env['account.tax'].create({
            'name': "Tax 15%",
            'amount_type': 'percent',
            'amount': 15,
            'type_tax_use': 'sale',
        })

        cls.tax_10pc_incl = cls.env['account.tax'].create({
            'name': "10% Tax incl",
            'amount_type': 'percent',
            'amount': 10,
            'price_include': True,
        })

        cls.tax_10pc_base_incl = cls.env['account.tax'].create({
            'name': "10% Tax incl base amount",
            'amount_type': 'percent',
            'amount': 10,
            'price_include': True,
            'include_base_amount': True,
        })

        cls.tax_10pc_excl = cls.env['account.tax'].create({
            'name': "10% Tax excl",
            'amount_type': 'percent',
            'amount': 10,
            'price_include': False,
        })

        cls.tax_20pc_excl = cls.env['account.tax'].create({
            'name': "20% Tax excl",
            'amount_type': 'percent',
            'amount': 20,
            'price_include': False,
        })

        #products
        cls.product_A = cls.env['product.product'].create({
            'name': 'Product A',
            'list_price': 100,
            'sale_ok': True,
            'taxes_id': [(6, 0, [cls.tax_15pc_excl.id])],
        })

        cls.product_B = cls.env['product.product'].create({
            'name': 'Product B',
            'list_price': 5,
            'sale_ok': True,
            'taxes_id': [(6, 0, [cls.tax_15pc_excl.id])],
        })

        cls.product_C = cls.env['product.product'].create({
            'name': 'Product C',
            'list_price': 100,
            'sale_ok': True,
            'taxes_id': [(6, 0, [])],

        })

        # Immediate Program By A + B: get B free
        # No Conditions
        cls.immediate_promotion_program = cls.env['coupon.program'].create({
            'name': 'Buy A + 1 B, 1 B are free',
            'promo_code_usage': 'no_code_needed',
            'reward_type': 'product',
            'reward_product_id': cls.product_B.id,
            'rule_products_domain': "[('id', 'in', [%s])]" % (cls.product_A.id),
            'active': True,
        })

        cls.code_promotion_program = cls.env['coupon.program'].create({
            'name': 'Buy 1 A + Enter code, 1 A is free',
            'promo_code_usage': 'code_needed',
            'reward_type': 'product',
            'reward_product_id': cls.product_A.id,
            'rule_products_domain': "[('id', 'in', [%s])]" % (cls.product_A.id),
            'active': True,
        })

        cls.code_promotion_program_with_discount = cls.env['coupon.program'].create({
            'name': 'Buy 1 C + Enter code, 10 percent discount on C',
            'promo_code_usage': 'code_needed',
            'reward_type': 'discount',
            'discount_type': 'percentage',
            'discount_percentage': 10,
            'rule_products_domain': "[('id', 'in', [%s])]" % (cls.product_C.id),
            'active': True,
            'discount_apply_on': 'on_order',
        })
