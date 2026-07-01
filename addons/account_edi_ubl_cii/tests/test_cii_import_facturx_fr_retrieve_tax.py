from odoo.addons.account_edi_ubl_cii.tests.test_cii_import_facturx_fr import CiiImportFacturXFR
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestCiiImportFacturXFRRetrieveTax(CiiImportFacturXFR):

    def test_partial_import_tax_manual_tax_amounts(self):
        # Fail to retrieve the tax.
        tax_ids = self.env['account.tax'].search([('amount_type', '=', 'percent'), ('amount', '=', 20)])
        tax_ids.unlink()
        invoice = self._import_invoice_as_attachment_on(
            test_name='test_partial_import_tax_manual_tax_amounts',
            journal=self.company_data['default_journal_sale'],
        )
        self.assertRecordValues(
            invoice.invoice_line_ids,
            [
                {
                    'quantity': 1.0,
                    'price_unit': 500.0,
                    'tax_ids': [],
                },
                {
                    'quantity': 1.0,
                    'price_unit': 500.0,
                    'tax_ids': [],
                },
            ],
        )
        self.assertRecordValues(
            invoice,
            [
                {
                    'amount_untaxed': 1000.0,
                    'amount_tax': 0.0,
                    'amount_total': 1000.0,
                },
            ],
        )

        # Lines are linked to a single tax, the tax amount has been fixed
        tax_20 = self.percent_tax(20.0)
        invoice = self._import_invoice_as_attachment_on(
            test_name='test_partial_import_tax_manual_tax_amounts',
            journal=self.company_data['default_journal_sale'],
        )
        self.assertRecordValues(
            invoice.invoice_line_ids,
            [
                {
                    'quantity': 1.0,
                    'price_unit': 500.0,
                    'tax_ids': tax_20.ids,
                },
                {
                    'quantity': 1.0,
                    'price_unit': 500.0,
                    'tax_ids': tax_20.ids,
                },
            ],
        )
        self.assertRecordValues(
            invoice,
            [
                {
                    'amount_untaxed': 1000.0,
                    'amount_tax': 200.0,
                    'amount_total': 1200.0,
                },
            ],
        )

    def test_partial_import_tax_charge_to_fixed_tax(self):
        tax_20 = self.percent_tax(20.0)

        # Fail to retrieve the tax.
        invoice = self._import_invoice_as_attachment_on(
            test_name='test_partial_import_tax_charge_to_fixed_tax',
            journal=self.company_data['default_journal_sale'],
        )
        self.assertRecordValues(
            invoice.invoice_line_ids,
            [
                {
                    'quantity': 5.0,
                    'price_unit': 200.0,
                    'discount': 0.0,
                    'tax_ids': tax_20.ids,
                },
            ],
        )
        self.assertRecordValues(
            invoice,
            [
                {
                    'amount_untaxed': 1000.0,
                    'amount_tax': 200.0,
                    'amount_total': 1200.0,
                },
            ],
        )

        # Lines are linked to a single tax, the tax amount has been fixed
        recupel = self.fixed_tax(1.0, name='RECUPEL', include_base_amount=True, sequence=0)
        invoice = self._import_invoice_as_attachment_on(
            test_name='test_partial_import_tax_charge_to_fixed_tax',
            journal=self.company_data['default_journal_sale'],
        )
        self.assertRecordValues(
            invoice.invoice_line_ids,
            [
                {
                    'quantity': 5.0,
                    'price_unit': 199.0,
                    'discount': 0.0,
                    'tax_ids': (recupel + tax_20).ids,
                },
            ],
        )
        self.assertRecordValues(
            invoice,
            [
                {
                    'amount_untaxed': 995.0,
                    'amount_tax': 205.0,
                    'amount_total': 1200.0,
                },
            ],
        )
