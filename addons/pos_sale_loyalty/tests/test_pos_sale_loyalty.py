# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestPoSSaleLoyalty(TestPointOfSaleHttpCommon):
    @classmethod
    def get_default_groups(cls):
        groups = super().get_default_groups()
        return groups | cls.quick_ref('sales_team.group_sale_manager')

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
        self.env['sale.order'].sudo().create({
            'partner_id': self.partner_a.id,
            'order_line': [(0, 0, {
                'product_id': self.desk_organizer.product_variant_id.id,
                'product_uom_qty': 1,
                'price_unit': 100,
            })]
        })

        self.main_pos_config.open_ui()
        self.start_pos_tour("PosSaleLoyaltyTour1", login="accountman")
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
        test_product = self.env['product.product'].create({
            'name': 'Test Product',
            'list_price': 100,
            'taxes_id': [],
        })
        sale_order = self.env['sale.order'].sudo().create({
            'partner_id': self.partner_a.id,
            'order_line': [(0, 0, {
                'product_id': test_product.id,
                'product_uom_qty': 1,
                'price_unit': 100,
            })]
        })
        sale_order.action_open_reward_wizard()
        self.assertEqual(sale_order.amount_total, 90)
        self.main_pos_config.open_ui()
        self.start_tour("/pos/web?config_id=%d" % self.main_pos_config.id, "test_pos_sale_loyalty_ignored_in_pos", login="accountman")

    def test_sale_order_loyalty_card_can_be_used_in_pos(self):
        """Create loyalty program & card → Confirm sale order → Verify loyalty card usable in POS"""
        self.env['loyalty.program'].search([]).write({'active': False})
        self.env['loyalty.program'].create({
            'name': 'Promo Code Program',
            'program_type': 'promotion',
            'trigger': 'with_code',
            'applies_on': 'current',
            'rule_ids': [(0, 0, {
                'mode': 'with_code',
                'code': 'promocode',
            })],
            'reward_ids': [(0, 0, {
                'reward_type': 'discount',
                'discount': 50,
                'discount_mode': 'percent',
                'discount_applicability': 'order',
                'required_points': 1,
            })],
        })
        loyalty_program = self.env['loyalty.program'].create({
            'name': 'Loyalty Program',
            'program_type': 'loyalty',
            'trigger': 'auto',
            'applies_on': 'both',
            'rule_ids': [(0, 0, {
                'reward_point_mode': 'unit',
                'reward_point_amount': 1,
            })],
            'reward_ids': [(0, 0, {
                'reward_type': 'discount',
                'discount': 10,
                'discount_mode': 'per_point',
                'discount_applicability': 'order',
                'required_points': 1,
            })],
        })
        test_product = self.env['product.product'].create({
            'name': 'Test Product',
            'list_price': 100,
            'taxes_id': [],
        })
        loyalty_card = self.env['loyalty.card'].create({
            'program_id': loyalty_program.id,
            'partner_id': self.partner_a.id,
            'points': 0,
            'code': 'LOYALTY123',
        })
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [(0, 0, {
                'product_id': test_product.id,
                'product_uom_qty': 1,
                'price_unit': 100,
            })]
        })
        sale_order.action_confirm()
        self.assertEqual(loyalty_card.points, 1)
        self.env['ir.config_parameter'].set_param('point_of_sale.limited_customer_count', '0')
        self.main_pos_config.open_ui()
        self.start_pos_tour('test_sale_order_loyalty_card_can_be_used_in_pos')
        order = self.main_pos_config.current_session_id.order_ids[0]
        self.assertEqual(order.partner_id.id, self.partner_a.id)
        self.assertEqual(loyalty_card.points, 2)
