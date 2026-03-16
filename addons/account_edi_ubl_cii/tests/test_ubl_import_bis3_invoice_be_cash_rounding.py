from odoo.addons.account_edi_ubl_cii.tests.test_ubl_import_bis3_invoice_be import TestUblImportBis3InvoiceBE
from odoo.tests import tagged

from freezegun import freeze_time


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestUblImportBis3InvoiceBECashRounding(TestUblImportBis3InvoiceBE):

    @freeze_time('2020-01-01')
    def test_import_cash_rounding_add_invoice_line(self):
        tax_21 = self.percent_tax(21.0)

        invoice = self._import_invoice_as_attachment_on(
            test_name='test_import_cash_rounding_add_invoice_line',
            journal=self.company_data['default_journal_sale'],
        )

        self.assertRecordValues(
            invoice.invoice_line_ids,
            [
                {
                    'quantity': 1.0,
                    'price_unit': 899.99,
                    'tax_ids': tax_21.ids,
                },
                {
                    'quantity': 1.0,
                    'price_unit': 0.01,
                    'tax_ids': [],
                },
            ],
        )
        self.assertRecordValues(
            invoice,
            [
                {
                    'amount_untaxed': 900.0,
                    'amount_tax': 189.0,
                    'amount_total': 1089.0,
                },
            ],
        )

    @freeze_time('2020-01-01')
    def test_import_cash_rounding_biggest_tax(self):
        tax_21 = self.percent_tax(21.0)

        invoice = self._import_invoice_as_attachment_on(
            test_name='test_import_cash_rounding_biggest_tax',
            journal=self.company_data['default_journal_sale'],
        )

        self.assertRecordValues(
            invoice.invoice_line_ids,
            [
                {
                    'quantity': 1.0,
                    'price_unit': 899.99,
                    'tax_ids': tax_21.ids,
                },
            ],
        )
        self.assertRecordValues(
            invoice,
            [
                {
                    'amount_untaxed': 899.99,
                    'amount_tax': 189.01,
                    'amount_total': 1089.0,
                },
            ],
        )
