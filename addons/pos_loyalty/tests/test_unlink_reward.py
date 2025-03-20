# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.addons.point_of_sale.tests.test_common import TestPointOfSaleDataHttpCommon
from odoo.tests.common import tagged


@tagged('-at_install', 'post_install')
class TestUnlinkReward(TestPointOfSaleDataHttpCommon):
    @classmethod
    def setUpClass(self):
        super().setUpClass()
        # Create a loyalty program
        self.loyalty_program = self.env['loyalty.program'].create({
            'name': 'Buy 4 whiteboard_pen, Take 1 whiteboard_pen',
            'program_type': 'loyalty',
            'trigger': 'auto',
            'applies_on': 'both',
            'rule_ids': [Command.create({
                'product_ids': self.product_awesome_item.product_variant_ids.ids,
                'reward_point_mode': 'unit',
                'minimum_qty': 1,
            })],
        })

        # Create a reward
        self.reward = self.env['loyalty.reward'].create({
            'program_id': self.loyalty_program.id,
            'reward_type': 'product',
            'reward_product_id': self.product_awesome_item.product_variant_id.id,
            'reward_product_qty': 1,
            'required_points': 4,
        })

    def test_pos_unlink_reward(self):
        self.pos_config.open_ui()
        self.create_order([{
            'product_id': self.product_awesome_item.product_variant_id,
            'qty': 1,
            'discount': 0,
            'reward_id': self.reward.id,
        }], [
            {'payment_method_id': self.bank_payment_method, 'amount': 1.98},
        ])

        # Attempt to delete the reward
        self.reward.unlink()

        # Ensure the reward is archived and not deleted
        self.assertTrue(self.reward.exists())
        self.assertFalse(self.reward.active)
