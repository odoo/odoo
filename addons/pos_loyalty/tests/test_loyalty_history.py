# Part of Odoo. See LICENSE file for full copyright and licensing details

from odoo import Command
from odoo.tests import tagged

from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon


@tagged('post_install', '-at_install')
class TestPOSLoyaltyHistory(TestPointOfSaleHttpCommon):

    def test_pos_loyalty_history(self):
        partner_aaa = self.env['res.partner'].create({'name': 'AAA Test Partner'})
        self.whiteboard_pen.product_variant_ids.write({'lst_price': 10})
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

    def test_programs_loaded(self):
        eur_currency = self.setup_other_currency('EUR')
        usd_loyalty = self.env['loyalty.program'].create({'name': "USD program"})
        eur_loyalty = self.env['loyalty.program'].create({'name': "EUR program", 'currency_id': eur_currency.id})
        loaded_programs = self.main_pos_config._get_program_ids()
        self.assertIn(usd_loyalty, loaded_programs)
        self.assertNotIn(eur_loyalty, loaded_programs)

    def test_loyalty_history_earn_and_spend(self):
        """When points are earned and spent in the same order, the loyalty history
        must record the gross issued and used amounts separately, not only the net
        difference. Regression test for: earn 10 pts + spend 5 pts → issued=10,
        used=5 (instead of the incorrect issued=5, used=0)."""
        partner_aaa = self.env['res.partner'].create({'name': 'AAA Test Partner'})
        self.env['product.product'].create({
            'name': 'Test Product',
            'available_in_pos': True,
            'list_price': 10,
            'taxes_id': [],
        })
        self.main_pos_config.write({
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
                'discount': 10,
                'required_points': 5,
                'discount_applicability': 'order',
            })],
        })
        # Pre-load the partner with 5 points so they can immediately claim the reward
        loyalty_card = self.env['loyalty.card'].create({
            'program_id': loyalty_program.id,
            'partner_id': partner_aaa.id,
            'points': 5,
        })
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour("test_loyalty_history_earn_and_spend")

        loyalty_card.invalidate_recordset()
        history = loyalty_card.history_ids
        self.assertEqual(len(history), 1, "One history entry should be created for the order")
        # $10 product → 10 pts earned; 10% discount reward → 5 pts spent
        self.assertEqual(history.issued, 10.0, "Issued should be 10 (gross earned), not the net")
        self.assertEqual(history.used, 5.0, "Used should be 5 (gross spent), not the net")
