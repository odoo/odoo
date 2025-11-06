from odoo.addons.account_edi_ubl_cii.tests.common import TestUblBis3Common, TestUblCiiBECommon
from odoo.tests import tagged

from freezegun import freeze_time


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestUblImportBis3InvoiceBE(TestUblBis3Common, TestUblCiiBECommon):

    @classmethod
    def subfolders(cls):
        subfolder_format, _subfolder_document, subfolder_country = super().subfolders()
        return subfolder_format, 'invoice', subfolder_country

    @freeze_time('2020-01-01')
    def test_import_discount_per_line_price_on_big_quantity(self):
        tax_21 = self.percent_tax(21.0)

        invoice = self._import_invoice_as_attachment_on(
            test_name='test_import_discount_per_line_price_on_big_quantity',
            journal=self.company_data['default_journal_sale'],
        )
        self.assertRecordValues(
            invoice.invoice_line_ids,
            [
                {
                    'quantity': 150.0,
                    'price_unit': 0.53073,
                    'discount': 11.996055747115614,
                    'tax_ids': tax_21.ids,
                },
                {
                    'quantity': 200.0,
                    'price_unit': 0.6369,
                    'discount': 12.00345423143351,
                    'tax_ids': tax_21.ids,
                },
            ],
        )
        self.assertRecordValues(
            invoice,
            [
                {
                    'amount_untaxed': 182.15,
                    'amount_tax': 38.25,
                    'amount_total': 220.40,
                },
            ],
        )

    @freeze_time('2020-01-01')
    def test_import_lot_of_decimals_in_quantities(self):
        tax_21 = self.percent_tax(21.0)

        invoice = self._import_invoice_as_attachment_on(
            test_name='test_import_lot_of_decimals_in_quantities',
            journal=self.company_data['default_journal_sale'],
        )
        self.assertRecordValues(
            invoice.invoice_line_ids,
            [
                {
                    'quantity': 0.93,
                    'price_unit': 101.35,
                    'tax_ids': tax_21.ids,
                },
                {
                    'quantity': 0.28,
                    'price_unit': 101.35,
                    'tax_ids': tax_21.ids,
                },
                {
                    'quantity': 0.5,
                    'price_unit': 126.7,
                    'tax_ids': tax_21.ids,
                },
                {
                    'quantity': 1.0,
                    'price_unit': 6.45,
                    'tax_ids': tax_21.ids,
                },
                {
                    'quantity': 1.0,
                    'price_unit': 14.44,
                    'tax_ids': tax_21.ids,
                },
                {
                    'quantity': 1.0,
                    'price_unit': 25.79,
                    'tax_ids': tax_21.ids,
                },
            ],
        )
        self.assertRecordValues(
            invoice,
            [
                {
                    'amount_untaxed': 233.34,
                    'amount_tax': 49.0,
                    'amount_total': 282.34,
                },
            ],
        )
