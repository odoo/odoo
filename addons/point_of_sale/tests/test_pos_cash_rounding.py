from odoo import Command
from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon
from odoo.tests import tagged
from odoo import fields


@tagged('post_install', '-at_install')
class TestPosCashRounding(TestPointOfSaleHttpCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner_a.name = "AAAAAA"  # The POS only load the first 100 partners
        cls.cash_rounding_add_invoice_line = cls.env['account.cash.rounding'].create({
            'name': "cash_rounding_add_invoice_line",
            'rounding': 0.05,
            'rounding_method': 'HALF-UP',
            'strategy': 'add_invoice_line',
            'profit_account_id': cls.env.company.default_cash_difference_income_account_id.id,
            'loss_account_id': cls.env.company.default_cash_difference_expense_account_id.id,
        })
        cls.cash_rounding_biggest_tax = cls.env['account.cash.rounding'].create({
            'name': "cash_rounding_biggest_tax",
            'rounding': 0.05,
            'rounding_method': 'HALF-UP',
            'strategy': 'biggest_tax',
            'profit_account_id': cls.env.company.default_cash_difference_income_account_id.id,
            'loss_account_id': cls.env.company.default_cash_difference_expense_account_id.id,
        })

        cls.product = cls.env['product.product'].create({
            'name': "random_product",
            'available_in_pos': True,
            'list_price': 13.67,
            'taxes_id': [Command.set(cls.company_data['default_tax_sale'].ids)],
            'pos_categ_ids': [Command.set(cls.pos_desk_misc_test.ids)],
        })

    def test_cash_rounding_halfup_add_invoice_line_not_only_round_cash_method(self):
        self.main_pos_config.write({
            'rounding_method': self.cash_rounding_add_invoice_line.id,
            'cash_rounding': True,
            'only_round_cash_method': False,
        })
        with self.with_new_session(user=self.pos_user) as session:
            self.start_pos_tour('test_cash_rounding_halfup_add_invoice_line_not_only_round_cash_method')
            refund, order = self.env['pos.order'].search([('session_id', '=', session.id)], limit=2)
            self.assertRecordValues(order, [{
                'amount_tax': 2.05,
                'amount_total': 15.72,
                'amount_paid': 15.7,
            }])
            self.assertRecordValues(order.account_move, [{
                'amount_untaxed': 13.65,
                'amount_tax': 2.05,
                'amount_total': 15.7,
            }])
            self.assertRecordValues(refund, [{
                'amount_tax': -2.05,
                'amount_total': -15.72,
                'amount_paid': -15.7,
            }])
            self.assertRecordValues(refund.account_move, [{
                'amount_untaxed': 13.65,
                'amount_tax': 2.05,
                'amount_total': 15.7,
            }])

    def test_cash_rounding_halfup_add_invoice_line_not_only_round_cash_method_pay_by_bank_and_cash(self):
        self.main_pos_config.write({
            'rounding_method': self.cash_rounding_add_invoice_line.id,
            'cash_rounding': True,
            'only_round_cash_method': False,
        })
        with self.with_new_session(user=self.pos_user) as session:
            self.start_pos_tour('test_cash_rounding_halfup_add_invoice_line_not_only_round_cash_method_pay_by_bank_and_cash')
            refund, order = self.env['pos.order'].search([('session_id', '=', session.id)], limit=2)
            self.assertRecordValues(order, [{
                'amount_tax': 2.05,
                'amount_total': 15.72,
                'amount_paid': 15.73,
            }])
            self.assertRecordValues(order.account_move, [{
                'amount_untaxed': 13.68,
                'amount_tax': 2.05,
                'amount_total': 15.73,
            }])
            self.assertRecordValues(refund, [{
                'amount_tax': -2.05,
                'amount_total': -15.72,
                'amount_paid': -15.73,
            }])
            self.assertRecordValues(refund.account_move, [{
                'amount_untaxed': 13.68,
                'amount_tax': 2.05,
                'amount_total': 15.73,
            }])

    def test_cash_rounding_down_add_invoice_line_not_only_round_cash_method_no_rounding_left(self):
        self.cash_rounding_add_invoice_line.rounding_method = 'DOWN'
        self.main_pos_config.write({
            'rounding_method': self.cash_rounding_add_invoice_line.id,
            'cash_rounding': True,
            'only_round_cash_method': False,
        })
        with self.with_new_session(user=self.pos_user) as session:
            self.start_pos_tour('test_cash_rounding_down_add_invoice_line_not_only_round_cash_method_no_rounding_left')
            refund, order = self.env['pos.order'].search([('session_id', '=', session.id)], limit=2)
            self.assertRecordValues(order, [{
                'amount_tax': 2.05,
                'amount_total': 15.72,
                'amount_paid': 15.72,
            }])
            self.assertRecordValues(order.account_move, [{
                'amount_untaxed': 13.67,
                'amount_tax': 2.05,
                'amount_total': 15.72,
            }])
            self.assertRecordValues(refund, [{
                'amount_tax': -2.05,
                'amount_total': -15.72,
                'amount_paid': -15.72,
            }])
            self.assertRecordValues(refund.account_move, [{
                'amount_untaxed': 13.67,
                'amount_tax': 2.05,
                'amount_total': 15.72,
            }])

    def test_cash_rounding_down_add_invoice_line_not_only_round_cash_method_with_residual_rounding(self):
        self.cash_rounding_add_invoice_line.rounding_method = 'DOWN'
        self.main_pos_config.write({
            'rounding_method': self.cash_rounding_add_invoice_line.id,
            'cash_rounding': True,
            'only_round_cash_method': False,
        })
        with self.with_new_session(user=self.pos_user) as session:
            self.start_pos_tour('test_cash_rounding_down_add_invoice_line_not_only_round_cash_method_with_residual_rounding')
            refund, order = self.env['pos.order'].search([('session_id', '=', session.id)], limit=2)
            self.assertRecordValues(order, [{
                'amount_tax': 2.05,
                'amount_total': 15.72,
                'amount_paid': 15.68,
            }])
            self.assertRecordValues(order.account_move, [{
                'amount_untaxed': 13.63,
                'amount_tax': 2.05,
                'amount_total': 15.68,
            }])
            self.assertRecordValues(refund, [{
                'amount_tax': -2.05,
                'amount_total': -15.72,
                'amount_paid': -15.68,
            }])
            self.assertRecordValues(refund.account_move, [{
                'amount_untaxed': 13.63,
                'amount_tax': 2.05,
                'amount_total': 15.68,
            }])

    def test_cash_rounding_up_add_invoice_line_not_only_round_cash_method(self):
        self.cash_rounding_add_invoice_line.rounding_method = 'UP'
        self.main_pos_config.write({
            'rounding_method': self.cash_rounding_add_invoice_line.id,
            'cash_rounding': True,
            'only_round_cash_method': False,
        })
        with self.with_new_session(user=self.pos_user) as session:
            self.start_pos_tour('test_cash_rounding_up_add_invoice_line_not_only_round_cash_method')
            refund, order = self.env['pos.order'].search([('session_id', '=', session.id)], limit=2)
            self.assertRecordValues(order, [{
                'amount_tax': 2.05,
                'amount_total': 15.72,
                'amount_paid': 15.74,
            }])
            self.assertRecordValues(order.account_move, [{
                'amount_untaxed': 13.69,
                'amount_tax': 2.05,
                'amount_total': 15.74,
            }])
            self.assertRecordValues(refund, [{
                'amount_tax': -2.05,
                'amount_total': -15.72,
                'amount_paid': -15.74,
            }])
            self.assertRecordValues(refund.account_move, [{
                'amount_untaxed': 13.69,
                'amount_tax': 2.05,
                'amount_total': 15.74,
            }])

    def test_cash_rounding_halfup_add_invoice_line_only_round_cash_method(self):
        self.main_pos_config.write({
            'rounding_method': self.cash_rounding_add_invoice_line.id,
            'cash_rounding': True,
            'only_round_cash_method': True,
        })
        with self.with_new_session(user=self.pos_user) as session:
            self.start_pos_tour('test_cash_rounding_halfup_add_invoice_line_only_round_cash_method')
            refund, order = self.env['pos.order'].search([('session_id', '=', session.id)], limit=2)
            self.assertRecordValues(order, [{
                'amount_tax': 2.05,
                'amount_total': 15.72,
                'amount_paid': 15.7,
            }])
            self.assertRecordValues(order.account_move, [{
                'amount_untaxed': 13.65,
                'amount_tax': 2.05,
                'amount_total': 15.7,
            }])
            self.assertRecordValues(refund, [{
                'amount_tax': -2.05,
                'amount_total': -15.72,
                'amount_paid': -15.7,
            }])
            self.assertRecordValues(refund.account_move, [{
                'amount_untaxed': 13.65,
                'amount_tax': 2.05,
                'amount_total': 15.7,
            }])

    def test_cash_rounding_halfup_add_invoice_line_only_round_cash_method_pay_by_bank_and_cash(self):
        self.main_pos_config.write({
            'rounding_method': self.cash_rounding_add_invoice_line.id,
            'cash_rounding': True,
            'only_round_cash_method': True,
        })
        with self.with_new_session(user=self.pos_user) as session:
            self.start_pos_tour('test_cash_rounding_halfup_add_invoice_line_only_round_cash_method_pay_by_bank_and_cash')
            refund, order = self.env['pos.order'].search([('session_id', '=', session.id)], limit=2)
            self.assertRecordValues(order, [{
                'amount_tax': 2.05,
                'amount_total': 15.72,
                'amount_paid': 15.73,
            }])
            self.assertRecordValues(order.account_move, [{
                'amount_untaxed': 13.68,
                'amount_tax': 2.05,
                'amount_total': 15.73,
            }])
            self.assertRecordValues(refund, [{
                'amount_tax': -2.05,
                'amount_total': -15.72,
                'amount_paid': -15.73,
            }])
            self.assertRecordValues(refund.account_move, [{
                'amount_untaxed': 13.68,
                'amount_tax': 2.05,
                'amount_total': 15.73,
            }])

    def test_cash_rounding_halfup_biggest_tax_not_only_round_cash_method(self):
        self.skipTest('To re-introduce when feature is ready')
        self.main_pos_config.write({
            'rounding_method': self.cash_rounding_biggest_tax.id,
            'cash_rounding': True,
            'only_round_cash_method': False,
        })
        with self.with_new_session(user=self.pos_user) as session:
            self.start_pos_tour('test_cash_rounding_halfup_biggest_tax_not_only_round_cash_method')
            refund, order = self.env['pos.order'].search([('session_id', '=', session.id)], limit=2)
            self.assertRecordValues(order, [{
                'amount_tax': 2.03,
                'amount_total': 15.7,
                'amount_paid': 15.7,
            }])
            self.assertRecordValues(order.account_move, [{
                'amount_untaxed': 13.67,
                'amount_tax': 2.03,
                'amount_total': 15.7,
            }])
            self.assertRecordValues(refund, [{
                'amount_tax': -2.03,
                'amount_total': -15.7,
                'amount_paid': -15.7,
            }])
            self.assertRecordValues(refund.account_move, [{
                'amount_untaxed': 13.67,
                'amount_tax': 2.03,
                'amount_total': 15.7,
            }])

    def test_cash_rounding_halfup_biggest_tax_not_only_round_cash_method_pay_by_bank_and_cash(self):
        self.skipTest('To re-introduce when feature is ready')
        self.main_pos_config.write({
            'rounding_method': self.cash_rounding_biggest_tax.id,
            'cash_rounding': True,
            'only_round_cash_method': False,
        })
        with self.with_new_session(user=self.pos_user) as session:
            self.start_pos_tour('test_cash_rounding_halfup_biggest_tax_not_only_round_cash_method_pay_by_bank_and_cash')
            refund, order = self.env['pos.order'].search([('session_id', '=', session.id)], limit=2)
            self.assertRecordValues(order, [{
                'amount_tax': 2.03,
                'amount_total': 15.7,
                'amount_paid': 15.72,
            }])
            self.assertRecordValues(order.account_move, [{
                'amount_untaxed': 13.69,
                'amount_tax': 2.03,
                'amount_total': 15.72,
            }])
            self.assertRecordValues(refund, [{
                'amount_tax': -2.03,
                'amount_total': -15.7,
                'amount_paid': -15.72,
            }])
            self.assertRecordValues(refund.account_move, [{
                'amount_untaxed': 13.69,
                'amount_tax': 2.03,
                'amount_total': 15.72,
            }])

    def test_cash_rounding_halfup_biggest_tax_only_round_cash_method(self):
        self.skipTest('To re-introduce when feature is ready')
        self.main_pos_config.write({
            'rounding_method': self.cash_rounding_biggest_tax.id,
            'cash_rounding': True,
            'only_round_cash_method': True,
        })
        with self.with_new_session(user=self.pos_user) as session:
            self.start_pos_tour('test_cash_rounding_halfup_biggest_tax_only_round_cash_method')
            refund, order = self.env['pos.order'].search([('session_id', '=', session.id)], limit=2)
            self.assertRecordValues(order, [{
                'amount_tax': 2.05,
                'amount_total': 15.72,
                'amount_paid': 15.7,
            }])
            self.assertRecordValues(order.account_move, [{
                'amount_untaxed': 13.67,
                'amount_tax': 2.03,
                'amount_total': 15.7,
            }])
            self.assertRecordValues(refund, [{
                'amount_tax': -2.05,
                'amount_total': -15.72,
                'amount_paid': -15.7,
            }])
            self.assertRecordValues(refund.account_move, [{
                'amount_untaxed': 13.67,
                'amount_tax': 2.03,
                'amount_total': 15.7,
            }])

    def test_cash_rounding_halfup_biggest_tax_only_round_cash_method_pay_by_bank_and_cash(self):
        self.skipTest('To re-introduce when feature is ready')
        self.main_pos_config.write({
            'rounding_method': self.cash_rounding_biggest_tax.id,
            'cash_rounding': True,
            'only_round_cash_method': True,
        })
        with self.with_new_session(user=self.pos_user) as session:
            self.start_pos_tour('test_cash_rounding_halfup_biggest_tax_only_round_cash_method_pay_by_bank_and_cash')
            refund, order = self.env['pos.order'].search([('session_id', '=', session.id)], limit=2)
            self.assertRecordValues(order, [{
                'amount_tax': 2.05,
                'amount_total': 15.72,
                'amount_paid': 15.73,
            }])
            self.assertRecordValues(order.account_move, [{
                'amount_untaxed': 13.70,
                'amount_tax': 2.03,
                'amount_total': 15.73,
            }])
            self.assertRecordValues(refund, [{
                'amount_tax': -2.05,
                'amount_total': -15.72,
                'amount_paid': -15.73,
            }])
            self.assertRecordValues(refund.account_move, [{
                'amount_untaxed': 13.70,
                'amount_tax': 2.03,
                'amount_total': 15.73,
            }])

    def test_cash_rounding_with_change(self):
        self.main_pos_config.write({
            'rounding_method': self.cash_rounding_add_invoice_line.id,
            'cash_rounding': True,
            'only_round_cash_method': False,
        })
        with self.with_new_session(user=self.pos_user) as session:
            self.start_pos_tour('test_cash_rounding_with_change')
            order = self.env['pos.order'].search([('session_id', '=', session.id)], limit=1)
            self.assertRecordValues(order, [{
                'amount_tax': 2.05,
                'amount_total': 15.7,
                'amount_paid': 15.7,
            }])
            self.assertRecordValues(order.account_move, [{
                'amount_untaxed': 13.65,
                'amount_tax': 2.05,
                'amount_total': 15.7,
            }])

    def test_cash_rounding_only_cash_method_with_change(self):
        self.main_pos_config.write({
            'rounding_method': self.cash_rounding_add_invoice_line.id,
            'cash_rounding': True,
            'only_round_cash_method': True,
        })
        with self.with_new_session(user=self.pos_user) as session:
            self.start_pos_tour('test_cash_rounding_only_cash_method_with_change')
            order = self.env['pos.order'].search([('session_id', '=', session.id)], limit=1)
            self.assertRecordValues(order.account_move, [{
                'amount_untaxed': 13.65,
                'amount_tax': 2.05,
                'amount_total': 15.7,
            }])
            self.assertRecordValues(order, [{
                'amount_tax': 2.05,
                'amount_total': 15.72,
                'amount_paid': 15.7,
            }])

    def test_cash_rounding_up_with_change(self):
        self.cash_rounding_add_invoice_line = self.env['account.cash.rounding'].create({
            'name': "cash_rounding_up_1",
            'rounding': 1.00,
            'rounding_method': 'UP',
            'strategy': 'add_invoice_line',
            'profit_account_id': self.env.company.default_cash_difference_income_account_id.id,
            'loss_account_id': self.env.company.default_cash_difference_expense_account_id.id,
        })
        self.main_pos_config.write({
            'rounding_method': self.cash_rounding_add_invoice_line.id,
            'cash_rounding': True,
            'only_round_cash_method': True,
        })
        tax_include = self.env['account.tax'].create({
            'name': 'tax incl',
            'type_tax_use': 'sale',
            'amount_type': 'percent',
            'amount': 7,
            'price_include_override': 'tax_included',
            'include_base_amount': True,
        })
        self.env['product.product'].create({
            'name': "product_a",
            'available_in_pos': True,
            'list_price': 95.00,
            'taxes_id': tax_include,
            'pos_categ_ids': [Command.set(self.pos_desk_misc_test.ids)],
        })
        self.env['product.product'].create({
            'name': "product_b",
            'available_in_pos': True,
            'list_price': 42.00,
            'taxes_id': tax_include,
            'pos_categ_ids': [Command.set(self.pos_desk_misc_test.ids)],
        })
        self.start_pos_tour('test_cash_rounding_up_with_change')

    def test_no_rounding_on_card_credit_note(self):
        """
        Tests that when we revert an invoice that was entirely paid by card, the rounding is
        not applied if the only_round_cash_method is activated
        """
        self.main_pos_config.write({
            'rounding_method': self.cash_rounding_add_invoice_line.id,
            'cash_rounding': True,
            'only_round_cash_method': True,
        })
        product = self.env['product.product'].create({
            'name': "product_a",
            'available_in_pos': True,
            'list_price': 13.31,
            'taxes_id': False,
            'pos_categ_ids': [Command.set(self.pos_desk_misc_test.ids)],
        })
        self.main_pos_config.open_ui()
        session = self.main_pos_config.current_session_id

        order_data = {
            'amount_paid': 13.31,
            'amount_return': 0,
            'amount_tax': 0,
            'amount_total': 13.31,
            'fiscal_position_id': False,
            'lines': [Command.create({
                'discount': 0,
                'id': 1,
                'pack_lot_ids': [],
                'price_unit': 13.31,
                'product_id': product.id,
                'price_subtotal': 13.31,
                'price_subtotal_incl': 13.31,
                'qty': 1,
                'tax_ids': [(6, 0, [])],
            })],
            'name': 'Order rounding test',
            'partner_id': self.partner_a.id,
            'session_id': session.id,
            'sequence_number': 1,
            'payment_ids': [Command.create({
                'amount': 13.31,
                'name': fields.Datetime.now(),
                'payment_method_id': self.bank_payment_method.id,
            })],
            'uuid': '12345-123-1234',
            'last_order_preparation_change': '{}',
            'user_id': self.env.uid,
            'to_invoice': True
        }

        order_id = self.env['pos.order'].sync_from_ui([order_data])['pos.order'][0]['id']
        order = self.env['pos.order'].browse(order_id)
        session.action_pos_session_closing_control()
        action = order._generate_pos_order_invoice()
        invoice = self.env['account.move'].browse(action['res_id'])
        reversal = invoice._reverse_moves(cancel=False)
        rounding_lines = reversal.line_ids.filtered(lambda l: l.name == 'cash_rounding_add_invoice_line')
        self.assertEqual(rounding_lines.balance, 0.0)
