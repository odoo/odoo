# -*- coding: utf-8 -*-
from openerp.addons.website_sale_coupon.tests.common import TestSaleCouponCommon


class TestSaleCoupon(TestSaleCouponCommon):
    def test_sale_coupon_type(self):

        order_id = self.SaleOrder.create({
            'partner_id': self.partner_id.id,
            'order_line': [(0, 0, {'product_id': self.product_mobile.id, 'product_uom_qty': 1})]})

        ######## buy 1 mobile get 1 cover
        product_line = order_id.order_line.filtered(lambda x: x.product_id == self.product_cover)
        applicable_line = order_id.order_line.filtered(lambda x: x.product_id == self.product_mobile)
        reward_line = order_id.order_line.filtered(lambda x: x.product_id == self.reward_product and x.generated_from_line_id == applicable_line)
        self.assertEqual(order_id.amount_total, 100.00, "Toatal amount is incorrect")
        self.assertTrue(product_line, "Product line is not created")
        self.assertEqual(product_line.product_uom_qty, 1, "Reward product is not created properly")
        self.assertTrue(reward_line, "Reward line is not created")
        #to check unit price of reward and reward product
        self.assertEqual(product_line.price_unit, (-1) * reward_line.price_unit, "Reward unit price is incorrect")
        #update the mobile qty and check qty of reward,qty addition
        applicable_line.write({'product_uom_qty': 5})
        order_id.apply_immediately_reward()
        self.assertEqual(order_id.amount_total, 500.00, "Total amount is incorrect")
        self.assertEqual(reward_line.product_uom_qty, 5, "Reward qty is incorrect in addition")
        #update the mobile qty n check qty of reward,qty deduction
        applicable_line.write({'product_uom_qty': 2})
        order_id.apply_immediately_reward()
        self.assertEqual(reward_line.product_uom_qty, 2, "Reward qty is incorrect in deletion")
        self.assertEqual(order_id.amount_total, 350.00, "Total amount is incorrect")
        #update the qty of cover n check qty of reward, greater than reward qty
        product_line.write({'product_uom_qty': 5})
        order_id.apply_immediately_reward()
        self.assertEqual(reward_line.product_uom_qty, 2, "Reward qty is incorrect")
        self.assertEqual(order_id.amount_total, 350.00, "Total amount is incorrect")
        #update the qty of cover n check qty of reward, less than reward qty
        product_line.write({'product_uom_qty': 1})
        order_id.apply_immediately_reward()
        self.assertEqual(product_line.product_uom_qty, 2, "Reward product qty is not updated")
        self.assertEqual(order_id.amount_total, 200.00, "Total amount is incorrect")
        #unlink the cover and check weather that is added automaticaly or not
        product_line.unlink()
        order_id.apply_immediately_reward()
        product_line = order_id.order_line.filtered(lambda x: x.product_id == self.product_cover)
        self.assertTrue(product_line, "reward product line is deleted")
        self.assertEqual(order_id.amount_total, 200.00, "Total amount is incorrect")
        #unlink the mobile line and check for reward line
        line_id = applicable_line.id
        applicable_line.unlink()
        order_id.apply_immediately_reward()
        reward_line = order_id.order_line.filtered(lambda x: x.product_id == self.reward_product and x.generated_from_line_id == line_id)
        self.assertFalse(reward_line, "reward line is not deleted")
        self.assertEqual(order_id.amount_total, 100.00, "Total amount is incorrect")
        product_line.unlink()
        self.assertEqual(order_id.amount_total, 0.00, "Total amount is incorrect")

        # ######### buy 2 Hard disk get 1 hard disk free
        order_id.write({'order_line': [(0, 0, {'product_id': self.product_harddisk.id, 'product_uom_qty': 2})]})
        product_line = order_id.order_line.filtered(lambda x: x.product_id == self.product_harddisk)
        reward_line = order_id.order_line.filtered(lambda x: x.product_id == self.reward_product and x.generated_from_line_id == product_line)
        self.assertTrue(product_line, "Product line is not created")
        self.assertEqual(product_line.product_uom_qty, 3, "Reward product qty is invalid")
        self.assertEqual(reward_line.product_uom_qty, 1, "Reward product qty is invalid")
        self.assertEqual(order_id.amount_total, 100, "Total amount is invalid")
        #to check unit price of reward and reward product
        self.assertEqual(product_line.price_unit, (-1) * reward_line.price_unit, "Reward unit price is incorrect")
        # #update the product qty, addition
        product_line.write({'product_uom_qty': 10})
        order_id.apply_immediately_reward()
        self.assertEqual(reward_line.product_uom_qty, 3, "Reward product qty is invalid")
        self.assertEqual(order_id.amount_total, 350, "Total amount is invalid")
        # #update the product qty, deduction
        product_line.write({'product_uom_qty': 6})
        order_id.apply_immediately_reward()
        self.assertEqual(reward_line.product_uom_qty, 2, "Reward product qty is invalid")
        self.assertEqual(order_id.amount_total, 200, "Total amount is invalid")
        # update the product qty = 1
        product_line.write({'product_uom_qty': 1})
        order_id.apply_immediately_reward()
        reward_line = order_id.order_line.filtered(lambda x: x.product_id == self.reward_product and x.generated_from_line_id == product_line)
        self.assertFalse(reward_line, "Reward line is not deleting properly")
        self.assertEqual(order_id.amount_total, 50, "Total amount is invalid")
        #update the product qty, addition
        product_line.write({'product_uom_qty': 3})
        order_id.apply_immediately_reward()
        reward_line = order_id.order_line.filtered(lambda x: x.product_id == self.reward_product and x.generated_from_line_id == product_line)
        self.assertEqual(reward_line.product_uom_qty, 1, "Reward product qty is invalid")
        self.assertEqual(order_id.amount_total, 100, "Total amount is invalid")
        #unlink the product line, reward line should be deleted
        product_line.unlink()
        reward_line = order_id.order_line.filtered(lambda x: x.product_id == self.reward_product and x.generated_from_line_id == product_line)
        self.assertFalse(reward_line, "Reward is not deleting properly")
        self.assertEqual(order_id.amount_total, 0, "Total amount is invalid")

        # #########buy any product in 2 qty of category beverage and get 2$ off
        order_id.write({'order_line': [(0, 0, {'product_id': self.product_pepsi.id, 'product_uom_qty': 2})]})
        product_line = order_id.order_line.filtered(lambda x: x.product_id == self.product_pepsi)
        reward_line = order_id.order_line.filtered(lambda x: x.product_id == self.reward_product and x.generated_from_line_id == product_line)
        self.assertTrue(product_line, "Product line is not created")
        self.assertEqual(product_line.product_uom_qty, 2, "Reward product qty is invalid")
        self.assertEqual(reward_line.price_subtotal, -2, "Reward amount on category is incorrect")
        self.assertEqual(order_id.amount_total, 18, "Total amount is invalid")
        # #update the qty of product line, addition
        product_line.write({'product_uom_qty': 4})
        order_id.apply_immediately_reward()
        self.assertEqual(reward_line.price_subtotal, -2, "Reward amount on category is incorrect")
        self.assertEqual(order_id.amount_total, 38, "Total amount is invalid")
        #unlink the product line
        product_line.unlink()
        order_id.apply_immediately_reward()
        reward_line = order_id.order_line.filtered(lambda x: x.product_id == self.reward_product and x.generated_from_line_id == product_line)
        self.assertFalse(reward_line, "Reward is not deleting properly")
        self.assertEqual(order_id.amount_total, 0, "Total amount is invalid")
        #add the new product line of coca cola
        order_id.write({'order_line': [(0, 0, {'product_id': self.product_coca_cola.id})]})
        product_line1 = order_id.order_line.filtered(lambda x: x.product_id == self.product_coca_cola)
        reward_line1 = order_id.order_line.filtered(lambda x: x.product_id == self.reward_product and x.generated_from_line_id == product_line1)
        self.assertFalse(reward_line1)
        self.assertEqual(order_id.amount_total, 20, "Total amount is invalid")
        #add 1 product line of pepsi
        order_id.write({'order_line': [(0, 0, {'product_id': self.product_pepsi.id})]})
        product_line2 = order_id.order_line.filtered(lambda x: x.product_id == self.product_pepsi)
        reward_line1 = order_id.order_line.filtered(lambda x: x.product_id == self.reward_product and x.generated_from_line_id == product_line2)
        reward_line2 = order_id.order_line.filtered(lambda x: x.product_id == self.reward_product and x.generated_from_line_id == product_line1)
        self.assertEqual(order_id.amount_total, 30, "Total amount is invalid")
        self.assertFalse(reward_line1)
        self.assertFalse(reward_line2)
        product_line1.unlink()
        product_line2.unlink()
        reward_line1.unlink()
        reward_line2.unlink()
        reward_line.unlink()
        self.assertEqual(order_id.amount_total, 0, "Total amount is invalid")

        ##########buy 1 pen drive and get 10% off on pen drive cover
        order_id.write({'order_line': [(0, 0, {'product_id': self.product_pendrive.id, 'product_uom_qty': 1})]})
        applicable_line = order_id.order_line.filtered(lambda x: x.product_id == self.product_pendrive)
        product_line = order_id.order_line.filtered(lambda x: x.product_id == self.product_pendrive_cover)
        self.assertFalse(product_line, "Reward is created in case of reward on specific product")
        self.assertEqual(order_id.amount_total, 60, "Total amount is invalid")
        #add the reward product line
        order_id.write({'order_line': [(0, 0, {'product_id': self.product_pendrive_cover.id})]})
        product_line = order_id.order_line.filtered(lambda x: x.product_id == self.product_pendrive_cover)
        reward_line = order_id.order_line.filtered(lambda x: x.product_id == self.reward_product and x.generated_from_line_id == applicable_line)
        self.assertTrue(reward_line, "reward line is not created")
        #check for reward amount and qty
        self.assertEqual(order_id.amount_total, 78, "Total amount is invalid")
        self.assertEqual(reward_line.price_unit, -2, "Reward percentage is incorrect")
        self.assertEqual(reward_line.product_uom_qty, 1, "Reward qty is incorrect")
        #update the applicable product qty, addition
        applicable_line.write({'product_uom_qty': 2})
        order_id.apply_immediately_reward()
        reward_line = order_id.order_line.filtered(lambda x: x.product_id == self.reward_product and x.generated_from_line_id == applicable_line)
        self.assertEqual(order_id.amount_total, 138, "Total amount is invalid")
        self.assertEqual(reward_line.price_unit, -2, "Reward percentage is incorrect")
        self.assertEqual(reward_line.product_uom_qty, 1, "Reward qty is incorrect")
        #add the reward product pendrive cover
        product_line.write({'product_uom_qty': 2})
        order_id.apply_immediately_reward()
        reward_line = order_id.order_line.filtered(lambda x: x.product_id == self.reward_product and x.generated_from_line_id == applicable_line)
        self.assertEqual(order_id.amount_total, 158, "Total amount is invalid")
        self.assertEqual(reward_line.price_unit, -2, "Reward percentage is incorrect")
        self.assertEqual(reward_line.product_uom_qty, 1, "Reward qty is incorrect")
        # #unlink the applicable line
        applicable_line.unlink()
        order_id.apply_immediately_reward()
        reward_line = order_id.order_line.filtered(lambda x: x.product_id == self.reward_product and x.generated_from_line_id == applicable_line)
        self.assertEqual(order_id.amount_total, 40, "Total amount is invalid")
        self.assertFalse(reward_line, "Reward line is not deleting properly")
        product_line.unlink()
        self.assertEqual(order_id.amount_total, 0, "Total amount is invalid")

        ########## purchase for 1000 and above and get 10% off on cart
        order_id.write({'order_line': [(0, 0, {'product_id': self.product_mobile.id, 'product_uom_qty': 10})]})
        reward_line = order_id.order_line.filtered(lambda x: x.product_id == self.reward_product and x.generated_from_line_id.id is False)
        applicable_line = order_id.order_line.filtered(lambda x: x.product_id == self.product_mobile)
        product_line = order_id.order_line.filtered(lambda x: x.product_id == self.product_cover)
        self.assertEqual(order_id.amount_total, 900, "Total amount is invalid")
        self.assertTrue(reward_line, "Reward is not created")
        self.assertEqual(reward_line.price_unit, -100, "Reward on amount percentage is incorrect")
        #update the qty of product so that cart amount is less than 1000
        applicable_line.write({'product_uom_qty': 5})
        order_id.apply_immediately_reward()
        reward_line = order_id.order_line.filtered(lambda x: x.product_id == self.reward_product and x.generated_from_line_id.id is False)
        self.assertFalse(reward_line, "Reward is not deleting properly")
        self.assertEqual(order_id.amount_total, 750, "Total amount is invalid")
        #update the qty of applicable product
        applicable_line.write({'product_uom_qty': 10})
        order_id.apply_immediately_reward()
        reward_line = order_id.order_line.filtered(lambda x: x.product_id == self.reward_product and x.generated_from_line_id.id is False)
        self.assertTrue(reward_line, "Reward line is not created properly")
        self.assertEqual(order_id.amount_total, 875, "Total amount is invalid")
        self.assertEqual(reward_line.price_unit, -125, "Reward on amount percentage is incorrect")
        #unlink the applicable product line
        applicable_line.unlink()
        order_id.apply_immediately_reward()
        reward_line = order_id.order_line.filtered(lambda x: x.product_id == self.reward_product and x.generated_from_line_id.id is False)
        self.assertFalse(reward_line, "Reward line is created improperly")
        self.assertEqual(order_id.amount_total, 500, "Total amount is invalid")
        product_line.unlink()
        self.assertEqual(order_id.amount_total, 0, "Total amount is invalid")
