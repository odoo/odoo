# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.sale_loyalty.tests.common import TestSaleCouponCommon


@tagged('post_install', '-at_install')
class TestLoyaltyhistory(TestSaleCouponCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner_a = cls.env['res.partner'].create({'name': 'Jean Jacques'})
        cls.loyalty_program = cls.env['loyalty.program'].create({
            'name': 'Full Discount',
            'program_type': 'loyalty',
            'trigger': 'auto',
            'applies_on': 'both',
            'rule_ids': [Command.create({
                'reward_point_mode': 'unit',
                'reward_point_amount': 1,
                'product_ids': [cls.product_A.id],
            })],
            'reward_ids': [
                Command.create({
                    'reward_type': 'discount',
                    'discount': 10,
                    'discount_mode': 'percent',
                    'discount_applicability': 'order',
                    'required_points': 1,
                }),
                Command.create({
                    'active': False,
                    'reward_type': 'product',
                    'reward_product_id': cls.product_B.id,
                    'required_points': 2,
                }),
            ],
        })
        cls.loyalty_card = cls.env['loyalty.card'].create({
            'program_id': cls.loyalty_program.id, 'partner_id': cls.partner_a.id, 'points': 2
        })

    def test_add_loyalty_history_line_with_reward(self):
        order = self.empty_order
        order.write({
            'order_line': [
                Command.create({
                'product_id': self.product_A.id,
                'name': 'Ordinary Product A',
                'product_uom_qty': 1.0,
                }),
            ],
        })
        order._update_programs_and_rewards()
        self._auto_rewards(order, self.immediate_promotion_program)

        order.action_confirm()
        coupon_applied = self.immediate_promotion_program.coupon_ids.filtered(lambda x: x.order_id == order)
        history_records = len(coupon_applied.history_ids.filtered(lambda history: history.order_id == order.id))
        self.assertEqual(history_records, 1, "A history line should be created on confirmation of order")

    def test_add_loyalty_history_line_without_reward(self):
        order = self.empty_order
        order.write({
            'partner_id': self.partner_a.id,
            'order_line': [
                Command.create({
                    'product_id': self.product_A.id,
                    'tax_ids': False,
                }),
            ]
        })
        order.action_confirm()
        order._update_programs_and_rewards()
        self._claim_reward(order, self.loyalty_program)
        history_records = self.loyalty_card.history_ids.filtered(lambda history: history.order_id == order.id)
        self.assertEqual(history_records.used, 1.0,
                        "The history line should be updated on change of order lines in a confirmed order")

    def test_delete_loyalty_history_line_on_cancel(self):
        order = self.empty_order
        order.write({
            'partner_id': self.partner_a.id,
            'order_line': [
                Command.create({
                    'product_id': self.product_A.id,
                    'tax_ids': False,
                }),
            ]
        })
        order._update_programs_and_rewards()
        self._claim_reward(order, self.loyalty_program)
        order.action_confirm()
        lines_before_cancel = len(self.loyalty_card.history_ids)
        order._action_cancel()
        self.assertEqual(lines_before_cancel - 1, len(self.loyalty_card.history_ids),
                         "History line should be deleted after order cancel")

    def test_loyalty_history_multi_reward(self):
        """Verify that applying multiple rewards sums up the total points cost."""
        self.loyalty_card.points = initial_points = 4
        self.loyalty_program.with_context(active_test=False).reward_ids.active = True
        order = self.empty_order
        order.write({
            'partner_id': self.partner_a.id,
            'order_line': [
                Command.create({
                    'product_id': self.product_A.id,
                    'tax_ids': False,
                }),
            ],
        })
        for reward in self.loyalty_program.reward_ids:
            order._apply_program_reward(reward, self.loyalty_card)
        self.assertEqual(len(order.order_line.filtered('reward_id')), 2)
        self.assertEqual(order.order_line.mapped('points_cost'), [0, 1, 2])

        order.action_confirm()
        loyalty_history = self.loyalty_card.history_ids
        self.assertEqual(loyalty_history.issued, 1, "1 point should be rewarded")
        self.assertEqual(loyalty_history.used, 3, "A total of 3 points should be used")
        self.assertEqual(
            self.loyalty_card.points,
            initial_points + loyalty_history.issued - loyalty_history.used,
            "Loyalty points should equal initial points + points issued - points used",
        )
