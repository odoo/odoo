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
            'list_price': 1,
            'is_deposit': True,
            'available_in_pos': True,
            'taxes_id': False,
        })
        cls.bottle = cls.env['product.product'].create({
            'name': 'Bottle',
            'list_price': 10,
            'deposit_product_id': cls.deposit.id,
            'available_in_pos': True,
            'taxes_id': False,
        })
        cls.pos_config_usd.open_ui()
        cls.pos_config_usd.current_session_id.set_opening_control(0, '')
        cls.order = cls.env['pos.order'].create({
            'session_id': cls.pos_config_usd.current_session_id.id,
            'amount_total': 0.0,
            'amount_tax': 0.0,
            'amount_return': 0.0,
            'amount_paid': 0.0,
        })
        cls.main_line = cls.env['pos.order.line'].create({
            'order_id': cls.order.id,
            'product_id': cls.bottle.id,
            'qty': 2,
            'price_unit': 10,
            'price_subtotal': 20,
            'price_subtotal_incl': 20,
        })
        cls.deposit_line = cls.env['pos.order.line'].create({
            'order_id': cls.order.id,
            'product_id': cls.deposit.id,
            'deposit_main_line_id': cls.main_line.id,
            'qty': 2,
            'price_unit': 1,
            'price_subtotal': 2,
            'price_subtotal_incl': 2,
        })

    def test_deposit_lines_are_not_prepared(self):
        lines = self.env['pos.prep.order']._get_lines_to_prepare(self.order)
        self.assertEqual(lines, self.main_line)

    def test_receipt_puts_the_deposit_under_its_product(self):
        other = self.env['pos.order.line'].create({
            'order_id': self.order.id,
            'product_id': self.bottle.id,
            'qty': 1,
            'price_unit': 10,
            'price_subtotal': 10,
            'price_subtotal_incl': 10,
        })
        lines = self.order._order_receipt_generate_line_data()
        self.assertEqual([line['id'] for line in lines], [self.main_line.id, self.deposit_line.id, other.id])
        self.assertTrue(lines[1]['is_deposit'])
        self.assertFalse(lines[1]['is_deposit_for_combo_child'])
        self.assertFalse(lines[0].get('is_deposit'))

    def test_receipt_does_not_count_deposit_lines(self):
        self.assertEqual(self.order._get_total_item_count(), 2)

    def test_copy_does_not_keep_the_deposit_link(self):
        self.assertFalse(self.deposit_line.copy({'order_id': self.order.id}).deposit_main_line_id)
