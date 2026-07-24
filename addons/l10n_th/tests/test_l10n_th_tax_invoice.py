from odoo.tests import tagged
from odoo.tools import html2plaintext

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nTHTaxInvoice(AccountTestInvoicingCommon):
    """ Test the Tax Invoice feature for Thailand Accounting """

    @classmethod
    @AccountTestInvoicingCommon.setup_country('th')
    def setUpClass(cls):
        super().setUpClass()

        cls.env.company.l10n_th_is_vat_registered = True
        cls.th_company_1_data = cls.setup_other_company()
        cls.th_company_1 = cls.th_company_1_data['company']
        cls.th_company_1.l10n_th_is_vat_registered = True
        cls.env = cls.env(context=dict(cls.env.context, allowed_company_ids=(cls.env.company + cls.th_company_1).ids))

        cls.tax_on_invoice = cls.env['account.tax'].create({
            'name': 'VAT On Invoice',
            'amount_type': 'percent',
            'amount': 7.0,
            'type_tax_use': 'sale',
            'tax_exigibility': 'on_invoice',
        })

        cls.tax_on_payment = cls.env['account.tax'].create({
            'name': 'VAT On Payment',
            'amount_type': 'percent',
            'amount': 7.0,
            'type_tax_use': 'sale',
            'tax_exigibility': 'on_payment',
        })

        cls.invoice = cls._create_invoice(
            move_type='out_invoice',
            invoice_date='2026-08-01',
            partner_id=cls.partner_a.id,
            invoice_line_ids=[],
        )

    def _assert_report_contains(self, tax_invoice, *expected_values):
        """Assert that the rendered report contains all expected values."""

        html = self.env['ir.actions.report']._render_qweb_html('l10n_th.report_tax_invoice', tax_invoice.ids)[0]
        text = html2plaintext(html)

        for value in expected_values:
            self.assertIn(value, text, f"Expected '{value}' to be present in the generated PDF report.")

    def test_tax_invoice_created_for_on_invoice_tax(self):
        """Ensure a tax invoice is created when posting an invoice with on-invoice VAT."""

        self.invoice.invoice_line_ids = [
            self._prepare_invoice_line(
                price_unit=1000,
                tax_ids=self.tax_on_invoice,
            ),
        ]
        self.invoice.action_post()

        tax_invoice = self.invoice.l10n_th_tax_invoice_ids

        self.assertRecordValues(
            self.invoice.l10n_th_tax_invoice_ids,
            [
                {
                    'tax_invoice_number': 'TINV/2026/00001',
                    'invoice_move_id': self.invoice.id,
                    'total_amount': 1070.0,
                    'vat_amount': 70.0,
                    'date': self.invoice.invoice_date,
                    'tax_invoice_lines': [{
                        'name': False,
                        'quantity': 1.0,
                        'product_uom': False,
                        'price_unit': 1000.0,
                        'discount': '',
                        'taxes': 'VAT On Invoice',
                        'total_amount': 1000.0,
                    }],
                },
            ],
        )

        # Ensure that each company generates its own tax invoice sequence.
        invoice = self._create_invoice(
            move_type='out_invoice',
            invoice_date='2026-08-01',
            journal_id=self.th_company_1_data['default_journal_sale'],
            invoice_line_ids=[
                self._prepare_invoice_line(
                    price_unit=1000,
                    tax_ids=self.th_company_1_data['default_tax_sale'],
                ),
            ],
        )
        invoice.action_post()
        self.assertEqual(invoice.l10n_th_tax_invoice_ids.tax_invoice_number, 'TINV/2026/00001')

        self._assert_report_contains(
            tax_invoice,
            tax_invoice.tax_invoice_number,
            'TINV',
            '1,070.00',
            '70.00',
        )

        # Cancelling the Invoice cancels the tax invoice.
        self.invoice.button_cancel()
        self.assertEqual(tax_invoice.state, 'cancel')

    def test_tax_invoice_created_for_full_payment(self):
        """Ensure a tax invoice is created after a full payment for on-payment VAT."""

        self.invoice.invoice_line_ids = [
            self._prepare_invoice_line(
                price_unit=1000,
                tax_ids=self.tax_on_payment,
            ),
        ]
        self.invoice.action_post()

        self._register_payment(
            self.invoice,
            amount=1070.0,
        )

        caba_entry = self.invoice.tax_cash_basis_created_move_ids

        self.assertEqual(
            len(caba_entry),
            1,
            "A cash basis journal entry should be created after the payment is reconciled.",
        )

        tax_invoice = self.invoice.l10n_th_tax_invoice_ids.filtered(
            lambda ti: ti.payment_move_id == caba_entry,
        )

        self.assertRecordValues(
            self.invoice.l10n_th_tax_invoice_ids,
            [
                {
                    'invoice_move_id': self.invoice.id,
                    'payment_move_id': caba_entry.id,
                    'total_amount': 1070.0,
                    'vat_amount': 70.0,
                    'date': caba_entry.date,
                    'reference': caba_entry.name,
                    'amount_residual': 0.0,
                    'tax_invoice_lines': [{
                        'name': False,
                        'quantity': 1.0,
                        'product_uom': False,
                        'price_unit': 1000.0,
                        'discount': '',
                        'taxes': 'VAT On Payment',
                        'total_amount': 1000.0,
                    }],
                },
            ],
        )

        self._assert_report_contains(
            tax_invoice,
            tax_invoice.tax_invoice_number,
            'RCT',
            '1,070.00',
            '70.00',
        )

        # Reverting the CABA move cancels the tax invoice.
        self._reverse_invoice(caba_entry)
        self.assertEqual(tax_invoice.state, 'cancel')

    def test_multiple_partial_payments_create_multiple_tax_invoices(self):
        """Ensure multiple partial payments create separate tax invoices for on-payment VAT."""

        self.invoice.invoice_line_ids = [
            self._prepare_invoice_line(
                price_unit=1000,
                tax_ids=self.tax_on_payment,
            ),
        ]
        self.invoice.action_post()

        self._register_payment(
            self.invoice,
            amount=535.0,
        )

        first_caba_entry = self.invoice.tax_cash_basis_created_move_ids

        self._register_payment(
            self.invoice,
            amount=535.0,
        )

        second_caba_entry = self.invoice.tax_cash_basis_created_move_ids.filtered(
            lambda caba: caba.id != first_caba_entry.id,
        )

        self.assertRecordValues(
            self.invoice.l10n_th_tax_invoice_ids,
            [
                {
                    'invoice_move_id': self.invoice.id,
                    'payment_move_id': first_caba_entry.id,
                    'total_amount': 535.0,
                    'vat_amount': 35.0,
                    'amount_residual': 535.0,
                    'date': first_caba_entry.date,
                    'reference': first_caba_entry.name,
                    'tax_invoice_lines': [{
                        'name': False,
                        'quantity': 1.0,
                        'product_uom': False,
                        'price_unit': 500.0,
                        'discount': '',
                        'taxes': 'VAT On Payment',
                        'total_amount': 500.0,
                    }],
                },
                {
                    'invoice_move_id': self.invoice.id,
                    'payment_move_id': second_caba_entry.id,
                    'total_amount': 535.0,
                    'vat_amount': 35.0,
                    'amount_residual': 0.0,
                    'date': second_caba_entry.date,
                    'reference': second_caba_entry.name,
                    'tax_invoice_lines': [{
                        'name': False,
                        'quantity': 1.0,
                        'product_uom': False,
                        'price_unit': 500.0,
                        'discount': '',
                        'taxes': 'VAT On Payment',
                        'total_amount': 500.0,
                    }],
                },
            ],
        )

        # Changing the non-wht tax on move cancles the tax invoice.
        self.invoice.button_draft()
        self.assertEqual(self.invoice.l10n_th_tax_invoice_ids.mapped('state'), ['draft', 'draft'])
        self.invoice.invoice_line_ids.tax_ids = False
        self.assertEqual(self.invoice.l10n_th_tax_invoice_ids.mapped('state'), ['cancel', 'cancel'])

    def test_tax_invoice_created_for_mixed_tax_exigibility(self):
        """Ensure invoice with mixed tax exigibility creates separate tax invoices with correct amounts."""

        self.invoice.invoice_line_ids = [
            self._prepare_invoice_line(
                price_unit=1000,
                tax_ids=self.tax_on_invoice,
            ),
            self._prepare_invoice_line(
                price_unit=2000,
                tax_ids=self.tax_on_payment,
            ),
        ]

        self.invoice.action_post()

        self._register_payment(
            self.invoice,
            amount=3210.0,
        )

        caba_entry = self.invoice.tax_cash_basis_created_move_ids

        self.assertRecordValues(
            self.invoice.l10n_th_tax_invoice_ids,
            [
                {
                    'invoice_move_id': self.invoice.id,
                    'payment_move_id': False,
                    'total_amount': 1070.0,
                    'vat_amount': 70.0,
                    'date': self.invoice.invoice_date,
                    'reference': False,
                    'tax_invoice_lines': [{
                        'name': False,
                        'quantity': 1.0,
                        'product_uom': False,
                        'price_unit': 1000.0,
                        'discount': '',
                        'taxes': 'VAT On Invoice',
                        'total_amount': 1000.0,
                    }],
                },
                {
                    'invoice_move_id': self.invoice.id,
                    'payment_move_id': caba_entry.id,
                    'total_amount': 2140.0,
                    'vat_amount': 140.0,
                    'date': caba_entry.date,
                    'reference': caba_entry.name,
                    'tax_invoice_lines': [{
                        'name': False,
                        'quantity': 1.0,
                        'product_uom': False,
                        'price_unit': 2000.0,
                        'discount': '',
                        'taxes': 'VAT On Payment',
                        'total_amount': 2000.0,
                    }],
                },
            ],
        )

    def test_no_tax_invoice_created_for_vendor_bill_payment(self):
        """Ensure no tax invoice is created for a vendor bill payment."""

        self.tax_on_payment.type_tax_use = 'purchase'

        self.invoice.move_type = 'in_invoice'
        self.invoice.invoice_line_ids = [
            self._prepare_invoice_line(
                price_unit=1000,
                tax_ids=self.tax_on_payment,
            ),
        ]
        self.invoice.action_post()

        self._register_payment(
            self.invoice,
            amount=1070.0,
        )

        self.assertEqual(
            len(self.invoice.tax_cash_basis_created_move_ids),
            1,
            "A cash basis journal entry should be created after the payment is reconciled.",
        )

        self.assertFalse(
            self.invoice.l10n_th_tax_invoice_ids,
            "No tax invoice should be created for a vendor bill payment.",
        )

    def test_tax_invoice_created_for_group_tax_with_mix_tax_exigibility(self):
        """Ensure an invoice with a complex group tax and mixed tax exigibility creates separate tax invoices with correct amounts."""

        # Use a group tax containing two child taxes:
        # - A 20% sales tax (tax included) with "Based on Invoice" tax exigibility.
        # - A 10% purchase tax (tax excluded) with "Based on Payment" tax exigibility.
        self.invoice.invoice_line_ids = [
            self._prepare_invoice_line(
                price_unit=1000,
                tax_ids=self.tax_armageddon,
            ),
        ]
        self.invoice.action_post()

        self._register_payment(
            self.invoice,
            amount=1300.0,
        )

        caba_entry = self.invoice.tax_cash_basis_created_move_ids

        self.assertEqual(
            len(caba_entry),
            1,
            "A cash basis journal entry should be created after the payment is reconciled.",
        )

        self.assertRecordValues(
            self.invoice.l10n_th_tax_invoice_ids,
            [
                {
                    'invoice_move_id': self.invoice.id,
                    'payment_move_id': False,
                    'total_amount': 1000.0,
                    'vat_amount': 166.67,
                    'date': self.invoice.date,
                    'reference': False,
                    'tax_invoice_lines': [{
                        'name': False,
                        'quantity': 1.0,
                        'product_uom': False,
                        'price_unit': 1000.0,
                        'discount': '',
                        'taxes': 'complex_tax (group)',
                        'total_amount': 833.33,
                    }],
                },
                {
                    'invoice_move_id': self.invoice.id,
                    'payment_move_id': caba_entry.id,
                    'total_amount': 1100.0,
                    'vat_amount': 100.0,
                    'date': caba_entry.date,
                    'reference': caba_entry.name,
                    'tax_invoice_lines': [{
                        'name': False,
                        'quantity': 1.0,
                        'product_uom': False,
                        'price_unit': 1000.0,
                        'discount': '',
                        'taxes': 'complex_tax (group)',
                        'total_amount': 833.33,
                    }],
                },
            ],
        )

    def test_tax_invoice_totals_reconcile_for_price_included_compounding_group_tax(self):
        """
        Ensure the tax invoice totals stay reconciled with the document total when a price-included
        group tax has its children applied sequentially (the second child's base includes the first
        child's tax).
        """
        self.tax_armageddon.children_tax_ids.filtered(
            lambda t: t.tax_exigibility == 'on_payment',
        ).price_include_override = 'tax_included'

        self.invoice.invoice_line_ids = [
            self._prepare_invoice_line(
                price_unit=1000,
                tax_ids=self.tax_armageddon,
            ),
        ]
        self.invoice.action_post()

        self._register_payment(
            self.invoice,
            amount=1000.0,
        )

        self.assertRecordValues(
            self.invoice.l10n_th_tax_invoice_ids,
            [
                {
                    'total_amount': 909.09,
                    'vat_amount': 151.52,
                    'tax_invoice_lines': [{
                        'name': False,
                        'quantity': 1.0,
                        'product_uom': False,
                        'price_unit': 1000.0,
                        'discount': '',
                        'taxes': 'complex_tax (group)',
                        'total_amount': 757.57,
                    }],
                },
                {
                    'total_amount': 1000.00,
                    'vat_amount': 90.91,
                    'tax_invoice_lines': [{
                        'name': False,
                        'quantity': 1.0,
                        'product_uom': False,
                        'price_unit': 1000.0,
                        'discount': '',
                        'taxes': 'complex_tax (group)',
                        'total_amount': 757.57,
                    }],
                },
            ],
        )
