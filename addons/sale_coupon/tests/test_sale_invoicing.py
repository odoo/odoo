# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.sale_coupon.tests.common import TestSaleCouponCommon
from odoo.exceptions import UserError
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestSaleInvoicing(TestSaleCouponCommon):

    def test_01_invoicing_order_with_promotions(self):
        discount_coupon_program = self.env['sale.coupon.program'].create({
            'name': '10% Discount', # Default behavior
            'program_type': 'coupon_program',
            'reward_type': 'discount',
            'discount_apply_on': 'on_order',
            'promo_code_usage': 'no_code_needed',
        })
        product = self.env['product.product'].create({
            'invoice_policy': 'delivery',
            'name': 'Product invoiced on delivery',
            'lst_price': 500,
        })

        order = self.empty_order
        order.write({
            'order_line': [
                (0, 0, {
                    'product_id': product.id,
                })
            ]
        })

        order.recompute_coupon_lines()
        # Order is not confirmed, there shouldn't be any invoiceable line
        invoiceable_lines = order._get_invoiceable_lines()
        self.assertEqual(len(invoiceable_lines), 0)

        order.action_confirm()
        invoiceable_lines = order._get_invoiceable_lines()
        # Product was not delivered, we cannot invoice
        # the product line nor the promotion line
        self.assertEqual(len(invoiceable_lines), 0)
        with self.assertRaises(UserError):
            order._create_invoices()

        order.order_line[0].qty_delivered = 1
        # Product is delivered, the two lines can be invoiced.
        invoiceable_lines = order._get_invoiceable_lines()
        self.assertEqual(order.order_line, invoiceable_lines)
        account_move = order._create_invoices()
        self.assertEqual(len(account_move.invoice_line_ids), 2)

    def test_02_double_invoice_order_with_order_percentage_discount(self):
        discount_coupon_program = self.env['sale.coupon.program'].create({
            'name': '10% Discount',
            'program_type': 'coupon_program',
            'reward_type': 'discount',
            'discount_apply_on': 'on_order',
            'promo_code_usage': 'no_code_needed',
        })
        product = self.env['product.product'].create({
            'invoice_policy': 'order',
            'name': 'Product invoiced on order',
            'lst_price': 800,
        })

        order = self.empty_order
        order.write({
            'order_line': [
                (0, 0, {
                    'product_id': product.id,
                })
            ]
        })

        order.recompute_coupon_lines()
        order.action_confirm()

        account_move = order._create_invoices()
        self.assertEqual(len(account_move.invoice_line_ids), 2, "We should have 2 lines as we now have one discount line")
        self.assertEqual(account_move.amount_untaxed, (product.list_price - discount_coupon_program.discount_percentage * product.list_price / 100.0), "The invoice untaxed amount should be equal to the sale order uninvoiced price with a 10% discount applied")

        order.write({
            'order_line': [
                (0, 0, {
                    'product_id': product.id,
                })
            ]
        })

        order.recompute_coupon_lines()

        second_account_move = order._create_invoices()
        self.assertEqual(len(second_account_move.invoice_line_ids), 2, "We should have 2 lines as we now have one discount line")
        self.assertEqual(second_account_move.amount_untaxed, (product.list_price - discount_coupon_program.discount_percentage * product.list_price / 100.0), "The invoice untaxed amount should be equal to the sale order uninvoiced price with a 10% discount applied")

    def test_03_double_invoice_order_with_free_product(self):
        order = self.empty_order
        product = self.env['product.product'].create({
            'invoice_policy': 'order',
            'name': 'Product invoiced on order',
            'lst_price': 800,
        })
        self.env['sale.coupon.program'].create({
            'name': 'Buy 4 Large Desks, one is free',
            'reward_type': 'product',
            'reward_product_id': product.id,
            'rule_products_domain': "[('id', 'in', [%s])]" % (product.id),
            'discount_apply_on': 'on_order',
            'promo_code_usage': 'no_code_needed',
            'rule_min_quantity': 3.0,
        })
        self.env['sale.order.line'].create({
            'product_id': product.id,
            'product_uom_qty': 4.0,
            'order_id': order.id,
        })

        order.recompute_coupon_lines()
        order.action_confirm()

        account_move = order._create_invoices()
        self.assertEqual(len(account_move.invoice_line_ids), 2, "We should have 2 lines as we now have one 'Free Large Cabinet' line as we bought 4 of them")
        self.assertEqual(account_move.amount_untaxed, 3 * product.list_price, "The invoice untaxed amount should be equal to 3 times the product price, as the promo should 'render' one free")

        self.env['sale.order.line'].create({
            'product_id': product.id,
            'product_uom_qty': 4.0,
            'order_id': order.id,
        })

        order.recompute_coupon_lines()

        second_account_move = order._create_invoices()
        self.assertEqual(len(second_account_move.invoice_line_ids), 2, "We should have 2 lines as we now have one 'Free Large Cabinet' line as we bought 4 of them")
        self.assertEqual(second_account_move.amount_untaxed, 3 * product.list_price, "The invoice untaxed amount should be equal to 3 times the product price, as the promo should 'render' one free")
