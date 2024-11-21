# Part of Odoo. See LICENSE file for full copyright and licensing details

from odoo import Command
from odoo.tests import tagged

from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon


@tagged('post_install', '-at_install')
class TestPOSLoyaltyHistory(TestPointOfSaleHttpCommon):

    def test_pos_loyalty_history(self):
        partner_aaa = self.env['res.partner'].create({'name': 'AAA Test Partner'})
        self.whiteboard_pen.write({'lst_price': 10})
        self.main_pos_config.write({
            'tax_regime_selection': False,
            'use_pricelist': False,
        })
        self.main_pos_config.with_user(self.pos_user).open_ui()
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
        loyalty_card = loyalty_program.coupon_ids.filtered(lambda coupon: coupon.partner_id.id == partner_aaa.id)
        self.assertEqual(len(loyalty_card.history_ids), 1,
                        "Loyalty History line should be created on pos oder confirmation")
