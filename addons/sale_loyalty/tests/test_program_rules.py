# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, timedelta

from freezegun import freeze_time
from pytz import timezone

from odoo.exceptions import ValidationError
from odoo.fields import Command, Datetime

from odoo.addons.payment.tests.common import PaymentCommon
from odoo.addons.sale_loyalty.tests.common import TestSaleCouponCommon


class TestProgramRules(TestSaleCouponCommon, PaymentCommon):
    # Test all the validity rules to allow a customer to have a reward.
    # The check based on the products is already done in the basic operations test

    def test_program_rules_minimum_purchased_amount(self):
        # Test case: Based on the minimum purchased

        self.immediate_promotion_program.rule_ids.write({
            'product_ids': False,
            'minimum_amount': 1006,
            'minimum_amount_tax_mode': 'excl'
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
        order._update_programs_and_rewards()
        self._claim_reward(order, self.immediate_promotion_program)
        self.assertEqual(len(order.order_line.ids), 2, "The promo offer shouldn't have been applied as the purchased amount is not enough")

        order = self.env['sale.order'].create({'partner_id': self.partner.id})
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
        order._update_programs_and_rewards()
        self._claim_reward(order, self.immediate_promotion_program)
        # 10*100 + 5 = 1005
        self.assertEqual(len(order.order_line.ids), 2, "The promo offer should not be applied as the purchased amount is not enough")

        self.immediate_promotion_program.rule_ids.minimum_amount = 1005
        order._update_programs_and_rewards()
        self._claim_reward(order, self.immediate_promotion_program)
        self.assertEqual(len(order.order_line.ids), 3, "The promo offer should be applied as the purchased amount is now enough")

        # 10*(100*1.15) + (5*1.15) = 10*115 + 5.75 = 1155.75
        self.immediate_promotion_program.rule_ids.minimum_amount = 1006
        self.immediate_promotion_program.rule_ids.minimum_amount_tax_mode = 'incl'
        order._update_programs_and_rewards()
        self._claim_reward(order, self.immediate_promotion_program)
        self.assertEqual(len(order.order_line.ids), 3, "The promo offer should be applied as the initial amount required is now tax included")

    def test_program_rules_min_amount_not_reached_and_specific_product(self):
        """
        Test that the discount isn't applied if the min amount isn't reached for the specified
        product.
        """
        self.env['loyalty.program'].search([]).active = False
        order = self.empty_order
        program = self.env['loyalty.program'].create({
            'name': "Discount on Product A",
            'program_type': 'promotion',
            'trigger': 'auto',
            'applies_on': 'current',
            'rule_ids': [Command.create({
                'minimum_amount': 110,
                'minimum_amount_tax_mode': 'excl',
                'product_ids': [Command.set(self.product_A.ids)],
            })],
            'reward_ids': [Command.create({
                'reward_type': 'discount',
                'discount': 10,
                'discount_mode': 'percent',
                'discount_applicability': 'specific',
                'discount_product_ids': [Command.set(self.product_A.ids)],
            })],
        })
        self.env['sale.order.line'].create([{
            'product_id': self.product_A.id,
            'product_uom_qty': 1.0,
            'order_id': order.id,
        }, {
            'product_id': self.product_B.id,
            'product_uom_qty': 40.0,
            'order_id': order.id,
        }])
        self.assertEqual(len(order.order_line), 2)
        self.assertEqual(order.amount_untaxed, 300)

        order._update_programs_and_rewards()
        self._claim_reward(order, program)

        self.assertEqual(len(order.order_line), 2)
        self.assertEqual(order.amount_untaxed, 300)

    def test_program_rules_min_amount_reached_and_specific_product(self):
        """
        Test that the discount is applied if the min amount is reached for the specified product.
        """
        self.env['loyalty.program'].search([]).active = False
        order = self.empty_order
        program = self.env['loyalty.program'].create({
            'name': "Discount on Product A",
            'program_type': 'promotion',
            'trigger': 'auto',
            'applies_on': 'current',
            'rule_ids': [Command.create({
                'minimum_amount': 110,
                'minimum_amount_tax_mode': 'excl',
                'product_ids': [Command.set(self.product_A.ids)],
            })],
            'reward_ids': [Command.create({
                'reward_type': 'discount',
                'discount': 10,
                'discount_mode': 'percent',
                'discount_applicability': 'specific',
                'discount_product_ids': [Command.set(self.product_A.ids)],
            })],
        })
        self.env['sale.order.line'].create([{
            'product_id': self.product_A.id,
            'product_uom_qty': 2.0,
            'order_id': order.id,
        }, {
            'product_id': self.product_B.id,
            'product_uom_qty': 20.0,
            'order_id': order.id,
        }])
        self.assertEqual(len(order.order_line), 2)
        self.assertEqual(order.amount_untaxed, 300)

        order._update_programs_and_rewards()
        self._claim_reward(order, program)

        self.assertEqual(len(order.order_line), 3)
        self.assertEqual(order.amount_untaxed, 280)

    def test_program_rules_coupon_qty_and_amount_remove_not_eligible(self):
        ''' This test will:
                * Check quantity and amount requirements works as expected (since it's slightly different from a promotion_program)
                * Ensure that if a reward from a coupon_program was allowed and the conditions are not met anymore,
                  the reward will be removed on recompute.
        '''
        self.immediate_promotion_program.active = False  # Avoid having this program to add rewards on this test
        order = self.empty_order

        program = self.env['loyalty.program'].create({
            'name': 'Get 10% discount if buy at least 4 Product A and $320',
            'program_type': 'coupons',
            'applies_on': 'current',
            'trigger': 'with_code',
            'rule_ids': [(0, 0, {
                'product_ids': self.product_A,
                'minimum_qty': 3,
                'minimum_amount': 320,
            })],
            'reward_ids': [(0, 0, {
                'reward_type': 'discount',
                'discount_mode': 'percent',
                'discount': 10,
                'discount_applicability': 'order',
            })],
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
        self.env['loyalty.generate.wizard'].with_context(active_id=program.id).create({'coupon_qty': 1, 'points_granted': 1}).generate_coupons()
        coupon = program.coupon_ids[0]

        # Not enough amount since we only have 220 (100*2 + 5*4)
        with self.assertRaises(ValidationError):
            self._apply_promo_code(order, coupon.code)

        sol2.product_uom_qty = 24

        # Not enough qty since we only have 3 Product A (Amount is ok: 100*2 + 5*24 = 320)
        with self.assertRaises(ValidationError):
            self._apply_promo_code(order, coupon.code)

        sol1.product_uom_qty = 3

        self._apply_promo_code(order, coupon.code)
        self._claim_reward(order, program, coupon)

        self.assertEqual(len(order.order_line.ids), 3, "The order should contain the Product A line, the Product B line and the discount line")

        sol1.product_uom_qty = 2
        order._update_programs_and_rewards()

        self.assertEqual(len(order.order_line.ids), 2, "The discount line should have been removed as we don't meet the program requirements")

    def test_program_rules_promotion_use_best(self):
        ''' This test verifies that only the best global discount is applied.
        '''
        self.immediate_promotion_program.active = False  # Avoid having this program to add rewards on this test
        order = self.empty_order

        p1 = self.env['loyalty.program'].create({
            'name': 'Get 5% discount if buy at least 2 Product',
            'trigger': 'auto',
            'program_type': 'promotion',
            'applies_on': 'current',
            'rule_ids': [(0, 0, {
                'reward_point_mode': 'order',
                'minimum_qty': 2,
            })],
            'reward_ids': [(0, 0, {
                'reward_type': 'discount',
                'discount': 5,
                'discount_mode': 'percent',
                'discount_applicability': 'order',
                'required_points': 1,
            })],
        })
        p2 = self.env['loyalty.program'].create({
            'name': 'Get 10% discount if buy at least 4 Product',
            'trigger': 'auto',
            'program_type': 'promotion',
            'applies_on': 'current',
            'rule_ids': [(0, 0, {
                'reward_point_mode': 'order',
                'minimum_qty': 4,
            })],
            'reward_ids': [(0, 0, {
                'reward_type': 'discount',
                'discount': 10,
                'discount_mode': 'percent',
                'discount_applicability': 'order',
                'required_points': 1,
            })],
        })
        sol = self.env['sale.order.line'].create({
            'product_id': self.product_A.id,
            'name': 'Product A',
            'product_uom_qty': 1.0,
            'order_id': order.id,
        })

        order._update_programs_and_rewards()
        self._claim_reward(order, p1)
        self._claim_reward(order, p2)
        self.assertEqual(len(order.order_line.ids), 1, "The order should only contains the Product A line")

        sol.product_uom_qty = 3
        order._update_programs_and_rewards()
        self._claim_reward(order, p1)
        self._claim_reward(order, p2)
        discounts = set(order.order_line.mapped('name')) - {'Product A'}
        self.assertEqual(len(discounts), 1, "The order should contains the Product A line and a discount")
        # The name of the discount is dynamically changed to smth looking like:
        # "Discount Get 5% discount if buy at least 2 Product - On product with following tax: Tax 15.00%"
        self.assertTrue('Discount 5% on your order' in discounts.pop(), "The discount should be a 5% discount")

        sol.product_uom_qty = 5
        order._update_programs_and_rewards()
        self._claim_reward(order, p1)
        self._claim_reward(order, p2)
        discounts = set(order.order_line.mapped('name')) - {'Product A'}
        self.assertEqual(len(discounts), 1, "The order should contains the Product A line and a discount")
        self.assertTrue('Discount 10% on your order' in discounts.pop(), "The discount should be a 10% discount")

    @freeze_time('2011-11-02 09:00:21')
    def test_program_rules_validity_dates(self):
        # Test date_to (no date_from)
        today = date.today()
        past_day = today - timedelta(days=2)
        future_day = today + timedelta(days=2)
        self.immediate_promotion_program.write({'date_to': past_day})
        order = self.empty_order
        order.write({'order_line': [
            Command.create({
                'product_id': self.product_A.id,
                'name': '1 Product A',
                'product_uom': self.uom_unit.id,
                'product_uom_qty': 1.0,
            }),
            Command.create({
                'product_id': self.product_B.id,
                'name': '2 Product B',
                'product_uom': self.uom_unit.id,
                'product_uom_qty': 1.0,
            })
        ]})
        self._auto_rewards(order, self.immediate_promotion_program)
        msg = "The promo shouldn't have been applied as it is expired."
        self.assertEqual(len(order.order_line.ids), 2, msg)

        self.immediate_promotion_program.write({'date_to': future_day})
        self._auto_rewards(order, self.immediate_promotion_program)
        msg = "The promo should have been applied we're between the validity dates."
        self.assertEqual(len(order.order_line.ids), 3, msg)

        # Test date_from (no date_to)
        self.immediate_promotion_program.write({
            'date_from': future_day, 'date_to': False,
        })
        self._auto_rewards(order, self.immediate_promotion_program)
        msg = "The promo shouldn't have been applied as it is not active yet."
        self.assertEqual(len(order.order_line.ids), 2, msg)

        self.immediate_promotion_program.write({'date_from': past_day})
        self._auto_rewards(order, self.immediate_promotion_program)
        msg = "The promo should have been applied we're between the validity dates."
        self.assertEqual(len(order.order_line.ids), 3, msg)

        # Test date_from and date_to
        self.immediate_promotion_program.write({'date_from': past_day, 'date_to': future_day})
        self._auto_rewards(order, self.immediate_promotion_program)
        msg = "The promo should have been applied as we're between the validity dates"
        self.assertEqual(len(order.order_line.ids), 3, msg)

        self.immediate_promotion_program.write({
            'date_from': today + timedelta(days=1),
            'date_to': future_day,
        })
        self._auto_rewards(order, self.immediate_promotion_program)
        msg = "The promo offer shouldn't have been applied as it is not active yet."
        self.assertEqual(len(order.order_line.ids), 2, msg)

        self.immediate_promotion_program.write({
            'date_from': past_day,
            'date_to': today - timedelta(days=1),
        })
        self._auto_rewards(order, self.immediate_promotion_program)
        msg = "The promo offer shouldn't have been applied as it is expired."
        self.assertEqual(len(order.order_line.ids), 2, msg)

        self.immediate_promotion_program.write({'date_from': today, 'date_to': today})
        self._auto_rewards(order, self.immediate_promotion_program)
        msg = "The promo should have been applied as today is a valid starting and ending date."
        self.assertEqual(len(order.order_line.ids), 3, msg)

    def test_program_rules_number_of_uses(self):
        # Test case: Based on the number of allowed uses
        self.immediate_promotion_program.write({
            'limit_usage': True,
            'max_usage': 1,
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
        self._auto_rewards(order, self.immediate_promotion_program)
        self.assertEqual(len(order.order_line.ids), 2, "The promo offer should have been applied")

        order = self.env['sale.order'].create({
            'partner_id': self.env['res.partner'].create({'name': 'My Partner'}).id
        })

        order.write({'order_line': [
            Command.create({
                'product_id': self.product_B.id,
                'name': '2 Product B',
                'product_uom': self.uom_unit.id,
                'product_uom_qty': 1.0,
            })
        ]})
        # Invalidate total_order_count
        self.immediate_promotion_program.invalidate_recordset(['order_count', 'total_order_count'])
        self._auto_rewards(order, self.immediate_promotion_program)
        msg = "The promo offer shouldn't have been applied as the number of uses is exceeded"
        self.assertEqual(len(order.order_line.ids), 1, msg)

    def test_program_rules_validity_date_timezones(self):
        """Test that the validity dates are checked according to the company's time zone"""
        self.env.company.partner_id.tz = 'Europe/London'
        self.partner.tz = 'America/Los_Angeles'
        midnight = Datetime.today()
        yesterday = (midnight - timedelta(days=1)).date()
        self.immediate_promotion_program.update({
            'date_to': yesterday,
            'limit_usage': True,
            'max_usage': 1,
        })
        order = self.empty_order.with_context(tz=self.partner.tz)
        order.order_line = [
            Command.create({'product_id': self.product_A.id}),
            Command.create({'product_id': self.product_B.id}),
        ]

        with freeze_time(midnight):
            # Try apply reward at UTC midnight with LA time zone in context (expired)
            self._auto_rewards(order, self.immediate_promotion_program)
            self.assertFalse(
                order.order_line.filtered('is_reward_line'),
                "Promo should not be applied if only valid in the customer's time zone",
            )

        with freeze_time(timezone(self.env.company.partner_id.tz).localize(midnight)):
            # Try apply reward at London midnight (expired)
            self._auto_rewards(order, self.immediate_promotion_program)
            self.assertFalse(
                order.order_line.filtered('is_reward_line'),
                "Promo should not be applied if only valid in the customer's time zone",
            )

        self.partner.tz = 'Europe/Brussels'
        with freeze_time(timezone(self.partner.tz).localize(midnight)):
            # Apply reward at Brussels midnight (still valid in company's time zone)
            self._auto_rewards(order, self.immediate_promotion_program)
            self.assertTrue(
                order.order_line.filtered('is_reward_line'),
                "Promo should be applied if valid in the company's time zone",
            )

    def test_program_rules_validity_date_transactions(self):
        """Test that the validity dates are checked according to the time of transaction."""
        today = Datetime.today()
        tomorrow = today + timedelta(days=1)
        self.immediate_promotion_program.update({
            'date_to': today,
            'limit_usage': True,
            'max_usage': 1,
            'reward_ids': [Command.set(self.program_gift_card.reward_ids.ids)],
        })
        order = self.empty_order
        order.order_line = [
            Command.create({'product_id': self.product_A.id}),
            Command.create({'product_id': self.product_B.id}),
        ]

        intial_amount = order.amount_total
        self._auto_rewards(order, self.immediate_promotion_program)
        self.assertLess(order.amount_total, intial_amount, "A discount should be applied")

        tx = order.transaction_ids = self._create_transaction(
            flow='redirect',
            sale_order_ids=[order.id],
            state='pending',
            reference=order.name,
            amount=order.amount_total,
        )
        # Our slow provider only gets around to confirming the transaction the next day
        with freeze_time(tomorrow):
            tx._set_done()
            tx._post_process()
            self.assertAlmostEqual(
                order.amount_total, tx.amount,
                msg="Discount should still apply if transaction gets confirmed post-expiration",
            )
