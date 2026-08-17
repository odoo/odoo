# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests import tagged

from odoo.addons.l10n_ph.tests.common import TestPhCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestCasInvoiceReport(TestPhCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.ensure_installed('l10n_ph_reports')  # provides `l10n_ph_is_vat_registered`
        cls.company_data['company'].l10n_ph_is_vat_registered = True
        chart_template = cls.env['account.chart.template'].with_company(cls.company_data['company'])
        cls.tax_vatable = chart_template.ref('l10n_ph_tax_sale_12')
        cls.tax_zero_rated = chart_template.ref('l10n_ph_tax_sale_0_zr')
        cls.tax_vat_exempt = chart_template.ref('l10n_ph_tax_sale_0_exempt')
        cls.tax_withholding = chart_template.ref('l10n_ph_tax_sale_10_wi011')
        cls.tax_percentage = chart_template.ref('l10n_ph_tax_sale_3_pt010')

    def _render(self, invoice, report='account.report_invoice'):
        html, _ = self.env['ir.actions.report']._render_qweb_html(report, invoice.ids)
        return html.decode()

    def test_commercial_invoice_uses_the_standard_document(self):
        invoice = self._create_invoice(
            partner_id=self.partner_a,
            invoice_line_ids=[self._prepare_invoice_line(product_id=self.product_a, tax_ids=self.tax_vatable)],
        )
        html = self._render(invoice, report='l10n_ph.report_commercial_invoice')
        self.assertNotIn('Total Amount Due', html)
        self.assertNotIn('VATable Sales', html)

    def test_invoice_report_selection(self):
        invoice = self._create_invoice(
            partner_id=self.partner_a,
            invoice_line_ids=[self._prepare_invoice_line(product_id=self.product_a, tax_ids=self.tax_vatable)],
        )
        self.assertEqual(invoice._get_name_invoice_report(), 'l10n_ph.report_invoice_document')
        credit_note = self._create_invoice(
            move_type='out_refund',
            partner_id=self.partner_a,
            invoice_line_ids=[self._prepare_invoice_line(product_id=self.product_a, tax_ids=self.tax_vatable)],
        )
        self.assertEqual(credit_note._get_name_invoice_report(), 'account.report_invoice_document')

    def test_company_vat_registration_label(self):
        invoice = self._create_invoice(
            partner_id=self.partner_a,
            post=True,
            invoice_line_ids=[self._prepare_invoice_line(product_id=self.product_a, tax_ids=self.tax_vatable)],
        )
        html = self._render(invoice)
        self.assertIn('VAT REG TIN', html)
        self.assertNotIn('NON VAT REG TIN', html)

        self.company_data['company'].l10n_ph_is_vat_registered = False
        self.assertIn('NON VAT REG TIN', self._render(invoice))

    def test_mixed_invoice(self):
        invoice = self._create_invoice(
            partner_id=self.partner_a,
            post=True,
            invoice_line_ids=[
                self._prepare_invoice_line(product_id=self.product_a, tax_ids=self.tax_vatable),
                self._prepare_invoice_line(product_id=self.product_b, tax_ids=self.tax_zero_rated),
                self._prepare_invoice_line(product_id=self.product_a, tax_ids=self.tax_vat_exempt),
            ],
        )
        self.assertEqual(invoice._l10n_ph_cas_get_invoice_report_values()['category'], 'mixed')
        html = self._render(invoice)
        self.assertIn('VATable Sales', html)
        self.assertIn('Total Sales (VAT-Inclusive)', html)
        self.assertIn('Add: VAT', html)

    def test_vat_exempt_invoice(self):
        invoice = self._create_invoice(
            partner_id=self.partner_a,
            post=True,
            invoice_line_ids=[
                self._prepare_invoice_line(product_id=self.product_a, tax_ids=self.tax_vat_exempt),
                self._prepare_invoice_line(product_id=self.product_b, tax_ids=self.tax_vat_exempt + self.tax_withholding),
            ],
        )
        self.assertEqual(invoice._l10n_ph_cas_get_invoice_report_values()['category'], 'vat_exempt')
        html = self._render(invoice)
        self.assertIn('VAT-EXEMPT SALES', html)
        self.assertIn('NOT VALID FOR CLAIM', html)
        self.assertIn('Less: Withholding Tax', html)
        self.assertNotIn('VAT-Inclusive', html)
        self.assertNotIn('Net of VAT', html)

    def test_zero_rated_invoice(self):
        invoice = self._create_invoice(
            partner_id=self.partner_a,
            post=True,
            invoice_line_ids=[self._prepare_invoice_line(product_id=self.product_a, tax_ids=self.tax_zero_rated)],
        )
        self.assertEqual(invoice._l10n_ph_cas_get_invoice_report_values()['category'], 'zero_rated')
        html = self._render(invoice)
        self.assertIn('ZERO-RATED SALES', html)
        self.assertNotIn('NOT VALID FOR CLAIM', html)
        # No 12% on the invoice: the VAT rows are reserved for mixed and pure VAT sales
        self.assertNotIn('Amount: Net of VAT', html)
        self.assertNotIn('Add: VAT', html)
        self.assertNotIn('VAT-Inclusive', html)

    def test_non_vat_invoice(self):
        self.company_data['company'].l10n_ph_is_vat_registered = False
        invoice = self._create_invoice(
            partner_id=self.partner_a,
            post=True,
            invoice_line_ids=[
                self._prepare_invoice_line(product_id=self.product_a, tax_ids=self.tax_vat_exempt),
                self._prepare_invoice_line(product_id=self.product_b, tax_ids=self.tax_percentage),
            ],
        )
        self.assertEqual(invoice._l10n_ph_cas_get_invoice_report_values()['category'], 'non_vat')
        html = self._render(invoice)
        self.assertIn('Sales Subject to Percentage Tax', html)
        self.assertIn('NOT VALID FOR CLAIM', html)
        self.assertIn('Total Sales', html)
        self.assertNotIn('VAT-Inclusive', html)
        self.assertNotIn('Net of VAT', html)
        self.assertNotIn('Add: VAT', html)
        self.assertNotIn('name="th_taxes"', html)

    def test_reprint_marker(self):
        invoice = self._create_invoice(
            partner_id=self.partner_a,
            post=True,
            invoice_line_ids=[self._prepare_invoice_line(product_id=self.product_a, tax_ids=self.tax_vatable)],
        )
        self.assertNotIn('REPRINT', self._render(invoice))
        self.assertIn('REPRINT', self._render(invoice, report='l10n_ph.report_invoice_reprint'))

    def test_withholding_affects_total_due(self):
        invoice = self._create_invoice(
            partner_id=self.partner_a,
            post=True,
            invoice_line_ids=[self._prepare_invoice_line(
                product_id=self.product_a, tax_ids=self.tax_vatable + self.tax_withholding,
                price_unit=100.0, discount=10.0,
            )],
        )
        html = self._render(invoice)
        self.assertNotIn('Less: Discount', html)
        self.assertIn('Less: Withholding Tax', html)
        expected_total_due = self.env['ir.qweb.field.monetary'].value_to_html(
            invoice.withholding_net_residual_amount_currency, {'display_currency': invoice.currency_id},
        )
        self.assertIn(expected_total_due, html)
