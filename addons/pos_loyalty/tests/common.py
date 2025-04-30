from odoo.addons.point_of_sale.tests.common import CommonPosTest
from odoo.fields import Command


class CommonPosLoyaltyTest(CommonPosTest):
    @classmethod
    def setUpClass(self):
        super().setUpClass()

        self.loyalty_create_programs(self)
        self.loyalty_create_rewards(self)

    def loyalty_create_programs(self):
        self.four_20_dollars_one_free_program = self.env['loyalty.program'].create({
            'name': 'Buy 4 20 dollars Take 1 20 dollars',
            'program_type': 'loyalty',
            'trigger': 'auto',
            'applies_on': 'both',
            'rule_ids': [Command.create({
                'product_ids': self.twenty_dollars_no_tax.product_variant_id.ids,
                'reward_point_mode': 'unit',
                'minimum_qty': 1,
            })],
        })

    def loyalty_create_rewards(self):
        self.twenty_dollars_reward = self.env['loyalty.reward'].create({
            'program_id': self.four_20_dollars_one_free_program.id,
            'reward_type': 'product',
            'reward_product_id': self.twenty_dollars_no_tax.product_variant_id.id,
            'reward_product_qty': 1,
            'required_points': 4,
        })
