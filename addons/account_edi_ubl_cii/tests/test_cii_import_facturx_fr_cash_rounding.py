from odoo.addons.account_edi_ubl_cii.tests.test_cii_import_facturx_fr import CiiImportFacturXFR
from odoo.tests import tagged

from freezegun import freeze_time


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestCiiImportFacturXFRCashRounding(CiiImportFacturXFR):

    @freeze_time('2026-01-01')
    def test_import_cash_rounding_add_invoice_line(self):
        tax_20 = self.percent_tax(20.0)

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
                    'tax_ids': tax_20.ids,
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
                    'amount_tax': 180.0,
                    'amount_total': 1080.0,
                },
            ],
        )

    @freeze_time('2026-01-01')
    def test_import_cash_rounding_biggest_tax(self):
        tax_20 = self.percent_tax(20.0)

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
                    'tax_ids': tax_20.ids,
                },
            ],
        )
        self.assertRecordValues(
            invoice,
            [
                {
                    'amount_untaxed': 899.99,
                    'amount_tax': 180.01,
                    'amount_total': 1080.0,
                },
            ],
        )
