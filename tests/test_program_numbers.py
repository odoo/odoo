# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.addons.sale_coupon.tests.common import TestSaleCouponCommon

class TestSaleCouponProgramNumbers(TestSaleCouponCommon):

    def setUp(self):
        super(TestSaleCouponProgramNumbers, self).setUp()

        self.iPadMini = self.env.ref('product.product_product_6').copy()
        self.computerCase = self.env.ref('product.product_product_16').copy()
        self.littleServer = self.env.ref('product.consu_delivery_02').copy()
        self.steve = self.env['res.partner'].create({
            'name': 'Steve Bucknor',
            'customer': True,
            'email': 'steve.bucknor@example.com',
        })
        self.empty_order = self.env['sale.order'].create({
            'partner_id': self.steve.id
        })

        self.p1 = self.env['sale.coupon.program'].create({
            'name': 'Code for 10% on orders',
            'promo_code_usage': 'code_needed',
            'promo_code': 'test_10pc',
            'discount_type': 'percentage',
            'discount_percentage': 10.0,
            'program_type': 'promotion_program',
        })
        self.p2 = self.env['sale.coupon.program'].create({
            'name': 'Buy 3 ipads, get one for free',
            'promo_code_usage': 'no_code_needed',
            'reward_type': 'product',
            'program_type': 'promotion_program',
            'reward_product_id': self.iPadMini.id,
            'rule_min_quantity': 3,
            'rule_products_domain': '[["name","ilike","ipad mini"]]',
        })
        self.p3 = self.env['sale.coupon.program'].create({
            'name': 'Buy 1 computer case, get a free little server',
            'promo_code_usage': 'no_code_needed',
            'reward_type': 'product',
            'program_type': 'promotion_program',
            'reward_product_id': self.littleServer.id,
            'rule_products_domain': '[["name","ilike","computer case"]]',
        })

    def test_program_numbers_free_and_paid_product_qty(self):
        # These tests will focus on numbers (free product qty, SO total, reduction total..)
        order = self.empty_order
        sol1 = self.env['sale.order.line'].create({
            'product_id': self.iPadMini.id,
            'name': 'iPad Mini',
            'product_uom_qty': 4.0,
            'order_id': order.id,
        })

        # Check we correctly get a free product
        order.recompute_coupon_lines()
        self.assertEqual(len(order.order_line.ids), 2, "We should have 2 lines as we now have one 'Free iPad Mini' line as we bought 4 of them")

        # Check free product's price is not added to total when applying reduction (Or the discount will also be applied on the free product's price)
        self.env['sale.coupon.apply.code'].sudo().apply_coupon(order, 'test_10pc')
        self.assertEqual(len(order.order_line.ids), 3, "We should 3 lines as we should have a new line for promo code reduction")
        self.assertEqual(order.amount_total, 864, "Only paid product should have their price discounted")
        order.order_line.filtered(lambda x: 'Discount' in x.name).unlink() # Remove Discount

        # Check free product is removed since we are below minimum required quantity
        sol1.product_uom_qty = 3
        order.recompute_coupon_lines()
        self.assertEqual(len(order.order_line.ids), 1, "Free iPad Mini should have been removed")

        # Free product in cart will be considered as paid product when changing quantity of paid product, so the free product quantity computation will be wrong.
        # 100 iPad in cart, 25 free, set quantity to 10 ipad, you should have 2 free ipad but you get 8 because it add the 25 initial free ipad to the total paid ipad when computing (25+10 > 35 > /4 = 8 free ipad)
        sol1.product_uom_qty = 100
        order.recompute_coupon_lines()
        self.assertEqual(order.order_line.filtered(lambda x: x.is_reward_line).product_uom_qty, 25, "We should have 25 Free iPad Mini")
        sol1.product_uom_qty = 10
        order.recompute_coupon_lines()
        self.assertEqual(order.order_line.filtered(lambda x: x.is_reward_line).product_uom_qty, 2, "We should have 2 Free iPad Mini")

    def test_program_numbers_check_eligibility(self):
        # These tests will focus on numbers (free product qty, SO total, reduction total..)

        # Check if we have enough paid product to receive free product in case of a free product that is different from the paid product required
        # Buy A, get free b. (remember we need a paid B in cart to receive free b). If your cart is 4A 1B then you should receive 1b (you are eligible to receive 4 because you have 4A but since you dont have enought B in your cart, you are limited to the B quantity)
        order = self.empty_order
        sol1 = self.env['sale.order.line'].create({
            'product_id': self.computerCase.id,
            'name': 'Computer Case',
            'product_uom_qty': 4.0,
            'order_id': order.id,
        })
        sol2 = self.env['sale.order.line'].create({
            'product_id': self.littleServer.id,
            'name': 'Little Server',
            'product_uom_qty': 1.0,
            'order_id': order.id,
        })
        order.recompute_coupon_lines()
        self.assertEqual(len(order.order_line.ids), 3, "We should have a 'Free Little Server' promotion line")
        self.assertEqual(order.order_line.filtered(lambda x: x.is_reward_line).product_uom_qty, 1, "We should receive one and only one free Little Server")

        # Check the required value amount to be eligible for the program is correctly computed (eg: it does not add negative value (from free product) to total)
        # A = free b | Have your cart with A 2B b | cart value should be A + 1B but in code it is only A (free b value is subsstract 2 times)
        # This is because _amount_all() is summing all SO lines (so + (-b.value)) and again in _check_promo_code() order.amount_untaxed + order.reward_amount | amount_untaxed has already free product value substracted (_amount_all)
        sol1.product_uom_qty = 1
        sol2.product_uom_qty = 2
        self.p1.rule_minimum_amount = 5000
        order.recompute_coupon_lines()
        self.env['sale.coupon.apply.code'].sudo().apply_coupon(order, 'test_10pc')
        self.assertEqual(len(order.order_line.ids), 4, "We should have 4 lines as we should have a new line for promo code reduction")

        # Check you can still have auto applied promotion if you have a promo code set to the order
        sol4 = self.env['sale.order.line'].create({
            'product_id': self.iPadMini.id,
            'name': 'iPad Mini',
            'product_uom_qty': 4.0,
            'order_id': order.id,
        })
        order.recompute_coupon_lines()
        self.assertEqual(len(order.order_line.ids), 6, "We should have 2 more lines as we now have one 'Free iPad Mini' line since we bought 4 of them")

    def test_program_numbers_taxes_and_rules(self):
        percent_tax = self.env['account.tax'].create({
            'name': "15% Tax",
            'amount_type': 'percent',
            'amount': 15,
            'price_include': True,
        })
        p_specific_product = self.env['sale.coupon.program'].create({
            'name': '20% reduction on ipad in cart',
            'promo_code_usage': 'no_code_needed',
            'reward_type': 'discount',
            'program_type': 'promotion_program',
            'discount_type': 'percentage',
            'discount_percentage': 20.0,
            'rule_minimum_amount': 320.00,
            'discount_apply_on': 'specific_product',
            'discount_specific_product_id': self.iPadMini.id,
        })
        order = self.empty_order
        self.iPadMini.taxes_id = percent_tax
        sol1 = self.env['sale.order.line'].create({
            'product_id': self.iPadMini.id,
            'name': 'iPad Mini',
            'product_uom_qty': 1.0,
            'order_id': order.id,
        })

        order.recompute_coupon_lines()
        self.assertEqual(len(order.order_line.ids), 1, "We should not get the reduction line since we dont have 320$ tax excluded (ipad is 320$ tax included)")
        sol1.tax_id.price_include = False
        sol1._compute_tax_id()
        order.recompute_coupon_lines()
        self.assertEqual(len(order.order_line.ids), 2, "We should now get the reduction line since we have 320$ tax included (ipad is 320$ tax included)")
        # (320 +15% tax) - (20% of (320 + 15% tax) = 368 + 73.6 = 294.4
        self.assertEqual(order.amount_total, 294.4, "Check discount has been applied correctly (eg: on taxes aswell)")

        # test coupon with code works the same as auto applied_programs
        p_specific_product.write({'promo_code_usage':'code_needed', 'promo_code':'20pc'})
        order.order_line.filtered(lambda l: l.is_reward_line).unlink()
        order.recompute_coupon_lines()
        self.assertEqual(len(order.order_line.ids), 1, "Reduction should be removed since we deleted it and it is now a promo code usage, it shouldn't be automatically reapplied")

        self.env['sale.coupon.apply.code'].sudo().apply_coupon(order, '20pc')
        order.recompute_coupon_lines()
        self.assertEqual(len(order.order_line.ids), 2, "We should now get the reduction line since we have 320$ tax included (ipad is 320$ tax included)")

        #check discount applied only on ipad
        sol2 = self.env['sale.order.line'].create({
            'product_id': self.computerCase.id,
            'name': 'Computer Case',
            'product_uom_qty': 10.0,
            'order_id': order.id,
        })
        order.recompute_coupon_lines()
        # (10x25) + (320 +15% tax) - (20% of (320 + 15% tax) = 250 + 368 - 73.6 = 544.4
        self.assertEqual(order.amount_total, 544.4, "We should only get reduction on ipad")
        sol1.product_uom_qty = 10
        order.recompute_coupon_lines()
        # (10x25) + (10x (320 +15% tax)) - (20% of (10x (320 + 15% tax))) - 2 free iPads = 250 + 3680 - 736 - 736 = 2458
        self.assertEqual(order.amount_total, 2458, "Changing ipad quantity should change discount amount correctly")

        p_specific_product.discount_max_amount = 200
        order.recompute_coupon_lines()
        self.assertEqual(order.amount_total, 2994, "The discount should be limited to $200")
