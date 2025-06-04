# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestPoSSaleLoyalty(TestPointOfSaleHttpCommon):
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

    def test_pos_sale_loyalty_ignored_in_pos(self):
        """Test that the loyalty program already applied in sales are not applied again in PoS"""
        self.env['loyalty.program'].search([]).write({'active': False})
        self.env['loyalty.program'].create({
            'name': 'Test Loyalty Program',
            'program_type': 'promotion',
            'trigger': 'auto',
            'applies_on': 'current',
            'rule_ids': [
                (0, 0, {
                    'reward_point_mode': 'order',
                    'minimum_amount': 1,
                    'minimum_qty': 0,
                    'reward_point_amount': 1,
                }),
            ],
            'reward_ids': [
                (0, 0, {
                    'reward_type': 'discount',
                    'discount': 10,
                    'required_points': 1,
                    'discount_mode': 'percent',
                    'discount_applicability': 'order',
                }),
            ],
        })
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [(0, 0, {
                'product_id': self.desk_organizer.id,
                'product_uom_qty': 1,
                'price_unit': 100,
            })]
        })
        sale_order.action_open_reward_wizard()
        self.assertEqual(sale_order.amount_total, 90.0)
        self.main_pos_config.open_ui()
        self.start_tour("/pos/web?config_id=%d" % self.main_pos_config.id, "test_pos_sale_loyalty_ignored_in_pos", login="accountman")
