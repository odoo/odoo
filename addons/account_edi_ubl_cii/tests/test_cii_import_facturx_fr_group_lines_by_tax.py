from odoo.addons.account_edi_ubl_cii.tests.test_cii_import_facturx_fr import CiiImportFacturXFR
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestCiiImportFacturXFRGroupLinesByTax(CiiImportFacturXFR):

    def test_import_invoice_group_lines_by_tax(self):
        tax_10 = self.percent_tax(10.0, type_tax_use='purchase')
        tax_20 = self.percent_tax(20.0, type_tax_use='purchase')

        invoice = self._import_invoice_as_attachment_on(
            test_name='test_import_invoice_group_lines_by_tax',
            journal=self.company_data['default_journal_purchase'],
        )

        expected_total_amounts = [{
            'amount_untaxed': 1900.0,
            'amount_tax': 320,
            'amount_total': 2220.00,
        }]
        expected_not_grouped_lines = [
            {
                'quantity': 1.0,
                'price_unit': 600.0,
                'tax_ids': tax_10.ids,
            },
            {
                'quantity': 1.0,
                'price_unit': 300.0,
                'tax_ids': tax_20.ids,
            },
            {
                'quantity': 2.0,
                'price_unit': 500.0,
                'tax_ids': tax_20.ids,
            },
        ]
        self.assertRecordValues(invoice.invoice_line_ids, expected_not_grouped_lines)
        self.assertRecordValues(invoice, expected_total_amounts)

        # Group the lines.
        invoice.action_group_ungroup_lines_by_tax()
        expected_grouped_lines = [
            {
                'quantity': 1.0,
                'price_unit': 600.0,
                'tax_ids': tax_10.ids,
            },
            {
                'quantity': 1.0,
                'price_unit': 1300.0,
                'tax_ids': tax_20.ids,
            },
        ]
        self.assertRecordValues(invoice.invoice_line_ids, expected_grouped_lines)
        self.assertRecordValues(invoice, expected_total_amounts)

        # Post it to test the next invoice is automatically grouped by default.
        invoice.action_post()

        # Import a second invoice, should have lines grouped
        invoice2 = self._import_invoice_as_attachment_on(
            test_name='test_import_invoice_group_lines_by_tax',
            journal=self.company_data['default_journal_purchase'],
        )
        self.assertRecordValues(invoice2.invoice_line_ids, expected_grouped_lines)
        self.assertRecordValues(invoice2, expected_total_amounts)

        # Still we should be able to ungroup lines
        invoice2.action_group_ungroup_lines_by_tax()
        self.assertRecordValues(invoice2.invoice_line_ids, expected_not_grouped_lines)
        self.assertRecordValues(invoice2, expected_total_amounts)

    def test_import_invoice_group_lines_correct_tax_amount(self):
        self.percent_tax(21.0, type_tax_use='purchase')

        # This invoice tax amount computation by odoo is 9.07 while in the XML, the amount is 9.06
        # The _correct_invoice_tax_amount method will update the tax amount to match the XML data
        invoice = self._import_invoice_as_attachment_on(
            test_name='test_import_invoice_group_lines_correct_tax_amount',
            journal=self.company_data['default_journal_purchase'],
        )

        # Check that we don't go back to 9.07 after grouping lines
        self.assertEqual(invoice.amount_tax, 9.06)
        invoice.action_group_ungroup_lines_by_tax()
        self.assertEqual(invoice.amount_tax, 9.06)
