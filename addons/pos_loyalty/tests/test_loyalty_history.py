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

    def test_duplicate_coupon_confirm(self):
        """ Test that duplicate coupon confirm calls do not affect the coupon."""
        test_partner = self.env['res.partner'].create({'name': 'Test Partner'})
        ewallet_program = self.env['loyalty.program'].create({
            'name': 'eWallet Program',
            'program_type': 'ewallet',
            'trigger': 'auto',
            'applies_on': 'future',
            'reward_ids': [Command.create({
                'reward_type': 'discount',
                'discount_mode': 'per_point',
                'discount': 1,
            })],
            'rule_ids': [Command.create({
                'reward_point_amount': '1',
                'reward_point_mode': 'money',
                'product_ids': self.env.ref('loyalty.ewallet_product_50'),
            })],
            'trigger_product_ids': self.env.ref('loyalty.ewallet_product_50'),
        })

        self.main_pos_config.open_ui()
        pos_order = self.env['pos.order'].create({
            'config_id': self.main_pos_config.id,
            'session_id': self.main_pos_config.current_session_id.id,
            'partner_id': test_partner.id,
            'amount_paid': 50,
            'amount_return': 0,
            'amount_tax': 0,
            'amount_total': 50,
        })

        coupon_data = {
            -1: {
                'points': 50,
                'program_id': ewallet_program.id,
                'coupon_id': -1,
                'barcode': '',
                'partner_id': test_partner.id,
            }
        }
        pos_order.confirm_coupon_programs(coupon_data)

        def check_coupon(points, history_count):
            created_card = self.env['loyalty.card'].search([('program_id', '=', ewallet_program.id), ('partner_id', '=', test_partner.id)])
            self.assertEqual(created_card.points, points, "The coupon should have 50 points after the first confirmation.")
            self.assertEqual(len(created_card.history_ids), history_count, "The history should have one entry after the first confirmation.")

        check_coupon(50, 1)
        # Confirm the coupon again
        pos_order.confirm_coupon_programs(coupon_data)
        check_coupon(50, 1)

        new_pos_order = self.env['pos.order'].create({
            'config_id': self.main_pos_config.id,
            'session_id': self.main_pos_config.current_session_id.id,
            'partner_id': test_partner.id,
            'amount_paid': 0,
            'amount_return': 0,
            'amount_tax': 0,
            'amount_total': 0,
        })

        loyalty_card = self.env['loyalty.card'].search([('program_id', '=', ewallet_program.id), ('partner_id', '=', test_partner.id)])
        coupon_data = {
            loyalty_card.id: {
                'points': -10,
                'program_id': ewallet_program.id,
                'coupon_id': loyalty_card.id,
                'barcode': '',
                'partner_id': test_partner.id,
            }
        }

        new_pos_order.confirm_coupon_programs(coupon_data)
        # Check that the coupon points are reduced correctly
        check_coupon(40, 2)
        # Confirm the coupon again
        new_pos_order.confirm_coupon_programs(coupon_data)
        check_coupon(40, 2)
