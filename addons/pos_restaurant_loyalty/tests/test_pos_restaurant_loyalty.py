# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.pos_restaurant.tests.test_frontend import TestFrontend
from odoo.addons.pos_loyalty.tests.test_frontend import TestUi
from odoo.tests import tagged
from odoo import Command


@tagged("post_install", "-at_install")
class TestPoSRestaurantLoyalty(TestFrontend, TestUi):
    def test_change_table_rewards_stay(self):
        """
        Test that make sure that rewards stay on the order when leaving the table
        """
        self.env['loyalty.program'].create({
            'name': 'My super program',
            'program_type': 'promotion',
            'trigger': 'auto',
            'applies_on': 'current',
            'rule_ids': [Command.create({
                'minimum_qty': 1,
            })],
            'reward_ids': [Command.create({
                'reward_type': 'discount',
                'discount': 10,
                'discount_mode': 'percent',
                'discount_applicability': 'order',
            })],
        })
        self.pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour("PosRestaurantRewardStay")
        order = self.env['pos.order'].search([])
        self.assertEqual(order.currency_id.round(order.amount_total), 1.98)

    def test_physical_gift_card_return_from_floor(self):
        """
        Test that make sure that physical gift card can be generated successfully after returning
        from floor
        """
        LoyaltyProgram = self.env['loyalty.program']
        # Deactivate all other programs to avoid interference and activate the gift_card_product_50
        LoyaltyProgram.search([]).write({'pos_ok': False})
        self.env.ref('loyalty.gift_card_product_50').product_tmpl_id.write({'active': True})

        # Create gift card program
        gift_card_program = self.create_programs([('arbitrary_name', 'gift_card')])['arbitrary_name']

        # Run the tour
        self.start_pos_tour("PosRestaurantGiftCardReturnFromFloor", login="pos_user")

        gift_card = self.env['loyalty.card'].search([('program_id', '=', gift_card_program.id)], limit=1)
        self.assertEqual(gift_card.code, 'dummy-card-0000', "Latest generated gift card code should be 'dummy-card-0000'")
        self.assertEqual(gift_card.points, 125, "Latest generated gift card points should be 125")
