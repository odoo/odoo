# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.addons.sale_coupon.tests.common import TestSaleCouponCommon
from odoo.exceptions import UserError


class TestSaleCouponProgramNumbers(TestSaleCouponCommon):

    def setUp(self):
        super(TestSaleCouponProgramNumbers, self).setUp()

        self.iPadMini = self.env.ref('product.product_product_6')
        self.iPod = self.env.ref('product.product_product_11')
        self.wirelessKeyboard = self.env.ref('product.product_product_9')
        self.computerCase = self.env.ref('product.product_product_16')
        self.littleServer = self.env.ref('product.consu_delivery_02')
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
            'name': 'Buy 3 cabinets, get one for free',
            'promo_code_usage': 'no_code_needed',
            'reward_type': 'product',
            'program_type': 'promotion_program',
            'reward_product_id': self.iPadMini.id,
            'rule_min_quantity': 3,
            'rule_products_domain': '[["name","ilike","large cabinet"]]',
        })
        self.p3 = self.env['sale.coupon.program'].create({
            'name': 'Buy 1 drawer black, get a free Large Meeting Table',
            'promo_code_usage': 'no_code_needed',
            'reward_type': 'product',
            'program_type': 'promotion_program',
            'reward_product_id': self.littleServer.id,
            'rule_products_domain': '[["name","ilike","drawer black"]]',
        })

    def test_program_numbers_free_and_paid_product_qty(self):
        # These tests will focus on numbers (free product qty, SO total, reduction total..)
        order = self.empty_order
        sol1 = self.env['sale.order.line'].create({
            'product_id': self.iPadMini.id,
            'name': 'Large Cabinet',
            'product_uom_qty': 4.0,
            'order_id': order.id,
        })

        # Check we correctly get a free product
        order.recompute_coupon_lines()
        self.assertEqual(len(order.order_line.ids), 2, "We should have 2 lines as we now have one 'Free Large Cabinet' line as we bought 4 of them")

        # Check free product's price is not added to total when applying reduction (Or the discount will also be applied on the free product's price)
        self.env['sale.coupon.apply.code'].sudo().apply_coupon(order, 'test_10pc')
        self.assertEqual(len(order.order_line.ids), 3, "We should 3 lines as we should have a new line for promo code reduction")
        self.assertEqual(order.amount_total, 864, "Only paid product should have their price discounted")
        order.order_line.filtered(lambda x: 'Discount' in x.name).unlink()  # Remove Discount

        # Check free product is removed since we are below minimum required quantity
        sol1.product_uom_qty = 3
        order.recompute_coupon_lines()
        self.assertEqual(len(order.order_line.ids), 1, "Free Large Cabinet should have been removed")

        # Free product in cart will be considered as paid product when changing quantity of paid product, so the free product quantity computation will be wrong.
        # 100 iPad in cart, 25 free, set quantity to 10 ipad, you should have 2 free ipad but you get 8 because it add the 25 initial free ipad to the total paid ipad when computing (25+10 > 35 > /4 = 8 free ipad)
        sol1.product_uom_qty = 100
        order.recompute_coupon_lines()
        self.assertEqual(order.order_line.filtered(lambda x: x.is_reward_line).product_uom_qty, 25, "We should have 25 Free Large Cabinet")
        sol1.product_uom_qty = 10
        order.recompute_coupon_lines()
        self.assertEqual(order.order_line.filtered(lambda x: x.is_reward_line).product_uom_qty, 2, "We should have 2 Free Large Cabinet")

    def test_program_numbers_check_eligibility(self):
        # These tests will focus on numbers (free product qty, SO total, reduction total..)

        # Check if we have enough paid product to receive free product in case of a free product that is different from the paid product required
        # Buy A, get free b. (remember we need a paid B in cart to receive free b). If your cart is 4A 1B then you should receive 1b (you are eligible to receive 4 because you have 4A but since you dont have enought B in your cart, you are limited to the B quantity)
        order = self.empty_order
        sol1 = self.env['sale.order.line'].create({
            'product_id': self.computerCase.id,
            'name': 'drawer black',
            'product_uom_qty': 4.0,
            'order_id': order.id,
        })
        sol2 = self.env['sale.order.line'].create({
            'product_id': self.littleServer.id,
            'name': 'Large Meeting Table',
            'product_uom_qty': 1.0,
            'order_id': order.id,
        })
        order.recompute_coupon_lines()
        self.assertEqual(len(order.order_line.ids), 3, "We should have a 'Free Large Meeting Table' promotion line")
        self.assertEqual(order.order_line.filtered(lambda x: x.is_reward_line).product_uom_qty, 1, "We should receive one and only one free Large Meeting Table")

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
        self.env['sale.order.line'].create({
            'product_id': self.iPadMini.id,
            'name': 'Large Cabinet',
            'product_uom_qty': 4.0,
            'order_id': order.id,
        })
        order.recompute_coupon_lines()
        self.assertEqual(len(order.order_line.ids), 6, "We should have 2 more lines as we now have one 'Free Large Cabinet' line since we bought 4 of them")

    def test_program_numbers_taxes_and_rules(self):
        percent_tax = self.env['account.tax'].create({
            'name': "15% Tax",
            'amount_type': 'percent',
            'amount': 15,
            'price_include': True,
        })
        p_specific_product = self.env['sale.coupon.program'].create({
            'name': '20% reduction on Large Cabinet in cart',
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
            'name': 'Large Cabinet',
            'product_uom_qty': 1.0,
            'order_id': order.id,
        })

        order.recompute_coupon_lines()
        self.assertEqual(len(order.order_line.ids), 1, "We should not get the reduction line since we dont have 320$ tax excluded (cabinet is 320$ tax included)")
        sol1.tax_id.price_include = False
        sol1._compute_tax_id()
        order.recompute_coupon_lines()
        self.assertEqual(len(order.order_line.ids), 2, "We should now get the reduction line since we have 320$ tax included (cabinet is 320$ tax included)")
        # Name                 | Qty | price_unit |  Tax     |  HTVA   |   TVAC  |  TVA  |
        # --------------------------------------------------------------------------------
        # iPod                 |  1  |    320.00  | 15% excl |  320.00 |  368.00 |   48.00
        # 20% discount on ipad |  1  |    -64.00  | 15% excl |  -64.00 |  -73.60 |   -9.60
        # --------------------------------------------------------------------------------
        # TOTAL                                              |  256.00 |  294.40 |   38.40
        self.assertEqual(order.amount_total, 294.4, "Check discount has been applied correctly (eg: on taxes aswell)")

        # test coupon with code works the same as auto applied_programs
        p_specific_product.write({'promo_code_usage': 'code_needed', 'promo_code': '20pc'})
        order.order_line.filtered(lambda l: l.is_reward_line).unlink()
        order.recompute_coupon_lines()
        self.assertEqual(len(order.order_line.ids), 1, "Reduction should be removed since we deleted it and it is now a promo code usage, it shouldn't be automatically reapplied")

        self.env['sale.coupon.apply.code'].sudo().apply_coupon(order, '20pc')
        order.recompute_coupon_lines()
        self.assertEqual(len(order.order_line.ids), 2, "We should now get the reduction line since we have 320$ tax included (cabinet is 320$ tax included)")

        # check discount applied only on ipad
        self.env['sale.order.line'].create({
            'product_id': self.computerCase.id,
            'name': 'Computer Case',
            'product_uom_qty': 10.0,
            'order_id': order.id,
        })
        order.recompute_coupon_lines()
        # Name                 | Qty | price_unit |  Tax     |  HTVA   |   TVAC  |  TVA  |
        # --------------------------------------------------------------------------------
        # Computer Case        | 10  |     25.00  |        / |  250.00 |  250.00 |       /
        # iPad                 |  1  |    320.00  | 15% excl |  320.00 |  368.00 |   48.00
        # 20% discount on ipad |  1  |    -64.00  | 15% excl |  -64.00 |  -73.60 |   -9.60
        # --------------------------------------------------------------------------------
        # TOTAL                                              |  506.00 |  544.40 |   38.40
        self.assertEqual(order.amount_total, 544.4, "We should only get reduction on cabinet")
        sol1.product_uom_qty = 10
        order.recompute_coupon_lines()
        # Note: Since we now have 2 free ipads, we should discount only 8 of the 10 ipads in carts since we don't want to discount free ipads
        # Name                 | Qty | price_unit |  Tax     |  HTVA   |   TVAC  |  TVA  |
        # --------------------------------------------------------------------------------
        # Computer Case        | 10  |     25.00  |        / |  250.00 |  250.00 |       /
        # iPad                 | 10  |    320.00  | 15% excl | 3200.00 | 3680.00 |  480.00
        # Free iPad            |  2  |   -320.00  | 15% excl | -640.00 | -736.00 |  -96.00
        # 20% discount on ipad |  1  |   -512.00  | 15% excl | -512.00 | -588.80 |  -78.80
        # --------------------------------------------------------------------------------
        # TOTAL                                              | 2298.00 | 2605.20 |  305.20
        self.assertEqual(order.amount_total, 2605.20, "Changing cabinet quantity should change discount amount correctly")

        p_specific_product.discount_max_amount = 200
        order.recompute_coupon_lines()
        # Name                 | Qty | price_unit |  Tax     |  HTVA   |   TVAC  |  TVA  |
        # --------------------------------------------------------------------------------
        # Computer Case        | 10  |     25.00  |        / |  250.00 |  250.00 |       /
        # iPad                 | 10  |    320.00  | 15% excl | 3200.00 | 3680.00 |  480.00
        # Free iPad            |  2  |   -320.00  | 15% excl | -640.00 | -736.00 |  -96.00
        # 20% discount on ipad |  1  |   -200.00  | 15% excl | -200.00 | -230.00 |  -30.00
        #  limited to 200 HTVA
        # --------------------------------------------------------------------------------
        # TOTAL                                              | 2610.00 | 2964.00 |  354.00
        self.assertEqual(order.amount_total, 2964, "The discount should be limited to $200 tax excluded")
        self.assertEqual(order.amount_untaxed, 2610, "The discount should be limited to $200 tax excluded (2)")

    def test_program_numbers_one_discount_line_per_tax(self):
        order = self.empty_order
        # Create taxes
        self.tax_15pc_excl = self.env['account.tax'].create({
            'name': "15% Tax excl",
            'amount_type': 'percent',
            'amount': 15,
        })
        self.tax_50pc_excl = self.env['account.tax'].create({
            'name': "50% Tax excl",
            'amount_type': 'percent',
            'amount': 50,
        })
        self.tax_35pc_incl = self.env['account.tax'].create({
            'name': "35% Tax incl",
            'amount_type': 'percent',
            'amount': 35,
            'price_include': True,
        })

        # Set tax and prices on products as neeed for the test
        (self.product_A + self.iPadMini + self.iPod + self.wirelessKeyboard + self.computerCase).write({'list_price': 100})
        (self.iPadMini + self.computerCase).write({'taxes_id': [(4, self.tax_15pc_excl.id, False)]})
        self.iPod.taxes_id = self.tax_10pc_incl
        self.wirelessKeyboard.taxes_id = None
        self.product_A.taxes_id = (self.tax_35pc_incl + self.tax_50pc_excl)

        # Add products in order
        self.env['sale.order.line'].create({
            'product_id': self.iPadMini.id,
            'name': 'iPad',
            'product_uom_qty': 7.0,
            'order_id': order.id,
        })
        sol2 = self.env['sale.order.line'].create({
            'product_id': self.iPod.id,
            'name': 'iPod',
            'product_uom_qty': 5.0,
            'order_id': order.id,
        })
        self.env['sale.order.line'].create({
            'product_id': self.wirelessKeyboard.id,
            'name': 'Wireless Keyboard',
            'product_uom_qty': 10.0,
            'order_id': order.id,
        })
        self.env['sale.order.line'].create({
            'product_id': self.product_A.id,
            'name': 'product A with multiple taxes',
            'product_uom_qty': 3.0,
            'order_id': order.id,
        })
        self.env['sale.order.line'].create({
            'product_id': self.computerCase.id,
            'name': 'Computer Case',
            'product_uom_qty': 2.0,
            'order_id': order.id,
        })

        # Create needed programs
        self.p2.active = False
        self.p_ipad = self.env['sale.coupon.program'].create({
            'name': 'Buy 1 large cabinet, get one for free',
            'promo_code_usage': 'no_code_needed',
            'reward_type': 'product',
            'program_type': 'promotion_program',
            'reward_product_id': self.iPadMini.id,
            'rule_products_domain': '[["name","ilike","large cabinet"]]',
        })
        self.p_ipod = self.env['sale.coupon.program'].create({
            'name': 'Buy 1 chair, get one for free',
            'promo_code_usage': 'no_code_needed',
            'reward_type': 'product',
            'program_type': 'promotion_program',
            'reward_product_id': self.iPod.id,
            'rule_products_domain': '[["name","ilike","conference chair"]]',
        })
        self.p_keyboard = self.env['sale.coupon.program'].create({
            'name': 'Buy 1 bin, get one for free',
            'promo_code_usage': 'no_code_needed',
            'reward_type': 'product',
            'program_type': 'promotion_program',
            'reward_product_id': self.wirelessKeyboard.id,
            'rule_products_domain': '[["name","ilike","pedal bin"]]',
        })

        # Name                 | Qty | price_unit |  Tax     |  HTVA   |   TVAC  |  TVA  |
        # --------------------------------------------------------------------------------
        # iPod                 |  5  |    100.00  | 10% incl |  454.55 |  500.00 |   45.45
        # Keyboards            |  10 |    100.00  | /        | 1000.00 | 1000.00 |       /
        # iPad                 |  7  |    100.00  | 15% excl |  700.00 |  805.00 |  105.00
        # Computer Case        |  2  |    100.00  | 15% excl |  200.00 |  230.00 |   30.00
        # Product A            |  3  |    100.00  | 35% incl |  222.22 |  450.00 |  227.78
        #                                           50% excl
        # --------------------------------------------------------------------------------
        # TOTAL                                              | 2576.77 | 2985.00 |  408.23

        self.assertEqual(order.amount_total, 2985, "The order total without any programs should be 2985")
        self.assertEqual(order.amount_untaxed, 2576.77, "The order untaxed total without any programs should be 2576.77")
        self.assertEqual(len(order.order_line.ids), 5, "The order without any programs should have 5 lines")

        # Apply all the programs
        order.recompute_coupon_lines()

        # Name                 | Qty | price_unit |  Tax     |  HTVA   |   TVAC  |  TVA  |
        # --------------------------------------------------------------------------------
        # Free iPod            |  2  |   -100.00  | 10% incl | -181.82 | -200.00 |  -18.18
        # Free Keyboard        |  5  |   -100.00  | /        | -500.00 | -500.00 |       /
        # Free iPad            |  3  |   -100.00  | 15% excl | -300.00 | -345.00 |  -45.00
        # --------------------------------------------------------------------------------
        # TOTAL AFTER APPLYING FREE PRODUCT PROGRAMS         | 1594.95 | 1940.00 |  345.05

        self.assertEqual(order.amount_total, 1940.00, "The order total with programs should be 1940")
        self.assertEqual(order.amount_untaxed, 1594.95, "The order untaxed total with programs should be 1594.95")
        self.assertEqual(len(order.order_line.ids), 8, "Order should contains 5 regular product lines and 3 free product lines")

        # Apply 10% on top of everything
        self.env['sale.coupon.apply.code'].sudo().apply_coupon(order, 'test_10pc')

        # Name                 | Qty | price_unit |  Tax     |  HTVA   |   TVAC  |  TVA  |
        # --------------------------------------------------------------------------------
        # 10% on tax 10% incl  |  1  |    -30.00  | 10% incl | -27.27  | -30.00  |   -2.73
        # 10% on no tax        |  1  |    -50.00  | /        | -50.00  | -50.00  |       /
        # 10% on tax 15% excl  |  1  |    -40.00  | 15% excl | -60.00  | -69.00  |   -9.00
        # 10% on tax 35%+50%   |  1  |    -30.00  | 35% incl | -22.22  | -45.00  |  -22.78
        #                                           50% excl
        # --------------------------------------------------------------------------------
        # TOTAL AFTER APPLYING 10% GLOBAL PROGRAM            | 1435.46 | 1746.00 | -310.55

        self.assertEqual(order.amount_total, 1746, "The order total with programs should be 1746")
        self.assertEqual(order.amount_untaxed, 1435.46, "The order untaxed total with programs should be 1435.46")
        self.assertEqual(len(order.order_line.ids), 12, "Order should contains 5 regular product lines, 3 free product lines and 4 discount lines (one for every tax)")

        # -- This is a test inside the test
        order.order_line._compute_tax_id()
        self.assertEqual(order.amount_total, 1746, "Recomputing tax on sale order lines should not change total amount")
        self.assertEqual(order.amount_untaxed, 1435.46, "Recomputing tax on sale order lines should not change untaxed amount")
        self.assertEqual(len(order.order_line.ids), 12, "Recomputing tax on sale order lines should not change number of order line")
        order.recompute_coupon_lines()
        self.assertEqual(order.amount_total, 1746, "Recomputing tax on sale order lines should not change total amount")
        self.assertEqual(order.amount_untaxed, 1435.46, "Recomputing tax on sale order lines should not change untaxed amount")
        self.assertEqual(len(order.order_line.ids), 12, "Recomputing tax on sale order lines should not change number of order line")
        # -- End test inside the test

        # Now we want to apply a 20% discount only on iPad
        self.env['sale.coupon.program'].create({
            'name': '20% reduction on ipad in cart',
            'promo_code_usage': 'no_code_needed',
            'reward_type': 'discount',
            'program_type': 'promotion_program',
            'discount_type': 'percentage',
            'discount_percentage': 20.0,
            'discount_apply_on': 'specific_product',
            'discount_specific_product_id': self.iPadMini.id,
        })
        order.recompute_coupon_lines()
        # Note: we have 7 regular ipads and 3 free ipads. We should then discount only 4 really paid iPads

        # Name                 | Qty | price_unit |  Tax     |  HTVA   |   TVAC  |  TVA  |
        # --------------------------------------------------------------------------------
        # 20% on iPad          |  1  |    -80.00  | 15% excl | -80.00  | -92.00  |  -12.00
        # --------------------------------------------------------------------------------
        # TOTAL AFTER APPLYING 20% ON IPAD                   | 1355.45 | 1654.00 | -298.55

        self.assertEqual(order.amount_total, 1654, "The order total with programs should be 1654")
        self.assertEqual(order.amount_untaxed, 1355.46, "The order untaxed total with programs should be 1435.45")
        self.assertEqual(len(order.order_line.ids), 13, "Order should have a new discount line for 20% on iPad")

        # Check that if you delete one of the discount tax line, the others tax lines from the same promotion got deleted as well.
        order.order_line.filtered(lambda l: '10%' in l.name)[0].unlink()
        self.assertEqual(len(order.order_line.ids), 9, "All of the 10% discount line per tax should be removed")
        # At this point, removing the iPod's discount line (split per tax) removed also the others discount lines
        # linked to the same program (eg: other taxes lines). So the coupon got removed from the SO since there were no discount lines left

        # Add back the coupon to continue the test flow
        self.env['sale.coupon.apply.code'].sudo().apply_coupon(order, 'test_10pc')
        order.recompute_coupon_lines()
        self.assertEqual(len(order.order_line.ids), 13, "The 10% discount line should be back")

        # Check that if you change a product qty, his discount tax line got updated
        sol2.product_uom_qty = 7
        order.recompute_coupon_lines()
        # iPod                 |  5  |    100.00  | 10% incl |  454.55 |  500.00 |   45.45
        # Free iPod            |  2  |   -100.00  | 10% incl | -181.82 | -200.00 |  -18.18
        # 10% on tax 10% incl  |  1  |    -30.00  | 10% incl | -27.27  | -30.00  |   -2.73
        # --------------------------------------------------------------------------------
        # TOTAL OF IPOD LINES                                |  245.46 |  270.00 |   24.54
        # ==> Should become:
        # iPod                 |  7  |    100.00  | 10% incl |  636.36 |  700.00 |   63.64
        # Free iPod            |  3  |   -100.00  | 10% incl | -272.73 | -300.00 |  -27.27
        # 10% on tax 10% incl  |  1  |    -40.00  | 10% incl |  -36.36 |  -40.00 |   -3.64
        # --------------------------------------------------------------------------------
        # TOTAL OF IPOD LINES AFTER ADDING 2 IPODS           |  327.27 |  360.00 |   32.73
        # --------------------------------------------------------------------------------
        # => DIFFERENCES BEFORE/AFTER                        |   81.81 |   90.00 |    8.19
        self.assertEqual(order.amount_untaxed, 1355.46 + 81.81, "The order should have one more paid ipod with 10% incl tax and discounted by 10%")

        # Check that if you remove a product, his reward lines got removed, especially the discount per tax one
        sol2.unlink()
        order.recompute_coupon_lines()
        # Name                 | Qty | price_unit |  Tax     |  HTVA   |   TVAC  |  TVA  |
        # --------------------------------------------------------------------------------
        # Keyboards            |  10 |    100.00  | /        | 1000.00 | 1000.00 |       /
        # iPad                 |  7  |    100.00  | 15% excl |  700.00 |  805.00 |  105.00
        # Computer Case        |  2  |    100.00  | 15% excl |  200.00 |  230.00 |   30.00
        # Product A            |  3  |    100.00  | 35% incl |  222.22 |  450.00 |  227.78
        #                                           50% excl
        # Free Keyboard        |  5  |   -100.00  | /        | -500.00 | -500.00 |       /
        # Free iPad            |  3  |   -100.00  | 15% excl | -300.00 | -345.00 |  -45.00
        # 20% on iPad          |  1  |    -80.00  | 15% excl | -80.00  | -92.00  |  -12.00
        # --------------------------------------------------------------------------------
        # TOTAL                                              | 1242.22 | 1548.00 |  305.78
        self.assertEqual(order.amount_total, 1548, "The order total with programs should be 1548")
        self.assertEqual(order.amount_untaxed, 1242.22, "The order untaxed total with programs should be 1242.22")
        self.assertEqual(len(order.order_line.ids), 7, "Order should contains 7 lines: 4 products lines, 2 free products lines and a 20% discount line")

    def test_program_numbers_extras(self):
        # Check that you can't apply a global discount promo code if there is already an auto applied global discount
        self.p1.copy({'promo_code_usage': 'no_code_needed', 'name': 'Auto applied 10% global discount'})
        order = self.empty_order
        self.env['sale.order.line'].create({
            'product_id': self.iPadMini.id,
            'name': 'iPad',
            'product_uom_qty': 1.0,
            'order_id': order.id,
        })
        order.recompute_coupon_lines()
        self.assertEqual(len(order.order_line.ids), 2, "We should get 1 iPad line and 1 10% auto applied global discount line")
        self.assertEqual(order.amount_total, 288, "320$ - 10%")
        with self.assertRaises(UserError):
            # Can't apply a second global discount
            self.env['sale.coupon.apply.code'].with_context(active_id=order.id).create({
                'coupon_code': 'test_10pc'
            }).process_coupon()

    def test_program_fixed_price(self):
        # Check fixed amount discount
        order = self.empty_order
        fixed_amount_program = self.env['sale.coupon.program'].create({
            'name': '$249 discount',
            'promo_code_usage': 'no_code_needed',
            'program_type': 'promotion_program',
            'discount_type': 'fixed_amount',
            'discount_fixed_amount': 249.0,
        })
        self.tax_0pc_excl = self.env['account.tax'].create({
            'name': "0% Tax excl",
            'amount_type': 'percent',
            'amount': 0,
        })
        fixed_amount_program.discount_line_product_id.write({'taxes_id': [(4, self.tax_0pc_excl.id, False)]})
        sol1 = self.env['sale.order.line'].create({
            'product_id': self.computerCase.id,
            'name': 'Computer Case',
            'product_uom_qty': 1.0,
            'order_id': order.id,
        })
        order.recompute_coupon_lines()
        self.assertEqual(order.amount_total, 0, "Total should be null. The fixed amount discount is higher than the SO total, it should be reduced to the SO total")
        self.assertEqual(len(order.order_line.ids), 2, "There should be the product line and the reward line")
        sol1.product_uom_qty = 17
        order.recompute_coupon_lines()
        self.assertEqual(order.amount_total, 176, "Fixed amount discount should be totally deduced")
        self.assertEqual(len(order.order_line.ids), 2, "Number of lines should be unchanged as we just recompute the reward line")
        sol2 = order.order_line.filtered(lambda l: l.id != sol1.id)
        self.assertEqual(len(sol2.tax_id.ids), 1, "One tax should be present on the reward line")
        self.assertEqual(sol2.tax_id.id, self.tax_0pc_excl.id, "The tax should be 0% Tax excl")
        fixed_amount_program.write({'active': False})  # Check archived product will remove discount lines on recompute
        order.recompute_coupon_lines()
        self.assertEqual(len(order.order_line.ids), 1, "Archiving the program should remove the program reward line")

    def test_program_next_order(self):
        order = self.empty_order
        self.env['sale.coupon.program'].create({
            'name': 'Free Keyboard if at least 1 article',
            'promo_code_usage': 'no_code_needed',
            'promo_applicability': 'on_next_order',
            'program_type': 'promotion_program',
            'reward_type': 'product',
            'reward_product_id': self.wirelessKeyboard.id,
            'rule_min_quantity': 2,
        })
        sol1 = self.env['sale.order.line'].create({
            'product_id': self.iPadMini.id,
            'name': 'iPad Mini',
            'product_uom_qty': 1.0,
            'order_id': order.id,
        })
        order.recompute_coupon_lines()
        self.assertEqual(len(order.order_line.ids), 1, "Nothing should be added to the cart")
        self.assertEqual(len(order.generated_coupon_ids), 0, "No coupon should have been generated yet")

        sol1.product_uom_qty = 2
        order.recompute_coupon_lines()
        generated_coupon = order.generated_coupon_ids
        self.assertEqual(len(order.order_line.ids), 1, "Nothing should be added to the cart (2)")
        self.assertEqual(len(generated_coupon), 1, "A coupon should have been generated")
        self.assertEqual(generated_coupon.state, 'reserved', "The coupon should be reserved")

        sol1.product_uom_qty = 1
        order.recompute_coupon_lines()
        generated_coupon = order.generated_coupon_ids
        self.assertEqual(len(order.order_line.ids), 1, "Nothing should be added to the cart (3)")
        self.assertEqual(len(generated_coupon), 1, "No more coupon should have been generated and the existing one should not have been deleted")
        self.assertEqual(generated_coupon.state, 'expired', "The coupon should have been set as expired as it is no more valid since we don't have the required quantity")

        sol1.product_uom_qty = 2
        order.recompute_coupon_lines()
        generated_coupon = order.generated_coupon_ids
        self.assertEqual(len(generated_coupon), 1, "We should still have only 1 coupon as we now benefit again from the program but no need to create a new one (see next assert)")
        self.assertEqual(generated_coupon.state, 'reserved', "The coupon should be set back to reserved as we had already an expired one, no need to create a new one")
