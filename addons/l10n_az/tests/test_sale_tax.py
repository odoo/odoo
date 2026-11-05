from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestAzSaleTax(AccountTestInvoicingCommon):
    chart_template = 'az'
    country_code = 'AZ'

    def test_default_sale_tax_cash_basis_flow(self):
        """ The 18% group defers the 1(B)/1(T) grids to payment time while 9(B) fires at invoice time. """
        chart_template = self.env['account.chart.template'].with_company(self.env.company)
        group_tax = chart_template.ref('az_tax_sale_vat_18_group')
        self.assertEqual(self.env.company.account_sale_tax_id, group_tax)
        self.assertEqual(group_tax.amount_type, 'group')
        self.assertEqual(
            group_tax.children_tax_ids,
            chart_template.ref('az_tax_sale_vat_18') + chart_template.ref('az_tax_sale_vat_18_r'),
        )

        invoice = self.init_invoice('out_invoice', amounts=[1000], taxes=group_tax, invoice_date='2024-01-15', post=True)
        base_line = invoice.invoice_line_ids
        self.assertIn('9(B)', base_line.tax_tag_ids.mapped('name'))
        self.assertNotIn('1(B)', base_line.tax_tag_ids.mapped('name'))
        tax_line = invoice.line_ids.filtered('tax_line_id')
        self.assertEqual(tax_line.account_id.code, '52120')
        self.assertEqual(tax_line.balance, -180.0)
        self.assertFalse(tax_line.tax_tag_ids)
        receivable_line = invoice.line_ids.filtered(lambda line: line.account_id.account_type == 'asset_receivable')
        self.assertEqual(receivable_line.account_id.code, '21100')
        self.assertEqual(receivable_line.balance, 1180.0)

        self.env['account.payment.register'].with_context(
            active_model='account.move', active_ids=invoice.ids,
        ).create({'payment_date': '2024-01-20'})._create_payments()
        self.assertEqual(invoice.payment_state, invoice._get_invoice_in_payment_state())

        caba_move = self.env['account.move'].search([('tax_cash_basis_origin_move_id', '=', invoice.id)])
        self.assertEqual(len(caba_move), 1)
        transition_line = caba_move.line_ids.filtered(lambda line: line.account_id.code == '52120')
        self.assertEqual(transition_line.balance, 180.0)
        final_tax_line = caba_move.line_ids.filtered(lambda line: line.account_id.code == '52110')
        self.assertEqual(final_tax_line.balance, -180.0)
        self.assertEqual(final_tax_line.tax_tag_ids.mapped('name'), ['1(T)'])
        caba_base_lines = caba_move.line_ids.filtered(lambda line: '1(B)' in line.tax_tag_ids.mapped('name'))
        self.assertTrue(caba_base_lines)
        self.assertEqual({abs(line.balance) for line in caba_base_lines}, {1000.0})
