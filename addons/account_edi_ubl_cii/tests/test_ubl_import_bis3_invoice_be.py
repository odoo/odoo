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

    @freeze_time('2020-01-01')
    def test_invoice_two_tax_subtotals_because_of_multi_currency(self):
        """ In PINT, when dealing with multi-currency invoice, there are 2 TaxSubtotal, one per currency. """
        tax_21 = self.percent_tax(21.0)
        invoice = self._import_invoice_as_attachment_on(
            test_name='test_invoice_two_tax_subtotals_because_of_multi_currency',
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

    @freeze_time('2020-01-01')
    def test_price_subtotal_agrees_with_balance(self):
        """Importing a UBL invoice on a round_globally company used to leave price_subtotal out
        of sync with the balance actually posted on lines nudged by the rounding redistribution.
        """
        self.assertEqual(
            self.company_data['company'].tax_calculation_rounding_method, 'round_globally',
            "This repro requires round_globally (the be_comp default) to trigger.",
        )

        invoice = self._import_invoice_as_attachment_on(
            test_name='subtotal_agrees_with_balance',
            journal=self.company_data['default_journal_sale'],
        )

        # The other two lines need a cent of rounding; round_globally nudges it onto this line
        # instead, so its subtotal is 1000.01, not the 1000.00 the file declared for it alone.
        big_line = invoice.invoice_line_ids.filtered(lambda l: l.quantity == 1)
        self.assertEqual(big_line.price_subtotal, 1000.01)
        self.assertEqual(big_line.balance, -1000.01)

        # Every line's price_subtotal must agree with its posted balance.
        for line in invoice.invoice_line_ids.filtered(lambda l: l.display_type == 'product'):
            self.assertAlmostEqual(line.price_subtotal, -line.balance)

        sum_of_displayed_price_subtotal = sum(invoice.invoice_line_ids.mapped('price_subtotal'))
        self.assertEqual(sum_of_displayed_price_subtotal, 1066.67)
        self.assertEqual(invoice.amount_untaxed, 1066.67)

    def test_import_embedded_pdf(self):
        """
        Importing an xml with embedded pdf should correctly import the
        pdf in the newly created bill
        """
        journal = self.company_data['default_journal_purchase']
        xml_attachment = self._import_invoice_as_attachment(test_name='test_import_embedded_pdf')

        # Import the document manually
        created_moves = []
        move_create = self.env.registry['account.move'].create

        # patch used to retrieve all created documents
        def patched_create(self, vals_list):
            records = move_create(self, vals_list)
            created_moves.extend(records.ids)
            return records
        self.patch(self.env.registry['account.move'], 'create', patched_create)

        # Import the document manually
        journal.create_document_from_attachment(xml_attachment.id)

        self.assertEqual(len(created_moves), 1, "A single bill should be created")
        bill = self.env['account.move'].browse(created_moves)
        self.assertTrue(bill.message_main_attachment_id, "The Bill should have a main attachment")
        self.assertEqual(bill.message_main_attachment_id.mimetype, "application/pdf", "The main attachment should be a pdf")
        self.assertEqual(bill.message_main_attachment_id.res_id, bill.id, "The main attachment res_id should be the invoice id")
        self.assertEqual(len(bill.message_ids.mapped('attachment_ids')), 4, "All nested attachments should be attached to a chatter message")

        # Import the document via mail alias
        init_vals = {'move_type': 'in_invoice', 'journal_id': journal.id}
        email_raw = self._get_raw_mail_message_str(attachments=xml_attachment, email_to=journal.alias_id.display_name)
        created_moves = []
        move_id = self.env['mail.thread'].message_process('account.move', email_raw, custom_values=init_vals)
        bill = self.env['account.move'].browse(move_id)

        self.assertEqual(len(created_moves), 1, "A single bill should be created")
        self.assertTrue(bill.message_main_attachment_id, "The Bill should have a main attachment")
        self.assertEqual(bill.message_main_attachment_id.mimetype, "application/pdf", "The main attachment should be a pdf")
        self.assertEqual(bill.message_main_attachment_id.res_id, bill.id, "The main attachment res_id should be the invoice id")
        self.assertEqual(len(bill.message_ids.mapped('attachment_ids')), 4, "All nested attachments should be attached to a chatter message")
