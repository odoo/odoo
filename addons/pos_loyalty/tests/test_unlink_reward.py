# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.pos_loyalty.tests.common import CommonPosLoyaltyTest
from odoo.tests.common import tagged


@tagged('-at_install', 'post_install')
class TestUnlinkReward(CommonPosLoyaltyTest):
    def test_pos_unlink_reward(self):
        self.create_backend_pos_order({
            'order_data': {
                'partner_id': self.partner_lowe.id,
                'pricelist_id': self.partner_lowe.property_product_pricelist.id,
            },
            'line_data': [{
                'qty': 5,
                'product_id': self.twenty_dollars_no_tax.product_variant_id.id,
                'reward_id': self.twenty_dollars_reward.id,
            }],
        })
        # Ensure the reward is archived and not deleted
        self.twenty_dollars_reward.unlink()
        self.assertTrue(self.twenty_dollars_reward.exists())
        self.assertFalse(self.twenty_dollars_reward.active)
