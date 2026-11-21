# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.point_of_sale.tests.common import CommonPosTest


@tagged('post_install', '-at_install')
class TestPosDeposit(CommonPosTest):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.deposit = cls.env['product.product'].create({
            'name': 'Bottle Deposit',
            'is_deposit': True,
            'available_in_pos': True,
            'list_price': 0.25,
        })
        cls.bottle = cls.env['product.product'].create({
            'name': 'Bottle',
            'available_in_pos': True,
            'list_price': 2.0,
            'deposit_product_id': cls.deposit.id,
        })

    def setUp(self):
        super().setUp()
        self.order, _ = self.create_backend_pos_order({
            'line_data': [
                {'product_id': self.bottle.id, 'qty': 2},
                {'product_id': self.bottle.id, 'qty': 1},
                {'product_id': self.deposit.id, 'qty': 2},
                {'product_id': self.deposit.id, 'qty': 1},
            ],
        })
        self.main_line, self.other_line, self.deposit_line, self.standalone_deposit_line = self.order.lines
        self.deposit_line.deposit_main_line_id = self.main_line

    def test_deposit_lines_are_not_prepared(self):
        lines = self.env['pos.prep.order']._get_lines_to_prepare(self.order)
        self.assertEqual(lines, self.main_line + self.other_line)

    def test_receipt_puts_the_deposit_under_its_product(self):
        lines = self.order._order_receipt_generate_line_data()
        self.assertEqual(
            [(line['id'], line.get('is_deposit_line', False)) for line in lines],
            [
                (self.main_line.id, False),
                (self.deposit_line.id, True),
                (self.other_line.id, False),
                (self.standalone_deposit_line.id, False),
            ],
        )

    def test_receipt_does_not_count_deposit_lines(self):
        self.assertEqual(self.order._get_total_item_count(), 3)
