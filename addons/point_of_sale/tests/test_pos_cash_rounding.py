from odoo import Command
from odoo.addons.point_of_sale.tests.test_common import TestPointOfSaleDataHttpCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestPosCashRounding(TestPointOfSaleDataHttpCommon):

    @classmethod
    def setUpClass(self):
        super().setUpClass()
        self.cash_rounding_add_invoice_line = self.env['account.cash.rounding'].create({
            'name': "cash_rounding_add_invoice_line",
            'rounding': 0.05,
            'rounding_method': 'HALF-UP',
            'strategy': 'add_invoice_line',
            'profit_account_id': self.env.company.default_cash_difference_income_account_id.id,
            'loss_account_id': self.env.company.default_cash_difference_expense_account_id.id,
        })
        self.cash_rounding_biggest_tax = self.env['account.cash.rounding'].create({
            'name': "cash_rounding_biggest_tax",
            'rounding': 0.05,
            'rounding_method': 'HALF-UP',
            'strategy': 'biggest_tax',
            'profit_account_id': self.env.company.default_cash_difference_income_account_id.id,
            'loss_account_id': self.env.company.default_cash_difference_expense_account_id.id,
        })
        self.product_awesome_thing.write({
            'list_price': 13.67,
            'taxes_id': [Command.set(self.company_data['default_tax_sale'].ids)],
        })

    def test_cash_rounding_halfup_add_invoice_line_not_only_round_cash_method(self):
        self.pos_config.write({
            'rounding_method': self.cash_rounding_add_invoice_line.id,
            'cash_rounding': True,
            'only_round_cash_method': False,
        })
        self.start_pos_tour('test_cash_rounding_halfup_add_invoice_line_not_only_round_cash_method')
        refund, order = self.env['pos.order'].search([('session_id', '=', self.pos_config.current_session_id.id)], limit=2)
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
        self.pos_config.write({
            'rounding_method': self.cash_rounding_add_invoice_line.id,
            'cash_rounding': True,
            'only_round_cash_method': False,
        })
        self.start_pos_tour('test_cash_rounding_halfup_add_invoice_line_not_only_round_cash_method_pay_by_bank_and_cash')
        refund, order = self.env['pos.order'].search([('session_id', '=', self.pos_config.current_session_id.id)], limit=2)
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
        self.pos_config.write({
            'rounding_method': self.cash_rounding_add_invoice_line.id,
            'cash_rounding': True,
            'only_round_cash_method': False,
        })
        self.start_pos_tour('test_cash_rounding_down_add_invoice_line_not_only_round_cash_method_no_rounding_left')
        refund, order = self.env['pos.order'].search([('session_id', '=', self.pos_config.current_session_id.id)], limit=2)
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
        self.pos_config.write({
            'rounding_method': self.cash_rounding_add_invoice_line.id,
            'cash_rounding': True,
            'only_round_cash_method': False,
        })
        self.start_pos_tour('test_cash_rounding_down_add_invoice_line_not_only_round_cash_method_with_residual_rounding')
        refund, order = self.env['pos.order'].search([('session_id', '=', self.pos_config.current_session_id.id)], limit=2)
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
        self.pos_config.write({
            'rounding_method': self.cash_rounding_add_invoice_line.id,
            'cash_rounding': True,
            'only_round_cash_method': False,
        })
        self.start_pos_tour('test_cash_rounding_up_add_invoice_line_not_only_round_cash_method')
        refund, order = self.env['pos.order'].search([('session_id', '=', self.pos_config.current_session_id.id)], limit=2)
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
        self.pos_config.write({
            'rounding_method': self.cash_rounding_add_invoice_line.id,
            'cash_rounding': True,
            'only_round_cash_method': True,
        })
        self.start_pos_tour('test_cash_rounding_halfup_add_invoice_line_only_round_cash_method')
        refund, order = self.env['pos.order'].search([('session_id', '=', self.pos_config.current_session_id.id)], limit=2)
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
        self.pos_config.write({
            'rounding_method': self.cash_rounding_add_invoice_line.id,
            'cash_rounding': True,
            'only_round_cash_method': True,
        })
        self.start_pos_tour('test_cash_rounding_halfup_add_invoice_line_only_round_cash_method_pay_by_bank_and_cash')
        refund, order = self.env['pos.order'].search([('session_id', '=', self.pos_config.current_session_id.id)], limit=2)
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
        self.pos_config.write({
            'rounding_method': self.cash_rounding_biggest_tax.id,
            'cash_rounding': True,
            'only_round_cash_method': False,
        })
        self.start_pos_tour('test_cash_rounding_halfup_biggest_tax_not_only_round_cash_method')
        refund, order = self.env['pos.order'].search([('session_id', '=', self.pos_config.current_session_id.id)], limit=2)
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
        self.pos_config.write({
            'rounding_method': self.cash_rounding_biggest_tax.id,
            'cash_rounding': True,
            'only_round_cash_method': False,
        })
        self.start_pos_tour('test_cash_rounding_halfup_biggest_tax_not_only_round_cash_method_pay_by_bank_and_cash')
        refund, order = self.env['pos.order'].search([('session_id', '=', self.pos_config.current_session_id.id)], limit=2)
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
        self.pos_config.write({
            'rounding_method': self.cash_rounding_biggest_tax.id,
            'cash_rounding': True,
            'only_round_cash_method': True,
        })
        self.start_pos_tour('test_cash_rounding_halfup_biggest_tax_only_round_cash_method')
        refund, order = self.env['pos.order'].search([('session_id', '=', self.pos_config.current_session_id.id)], limit=2)
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
        self.pos_config.write({
            'rounding_method': self.cash_rounding_biggest_tax.id,
            'cash_rounding': True,
            'only_round_cash_method': True,
        })
        self.start_pos_tour('test_cash_rounding_halfup_biggest_tax_only_round_cash_method_pay_by_bank_and_cash')
        refund, order = self.env['pos.order'].search([('session_id', '=', self.pos_config.current_session_id.id)], limit=2)
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
        self.pos_config.write({
            'rounding_method': self.cash_rounding_add_invoice_line.id,
            'cash_rounding': True,
            'only_round_cash_method': False,
        })
        self.start_pos_tour('test_cash_rounding_with_change')
        order = self.env['pos.order'].search([('session_id', '=', self.pos_config.current_session_id.id)], limit=1)
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
        self.pos_config.write({
            'rounding_method': self.cash_rounding_add_invoice_line.id,
            'cash_rounding': True,
            'only_round_cash_method': True,
        })
        self.start_pos_tour('test_cash_rounding_only_cash_method_with_change')
        order = self.env['pos.order'].search([('session_id', '=', self.pos_config.current_session_id.id)], limit=1)
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
