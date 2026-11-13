# Part of Odoo. See LICENSE file for full copyright and licensing details.

import uuid

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.pos_self_order.tests.self_order_common_test import SelfOrderCommonTest


@tagged('post_install', '-at_install')
class TestSelfOrderDeposit(SelfOrderCommonTest):

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

    def setUp(self):
        super().setUp()
        (self.bottle + self.deposit).taxes_id = False
        self.pos_config.write({'module_pos_deposit': True, 'self_ordering_mode': 'mobile'})
        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, '')

    def _create_order(self):
        return self.env['pos.order'].create({
            'session_id': self.pos_config.current_session_id.id,
            'preset_id': self.in_preset.id,
            'amount_total': 0.0,
            'amount_tax': 0.0,
            'amount_return': 0.0,
            'amount_paid': 0.0,
        })

    def _create_line(self, order, product, qty=1, **values):
        return self.env['pos.order.line'].create({
            'order_id': order.id,
            'product_id': product.id,
            'qty': qty,
            'price_unit': 0.0,
            'price_subtotal': 0.0,
            'price_subtotal_incl': 0.0,
            'uuid': uuid.uuid4().hex,
            'full_product_name': product.name,
            **values,
        })

    def test_valid_deposit_is_priced(self):
        order = self._create_order()
        main = self._create_line(order, self.bottle, 3)
        self._create_line(order, self.deposit, 3, deposit_main_line_id=main.id)
        order.recompute_prices()
        self.assertAlmostEqual(order.amount_total, 33)

    def test_missing_deposit_line_is_refused(self):
        order = self._create_order()
        self._create_line(order, self.bottle, 3)
        with self.assertRaises(UserError):
            order.recompute_prices()

    def test_deposit_quantity_must_match_the_product(self):
        order = self._create_order()
        main = self._create_line(order, self.bottle, 3)
        self._create_line(order, self.deposit, 1, deposit_main_line_id=main.id)
        with self.assertRaises(UserError):
            order.recompute_prices()

    def test_deposit_of_another_order_is_refused(self):
        other_main = self._create_line(self._create_order(), self.bottle, 1)
        order = self._create_order()
        main = self._create_line(order, self.bottle, 1)
        self._create_line(order, self.deposit, 1, deposit_main_line_id=other_main.id)
        self._create_line(order, self.deposit, 1, deposit_main_line_id=main.id)
        with self.assertRaises(UserError):
            order.recompute_prices()

    def test_deposit_must_be_the_one_of_the_product(self):
        other_deposit = self.deposit.copy({'name': 'Crate Deposit'})
        order = self._create_order()
        main = self._create_line(order, self.bottle, 1)
        self._create_line(order, other_deposit, 1, deposit_main_line_id=main.id)
        with self.assertRaises(UserError):
            order.recompute_prices()

    def test_check_pos_order_lines_keeps_the_deposit_link(self):
        line = [Command.CREATE, 0, {
            'product_id': self.bottle.id,
            'qty': 1,
            'uuid': uuid.uuid4().hex,
            'deposit_main_line_id': 42,
        }]
        result = self.env['pos.order']._check_pos_order_lines(
            self.pos_config, {}, line, self.env['account.fiscal.position'],
        )
        self.assertEqual(result[2]['deposit_main_line_id'], 42)
        del line[2]['deposit_main_line_id']
        result = self.env['pos.order']._check_pos_order_lines(
            self.pos_config, {}, line, self.env['account.fiscal.position'],
        )
        self.assertNotIn('deposit_main_line_id', result[2])
