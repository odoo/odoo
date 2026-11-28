from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon


@tagged('post_install', '-at_install')
class TestSplitPaymentLoyalty(TestPointOfSaleHttpCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.split_payment_product = cls.main_pos_config.split_payment_product_id
        cls.burger, cls.wine = cls.env['product.product'].create([
            {'name': 'Burger', 'available_in_pos': True, 'list_price': 12},
            {'name': 'Wine', 'available_in_pos': True, 'list_price': 25},
        ])
        cls.alice, cls.bob, cls.carol = cls.env['res.partner'].create([
            {'name': 'Alice'}, {'name': 'Bob'}, {'name': 'Carol'},
        ])
        cls.env['loyalty.program'].search([]).write({'active': False})
        cls.main_pos_config.open_ui()
        cls.pos_session = cls.main_pos_config.current_session_id

    def _create_program(self, reward_point_mode):
        return self.env['loyalty.program'].create({
            'name': 'Restaurant Loyalty',
            'program_type': 'loyalty',
            'trigger': 'auto',
            'applies_on': 'both',
            'rule_ids': [Command.create({
                'reward_point_mode': reward_point_mode,
                'reward_point_amount': 1,
                'minimum_qty': 1,
            })],
            'reward_ids': [Command.create({
                'reward_type': 'discount',
                'discount_mode': 'percent',
                'discount': 10,
                'discount_applicability': 'order',
                'required_points': 100,
            })],
        })

    def _line(self, product, qty, price):
        return {
            'product_id': product.id,
            'qty': qty,
            'price_unit': price,
            'price_subtotal': qty * price,
            'price_subtotal_incl': qty * price,
        }

    def _create_order(self, partner, lines, **kwargs):
        order = self.env['pos.order'].create({
            'config_id': self.main_pos_config.id,
            'session_id': self.pos_session.id,
            'partner_id': partner.id,
            'lines': [Command.create(line) for line in lines],
            'amount_paid': 0,
            'amount_return': 0,
            'amount_tax': 0,
            'amount_total': 0,
            **kwargs,
        })
        order._process_loyalty()
        return order

    def _split_bill(self):
        origin_order = self._create_order(self.carol, [
            self._line(self.burger, 2, 12),
            self._line(self.wine, 1, 25),
            self._line(self.split_payment_product, 1, -22),
        ])
        split_orders = [
            self._create_order(partner, [self._line(self.split_payment_product, 1, amount)], split_origin_order_id=origin_order.id)
            for partner, amount in ((self.alice, 10), (self.bob, 12))
        ]
        return origin_order, split_orders

    def _points_of(self, program, partner):
        card = self.env['loyalty.card'].search([
            ('program_id', '=', program.id),
            ('partner_id', '=', partner.id),
        ])
        return card.points if card else 0

    def test_split_payment_points_per_order(self):
        """Every guest paying through Split and Pay earns the points of an order."""
        self.assertTrue(self.split_payment_product)
        program = self._create_program('order')
        self._split_bill()
        self.assertEqual(self._points_of(program, self.alice), 1)
        self.assertEqual(self._points_of(program, self.bob), 1)
        self.assertEqual(self._points_of(program, self.carol), 1)

    def test_split_payment_points_per_unit(self):
        """
        Split payment lines are not units. The split payment orders earn nothing and the
        origin order earns the units of all its products, ignoring its negative split lines.
        """
        program = self._create_program('unit')
        self._split_bill()
        self.assertEqual(self._points_of(program, self.alice), 0)
        self.assertEqual(self._points_of(program, self.bob), 0)
        self.assertEqual(self._points_of(program, self.carol), 3)
