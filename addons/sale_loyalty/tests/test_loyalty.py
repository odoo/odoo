# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import TransactionCase, tagged

@tagged('post_install', '-at_install')
class TestLoyalty(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['loyalty.program'].search([]).write({'active': False})

    def test_nominative_programs(self):
        loyalty_program, ewallet_program = self.env['loyalty.program'].create([
            {
                'name': 'Loyalty Program',
                'program_type': 'loyalty',
                'trigger': 'auto',
                'applies_on': 'both',
                'rule_ids': [(0, 0, {
                    'reward_point_mode': 'money',
                    'reward_point_amount': 10,
                })],
                'reward_ids': [(0, 0, {})],
            },
            {
                'name': 'eWallet Program',
                'program_type': 'ewallet',
                'applies_on': 'future',
                'trigger': 'auto',
                'rule_ids': [(0, 0, {
                    'reward_point_mode': 'money',
                    'reward_point_amount': 10,
                })],
                'reward_ids': [(0, 0, {})],
            }
        ])
        product = self.env['product.product'].create({
            'name': 'Product C',
            'list_price': 100,
            'sale_ok': True,
            'taxes_id': [(6, 0, [])],
        })

        jean_jacques = self.env['res.partner'].create({'name': 'Jean Jacques'})
        order = self.env['sale.order'].create({
            'partner_id': jean_jacques.id,
        })
        order._update_programs_and_rewards()
        claimable_rewards = order._get_claimable_rewards()
        # Should be empty since we do not have any coupon created yet
        self.assertFalse(claimable_rewards, "No program should be applicable")
        _, ewallet_coupon = self.env['loyalty.card'].create([
            {
                'program_id': loyalty_program.id,
                'partner_id': jean_jacques.id,
                'points': 10,
            },
            {
                'program_id': ewallet_program.id,
                'partner_id': jean_jacques.id,
                'points': 0,
            },
        ])
        order.write({
            'order_line': [(0, 0, {
                'product_id': product.id,
                'product_uom_qty': 1,
            })]
        })
        order._update_programs_and_rewards()
        claimable_rewards = order._get_claimable_rewards()
        self.assertEqual(len(claimable_rewards), 1, "The ewallet program should not be applicable since the card has no points.")
        ewallet_coupon.points = 50
        order._update_programs_and_rewards()
        claimable_rewards = order._get_claimable_rewards()
        self.assertEqual(len(claimable_rewards), 2, "Now that the ewallet has some points they should both be applicable.")
