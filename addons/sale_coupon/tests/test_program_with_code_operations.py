# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.sale_coupon.tests.common import TestSaleCouponCommon
from odoo.exceptions import UserError


class TestProgramWithCodeOperations(TestSaleCouponCommon):
    # Test the basic operation (apply_coupon) on an coupon program on which we should
    # apply the reward when the code is correct or remove the reward automatically when the reward is
    # not valid anymore.

    def test_program_usability(self):
        # After clicking "Generate coupons", there is no domain so it shows "Match all records".
        # But when you click, domain is false (default field value; empty string) so it won't generate anything.
        # This is even more weird because if you add something in the domain and then delete it,
        # you visually come back to the initial state except the domain became '[]' instead of ''.
        # In this case, it will generate the coupon for every partner.
        # Thus, we should ensure that if you leave the domain untouched, it generates a coupon for each partner
        # as hinted on the screen ('Match all records (X records)')
        self.env['coupon.generate.wizard'].with_context(active_id=self.code_promotion_program.id).create({
            'generation_type': 'nbr_customer',
        }).generate_coupon()
        self.assertEqual(len(self.code_promotion_program.coupon_ids), len(self.env['res.partner'].search([])), "It should have generated a coupon for every partner")

    def test_program_basic_operation_coupon_code(self):
        # Test case: Generate a coupon for my customer, and add a reward then remove it automatically

        self.code_promotion_program.reward_type = 'discount'

        self.env['coupon.generate.wizard'].with_context(active_id=self.code_promotion_program.id).create({
            'generation_type': 'nbr_customer',
            'partners_domain': "[('id', 'in', [%s])]" % (self.steve.id),
        }).generate_coupon()
        coupon = self.code_promotion_program.coupon_ids

        # Test the valid code on a wrong sales order
        wrong_partner_order = self.env['sale.order'].create({
            'partner_id': self.env['res.partner'].create({'name': 'My Partner'}).id,
        })
        with self.assertRaises(UserError):
            self.env['sale.coupon.apply.code'].with_context(active_id=wrong_partner_order.id).create({
                'coupon_code': coupon.code
            }).process_coupon()

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
        self.env['sale.coupon.apply.code'].with_context(active_id=order.id).create({
            'coupon_code': coupon.code
        }).process_coupon()
        order.recompute_coupon_lines()
        self.assertEqual(len(order.order_line.ids), 2)
        self.assertEqual(coupon.state, 'used')

        # Remove the product A from the sale order
        order.write({'order_line': [(2, order.order_line[0].id, False)]})
        order.recompute_coupon_lines()
        self.assertEqual(len(order.order_line.ids), 0)
        self.assertEqual(coupon.state, 'new')

    def test_program_coupon_double_consuming(self):
        # Test case:
        # - Generate a coupon
        # - add to a sale order A, cancel the sale order
        # - add to a sale order B, confirm the order
        # - go back to A, reset to draft and confirm

        self.code_promotion_program.reward_type = 'discount'

        self.env['coupon.generate.wizard'].with_context(active_id=self.code_promotion_program.id).create({
            'generation_type': 'nbr_coupon',
            'nbr_coupons': 1,
        }).generate_coupon()
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
        self.env['sale.coupon.apply.code'].with_context(active_id=sale_order_a.id).create({
            'coupon_code': coupon.code
        }).process_coupon()
        sale_order_a.recompute_coupon_lines()
        self.assertEqual(len(sale_order_a.order_line.ids), 2)
        self.assertEqual(coupon.state, 'used')
        self.assertEqual(coupon.sales_order_id, sale_order_a)

        sale_order_a.action_cancel()

        sale_order_b.write({'order_line': [
            (0, False, {
                'product_id': self.product_A.id,
                'name': '1 Product A',
                'product_uom': self.uom_unit.id,
                'product_uom_qty': 1.0,
            })
        ]})
        self.env['sale.coupon.apply.code'].with_context(active_id=sale_order_b.id).create({
            'coupon_code': coupon.code
        }).process_coupon()
        sale_order_b.recompute_coupon_lines()
        self.assertEqual(len(sale_order_b.order_line.ids), 2)
        self.assertEqual(coupon.state, 'used')
        self.assertEqual(coupon.sales_order_id, sale_order_b)

        sale_order_b.action_confirm()

        sale_order_a.action_draft()
        sale_order_a.action_confirm()
        # reward line removed automatically
        self.assertEqual(len(sale_order_a.order_line.ids), 1)

    def test_coupon_code_with_pricelist(self):
        # Test case: Generate a coupon (10% discount) and apply it on an order with a specific pricelist (10% discount)

        self.env['coupon.generate.wizard'].with_context(active_id=self.code_promotion_program_with_discount.id).create({
            'generation_type': 'nbr_coupon',
            'nbr_coupons': 1,
        }).generate_coupon()
        coupon = self.code_promotion_program_with_discount.coupon_ids

        first_pricelist = self.env['product.pricelist'].create({
            'name': 'First pricelist',
            'discount_policy': 'with_discount',
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
        self.env['sale.coupon.apply.code'].with_context(active_id=order.id).create({
            'coupon_code': coupon.code
        }).process_coupon()
        order.recompute_coupon_lines()
        self.assertEqual(len(order.order_line.ids), 2)
        self.assertEqual(coupon.state, 'used')
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
        # 7. Create a new SO (with the same partner) and try to apply coupon generated by `A`. it SHOULD error since we don't have any `Product B` in the cart
        # 8. Add a Product B in the cart
        # 9. Try to apply once again coupon generated by `A`, it should give you the free product B
        # 10. Try to apply coupon generated by `B`, it should give you 10% discount.
        # => SO will then be 0$ until we recompute the order lines

        # 1.
        self.immediate_promotion_program.write({
            'promo_applicability': 'on_next_order',
            'promo_code_usage': 'code_needed',
            'promo_code': 'free_B_on_next_order',
        })
        # 2.
        self.p1 = self.env['coupon.program'].create({
            'name': 'Code for 10% on next order',
            'discount_type': 'percentage',
            'discount_percentage': 10.0,
            'program_type': 'promotion_program',
            'promo_code_usage': 'no_code_needed',
            'promo_applicability': 'on_next_order',
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
        order.recompute_coupon_lines()
        self.assertEqual(len(self.p1.coupon_ids.ids), 1, "You should get a coupon for you next order that will offer 10% discount")
        # 4.
        with self.assertRaises(UserError):
            self.env['sale.coupon.apply.code'].with_context(active_id=order.id).create({
                'coupon_code': 'free_B_on_next_order'
            }).process_coupon()
        # 5.
        order.write({'order_line': [
            (0, False, {
                'product_id': self.product_A.id,
                'name': '1 Product A',
                'product_uom': self.uom_unit.id,
                'product_uom_qty': 1.0,
            })
        ]})
        self.env['sale.coupon.apply.code'].with_context(active_id=order.id).create({
            'coupon_code': 'free_B_on_next_order'
        }).process_coupon()
        # 6.
        self.assertEqual(len(order.generated_coupon_ids), 2, "You should get a second coupon for your next order that will offer a free Product B")
        order.action_confirm()
        # 7.
        order_bis = self.empty_order
        with self.assertRaises(UserError):
            self.env['sale.coupon.apply.code'].with_context(active_id=order_bis.id).create({
                'coupon_code': order.generated_coupon_ids[1].code
            }).process_coupon()
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
        self.env['sale.coupon.apply.code'].with_context(active_id=order_bis.id).create({
            'coupon_code': order.generated_coupon_ids[1].code
        }).process_coupon()
        self.assertEqual(len(order_bis.order_line), 2, "You should get a free Product B")
        # 10.
        self.env['sale.coupon.apply.code'].with_context(active_id=order_bis.id).create({
            'coupon_code': order.generated_coupon_ids[0].code
        }).process_coupon()
        self.assertEqual(len(order_bis.order_line), 3, "You should get a 10% discount line")
        self.assertEqual(order_bis.amount_total, 0, "SO total should be null: (Paid product - Free product = 0) + 10% of nothing")

    def test_on_next_order_reward_promotion_program_with_requirements(self):
        self.immediate_promotion_program.write({
            'promo_applicability': 'on_next_order',
            'promo_code_usage': 'code_needed',
            'promo_code': 'free_B_on_next_order',
            'rule_minimum_amount': 700,
            'rule_minimum_amount_tax_inclusion': 'tax_excluded'
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
        self.env['sale.coupon.apply.code'].with_context(active_id=order.id).create({
            'coupon_code': 'free_B_on_next_order'
        }).process_coupon()
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
        with self.assertRaises(UserError):
            # It should error since we did not validated the previous SO, so the coupon is `reserved` but not `new`
            self.env['sale.coupon.apply.code'].with_context(active_id=order_bis.id).create({
                'coupon_code': order.generated_coupon_ids[0].code
            }).process_coupon()
        order.action_confirm()
        # It should not error even if the SO does not have the requirements (700$ and 1 product A), since these requirements where only used to generate the coupon that we are now applying
        self.env['sale.coupon.apply.code'].with_context(active_id=order_bis.id).create({
            'coupon_code': order.generated_coupon_ids[0].code
        }).process_coupon()
        self.assertEqual(len(order_bis.order_line), 2, "You should get 1 regular product_B and 1 free product_B")
        order_bis.recompute_coupon_lines()
        self.assertEqual(len(order_bis.order_line), 2, "Free product from a coupon generated from a promotion program on next order should not dissapear")

    def test_edit_and_reapply_promotion_program(self):
        # The flow:
        # 1. Create a program auto applied, giving a fixed amount discount
        # 2. Create a SO and apply the program
        # 3. Change the program, requiring a mandatory code
        # 4. Reapply the program on the same SO via code

        # 1.
        self.p1 = self.env['coupon.program'].create({
            'name': 'Promo fixed amount',
            'promo_code_usage': 'no_code_needed',
            'discount_type': 'fixed_amount',
            'discount_fixed_amount': 10.0,
            'program_type': 'promotion_program',
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
        order.recompute_coupon_lines()
        self.assertEqual(len(order.order_line), 2, "You should get a discount line")
        # 3.
        self.p1.write({
            'promo_code_usage': 'code_needed',
            'promo_code': 'test',
            })
        order.recompute_coupon_lines()
        # 4.
        with self.assertRaises(UserError):
            self.env['sale.coupon.apply.code'].with_context(active_id=order.id).create({
                'coupon_code': 'test'
            }).process_coupon()
        self.assertEqual(len(order.order_line), 2, "You should get a discount line")
