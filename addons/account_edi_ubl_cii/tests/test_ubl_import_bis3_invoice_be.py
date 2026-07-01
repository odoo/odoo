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
<<<<<<< 97d06d335d57b3f3c24a2ca02616d6a0df1f1bb5
||||||| c06be48ce7277a667719fd756e0a1f63e91cda27

    def test_import_embedded_pdf(self):
        """
        Importing an xml with embedded pdf should correctly import the
        pdf in the newly created bill
        """
        journal = self.company_data['default_journal_purchase']
        xml_attachment = self._import_invoice_as_attachment(test_name='test_import_embedded_pdf')

        # Import the document manually
        bill = self._import_invoice_as_attachment_on(attachment=xml_attachment, journal=journal)
        self.assertEqual(len(bill.attachment_ids), 1)

        init_vals = {'move_type': 'in_invoice', 'journal_id': journal.id}
        email_raw = self._get_raw_mail_message_str(attachments=xml_attachment, email_to=journal.alias_id.display_name)
        # Import the document via mail alias
        move_id = self.env['mail.thread'].message_process('account.move', email_raw, custom_values=init_vals)
        bill = self.env['account.move'].browse(move_id)

        self.assertEqual(len(bill.attachment_ids), 1)
=======

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
>>>>>>> 1d79a636208663a54835882d1a68e3fea961fcef
