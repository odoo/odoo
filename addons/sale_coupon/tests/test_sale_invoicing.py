# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.sale_coupon.tests.common import TestSaleCouponCommon
from odoo.exceptions import UserError
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestSaleInvoicing(TestSaleCouponCommon):

    def test_invoicing_order_with_promotions(self):
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

    def test_coupon_on_order_sequence(self):
        # discount_coupon_program
        self.env['sale.coupon.program'].create({
            'name': '10% Discount', # Default behavior
            'program_type': 'coupon_program',
            'reward_type': 'discount',
            'discount_apply_on': 'on_order',
            'promo_code_usage': 'no_code_needed',
        })
        order = self.empty_order

        # orderline1
        self.env['sale.order.line'].create({
            'product_id': self.env.ref('product.product_product_6').id,
            'name': 'largeCabinet',
            'product_uom_qty': 1.0,
            'order_id': order.id,
        })

        order.recompute_coupon_lines()
        self.assertEqual(len(order.order_line), 2, 'Coupon correctly applied')

        # orderline2
        self.env['sale.order.line'].create({
            'product_id': self.env.ref('product.product_product_11').id,
            'name': 'conferenceChair',
            'product_uom_qty': 1.0,
            'order_id': order.id,
        })

        order.recompute_coupon_lines()
        self.assertEqual(len(order.order_line), 3, 'Coupon correctly applied')

        self.assertTrue(order.order_line.sorted(lambda x: x.sequence)[-1].is_reward_line, 'Global coupons appear on the last line')
