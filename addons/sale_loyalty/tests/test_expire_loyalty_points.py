# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo import fields
from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.sale_loyalty.tests.common import TestSaleCouponCommon


@tagged('post_install', '-at_install')
class TestExpireLoyaltyPoints(TestSaleCouponCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner_a = cls.env['res.partner'].create({'name': 'Franklin Sierra'})
        cls.loyalty_program = cls.env['loyalty.program'].create({
            'name': 'Loyalty Program',
            'program_type': 'loyalty',
            'trigger': 'auto',
            'applies_on': 'both',
            'expire_after': 90,
            'rule_ids': [
                Command.create({
                    'reward_point_mode': 'money',
                    'reward_point_amount': 5,
                }),
            ],
            'reward_ids': [
                Command.create({
                    'reward_type': 'discount',
                    'discount': 20,
                    'discount_mode': 'percent',
                    'discount_applicability': 'order',
                    'required_points': 500,
                }),
            ],
        })
        cls.loyalty_card = cls.env['loyalty.card'].create({
            'program_id': cls.loyalty_program.id,
            'partner_id': cls.partner_a.id,
        })

    def test_expire_loyalty_points(self):
        """
        Checks that loyalty points are consumed in first earned, first used manner,
        and that expired points are correctly managed by the cron job.
        """
        orders = self.env['sale.order'].create([
            {'partner_id': self.partner_a.id},
            {'partner_id': self.partner_a.id},
        ])
        products = [self.product_A, self.product_B]
        quantities = [1.0, 28.0]
        expected_points = [75.0, 380.0]
        history_records = []

        for order, product, qty, expected in zip(orders, products, quantities, expected_points):
            order.order_line = [
                Command.create({
                    'product_id': product.id,
                    'product_uom_qty': qty,
                }),
            ]
            order._update_programs_and_rewards()
            self._claim_reward(order, self.loyalty_program)
            order.action_confirm()
            history_record = self.loyalty_card.history_ids.filtered(
                lambda history: history.order_id == order.id,
            )
            history_records.append(history_record)
            self.assertEqual(history_record.available_issued_points, expected)

        future_date = fields.Date.today() + timedelta(days=self.loyalty_program.expire_after + 1)
        with self.mock_datetime_and_now(future_date):
            self.env['loyalty.history']._cron_expire_loyalty_points()

        self.assertEqual(self.loyalty_card.points, 0.0)

        for history_record in history_records:
            self.assertFalse(history_record.active)
