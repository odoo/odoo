from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestAzWithholdingTax(AccountTestInvoicingCommon):
    chart_template = 'az'
    country_code = 'AZ'

    def test_gross_withholding_flow(self):
        """ Paying a bill with a gross withholding tax books the tax on 52190/52192 without touching the payable. """
        chart_template = self.env['account.chart.template'].with_company(self.env.company)
        tax = chart_template.ref('az_tax_wht_ins_4_g')
        bill = self.init_invoice('in_invoice', amounts=[100], taxes=tax, invoice_date='2024-01-15', post=True)

        payable_lines = bill.line_ids.filtered(lambda line: line.account_id.account_type == 'liability_payable')
        self.assertEqual(payable_lines.mapped('balance'), [-100.0])

        self.env['account.payment.register'].with_context(
            active_model='account.move', active_ids=bill.ids,
        ).create({'payment_date': '2024-01-20'})._create_payments()
        self.assertEqual(bill.payment_state, bill._get_invoice_in_payment_state())

        caba_move = self.env['account.move'].search([('tax_cash_basis_origin_move_id', '=', bill.id)])
        self.assertEqual(len(caba_move), 1)
        plus_leg = caba_move.line_ids.filtered(lambda line: line.account_id.code == '52190')
        minus_leg = caba_move.line_ids.filtered(lambda line: line.account_id.code == '52192')
        self.assertTrue(plus_leg)
        self.assertFalse(plus_leg.tax_tag_ids)
        self.assertTrue(minus_leg)
        self.assertEqual(minus_leg.tax_tag_ids.mapped('name'), ['1(T)_W_G'])
        base_tags = (caba_move.line_ids - plus_leg - minus_leg).tax_tag_ids
        self.assertIn('1(B)_W_G', base_tags.mapped('name'))
