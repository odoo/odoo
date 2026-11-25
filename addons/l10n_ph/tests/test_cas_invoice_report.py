# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests import tagged

from odoo.addons.l10n_ph.tests.common import TestPhCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestCasInvoiceReport(TestPhCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_data['company'].l10n_ph_is_vat_registered = True
        chart_template = cls.env['account.chart.template'].with_company(cls.company_data['company'])
        cls.tax_vatable = chart_template.ref('l10n_ph_tax_sale_12')
        cls.tax_zero_rated = chart_template.ref('l10n_ph_tax_sale_0_zr')
        cls.tax_vat_exempt = chart_template.ref('l10n_ph_tax_sale_0_exempt')
        cls.tax_withholding = chart_template.ref('l10n_ph_tax_sale_10_wi011')
        cls.tax_percentage = chart_template.ref('l10n_ph_tax_sale_3_pt010')

    def assertTitle(self, html, title):
        self.assertRegex(html, rf'<span class="text-uppercase fs-1">\s*{title}\s*</span>')

    def test_commercial_invoice_uses_the_standard_document(self):
        invoice = self._create_invoice(
            partner_id=self.partner_a,
            post=True,
            invoice_line_ids=[self._prepare_invoice_line(product_id=self.product_a, tax_ids=self.tax_vatable)],
        )
        self._register_payment(invoice)
        html = self._render(invoice, report='l10n_ph.report_commercial_invoice')
        self.assertIn('Paid on', html)
        self.assertNotIn('Sold To:', html)
        self.assertNotIn('Total Amount Due', html)
        self.assertNotIn('VATable Sales', html)

    def test_pdf_without_payment_uses_the_standard_document(self):
        invoice = self._create_invoice(
            partner_id=self.partner_a,
            post=True,
            invoice_line_ids=[self._prepare_invoice_line(product_id=self.product_a, tax_ids=self.tax_vatable)],
        )
        self._register_payment(invoice)
        credit_note = self._reverse_invoice(invoice, post=True)
        for move in invoice + credit_note:
            with self.subTest(move_type=move.move_type):
                self.assertIn('Total Amount Due', self._render(move))
                html = self._render(move, report='account.report_invoice')
                self.assertNotIn('Paid on', html)
                self.assertNotIn('Sold To:', html)
                self.assertNotIn('Billed To:', html)
                self.assertNotIn('Total Amount Due', html)
                self.assertNotIn('text-uppercase fs-1', html)

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
        self.assertEqual(credit_note._get_name_invoice_report(), 'l10n_ph.report_invoice_document')
        vendor_credit_note = self._create_invoice(
            move_type='in_refund',
            partner_id=self.partner_a,
            invoice_line_ids=[self._prepare_invoice_line(product_id=self.product_a)],
        )
        self.assertEqual(vendor_credit_note._get_name_invoice_report(), 'account.report_invoice_document')

    def test_company_vat_registration_label(self):
        invoice = self._create_invoice(
            partner_id=self.partner_a,
            post=True,
            invoice_line_ids=[self._prepare_invoice_line(product_id=self.product_a, tax_ids=self.tax_vatable)],
        )
        html = self._render(invoice)
        self.assertIn('Sold To:', html)
        self.assertNotIn('Billed To:', html)
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
        self.assertIn('Gross Sales', html)
        self.assertIn('Add: VAT', html)
        self.assertNotIn('VAT-Inclusive', html)

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
        self.assertIn('Gross Sales', html)
        self.assertIn('Less: Withholding Tax', html)
        self.assertNotIn('Add: VAT', html)

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
        self.assertIn('Gross Sales', html)
        self.assertNotIn('Add: VAT', html)

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
        self.assertIn('Gross Sales', html)
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

        # The total due is the invoiced amount: it is left untouched by a credit note or a payment
        self._reverse_invoice(invoice, post=True)
        self.assertIn(expected_total_due, self._render(invoice))

    def test_credit_note_layout(self):
        invoice = self._create_invoice(
            partner_id=self.partner_a,
            post=True,
            invoice_line_ids=[self._prepare_invoice_line(
                product_id=self.product_a, tax_ids=self.tax_vatable + self.tax_withholding, price_unit=100.0,
            )],
        )
        credit_note = self._reverse_invoice(invoice)
        self.assertTitle(self._render(credit_note), 'Draft Credit Note')

        credit_note.action_post()
        html = self._render(credit_note)
        self.assertTitle(html, 'Credit Note')
        self.assertIn('Billed To:', html)
        self.assertNotIn('Sold To:', html)
        self.assertIn('Gross Sales', html)
        self.assertIn('Add: VAT', html)
        self.assertIn('Less: Withholding Tax', html)
        self.assertIn('Total Amount Due', html)
        expected_total_due = self.env['ir.qweb.field.monetary'].value_to_html(
            invoice.amount_total - invoice.withholding_total_amount_currency, {'display_currency': invoice.currency_id},
        )
        self.assertIn(expected_total_due, html)
        self.assertNotIn('REPRINT', html)
        self.assertIn('REPRINT', self._render(credit_note, report='l10n_ph.report_invoice_reprint'))

        # The PDF attached by the Send wizard uses the BIR layout as well
        send_report = self.env['account.move.send']._get_default_pdf_report_id(credit_note)
        send_html = self._render(credit_note, report=send_report.report_name)
        self.assertTitle(send_html, 'Credit Note')
        self.assertIn('Billed To:', send_html)
        self.assertIn('Total Amount Due', send_html)

    def test_vat_exempt_label_in_every_state(self):
        """ The VAT-exempt sales line follows the title in every state, without replacing any title. """
        line_vals = [self._prepare_invoice_line(product_id=self.product_a, tax_ids=self.tax_vat_exempt)]
        for move_type, title in (('out_invoice', 'Invoice'), ('out_refund', 'Credit Note')):
            with self.subTest(move_type=move_type):
                move = self._create_invoice(move_type=move_type, partner_id=self.partner_a, invoice_line_ids=line_vals)
                html = self._render(move)
                self.assertTitle(html, f'Draft {title}')
                self.assertIn('VAT-EXEMPT SALES', html)

                move.action_post()
                html = self._render(move)
                self.assertTitle(html, title)
                self.assertIn('VAT-EXEMPT SALES', html)
                self.assertIn('NOT VALID FOR CLAIM', html)

                move.button_draft()
                move.button_cancel()
                html = self._render(move)
                self.assertTitle(html, f'Cancelled {title}')
                self.assertIn('VAT-EXEMPT SALES', html)
