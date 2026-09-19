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
    def test_amount_tax_consistent_with_amount_untaxed(self):
        """On round_globally (this test class's default company setting), a large enough
        invoice can make Odoo's natural recomputation of amount_tax drift from the file's
        declared TaxTotal by more than a few cents: amount_tax must still be reconciled
        with it, not left at its natural, never-corrected value.
        """
        for move_type, journal in (
            ('sale', self.company_data['default_journal_sale']),
            ('purchase', self.company_data['default_journal_purchase']),
        ):
            with self.subTest(move_type=move_type):
                self.percent_tax(21.0, type_tax_use=move_type)

                move = self._import_invoice_as_attachment_on(
                    test_name='test_amount_tax_consistent_with_amount_untaxed',
                    journal=journal,
                )

                self.assertRecordValues(
                    move,
                    [
                        {
                            'amount_untaxed': 11202.00,
                            'amount_tax': 2352.42,
                            'amount_total': 13554.42,
                        },
                    ],
                )

    @freeze_time('2020-01-01')
    def test_price_subtotal_consistent_with_amount_currency(self):
        """ On round_globally (this test class's default company setting), a line's
        displayed Subtotal (price_subtotal) must always match the amount actually posted
        to the ledger for that same line, in the document's own currency (amount_currency),
        even when the whole-invoice redistribution nudges some lines away from their
        naturally-rounded amount.
        """
        self.percent_tax(21.0)

        invoice = self._import_invoice_as_attachment_on(
            test_name='test_price_subtotal_balance_mismatch',
            journal=self.company_data['default_journal_sale'],
        )

        self.assertRecordValues(
            invoice.invoice_line_ids,
            [
                {'price_subtotal': 214.29, 'price_total': 259.29, 'amount_currency': -214.29},
                {'price_subtotal': 542.31, 'price_total': 656.19, 'amount_currency': -542.31},
                {'price_subtotal': 242.86, 'price_total': 293.86, 'amount_currency': -242.86},
                {'price_subtotal': 37.78, 'price_total': 45.71, 'amount_currency': -37.78},
                {'price_subtotal': 54.55, 'price_total': 66.0, 'amount_currency': -54.55},
                {'price_subtotal': 522.73, 'price_total': 632.5, 'amount_currency': -522.73},
                {'price_subtotal': 141.67, 'price_total': 171.42, 'amount_currency': -141.67},
                {'price_subtotal': 3549.98, 'price_total': 4295.49, 'amount_currency': -3549.98},
                {'price_subtotal': 3066.66, 'price_total': 3710.66, 'amount_currency': -3066.66},
                {'price_subtotal': 84.62, 'price_total': 102.39, 'amount_currency': -84.62},
                {'price_subtotal': 178.85, 'price_total': 216.41, 'amount_currency': -178.85},
                {'price_subtotal': 722.22, 'price_total': 873.89, 'amount_currency': -722.22},
                {'price_subtotal': 1011.11, 'price_total': 1223.44, 'amount_currency': -1011.11},
                {'price_subtotal': 314.29, 'price_total': 380.29, 'amount_currency': -314.29},
                {'price_subtotal': 3066.66, 'price_total': 3710.66, 'amount_currency': -3066.66},
                {'price_subtotal': 0.04, 'price_total': 0.04, 'amount_currency': -0.04},
            ],
        )
        self.assertRecordValues(
            invoice,
            [
                {
                    'amount_untaxed': 13750.62,
                    'amount_tax': 2887.63,
                    'amount_total': 16638.25,
                },
            ],
        )

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
