# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.sale_loyalty.tests.common import TestSaleCouponCommon


@tagged('post_install', '-at_install')
class TestSaleInvoicing(TestSaleCouponCommon):

    def test_invoicing_order_with_promotions(self):
        discount_coupon_program = self.env['loyalty.program'].create({
            'name': '10% Discount',
            'program_type': 'coupons',
            'applies_on': 'current',
            'trigger': 'auto',
            'rule_ids': [(0, 0, {})],
            'reward_ids': [(0, 0, {
                'reward_type': 'discount',
                'discount': 10,
                'discount_mode': 'percent',
                'discount_applicability': 'order',
            })]
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

        #Check default invoice_policy on discount product
        self.assertEqual(discount_coupon_program.reward_ids.discount_line_product_id.invoice_policy, 'order')

        order._update_programs_and_rewards()
        self._claim_reward(order, discount_coupon_program)
        # Order is not confirmed, there shouldn't be any invoiceable line
        invoiceable_lines = order._get_invoiceable_lines()
        self.assertEqual(len(invoiceable_lines), 0)

        order.action_confirm()
        invoiceable_lines = order._get_invoiceable_lines()
        # Product was not delivered, the order invoice status is 'No' as invoicing it should not be
        # promoted, but the reward line should still be invoiceable, if users wants to invoice it
        self.assertEqual(order.invoice_status, 'no')
        self.assertEqual(len(invoiceable_lines), 1)

        inv = order._create_invoices()
        self.assertEqual(len(inv.invoice_line_ids), 1)
        invoiceable_lines = order._get_invoiceable_lines()
        self.assertEqual(len(invoiceable_lines), 0)
        inv.button_cancel()

        order.order_line[0].qty_delivered = 1
        # Product is delivered, the two lines can be invoiced.
        self.assertEqual(order.invoice_status, 'to invoice')
        invoiceable_lines = order._get_invoiceable_lines()
        self.assertEqual(order.order_line, invoiceable_lines)
        account_move = order._create_invoices()
        self.assertEqual(len(account_move.invoice_line_ids), 2)

    def test_coupon_on_order_sequence(self):
        discount_coupon_program = self.env['loyalty.program'].create({
            'name': '10% Discount',
            'program_type': 'coupons',
            'applies_on': 'current',
            'trigger': 'auto',
            'rule_ids': [(0, 0, {})],
            'reward_ids': [(0, 0, {
                'reward_type': 'discount',
                'discount': 10,
                'discount_mode': 'percent',
                'discount_applicability': 'order',
            })]
        })

        order = self.empty_order

        product_6 = self.env['product.product'].create({
            'name': 'Large Cabinet',
        })
        # orderline1
        self.env['sale.order.line'].create({
            'product_id': product_6.id,
            'name': 'largeCabinet',
            'product_uom_qty': 1.0,
            'order_id': order.id,
        })

        #Check default invoice_policy on discount product
        self.assertEqual(discount_coupon_program.reward_ids.discount_line_product_id.invoice_policy, 'order')

        self._auto_rewards(order, discount_coupon_program)

        self.assertEqual(len(order.order_line), 2, 'Coupon correctly applied')

        product_11 = self.env['product.product'].create({
            'name': 'Conference Chair',
        })

        # orderline2
        self.env['sale.order.line'].create({
            'product_id': product_11.id,
            'name': 'conferenceChair',
            'product_uom_qty': 1.0,
            'order_id': order.id,
        })

        order._update_programs_and_rewards()
        self.assertEqual(len(order.order_line), 3, 'Coupon correctly applied')

        self.assertTrue(order.order_line.sorted(lambda x: x.sequence)[-1].is_reward_line, 'Global coupons appear on the last line')
