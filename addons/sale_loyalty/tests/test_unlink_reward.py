# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command

from odoo.addons.sale_loyalty.tests.common import TestSaleCouponCommon
from odoo.tests.common import tagged


@tagged('-at_install', 'post_install')
class TestUnlinkReward(TestSaleCouponCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.promotion_program = cls.env['loyalty.program'].create({
            'name': 'Buy A + 1 B, 1 B are free',
            'program_type': 'promotion',
            'applies_on': 'current',
            'company_id': cls.env.company.id,
            'trigger': 'auto',
            'rule_ids': [Command.create({
                'product_ids': cls.product_A,
                'reward_point_amount': 1,
                'reward_point_mode': 'order',
                'minimum_qty': 1,
            })],
        })
        cls.reward = cls.env['loyalty.reward'].create({
            'program_id': cls.promotion_program.id,
            'reward_type': 'discount',
        })

    def test_sale_unlink_reward(self):
        order = self.empty_order
        order.write({'order_line': [
            Command.create({
                'product_id': self.product_A.id,
                'name': 'Ordinary Product A',
                'product_uom': self.uom_unit.id,
                'product_uom_qty': 1.0,
            }),
            Command.create({
                'product_id': self.product_B.id,
                'name': '2 Product B',
                'product_uom': self.uom_unit.id,
                'product_uom_qty': 1.0,
            }),
        ]})
        order._update_programs_and_rewards()
        self._claim_reward(order, self.promotion_program)
        self.reward.unlink()

        # Check that the reward is archived and not deleted
        self.assertTrue(self.reward.exists())
        self.assertFalse(self.reward.active)
