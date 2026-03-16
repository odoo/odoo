from odoo.addons.account_edi_ubl_cii.tests.test_ubl_import_bis3_invoice_be import TestUblImportBis3InvoiceBE
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestUblImportBis3InvoiceBEDecodeInvoiceLine(TestUblImportBis3InvoiceBE):

    def test_partial_import_invoice_line_name_and_description(self):
        invoice = self._import_invoice_as_attachment_on(test_name='test_partial_import_invoice_line_name_and_description')
        self.assertRecordValues(invoice.invoice_line_ids, [{'name': 'description value'}])

    def test_partial_import_invoice_line_name(self):
        invoice = self._import_invoice_as_attachment_on(test_name='test_partial_import_invoice_line_name')
        self.assertRecordValues(invoice.invoice_line_ids, [{'name': 'name value'}])

    def test_partial_import_invoice_line_line_extension_amount(self):
        invoice = self._import_invoice_as_attachment_on(test_name='test_partial_import_invoice_line_line_extension_amount')
        self.assertRecordValues(invoice.invoice_line_ids, [{
            'price_unit': 1050.00,
            'quantity': 1.0,
            'discount': 9.52380952380953,
        }])

    def test_partial_import_invoice_line_line_extension_amount_full_price_node_and_invoiced_quantity(self):
        invoice = self._import_invoice_as_attachment_on(test_name='test_partial_import_invoice_line_line_extension_amount_full_price_node_and_invoiced_quantity')
        self.assertRecordValues(invoice.invoice_line_ids, [
            {
                'price_unit': 250.00,
                'quantity': 6.0,
                'discount': 20.0,
            },
        ])

    def test_partial_import_invoice_line_line_extension_amount_quantity(self):
        invoice = self._import_invoice_as_attachment_on(test_name='test_partial_import_invoice_line_line_extension_amount_quantity')
        self.assertRecordValues(invoice.invoice_line_ids, [{
            'price_unit': 210.00,
            'quantity': 5.0,
            'discount': 9.52380952380953,
        }])

    def test_partial_import_invoice_line_negative_lines_and_total(self):
        invoice = self._import_invoice_as_attachment_on(test_name='test_partial_import_invoice_line_negative_lines_and_total')
        self.assertRecordValues(invoice.invoice_line_ids, [
            {
                'price_unit': 400.0,
                'quantity': 7.0,
                'discount': 0.0,
                'price_subtotal': 2800.0,
            },
            {
                'price_unit': 500.0,
                'quantity': -3.0,
                'discount': 0.0,
                'price_subtotal': -1500.0,
            },
        ])
