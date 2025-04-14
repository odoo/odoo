# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.pos_loyalty.tests.test_frontend import TestPoSLoyaltyCommon
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestPoSSaleLoyalty(TestPoSLoyaltyCommon):
    def test_pos_sale_loyalty_1(self):
        """Test that only one loyalty card is created when settling an unconfirmed order."""
        self.env['loyalty.program'].search([]).write({'active': False})
        self.env['loyalty.program'].create({
            'name': 'Test Loyalty Program',
            'program_type': 'loyalty',
            'trigger': 'auto',
            'applies_on': 'both',
            'rule_ids': [
                (0, 0, {
                    'reward_point_mode': 'money',
                    'minimum_amount': 1,
                    'reward_point_amount': 1,
                }),
            ],
            'reward_ids': [
                (0, 0, {
                    'reward_type': 'discount',
                    'discount': 1,
                    'required_points': 1000,
                    'discount_mode': 'percent',
                    'discount_applicability': 'order',
                }),
            ],
        })
        self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [(0, 0, {
                'product_id': self.desk_organizer.id,
                'product_uom_qty': 1,
                'price_unit': 100,
            })]
        })

        self.main_pos_config.open_ui()
        self.start_tour("/pos/web?config_id=%d" % self.main_pos_config.id, "PosSaleLoyaltyTour1", login="accountman")
        self.assertEqual(self.env['loyalty.card'].search_count([('partner_id', '=', self.partner_a.id)]), 1)
