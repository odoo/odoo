# -*- coding: utf-8 -*-
from openerp.addons.website_sale_coupon.tests.common import TestSaleCouponCommon


class TestSaleCoupon(TestSaleCouponCommon):
    def test_sale_coupon_type(self):

        order_id = self.SaleOrder.create({
            'partner_id': self.partner_id.id})

        ######Buy 1 refrigerator + get shipment free
        order_id.write({'order_line': [(0, 0, {'product_id': self.product_refrigerator.id, 'product_uom_qty': 1})]})
        applicable_line = order_id.order_line.filtered(lambda x: x.product_id == self.product_refrigerator)
        reward_line = order_id.order_line.filtered(lambda x: x.product_id == self.reward_product and x.generated_from_line_id == applicable_line)
        self.assertFalse(reward_line, "Reward line is created before entering the delivery charge line")
        order_id.write({'order_line': [(0, 0, {'product_id': self.product_delivery_charge.id, 'product_uom_qty': 1})]})
        delivery_line = order_id.order_line.filtered(lambda x: x.product_id.is_delivery_charge_product is True)
        reward_line = order_id.order_line.filtered(lambda x: x.product_id == self.reward_product and x.generated_from_line_id == applicable_line)
        self.assertTrue(reward_line, "reward line is not created")
        self.assertEqual((-1) * reward_line.price_unit, delivery_line.price_unit, "Delivery charge is incorrect")
        self.assertEqual(order_id.amount_total, 150, "Total amount is incorret")
        delivery_line.unlink()
        order_id.apply_immediately_reward()
        reward_line = order_id.order_line.filtered(lambda x: x.product_id == self.reward_product and x.generated_from_line_id == applicable_line)
        self.assertFalse(reward_line, "reward line is not deleting properly")
        self.assertEqual(order_id.amount_total, 150, "Total amount is incorrect")
        order_id.write({'order_line': [(0, 0, {'product_id': self.product_delivery_charge.id, 'product_uom_qty': 1})]})
        delivery_line = order_id.order_line.filtered(lambda x: x.product_id.is_delivery_charge_product is True)
        reward_line = order_id.order_line.filtered(lambda x: x.product_id == self.reward_product and x.generated_from_line_id == applicable_line)
        self.assertTrue(reward_line, "Reward line is not created properly")
        applicable_id = applicable_line.id
        applicable_line.unlink()
        order_id.apply_immediately_reward()
        reward_line = order_id.order_line.filtered(lambda x: x.product_id == self.reward_product and x.generated_from_line_id.id == applicable_id)
        self.assertFalse(reward_line, "Reward line is not deleting properly")
        self.assertEqual(order_id.amount_total, delivery_line.price_unit, "Total amount is incorrect")
