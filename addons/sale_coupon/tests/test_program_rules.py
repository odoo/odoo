# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo.addons.sale_coupon.tests.common import TestSaleCouponCommon
from odoo.exceptions import UserError
from odoo.fields import Date
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestProgramRules(TestSaleCouponCommon):
    # Test all the validity rules to allow a customer to have a reward.
    # The check based on the products is already done in the basic operations test

    def test_program_rules_partner_based(self):
        # Test case: Based on the partners domain

        self.immediate_promotion_program.write({'rule_partners_domain': "[('id', 'in', [%s])]" % (self.steve.id)})

        order = self.empty_order
        order.write({'order_line': [
            (0, False, {
                'product_id': self.product_A.id,
                'name': '1 Product A',
                'product_uom': self.uom_unit.id,
                'product_uom_qty': 1.0,
            }),
            (0, False, {
                'product_id': self.product_B.id,
                'name': '2 Product B',
                'product_uom': self.uom_unit.id,
                'product_uom_qty': 1.0,
            })
        ]})
        order.recompute_coupon_lines()
        self.assertEqual(len(order.order_line.ids), 3, "The promo offert should have been applied as the partner is correct, the discount is not created")

        order = self.env['sale.order'].create({'partner_id': self.env['res.partner'].create({'name': 'My Partner'}).id})
        order.write({'order_line': [
            (0, False, {
                'product_id': self.product_A.id,
                'name': '1 Product A',
                'product_uom': self.uom_unit.id,
                'product_uom_qty': 1.0,
            }),
            (0, False, {
                'product_id': self.product_B.id,
                'name': '2 Product B',
                'product_uom': self.uom_unit.id,
                'product_uom_qty': 1.0,
            })
        ]})
        order.recompute_coupon_lines()
        self.assertEqual(len(order.order_line.ids), 2, "The promo offert shouldn't have been applied, the discount is created")

    def test_program_rules_minimum_purchased_amount(self):
        # Test case: Based on the minimum purchased

        self.immediate_promotion_program.write({
            'rule_minimum_amount': 1006,
            'rule_minimum_amount_tax_inclusion': 'tax_excluded'
        })

        order = self.empty_order
        order.write({'order_line': [
            (0, False, {
                'product_id': self.product_A.id,
                'name': '1 Product A',
                'product_uom': self.uom_unit.id,
                'product_uom_qty': 1.0,
            }),
            (0, False, {
                'product_id': self.product_B.id,
                'name': '2 Product B',
                'product_uom': self.uom_unit.id,
                'product_uom_qty': 1.0,
            })
        ]})
        order.recompute_coupon_lines()
        self.assertEqual(len(order.order_line.ids), 2, "The promo offert shouldn't have been applied as the purchased amount is not enough")

        order = self.env['sale.order'].create({'partner_id': self.steve.id})
        order.write({'order_line': [
            (0, False, {
                'product_id': self.product_A.id,
                'name': '10 Product A',
                'product_uom': self.uom_unit.id,
                'product_uom_qty': 10.0,
            }),
            (0, False, {
                'product_id': self.product_B.id,
                'name': '2 Product B',
                'product_uom': self.uom_unit.id,
                'product_uom_qty': 1.0,
            })
        ]})
        order.recompute_coupon_lines()
        # 10*100 + 5 = 1005
        self.assertEqual(len(order.order_line.ids), 2, "The promo offert should not be applied as the purchased amount is not enough")

        self.immediate_promotion_program.rule_minimum_amount = 1005
        order.recompute_coupon_lines()
        self.assertEqual(len(order.order_line.ids), 3, "The promo offert should be applied as the purchased amount is now enough")

        # 10*(100*1.15) + (5*1.15) = 10*115 + 5.75 = 1155.75
        self.immediate_promotion_program.rule_minimum_amount = 1006
        self.immediate_promotion_program.rule_minimum_amount_tax_inclusion = 'tax_included'
        order.recompute_coupon_lines()
        self.assertEqual(len(order.order_line.ids), 3, "The promo offert should be applied as the initial amount required is now tax included")

    def test_program_rules_minimum_purchased_amount_and_free_product(self):
        # Test cases: Based on the minimum purchased and free product
        self.immediate_promotion_program.write({
            'rule_minimum_amount': 10,
            'rule_products_domain': "[]",
            'rule_minimum_amount_tax_inclusion': 'tax_excluded',
        })

        # Case 1: price unit = 5, qty = 2, total = 10, no reward
        order = self.empty_order
        order.write({
            'order_line': [(0, False, {
                'product_id': self.product_B.id,
                'name': '2 Product B',
                'product_uom': self.uom_unit.id,
                'product_uom_qty': 2.0,
            })]
        })
        order.recompute_coupon_lines()
        msg = """
            The promo shouldn't have been applied as the order amount is not enough after 
            applying promo with free product.
        """
        self.assertEqual(len(order.order_line.ids), 1, msg)
        self.assertEqual(order.amount_untaxed, 10)

        # Case 2: price unit = 5, qty = 5, total = 25-5, 1 reward (5)
        order = self.env['sale.order'].create({'partner_id': self.steve.id})
        order.write({
            'order_line': [(0, False, {
                'product_id': self.product_B.id,
                'name': '5 Product B',
                'product_uom': self.uom_unit.id,
                'product_uom_qty': 5.0,
                })]
        })
        order.recompute_coupon_lines()
        promo_lines = order.order_line.filtered(lambda l: l.is_reward_line)
        msg = "The promo offer should have been applied only once."
        self.assertEqual(len(promo_lines), 1, msg)
        self.assertEqual(promo_lines[0].product_uom_qty, 1, msg)
        self.assertEqual(order.amount_untaxed, 20)

        # Case 3: price unit = 5, qty = 6, total = 30-10, 2 rewards (2*5)
        order = self.env['sale.order'].create({'partner_id': self.steve.id})
        order.write({
            'order_line': [(0, False, {
                'product_id': self.product_B.id,
                'name': '6 Product B',
                'product_uom': self.uom_unit.id,
                'product_uom_qty': 6.0,
                })]
        })
        order.recompute_coupon_lines()
        promo_lines = order.order_line.filtered(lambda l: l.is_reward_line)
        msg = "The promo offer should have been applied twice."
        self.assertEqual(len(promo_lines), 1, msg)
        self.assertEqual(promo_lines[0].product_uom_qty, 2, msg)
        self.assertEqual(order.amount_untaxed, 20)

    def test_program_rules_validity_dates_and_uses(self):
        # Test case: Based on the validity dates and the number of allowed uses

        self.immediate_promotion_program.write({
            'rule_date_from': Date.to_string((datetime.now() - timedelta(days=7))),
            'rule_date_to': Date.to_string((datetime.now() - timedelta(days=2))),
            'maximum_use_number': 1,
        })

        order = self.empty_order
        order.write({'order_line': [
            (0, False, {
                'product_id': self.product_A.id,
                'name': '1 Product A',
                'product_uom': self.uom_unit.id,
                'product_uom_qty': 1.0,
            }),
            (0, False, {
                'product_id': self.product_B.id,
                'name': '2 Product B',
                'product_uom': self.uom_unit.id,
                'product_uom_qty': 1.0,
            })
        ]})
        order.recompute_coupon_lines()
        self.assertEqual(len(order.order_line.ids), 2, "The promo offert shouldn't have been applied we're not between the validity dates")

        self.immediate_promotion_program.write({
            'rule_date_from': Date.to_string((datetime.now() - timedelta(days=7))),
            'rule_date_to': Date.to_string((datetime.now() + timedelta(days=2))),
        })
        order = self.env['sale.order'].create({'partner_id': self.steve.id})
        order.write({'order_line': [
            (0, False, {
                'product_id': self.product_A.id,
                'name': '1 Product A',
                'product_uom': self.uom_unit.id,
                'product_uom_qty': 10.0,
            }),
            (0, False, {
                'product_id': self.product_B.id,
                'name': '2 Product B',
                'product_uom': self.uom_unit.id,
                'product_uom_qty': 1.0,
            })
        ]})
        order.recompute_coupon_lines()
        self.assertEqual(len(order.order_line.ids), 3, "The promo offert should have been applied as we're between the validity dates")
        order = self.env['sale.order'].create({'partner_id': self.env['res.partner'].create({'name': 'My Partner'}).id})
        order.write({'order_line': [
            (0, False, {
                'product_id': self.product_A.id,
                'name': '1 Product A',
                'product_uom': self.uom_unit.id,
                'product_uom_qty': 10.0,
            }),
            (0, False, {
                'product_id': self.product_B.id,
                'name': '2 Product B',
                'product_uom': self.uom_unit.id,
                'product_uom_qty': 1.0,
            })
        ]})
        order.recompute_coupon_lines()
        self.assertEqual(len(order.order_line.ids), 2, "The promo offert shouldn't have been applied as the number of uses is exceeded")

    def test_program_rules_one_date(self):
        # Test case: Based on the validity dates and the number of allowed uses

        # VFE NOTE the .rule_id is necessary to ensure the dates constraints doesn't raise
        # because the orm applies the related inverse one by one, raising the constraint...
        self.immediate_promotion_program.rule_id.write({
            'rule_date_from': False,
            'rule_date_to': Date.to_string((datetime.now() - timedelta(days=2))),
        })

        order = self.empty_order
        order.write({'order_line': [
            (0, False, {
                'product_id': self.product_A.id,
                'name': '1 Product A',
                'product_uom': self.uom_unit.id,
                'product_uom_qty': 1.0,
            }),
            (0, False, {
                'product_id': self.product_B.id,
                'name': '2 Product B',
                'product_uom': self.uom_unit.id,
                'product_uom_qty': 1.0,
            })
        ]})
        order.recompute_coupon_lines()
        self.assertNotIn(self.immediate_promotion_program, order._get_applicable_programs())
        self.assertEqual(len(order.order_line.ids), 2, "The promo offert shouldn't have been applied we're not between the validity dates")

        self.immediate_promotion_program.rule_id.write({
            'rule_date_from': Date.to_string((datetime.now() + timedelta(days=1))),
            'rule_date_to': False,
        })
        order.recompute_coupon_lines()
        self.assertNotIn(self.immediate_promotion_program, order._get_applicable_programs())
        self.assertEqual(len(order.order_line.ids), 2, "The promo offert shouldn't have been applied we're not between the validity dates")

        self.immediate_promotion_program.rule_id.write({
            'rule_date_from': False,
            'rule_date_to': Date.to_string((datetime.now() + timedelta(days=2))),
        })
        order.recompute_coupon_lines()
        self.assertIn(self.immediate_promotion_program, order._get_applicable_programs())
        self.assertEqual(len(order.order_line.ids), 3, "The promo offer should have been applied as we're between the validity dates")

        self.immediate_promotion_program.rule_id.write({
            'rule_date_from': Date.to_string((datetime.now() - timedelta(days=1))),
            'rule_date_to': False,
        })
        order.recompute_coupon_lines()
        self.assertIn(self.immediate_promotion_program, order._get_applicable_programs())
        self.assertEqual(len(order.order_line.ids), 3, "The promo offer should have been applied as we're between the validity dates")

    def test_program_rules_date(self):
        # Test case: Based on the validity dates

        # VFE NOTE the .rule_id is necessary to ensure the dates constraints doesn't raise
        # because the orm applies the related inverse one by one, raising the constraint...
        self.immediate_promotion_program.rule_id.write({
            'rule_date_from': Date.to_string((datetime.now() - timedelta(days=7))),
            'rule_date_to': Date.to_string((datetime.now() - timedelta(days=2))),
        })

        order = self.empty_order
        order.write({
            'date_order': Date.to_string((datetime.now() - timedelta(days=5))),
        })
        order.write({'order_line': [
            (0, False, {
                'product_id': self.product_A.id,
                'name': '1 Product A',
                'product_uom': self.uom_unit.id,
                'product_uom_qty': 1.0,
            }),
            (0, False, {
                'product_id': self.product_B.id,
                'name': '2 Product B',
                'product_uom': self.uom_unit.id,
                'product_uom_qty': 1.0,
            })
        ]})
        order.recompute_coupon_lines()
        self.assertNotIn(self.immediate_promotion_program, order._get_applicable_programs())
        self.assertEqual(len(order.order_line.ids), 2, "The promo offert shouldn't have been applied we're not between the validity dates")

        self.immediate_promotion_program.rule_id.write({
            'rule_date_from': Date.to_string((datetime.now() + timedelta(days=2))),
            'rule_date_to': Date.to_string((datetime.now() + timedelta(days=7))),
        })
        order.recompute_coupon_lines()
        self.assertNotIn(self.immediate_promotion_program, order._get_applicable_programs())
        self.assertEqual(len(order.order_line.ids), 2, "The promo offert shouldn't have been applied we're not between the validity dates")

        self.immediate_promotion_program.rule_id.write({
            'rule_date_from': Date.to_string((datetime.now() - timedelta(days=2))),
            'rule_date_to': Date.to_string((datetime.now() + timedelta(days=2))),
        })
        order.recompute_coupon_lines()
        self.assertIn(self.immediate_promotion_program, order._get_applicable_programs())
        self.assertEqual(len(order.order_line.ids), 3, "The promo offer should have been applied as we're between the validity dates")

    def test_program_rules_coupon_qty_and_amount_remove_not_eligible(self):
        ''' This test will:
                * Check quantity and amount requirements works as expected (since it's slightly different from a promotion_program)
                * Ensure that if a reward from a coupon_program was allowed and the conditions are not met anymore,
                  the reward will be removed on recompute.
        '''
        self.immediate_promotion_program.active = False  # Avoid having this program to add rewards on this test
        order = self.empty_order

        program = self.env['coupon.program'].create({
            'name': 'Get 10% discount if buy at least 4 Product A and $320',
            'program_type': 'coupon_program',
            'reward_type': 'discount',
            'discount_type': 'percentage',
            'discount_percentage': 10.0,
            'rule_products_domain': "[('id', 'in', [%s])]" % (self.product_A.id),
            'rule_min_quantity': 3,
            'rule_minimum_amount': 320.00,
        })

        sol1 = self.env['sale.order.line'].create({
            'product_id': self.product_A.id,
            'name': 'Product A',
            'product_uom_qty': 2.0,
            'order_id': order.id,
        })

        sol2 = self.env['sale.order.line'].create({
            'product_id': self.product_B.id,
            'name': 'Product B',
            'product_uom_qty': 4.0,
            'order_id': order.id,
        })

        # Default value for coupon generate wizard is generate by quantity and generate only one coupon
        self.env['coupon.generate.wizard'].with_context(active_id=program.id).create({}).generate_coupon()
        coupon = program.coupon_ids[0]

        # Not enough amount since we only have 220 (100*2 + 5*4)
        with self.assertRaises(UserError):
            self.env['sale.coupon.apply.code'].with_context(active_id=order.id).create({
                'coupon_code': coupon.code
            }).process_coupon()

        sol2.product_uom_qty = 24

        # Not enough qty since we only have 3 Product A (Amount is ok: 100*2 + 5*24 = 320)
        with self.assertRaises(UserError):
            self.env['sale.coupon.apply.code'].with_context(active_id=order.id).create({
                'coupon_code': coupon.code
            }).process_coupon()

        sol1.product_uom_qty = 3

        self.env['sale.coupon.apply.code'].with_context(active_id=order.id).create({
            'coupon_code': coupon.code
        }).process_coupon()
        order.recompute_coupon_lines()

        self.assertEqual(len(order.order_line.ids), 3, "The order should contains the Product A line, the Product B line and the discount line")
        self.assertEqual(coupon.state, 'used', "The coupon should be set to Consumed as it has been used")

        sol1.product_uom_qty = 2
        order.recompute_coupon_lines()

        self.assertEqual(len(order.order_line.ids), 2, "The discount line should have been removed as we don't meet the program requirements")
        self.assertEqual(coupon.state, 'new', "The coupon should be reset to Valid as it's reward got removed")


    def test_program_rules_promotion_use_best(self):
        ''' This test will:
                * Verify the best global promotion according to the
                  current sale order is used.
        '''
        self.immediate_promotion_program.active = False  # Avoid having this program to add rewards on this test
        order = self.empty_order

        program_5pc = self.env['coupon.program'].create({
            'name': 'Get 5% discount if buy at least 2 Product',
            'program_type': 'promotion_program',
            'reward_type': 'discount',
            'discount_type': 'percentage',
            'discount_percentage': 5.0,
            'rule_min_quantity': 2,
            'promo_code_usage': 'no_code_needed',
        })
        program_10pc = self.env['coupon.program'].create({
            'name': 'Get 10% discount if buy at least 4 Product',
            'program_type': 'promotion_program',
            'reward_type': 'discount',
            'discount_type': 'percentage',
            'discount_percentage': 10.0,
            'rule_min_quantity': 4,
            'promo_code_usage': 'no_code_needed',
        })
        sol = self.env['sale.order.line'].create({
            'product_id': self.product_A.id,
            'name': 'Product A',
            'product_uom_qty': 1.0,
            'order_id': order.id,
        })

        order.recompute_coupon_lines()
        self.assertEqual(len(order.order_line.ids), 1, "The order should only contains the Product A line")

        sol.product_uom_qty = 3
        order.recompute_coupon_lines()
        discounts = set(order.order_line.mapped('name')) - {'Product A'}
        self.assertEqual(len(discounts), 1, "The order should contains the Product A line and a discount")
        # The name of the discount is dynamically changed to smth looking like:
        # "Discount: Get 5% discount if buy at least 2 Product - On product with following tax: Tax 15.00%"
        self.assertTrue('Get 5% discount' in discounts.pop(), "The discount should be a 5% discount")

        sol.product_uom_qty = 5
        order.recompute_coupon_lines()
        discounts = set(order.order_line.mapped('name')) - {'Product A'}
        self.assertEqual(len(discounts), 1, "The order should contains the Product A line and a discount")
        self.assertTrue('Get 10% discount' in discounts.pop(), "The discount should be a 10% discount")
