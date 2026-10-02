# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.point_of_sale.tests.common import TestPoSCommon


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestPosWithholding(TestPoSCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('ph')
    def setUpClass(cls):
        super().setUpClass()
        cls.config = cls.basic_config
        ChartTemplate = cls.env['account.chart.template']
        cls.withholding_tax = ChartTemplate.ref('l10n_ph_tax_sale_0_5_wc830')
        cls.product = cls.create_product('Product', cls.categ_basic, 1000.0, tax_ids=cls.withholding_tax.ids)

    def _close_session(self):
        cash_amount = sum(self.pos_session.order_ids.payment_ids.filtered(lambda p: p.payment_method_id == self.cash_pm1).mapped('amount'))
        self.pos_session.close_session_from_ui({self.cash_pm1.id: cash_amount})
        return self.env['account.move'].search([('pos_session_ids', 'in', self.pos_session.ids), ('move_type', '=', 'out_invoice')])

    def _get_withholding_payments(self, move):
        return self.env['account.payment'].search([('invoice_ids', 'in', move.ids), ('withhold', '=', 'withhold_pay')])

    def _assert_withholding_tax_lines_tagged(self, payments):
        for payment in payments:
            withholding_lines = payment.move_id.line_ids.filtered(lambda line: line.tax_line_id == self.withholding_tax or self.withholding_tax in line.tax_ids)
            self.assertEqual(len(withholding_lines), 2, "the payment should book both the withholding base and tax lines")
            self.assertTrue(all(withholding_lines.mapped('tax_tag_ids')), "the withholding lines must carry the tax grids of the BIR reports")

    def test_session_receipt_withholding_split_between_cash_and_bank(self):
        """ Scenario A of the spec: the session closing receipt (walk-in partner, several orders)
        is paid by card and cash. The bank payment withholds its share of the withholding and
        pays the rest; the share paid in cash can't be withheld and stays due on the receipt. """
        self.open_new_session()
        self._create_orders([
            {'pos_order_lines_ui_args': [(self.product, 1)], 'payments': [(self.bank_pm1, 1000.0)]},
            {'pos_order_lines_ui_args': [(self.product, 1)], 'payments': [(self.cash_pm1, 400.0), (self.bank_pm1, 600.0)]},
        ])
        receipt = self._close_session()

        self.assertEqual(self.pos_session.state, 'closed')
        payment = self._get_withholding_payments(receipt)
        self.assertRecordValues(payment, [{
            'amount': 1600.0,
            'withholding_amount': 8.0,  # 0.5% of the 1600.0 paid by bank
            'withholding_net_amount': 1592.0,
            'outstanding_account_id': self.outstanding_bank.id,
            'partner_id': self.config.default_partner_id.id,
        }])
        self._assert_withholding_tax_lines_tagged(payment)
        self.assertRecordValues(receipt, [{
            'amount_residual': 0.0,
            'withholding_total_amount_currency': 10.0,
            'withholding_residual_amount_currency': 2.0,  # 0.5% of the 400.0 paid in cash
        }])

    def test_session_receipt_withholding_with_vat(self):
        """ The example of the spec: a 935.00 product with 12% VAT and 10% WI516 is paid 1047.20 by
        card, withholding 93.50 on the untaxed amount. """
        ChartTemplate = self.env['account.chart.template']
        self.withholding_tax = ChartTemplate.ref('l10n_ph_tax_sale_10_wi516')
        product = self.create_product('Product VAT', self.categ_basic, 935.0, tax_ids=(ChartTemplate.ref('l10n_ph_tax_sale_12') | self.withholding_tax).ids)
        self.open_new_session()
        self._create_orders([
            {'pos_order_lines_ui_args': [(product, 1)], 'payments': [(self.bank_pm1, 1047.20)]},
        ])
        receipt = self._close_session()

        payment = self._get_withholding_payments(receipt)
        self.assertRecordValues(payment, [{'amount': 1047.20, 'withholding_amount': 93.50, 'withholding_net_amount': 953.70}])
        self._assert_withholding_tax_lines_tagged(payment)
        self.assertRecordValues(receipt, [{'amount_residual': 0.0, 'withholding_residual_amount_currency': 0.0}])

    def test_session_receipt_withholding_split_between_bank_payment_methods(self):
        """ When bank payments pay the whole receipt, their withholding shares add up to exactly the
        full withholding, whatever the rounding of each share. """
        self.product.lst_price = 100.0
        self.open_new_session()
        self._create_orders([
            {'pos_order_lines_ui_args': [(self.product, 1)], 'payments': [(self.bank_pm1, 33.33), (self.bank_split_pm1, 66.67)]},
        ])
        receipt = self._close_session()

        payments = self._get_withholding_payments(receipt)
        self.assertEqual(len(payments), 2)
        self.assertAlmostEqual(sum(payments.mapped('withholding_amount')), 0.5)
        self._assert_withholding_tax_lines_tagged(payments)
        self.assertRecordValues(receipt, [{'amount_residual': 0.0, 'withholding_residual_amount_currency': 0.0}])

    def test_invoiced_order_withholding(self):
        """ An invoiced order is paid with its own payments against its own invoice: the bank
        payment withholds as well, under the customer of the order. """
        self.open_new_session()
        order = next(iter(self._create_orders([
            {'pos_order_lines_ui_args': [(self.product, 1)], 'payments': [(self.bank_pm1, 1000.0)], 'customer': self.customer, 'is_invoiced': True},
        ]).values()))
        invoice = order.account_move

        payment = self._get_withholding_payments(invoice)
        self.assertRecordValues(payment, [{'amount': 1000.0, 'withholding_amount': 5.0, 'partner_id': self.customer.id}])
        self._assert_withholding_tax_lines_tagged(payment)
        self.assertRecordValues(invoice, [{'amount_residual': 0.0, 'withholding_residual_amount_currency': 0.0}])

    def test_withholding_requires_outstanding_account(self):
        self.bank_pm1.outstanding_account_id = False
        self.open_new_session()
        with self.assertRaisesRegex(UserError, "Outstanding account is not set"):
            self._create_orders([
                {'pos_order_lines_ui_args': [(self.product, 1)], 'payments': [(self.bank_pm1, 1000.0)], 'customer': self.customer, 'is_invoiced': True},
            ])
