# Part of Odoo. See LICENSE file for full copyright and licensing details

from odoo import Command
from odoo.tests import tagged
from odoo.addons.point_of_sale.tests.test_common import TestPointOfSaleDataHttpCommon


@tagged('post_install', '-at_install')
class TestPOSLoyaltyHistory(TestPointOfSaleDataHttpCommon):

    def test_pos_loyalty_history(self):
        self.product_awesome_item.product_variant_ids.write({'lst_price': 10})
        self.pos_config.write({
            'tax_regime_selection': False,
            'use_pricelist': False,
        })
        loyalty_program = self.env['loyalty.program'].create({
            'name': 'Test Loyalty Program',
            'program_type': 'loyalty',
            'trigger': 'auto',
            'applies_on': 'both',
            'rule_ids': [Command.create({
                'reward_point_amount': 1,
                'reward_point_mode': 'money',
                'minimum_qty': 1,
            })],
            'reward_ids': [Command.create({
                'reward_type': 'discount',
                'discount_mode': 'percent',
                'discount': 15,
                'discount_applicability': 'order',
            })],
        })
        self.start_pos_tour("LoyaltyHistoryTour")
        loyalty_card = loyalty_program.coupon_ids.filtered(lambda coupon: coupon.partner_id.id == self.partner_one.id)
        self.assertEqual(len(loyalty_card.history_ids), 1,
                        "Loyalty History line should be created on pos oder confirmation")
