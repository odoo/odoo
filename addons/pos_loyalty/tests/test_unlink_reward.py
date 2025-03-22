# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.addons.point_of_sale.tests.common import TestPointOfSaleCommon
from odoo.tests.common import tagged


@tagged('-at_install', 'post_install')
class TestUnlinkReward(TestPointOfSaleCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Create a loyalty program
        cls.loyalty_program = cls.env['loyalty.program'].create({
            'name': 'Buy 4 whiteboard_pen, Take 1 whiteboard_pen',
            'program_type': 'loyalty',
            'trigger': 'auto',
            'applies_on': 'both',
            'rule_ids': [Command.create({
                'product_ids': cls.whiteboard_pen.ids,
                'reward_point_mode': 'unit',
                'minimum_qty': 1,
            })],
        })

        # Create a reward
        cls.reward = cls.env['loyalty.reward'].create({
            'program_id': cls.loyalty_program.id,
            'reward_type': 'product',
            'reward_product_id': cls.whiteboard_pen.id,
            'reward_product_qty': 1,
            'required_points': 4,
        })

    def test_pos_unlink_reward(self):
        self.pos_config.open_ui()
        current_session = self.pos_config.current_session_id
        self.PosOrder.create({
            'company_id': self.env.company.id,
            'session_id': current_session.id,
            'partner_id': self.partner1.id,
            'pricelist_id': self.partner1.property_product_pricelist.id,
            'lines': [
                Command.create({
                    'product_id': self.whiteboard_pen.id,
                    'qty': 5,
                    'price_subtotal': 12.0,
                    'price_subtotal_incl': 12.0,
                    'reward_id': self.reward.id,
                })
            ],
            'amount_tax': 0.0,
            'amount_total': 134.38,
            'amount_paid': 0.0,
            'amount_return': 0.0,
        })
        # Attempt to delete the reward
        self.reward.unlink()

        # Ensure the reward is archived and not deleted
        self.assertTrue(self.reward.exists())
        self.assertFalse(self.reward.active)
