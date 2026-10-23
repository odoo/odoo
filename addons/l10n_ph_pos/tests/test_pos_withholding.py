# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import Command
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

    def test_withholding_on_session_receipt_and_invoice(self):
        """ Each bank payment withholds the share of the withholding of the session closing receipt
        or of the invoice it pays, the share paid in cash staying due. The cashier doing so may have
        no access to accounting. """
        cashier = self.env['res.users'].create({
            'name': 'Cashier',
            'login': 'cashier',
            'group_ids': [Command.set(self.env.ref('point_of_sale.group_pos_user').ids)],
        })
        self.open_new_session()
        self.env['pos.order'].with_user(cashier).sync_from_ui([
            self.create_ui_order_data([(self.product, 1)], payments=[(self.bank_pm1, 1000.0)], customer=self.customer, is_invoiced=True),
            self.create_ui_order_data([(self.product, 1)], payments=[(self.bank_pm1, 1000.0)]),
            self.create_ui_order_data([(self.product, 1)], payments=[(self.cash_pm1, 400.0), (self.bank_pm1, 600.0)]),
        ])
        self.pos_session.with_user(cashier).close_session_from_ui({self.cash_pm1.id: 400.0})

        invoice = self.pos_session.order_ids.account_move
        receipt = self.pos_session.sale_move_ids
        self.assertRecordValues(invoice | receipt, [
            {'amount_residual': 0.0, 'withholding_total_amount_currency': 5.0, 'withholding_residual_amount_currency': 0.0},
            {'amount_residual': 0.0, 'withholding_total_amount_currency': 10.0, 'withholding_residual_amount_currency': 2.0},
        ])
        self.assertRecordValues(invoice.matched_payment_ids | receipt.matched_payment_ids, [
            {'partner_id': self.customer.id, 'withhold': 'withhold_pay', 'amount': 1000.0, 'withholding_amount': 5.0, 'withholding_net_amount': 995.0},
            {'partner_id': self.config.default_partner_id.id, 'withhold': 'withhold_pay', 'amount': 1600.0, 'withholding_amount': 8.0, 'withholding_net_amount': 1592.0},
        ])
        withholding_account = self.withholding_tax.invoice_repartition_line_ids.filtered(lambda rep: rep.repartition_type == 'tax').account_id
        self.assertRecordValues(receipt.matched_payment_ids.move_id.line_ids.sorted('balance'), [
            {'account_id': self.config.default_partner_id.property_account_receivable_id.id, 'balance': -1600.0, 'tax_line_id': False},
            {'account_id': self.sales_account.id, 'balance': -1600.0, 'tax_line_id': False},
            {'account_id': withholding_account.id, 'balance': 8.0, 'tax_line_id': self.withholding_tax.id},
            {'account_id': self.outstanding_bank.id, 'balance': 1592.0, 'tax_line_id': False},
            {'account_id': self.sales_account.id, 'balance': 1600.0, 'tax_line_id': False},
        ])
        self.assertTrue(all(receipt.matched_payment_ids.move_id.line_ids.filtered(lambda line: line.tax_line_id or line.tax_ids).mapped('tax_tag_ids')))

    def test_withholding_split_between_bank_payment_methods(self):
        """ The example of the spec: a 935.00 product with 12% VAT and 10% WI516, paid 1047.20 by
        card. The withholding is computed on the untaxed amount, and the shares of the bank payments
        add up to the full withholding, whatever their rounding. """
        ChartTemplate = self.env['account.chart.template']
        taxes = ChartTemplate.ref('l10n_ph_tax_sale_12') | ChartTemplate.ref('l10n_ph_tax_sale_10_wi516')
        product = self.create_product('Product VAT', self.categ_basic, 935.0, tax_ids=taxes.ids)
        self.open_new_session()
        self._create_orders([
            {'pos_order_lines_ui_args': [(product, 1)], 'payments': [(self.bank_pm1, 349.07), (self.bank_split_pm1, 698.13)]},
        ])
        self.pos_session.close_session_from_ui()

        receipt = self.pos_session.sale_move_ids
        self.assertRecordValues(receipt, [{'amount_residual': 0.0, 'withholding_total_amount_currency': 93.5, 'withholding_residual_amount_currency': 0.0}])
        self.assertRecordValues(receipt.matched_payment_ids.sorted('amount'), [
            {'amount': 349.07, 'withholding_amount': 31.17},
            {'amount': 698.13, 'withholding_amount': 62.33},
        ])

    def test_withholding_requires_outstanding_account(self):
        self.bank_pm1.outstanding_account_id = False
        self.open_new_session()
        with self.assertRaisesRegex(UserError, "Outstanding account is not set"):
            self._create_orders([
                {'pos_order_lines_ui_args': [(self.product, 1)], 'payments': [(self.bank_pm1, 1000.0)], 'customer': self.customer, 'is_invoiced': True},
            ])
