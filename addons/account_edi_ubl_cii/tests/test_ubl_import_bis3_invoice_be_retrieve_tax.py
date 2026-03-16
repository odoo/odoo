from odoo.addons.account_edi_ubl_cii.tests.test_ubl_import_bis3_invoice_be import TestUblImportBis3InvoiceBE
from odoo.tests import tagged

from freezegun import freeze_time


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestUblImportBis3InvoiceBERetrieveTax(TestUblImportBis3InvoiceBE):

    def test_partial_import_tax_fixed_tax_amounts(self):
        # Fail to retrieve the tax.
        invoice = self._import_invoice_as_attachment_on(
            test_name='test_partial_import_tax_fixed_tax_amounts',
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
        tax_21 = self.percent_tax(21.0)
        invoice = self._import_invoice_as_attachment_on(
            test_name='test_partial_import_tax_fixed_tax_amounts',
            journal=self.company_data['default_journal_sale'],
        )
        self.assertRecordValues(
            invoice.invoice_line_ids,
            [
                {
                    'quantity': 1.0,
                    'price_unit': 500.0,
                    'tax_ids': tax_21.ids,
                },
                {
                    'quantity': 1.0,
                    'price_unit': 500.0,
                    'tax_ids': tax_21.ids,
                },
            ],
        )
        self.assertRecordValues(
            invoice,
            [
                {
                    'amount_untaxed': 1000.0,
                    'amount_tax': 210.01,
                    'amount_total': 1210.01,
                },
            ],
        )

    @freeze_time('2020-01-01')
    def test_partial_import_tax_fixed_tax_amounts_invoice_predictive(self):
        self.ensure_installed('account_accountant')

        tax_21_1 = self.percent_tax(21.0)
        tax_21_2 = self.percent_tax(21.0)

        # First invoice to train the prediction.
        self._create_invoice(
            partner_id=self.partner_be,
            invoice_line_ids=[
                self._prepare_invoice_line(name="turltututu", price_unit=500.0, tax_ids=tax_21_1),
                self._prepare_invoice_line(name="tsointsoin", price_unit=500.0, tax_ids=tax_21_2),
            ],
            post=True,
        )

        # Check the prediction.
        invoice = self._import_invoice_as_attachment_on(
            test_name='test_partial_import_tax_fixed_tax_amounts',
            journal=self.company_data['default_journal_sale'],
        )
        self.assertRecordValues(
            invoice.invoice_line_ids,
            [
                {
                    'quantity': 1.0,
                    'price_unit': 500.0,
                    'tax_ids': tax_21_1.ids,
                },
                {
                    'quantity': 1.0,
                    'price_unit': 500.0,
                    'tax_ids': tax_21_2.ids,
                },
            ],
        )
        self.assertRecordValues(
            invoice,
            [
                {
                    'partner_id': self.partner_be.id,
                    'amount_untaxed': 1000.0,
                    'amount_tax': 210.01,
                    'amount_total': 1210.01,
                },
            ],
        )
