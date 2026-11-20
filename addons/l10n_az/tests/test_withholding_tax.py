from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestAzWithholdingTax(AccountTestInvoicingCommon):
    chart_template = 'az'
    country_code = 'AZ'

    def test_gross_withholding_flow(self):
        """ Paying a bill with a gross withholding tax books it as Dr 52192 expense / Cr 52190 payable,
        without touching the vendor payable.
        """
        chart_template = self.env['account.chart.template'].with_company(self.env.company)
        tax = chart_template.ref('az_tax_wht_ins_4_g')
        bill = self.init_invoice('in_invoice', amounts=[100], taxes=tax, invoice_date='2024-01-15', post=True)

        payable_lines = bill.line_ids.filtered(lambda line: line.account_id.account_type == 'liability_payable')
        self.assertEqual(payable_lines.mapped('balance'), [-100.0])

        self._register_payment(bill, payment_date='2024-01-20')
        self.assertEqual(bill.payment_state, bill._get_invoice_in_payment_state())

        caba_move = self.env['account.move'].search([('tax_cash_basis_origin_move_id', '=', bill.id)])
        self.assertEqual(len(caba_move), 1)
        expense_line = caba_move.line_ids.filtered(lambda line: line.account_id.code == '52192')
        payable_line = caba_move.line_ids.filtered(lambda line: line.account_id.code == '52190')
        # Grossed up: the vendor receives 100, so the 4% is due on 100 / 0.96 = 104.17.
        self.assertRecordValues(expense_line + payable_line, [
            {'balance': 4.17, 'tax_tag_ids': []},
            {'balance': -4.17, 'tax_tag_ids': self.env.ref('l10n_az.az_tag_1_t_w_g').ids},
        ])
        base_tags = (caba_move.line_ids - expense_line - payable_line).tax_tag_ids
        self.assertIn('1(B)_W_G', base_tags.mapped('name'))
