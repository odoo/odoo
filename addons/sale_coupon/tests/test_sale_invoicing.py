# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.sale_coupon.tests.common import TestSaleCouponCommon
from odoo.exceptions import UserError
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestSaleInvoicing(TestSaleCouponCommon):

    def test_invoicing_order_with_promotions(self):
        discount_coupon_program = self.env['coupon.program'].create({
            'name': '10% Discount', # Default behavior
            'program_type': 'coupon_program',
            'reward_type': 'discount',
            'discount_apply_on': 'on_order',
            'promo_code_usage': 'no_code_needed',
        })
        # Override the default invoice_policy on products
        discount_coupon_program.discount_line_product_id.invoice_policy = 'order'
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
