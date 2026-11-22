# Part of Odoo. See LICENSE file for full copyright and licensing details.
from unittest.mock import patch

from odoo import Command
from odoo.tests import tagged

from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon

# Orders mixing sale lines (positive quantity) and refund lines (negative quantity).
# Sale product: 10.04 + 15% tax, refund product: 2.36 + 15% tax, taxes rounded globally.
#
# Rules checked:
# - Refund lines are rounded apart from sale lines: the sale tax 1.506 and the refund tax -0.354
#   are rounded separately (1.51 and -0.35), not together (1.152 -> 1.15).
# - The order is a refund when its total is negative.
# - The cash rounding goes the other way for a negative total (UP rounds a refund toward zero).
#
# Keep the scenarios in sync with mixed_sale_refund_tour.js and mixed_sale_refund.test.js.
EXPECTED = {
    'net_positive': {
        'is_refund': False,
        'amount_total': 8.84,
        'amount_tax': 1.16,
        'lines': [11.55, -2.71],
        'payment_amount': 8.84,
        'payment_amount_cash_rounding_up': 8.85,
    },
    'net_negative': {
        'is_refund': True,
        'amount_total': -4.73,
        'amount_tax': -0.61,
        'lines': [11.55, -16.28],
        'payment_amount': -4.73,
        'payment_amount_cash_rounding_up': -4.70,
    },
    'pure_refund': {
        'is_refund': True,
        'amount_total': -16.28,
        'amount_tax': -2.12,
        'lines': [-16.28],
        'payment_amount': -16.28,
        'payment_amount_cash_rounding_up': -16.25,
    },
}


@tagged('post_install', '-at_install')
class TestMixedSaleRefund(TestPointOfSaleHttpCommon):
    _test_user_groups = None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.main_pos_config.company_id.tax_calculation_rounding_method = 'round_globally'
        tax_15 = cls.env['account.tax'].create({
            'name': 'Mixed 15%',
            'amount': 15,
            'amount_type': 'percent',
            'type_tax_use': 'sale',
            'price_include_override': 'tax_excluded',
            'company_id': cls.main_pos_config.company_id.id,
        })
        product_vals = {
            'available_in_pos': True,
            'taxes_id': [Command.set(tax_15.ids)],
            'pos_categ_ids': [Command.set(cls.pos_desk_misc_test.ids)],
        }
        cls.env['product.product'].create([
            {**product_vals, 'name': 'Mixed Sale Product', 'list_price': 10.04},
            {**product_vals, 'name': 'Mixed Refund Product', 'list_price': 2.36},
        ])
        cls.cash_rounding_up = cls.env['account.cash.rounding'].create({
            'name': 'Mixed rounding UP',
            'rounding': 0.05,
            'rounding_method': 'UP',
            'strategy': 'add_invoice_line',
            'profit_account_id': cls.env.company.default_cash_difference_income_account_id.id,
            'loss_account_id': cls.env.company.default_cash_difference_expense_account_id.id,
        })

    def _run_tour(self):
        received = []

        def get_mixed_sale_refund_frontend_data(self, frontend_data):
            received.extend(frontend_data)

        with patch.object(
            self.env.registry['pos.order'],
            'get_mixed_sale_refund_frontend_data',
            get_mixed_sale_refund_frontend_data,
            create=True,
        ):
            self.start_pos_tour('test_mixed_sale_refund')

        self.assertEqual([data['name'] for data in received], list(EXPECTED))
        return received

    def assertAmount(self, currency, value, expected, msg=None):
        self.assertTrue(currency.compare_amounts(value, expected) == 0, msg or f"{value} != {expected}")

    def _get_backend_base_lines(self, order):
        """ Base lines of the order totals, with the real signed quantities. """
        AccountTax = self.env['account.tax']
        base_lines = order.lines.with_context(pos_move_type='out_invoice')._prepare_base_lines_for_taxes_computation()
        AccountTax._add_tax_details_in_base_lines(base_lines, order.company_id)
        AccountTax._round_base_lines_tax_details(base_lines, order.company_id)
        return {base_line['record'].uuid: base_line for base_line in base_lines}

    def _check_scenarios(self, received, payment_key):
        for frontend in received:
            expected = EXPECTED[frontend['name']]
            order = self.env['pos.order'].search([('uuid', '=', frontend['uuid'])])
            currency = order.currency_id

            with self.subTest(scenario=frontend['name']):
                self.assertEqual(order.state, 'paid', "The backend must accept the payment computed by the frontend")

                # Backend == frontend
                self.assertEqual(order.is_refund, frontend['is_refund'])
                self.assertAmount(currency, order.amount_total, frontend['amount_total'], "amount_total")
                self.assertAmount(currency, order.amount_tax, frontend['amount_tax'], "amount_tax")
                self.assertAmount(currency, order._get_rounded_amount(order.amount_total), frontend['total_due'], "total due")
                self.assertAmount(currency, order.amount_paid, frontend['payment_amount'], "amount_paid")
                self.assertAmount(currency, frontend['remaining_due'], 0.0, "remaining due after payment")

                base_lines = self._get_backend_base_lines(order)
                for frontend_line in frontend['lines']:
                    base_line = base_lines[frontend_line['uuid']]
                    tax_details = base_line['tax_details']
                    self.assertEqual(base_line['is_refund'], frontend_line['is_refund'])
                    self.assertAmount(currency, tax_details['total_excluded_currency'], frontend_line['price_subtotal'], "line price_subtotal")
                    self.assertAmount(currency, tax_details['total_included_currency'], frontend_line['price_subtotal_incl'], "line price_subtotal_incl")

                # Expected values
                self.assertEqual(order.is_refund, expected['is_refund'])
                self.assertAmount(currency, order.amount_total, expected['amount_total'], "expected amount_total")
                self.assertAmount(currency, order.amount_tax, expected['amount_tax'], "expected amount_tax")
                self.assertAmount(currency, order.amount_paid, expected[payment_key], "expected amount_paid")
                for frontend_line, expected_line in zip(frontend['lines'], expected['lines'], strict=True):
                    self.assertAmount(currency, frontend_line['price_subtotal_incl'], expected_line, "expected line total")

                # The invoice is balanced and goes in the direction of the order
                order.partner_id = self.partner_a
                move = self.env['account.move'].browse(order.action_pos_order_invoice()['res_id'])
                self.assertEqual(move.state, 'posted')
                self.assertEqual(move.move_type, 'out_refund' if order.is_refund else 'out_invoice')
                self.assertAmount(currency, sum(move.line_ids.mapped('debit')), sum(move.line_ids.mapped('credit')), "balanced invoice")
                self.assertAmount(currency, move.amount_total, abs(order.amount_paid), "invoice total")

    def test_mixed_sale_refund(self):
        self.main_pos_config.with_user(self.pos_user).open_ui()
        received = self._run_tour()
        self._check_scenarios(received, 'payment_amount')

    def test_mixed_sale_refund_cash_rounding_up(self):
        self.main_pos_config.write({
            'cash_rounding': True,
            'only_round_cash_method': False,
            'rounding_method': self.cash_rounding_up.id,
        })
        self.main_pos_config.with_user(self.pos_user).open_ui()
        received = self._run_tour()
        self._check_scenarios(received, 'payment_amount_cash_rounding_up')
