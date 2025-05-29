# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.addons.sale_loyalty.tests.common import TestSaleCouponCommon
from odoo.exceptions import ValidationError


class TestProgramWithCodeOperations(TestSaleCouponCommon):
    # Test the basic operation (apply_coupon) on an coupon program on which we should
    # apply the reward when the code is correct or remove the reward automatically when the reward is
    # not valid anymore.
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.discount_with_multi_rewards = cls.env['loyalty.program'].create({
            'name': 'Loyalty program with multiple discount rewards',
            'program_type': 'coupons',
            'reward_ids': [
                Command.create({
                    'reward_type': 'discount',
                    'discount_mode': 'percent',
                    'discount': 20,
                }),
                Command.create({
                    'reward_type': 'discount',
                    'discount_mode': 'percent',
                    'discount': 5,
                }),
            ],
        })

    def test_program_usability(self):
        # After clicking "Generate coupons", there is no domain so it shows "Match all records".
        # But when you click, domain is false (default field value; empty string) so it won't generate anything.
        # This is even more weird because if you add something in the domain and then delete it,
        # you visually come back to the initial state except the domain became '[]' instead of ''.
        # In this case, it will generate the coupon for every partner.
        # Thus, we should ensure that if you leave the domain untouched, it generates a coupon for each partner
        # as hinted on the screen ('Match all records (X records)')
        self.env['loyalty.generate.wizard'].with_context(active_id=self.code_promotion_program.id).create({
            'mode': 'selected',
        }).generate_coupons()
        self.assertEqual(len(self.code_promotion_program.coupon_ids), len(self.env['res.partner'].search([])), "It should have generated a coupon for every partner")

    def test_program_basic_operation_coupon_code(self):
        # Test case: Generate a coupon for my customer, and add a reward then remove it automatically

        self.immediate_promotion_program.active = False
        self.code_promotion_program.reward_ids.reward_type = 'discount'
        self.code_promotion_program.reward_ids.discount = 10

        self.env['loyalty.generate.wizard'].with_context(active_id=self.code_promotion_program.id).create({
            'mode': 'selected',
            'customer_ids': self.partner,
            'points_granted': 1,
        }).generate_coupons()
        coupon = self.code_promotion_program.coupon_ids

        # Test the valid code on a wrong sales order
        wrong_partner_order = self.env['sale.order'].create({
            'partner_id': self.env['res.partner'].create({'name': 'My Partner'}).id,
        })
        with self.assertRaises(ValidationError):
            self._apply_promo_code(wrong_partner_order, coupon.code)

        # Test now on a valid sales order
        order = self.empty_order
        order.write({'order_line': [
            (0, False, {
                'product_id': self.product_A.id,
                'name': '1 Product A',
                'product_uom': self.uom_unit.id,
                'product_uom_qty': 1.0,
            })
        ]})
        self._apply_promo_code(order, coupon.code)
        self.assertEqual(len(order.order_line.ids), 2)

        # Remove the product A from the sale order
        order.write({'order_line': [(2, order.order_line[0].id, False)]})
        order._update_programs_and_rewards()
        self.assertEqual(len(order.order_line.ids), 0)

    def test_program_coupon_double_consuming(self):
        # Test case:
        # - Generate a coupon
        # - add to a sale order A, cancel the sale order
        # - add to a sale order B, confirm the order
        # - go back to A, reset to draft and confirm

        self.immediate_promotion_program.active = False
        self.code_promotion_program.applies_on = 'future'
        self.code_promotion_program.reward_ids.reward_type = 'discount'
        self.code_promotion_program.reward_ids.discount = 10

        self.env['loyalty.generate.wizard'].with_context(active_id=self.code_promotion_program.id).create({
            'coupon_qty': 1,
            'points_granted': 1,
        }).generate_coupons()
        coupon = self.code_promotion_program.coupon_ids

        sale_order_a = self.empty_order.copy()
        sale_order_b = self.empty_order.copy()

        sale_order_a.write({'order_line': [
            (0, False, {
                'product_id': self.product_A.id,
                'name': '1 Product A',
                'product_uom': self.uom_unit.id,
                'product_uom_qty': 1.0,
            })
        ]})
        self._apply_promo_code(sale_order_a, coupon.code)
        self.assertEqual(len(sale_order_a.order_line.ids), 2)

        sale_order_a._action_cancel()

        sale_order_b.write({'order_line': [
            (0, False, {
                'product_id': self.product_A.id,
                'name': '1 Product A',
                'product_uom': self.uom_unit.id,
                'product_uom_qty': 1.0,
            })
        ]})
        self._apply_promo_code(sale_order_b, coupon.code)
        self.assertEqual(len(sale_order_b.order_line.ids), 2)

        sale_order_b.action_confirm()

        sale_order_a.action_draft()
        sale_order_a.action_confirm()
        # reward line removed automatically
        self.assertEqual(len(sale_order_a.order_line.ids), 1)

    def test_coupon_code_with_pricelist(self):
        # Test case: Generate a coupon (10% discount) and apply it on an order with a specific pricelist (10% discount)

        self.code_promotion_program_with_discount.applies_on = 'future'
        self.env['loyalty.generate.wizard'].with_context(active_id=self.code_promotion_program_with_discount.id).create({
            'coupon_qty': 1,
            'points_granted': 1,
        }).generate_coupons()
        coupon = self.code_promotion_program_with_discount.coupon_ids

        first_pricelist = self.env['product.pricelist'].create({
            'name': 'First pricelist',
            'item_ids': [(0, 0, {
                'compute_price': 'percentage',
                'base': 'list_price',
                'percent_price': 10,
                'applied_on': '3_global',
                'name': 'First discount'
            })]
        })

        order = self.empty_order
        order.pricelist_id = first_pricelist
        order.write({'order_line': [
            (0, False, {
                'product_id': self.product_C.id,
                'name': '1 Product C',
                'product_uom': self.uom_unit.id,
                'product_uom_qty': 1.0,
            })
        ]})
        self._apply_promo_code(order, coupon.code)
        self.assertEqual(len(order.order_line.ids), 2)
        self.assertEqual(order.amount_total, 81, "SO total should be 81: (10% of 100 with pricelist) + 10% of 90 with coupon code")

    def test_on_next_order_reward_promotion_program(self):
        # The flow:
        # 1. Create a program `A` that gives a free `Product B` on next order if you buy a an `product A`
        #    This program should be code_needed with code `free_B_on_next_order`
        # 2. Create a program `B` that gives 10% discount on next order automatically
        # 3. Create a SO with a `third product` and recompute coupon, you SHOULD get a coupon (from program `B`) for your next order that will discount 10%
        # 4. Try to apply `A`, it should error since we did not buy any product A.
        # 5. Add a product A to the cart and try to apply `A` again, this time it should work
        # 6. Verify you have 2 generated coupons and validate the SO (so the 2 generated coupons will be valid)
        # 7. Create a new SO (with the same partner)
        # 8. Add a Product B in the cart
        # 9. Try to apply once again coupon generated by `A`, it should give you the free product B
        # 10. Try to apply coupon generated by `B`, it should give you 10% discount.
        # => SO will then be 0$ until we recompute the order lines

        # 1.
        self.immediate_promotion_program.write({
            'applies_on': 'future',
            'trigger': 'with_code',
        })
        self.immediate_promotion_program.rule_ids.write({
            'mode': 'with_code',
            'code': 'free_B_on_next_order',
        })
        # 2.
        self.p1 = self.env['loyalty.program'].create({
            'name': 'Code for 10% on next order',
            'program_type': 'promotion',
            'applies_on': 'future',
            'trigger': 'auto',
            'rule_ids': [(0, 0, {})],
            'reward_ids': [(0, 0, {
                'reward_type': 'discount',
                'discount': 10,
                'discount_mode': 'percent',
                'discount_applicability': 'order',
            })],
        })
        # 3.
        order = self.empty_order.copy()
        self.third_product = self.env['product.product'].create({
            'name': 'Thrid Product',
            'list_price': 5,
            'sale_ok': True
        })
        order.write({'order_line': [
            (0, False, {
                'product_id': self.third_product.id,
                'name': '1 Third Product',
                'product_uom': self.uom_unit.id,
                'product_uom_qty': 1.0,
            })
        ]})
        order._update_programs_and_rewards()
        self.assertEqual(len(self.p1.coupon_ids.ids), 1, "You should get a coupon for you next order that will offer 10% discount")
        # 4.
        with self.assertRaises(ValidationError):
            self._apply_promo_code(order, 'free_B_on_next_order')
        # 5.
        order.write({'order_line': [
            (0, False, {
                'product_id': self.product_A.id,
                'name': '1 Product A',
                'product_uom': self.uom_unit.id,
                'product_uom_qty': 1.0,
            })
        ]})
        self._apply_promo_code(order, 'free_B_on_next_order', no_reward_fail=False)
        # 6.
        self.assertEqual(len(order._get_reward_coupons()), 2, "You should get a second coupon for your next order that will offer a free Product B")
        order.action_confirm()
        # 7.
        order_bis = self.empty_order

        # 8.
        order_bis.write({'order_line': [
            (0, False, {
                'product_id': self.product_B.id,
                'name': '1 Product B',
                'product_uom': self.uom_unit.id,
                'product_uom_qty': 1.0,
            })
        ]})
        # 9.
        self._apply_promo_code(order_bis, order._get_reward_coupons()[1].code)
        self.assertEqual(len(order_bis.order_line), 2, "You should get a free Product B")
        # 10.
        self._apply_promo_code(order_bis, order._get_reward_coupons()[0].code)
        self.assertEqual(len(order_bis.order_line), 3, "You should get a 10% discount line")
        self.assertAlmostEqual(order_bis.amount_total, order_bis.order_line[0].price_total * 0.9, 2, "SO total should be null: (Paid product - Free product = 0) + 10% of nothing")

    def test_on_next_order_reward_promotion_program_with_requirements(self):
        self.immediate_promotion_program.write({
            'applies_on': 'future',
            'trigger': 'with_code',
        })
        self.immediate_promotion_program.rule_ids.write({
            'minimum_amount': 700,
            'minimum_amount_tax_mode': 'excl',
            'mode': 'with_code',
            'code': 'free_B_on_next_order',
        })
        order = self.empty_order.copy()
        self.product_A.lst_price = 700
        order.write({'order_line': [
            (0, False, {
                'product_id': self.product_A.id,
                'name': '1 Product A',
                'product_uom': self.uom_unit.id,
                'product_uom_qty': 1.0,
            })
        ]})
        self._apply_promo_code(order, 'free_B_on_next_order', no_reward_fail=False)
        self.assertEqual(len(self.immediate_promotion_program.coupon_ids.ids), 1, "You should get a coupon for you next order that will offer a free product B")
        order_bis = self.empty_order
        order_bis.write({'order_line': [
            (0, False, {
                'product_id': self.product_B.id,
                'name': '1 Product B',
                'product_uom': self.uom_unit.id,
                'product_uom_qty': 1.0,
            })
        ]})
        with self.assertRaises(ValidationError):
            # It should error since we did not validate the previous SO, so the coupon is `reserved` but not `new`
            self._apply_promo_code(order_bis, order._get_reward_coupons()[0].code)
        order.action_confirm()
        # It should not error even if the SO does not have the requirements (700$ and 1 product A), since these requirements where only used to generate the coupon that we are now applying
        self._apply_promo_code(order_bis, order._get_reward_coupons()[0].code, no_reward_fail=False)
        self.assertEqual(len(order_bis.order_line), 2, "You should get 1 regular product_B and 1 free product_B")
        order_bis._update_programs_and_rewards()
        self.assertEqual(len(order_bis.order_line), 2, "Free product from a coupon generated from a promotion program on next order should not dissapear")

    def test_partner_assigned_to_next_order_coupon(self):
        """ Test the assignment of a partner on coupons with program type `next_order_coupons`.

        1. Create a loyalty program of type `next_order_coupons`.
        2. Create a sale order and add a product to it.
        3. Apply the loyalty program to the sale order.
        4. Verify that the generated coupon is assigned to the order's partner.
        """
        loyalty_program = self.env['loyalty.program'].create({
            'name': '10% Discount on Next Order',
            'program_type': 'next_order_coupons',
            'applies_on': 'future',
            'trigger': 'auto',
            'rule_ids': [Command.create({})],
            'reward_ids': [Command.create({
                'reward_type': 'discount',
                'discount': 10,
                'discount_mode': 'percent',
                'discount_applicability': 'order',
            })],
        })
        order = self.empty_order
        order.write({'order_line': [
            Command.create({
                'product_id': self.product_A.id,
                'name': '1 Product A',
                'product_uom': self.uom_unit.id,
                'product_uom_qty': 1.0,
            })
        ]})
        generated_coupons = order._try_apply_program(loyalty_program).get('coupon')
        self.assertTrue(generated_coupons, "A coupon should have been generated")
        self.assertEqual(generated_coupons.partner_id, order.partner_id,
            "The partner should be set on the coupon with program type 'next_order_coupons'"
        )

    def test_public_partner_updated_in_next_order_coupon(self):
        """ Test the update of a partner on coupons with program type `next_order_coupons`.

        1. Create a loyalty program of type `next_order_coupons`.
        2. Create a sale order for a public user and add a product to it.
        3. Apply the loyalty program to the sale order.
        4. Verify that the generated coupon is assigned to the public user.
        5. Change the partner.
        6. Verify that the generated coupon was updated to this new user.
        """
        loyalty_program = self.env['loyalty.program'].create({
            'name': "10% Discount on Next Order",
            'program_type': 'next_order_coupons',
            'applies_on': 'future',
            'trigger': 'auto',
            'rule_ids': [Command.create({})],
            'reward_ids': [Command.create({
                'reward_type': 'discount',
                'discount': 10,
                'discount_mode': 'percent',
                'discount_applicability': 'order',
            })],
        })
        order = self.empty_order
        order.write({
            'partner_id': self.env.ref('base.public_partner').id,
            'order_line': [Command.create({'product_id': self.product_A.id})],
        })
        generated_coupons = order._try_apply_program(loyalty_program).get('coupon')
        self.assertTrue(generated_coupons, "A coupon should have been generated")
        self.assertEqual(
            generated_coupons.partner_id, order.partner_id,
            "The partner should be set on the coupon with program type 'next_order_coupons'",
        )
        self.assertTrue(generated_coupons.partner_id.is_public)

        # Change partner from Public User to a known customer (e.g. a portal user logging in)
        order.partner_id = self.partner
        order._update_programs_and_rewards()
        self.assertEqual(
            generated_coupons.partner_id, self.partner,
            "The coupon's partner_id should be updated if it was created for a Public User",
        )

    def test_edit_and_reapply_promotion_program(self):
        # The flow:
        # 1. Create a program auto applied, giving a fixed amount discount
        # 2. Create a SO and apply the program
        # 3. Change the program, requiring a mandatory code
        # 4. Reapply the program on the same SO via code

        self.immediate_promotion_program.active = False
        # 1.
        self.p1 = self.env['loyalty.program'].create({
            'name': 'Promo fixed amount',
            'trigger': 'auto',
            'program_type': 'promotion',
            'rule_ids': [(0, 0, {})],
            'reward_ids': [(0, 0, {
                'reward_type': 'discount',
                'discount': 10,
                'discount_mode': 'per_point',
                'discount_applicability': 'order',
            })]
        })
        # 2.
        order = self.empty_order.copy()
        order.write({'order_line': [
            (0, False, {
                'product_id': self.product_A.id,
                'name': '1 Product A',
                'product_uom': self.uom_unit.id,
                'product_uom_qty': 1.0,
            })
        ]})
        order._update_programs_and_rewards()
        self._claim_reward(order, self.p1)
        self.assertEqual(len(order.order_line), 2, "You should get a discount line") # product + discount
        # 3.
        self.p1.write({
            'trigger': 'with_code',
        })
        self.p1.rule_ids.write({
            'mode': 'with_code',
            'code': 'test',
        })
        order._update_programs_and_rewards()
        self.assertEqual(len(order.order_line), 1, "You loose a discount line")
        # 4.
        self._apply_promo_code(order, 'test')
        # But the above line should not add any reward
        self.assertEqual(len(order.order_line), 2, "You should get a discount line") # product + discount

    def test_reapply_multiple_global_rewards_when_new_discount_greater(self):
        """ Test applying the maximum reward discount from multiple rewards when the applied
            coupon discount is lower.

        1. Create a two loyalty program of type `coupons`.
        2. Add multiple rewards to the second program.
        3. Generate a coupon for each program.
        2. Create a sale order and add a product to it.
        3. Apply the Coupon to the sale order.
        4. Try to apply the second coupon with multiple rewards.
        5. Reward with best discount will be shown.
        """
        self.code_promotion_program_with_discount.rule_ids.unlink()
        coupon_1 = self._generate_coupons(self.code_promotion_program_with_discount)
        coupon_2 = self._generate_coupons(self.discount_with_multi_rewards)

        order = self.empty_order
        self.assertEqual(order.amount_total, 0.0)
        order.write({'order_line': [
            Command.create({
                'product_id': self.product_A.id,
                'name': '1 Product A',
                'product_uom': self.uom_unit.id,
                'product_uom_qty': 1.0,
            }),
            Command.create({
                'product_id': self.product_B.id,
                'name': '1 Product B',
                'product_uom': self.uom_unit.id,
                'product_uom_qty': 1.0,
            }),
        ]})

        # The order line should be created with the correct price unit
        self.assertEqual(len(order.order_line.ids), 2)
        self.assertEqual(order.order_line[0].price_unit, 100.0)
        self.assertEqual(order.order_line[1].price_unit, 5.0)
        expected_total = order.amount_total * 0.80

        # Apply the first coupon
        self._apply_promo_code(order, coupon_1.code)
        self.assertEqual(len(order.order_line.ids), 3)
        msg = "The discount line should be the 10% discount on the sale order total."
        self.assertEqual(order.order_line[2].price_unit, -10.5, msg=msg)

        # Apply the second coupon with multiple rewards
        self._apply_promo_code(order, coupon_2.code)
        self.assertEqual(len(order.order_line.ids), 3)
        msg = "The discount line should be the 20% discount on the sale order total."
        self.assertEqual(order.order_line[2].price_unit, -21.0, msg=msg)
        msg = "Order total should reflect the 20% discount"
        self.assertAlmostEqual(order.amount_total, expected_total, msg=msg)

    def test_reapply_multiple_higher_global_rewards_lets_choose_best(self):
        """ Test applying the maximum reward discount from multiple rewards when the applied
            coupon discount is lower.

        1. Create a two loyalty program of type `coupons`.
        2. Add multiple rewards of higher discount than the applied discount.
        3. Generate a coupon for each program.
        2. Create a sale order and add a product to it.
        3. Apply the Coupon to the sale order.
        4. Try to apply the second coupon with multiple rewards.
        5. Reward with max discount will be shown.
        """
        self.code_promotion_program_with_discount.rule_ids.unlink()
        coupon_1 = self._generate_coupons(self.code_promotion_program_with_discount)
        self.discount_with_multi_rewards.reward_ids[1].discount = 15
        coupon_2 = self._generate_coupons(self.discount_with_multi_rewards)

        order = self.empty_order
        self.assertEqual(order.amount_total, 0.0)
        order.write({'order_line': [
            Command.create({
                'product_id': self.product_A.id,
                'name': '1 Product A',
                'product_uom': self.uom_unit.id,
                'product_uom_qty': 1.0,
            })
        ]})

        # The order line should be created with the correct price unit
        self.assertEqual(len(order.order_line.ids), 1)
        self.assertEqual(order.order_line[0].price_unit, 100.0)
        expected_total = order.amount_total * 0.80

        # Apply the first coupon
        self._apply_promo_code(order, coupon_1.code)
        self.assertEqual(len(order.order_line.ids), 2)
        msg = "The discount line should be the 10% discount on the sale order total."
        self.assertEqual(order.order_line[1].price_unit, -10.0, msg=msg)

        # Apply the second coupon with multiple rewards of higher discount
        rewards = self._apply_promo_code(order, coupon_2.code)
        self.assertEqual(len(rewards), 2)

        # Choose the reward with the maximum discount
        chosen_reward = rewards.filtered(lambda r: r.discount == 20)
        order._apply_program_reward(chosen_reward, coupon_2)
        self.assertEqual(len(order.order_line), 2)
        msg = "The discount line should be the 20% discount on the sale order total."
        self.assertEqual(order.order_line[1].price_unit, -20.0, msg=msg)
        msg = "Order total should reflect the 20% discount"
        self.assertAlmostEqual(order.amount_total, expected_total, msg=msg)

    def test_reapplying_new_multiple_lower_global_rewards_discount_raise_validation(self):
        """ Test raising validation when the new coupon discount from multiple rewards
            is less than the applied coupon discount.

        1. Create a two loyalty program of type `coupons`.
        2. Add multiple rewards to the second program.
        3. Generate a coupon for each program.
        2. Create a sale order and add a product to it.
        3. Apply the Coupon to the sale order.
        4. Try to apply the second coupon with multiple rewards.
        5. Verify that it raises a validation error.
        """
        self.code_promotion_program_with_discount.rule_ids.unlink()
        coupon_1 = self._generate_coupons(self.code_promotion_program_with_discount)
        self.discount_with_multi_rewards.reward_ids[0].discount = 7
        coupon_2 = self._generate_coupons(self.discount_with_multi_rewards)

        order = self.empty_order
        self.assertEqual(order.amount_total, 0.0)
        order.write({'order_line': [
            Command.create({
                'product_id': self.product_A.id,
                'name': '1 Product A',
                'product_uom': self.uom_unit.id,
                'product_uom_qty': 1.0,
            })
        ]})

        # The order line should be created with the correct price unit
        self.assertEqual(len(order.order_line.ids), 1)
        self.assertEqual(order.order_line[0].price_unit, 100.0)

        # Apply the first coupon
        self._apply_promo_code(order, coupon_1.code)
        msg = "The discount line should be the 10% discount on the sale order total."
        self.assertEqual(order.order_line[1].price_unit, -10.0, msg=msg)
        self.assertEqual(len(order.order_line.ids), 2)

        # raise validation error when applying the second coupon with multiple rewards
        # with a discount lower than the applied coupon discount
        msg = "The new coupon discount should be greater than the applied coupon discount"
        with self.assertRaises(ValidationError, msg=msg):
            self._apply_promo_code(order, coupon_2.code)
