from datetime import timedelta
from unittest.mock import patch

from odoo import Command, fields
from odoo.exceptions import UserError
from odoo.models import Model
from odoo.tests import tagged
from odoo.tools import format_date

from odoo.addons.l10n_pt_certification.tests.common import TestL10nPtCommon


@tagged('external_l10n', '-at_install', 'post_install', '-standard', 'external')
class TestL10nPtHashing(TestL10nPtCommon):
    def test_l10n_pt_hash_sequence(self):
        """
        Test that the hash sequence is correct.
        For this, we use the following resource provided by the Portuguese tax authority:
        https://info.portaldasfinancas.gov.pt/apps/saft-pt01/local/saft_idemo599999999.xml
        We create invoices with the same info as in the link, and we check that the hash that we obtain in Odoo
        is the same as the one given in the link (using the same sample keys).
        """

        # This patch is necessary because we use the move_type in l10n_pt_document_number, but our
        # move types (out_invoice, out_refund, ...) are different from the ones used in the link (FT, NC, ...)
        l10n_pt_document_number = ""

        def _get_l10n_pt_document_number_patched(self_patched):
            return l10n_pt_document_number

        with patch('odoo.addons.l10n_pt_certification.models.account_move.AccountMove._get_l10n_pt_document_number', _get_l10n_pt_document_number_patched):
            for (l10n_pt_document_number, invoice_date, l10n_pt_hashed_on, amount, expected_hash) in [
                ('1T 1/1', '2017-03-10', '2017-03-10T15:58:01', 28.07, "vfinNfF+rToGp3dWF1LV6mEctQ76hAeZm+PlhBnV4wokN//N79L7fTNvi71ONnMHzfIzVR/Iz2zOOo9MUrYfYYZhqtpcEgFNHMdET6ZqbVVke7HbfqSACzaKXNdgWZt7lm7AFOfhcizQgC4a66SNvJvPJUqF7bCTUMIJFR9Zfro="),
                ('1T 1/2', '2017-09-16', '2017-09-16T15:58:10', 235.15, "jABYv0ThJHWoocmbzuLPOJXknl2WHBpLRBPqhIBSYP6GRzo3WiMxh6ryFiaa8rQD2BM9tdLxjhPHOZo1XPeGR5hFGK5BI/NzTXBu9+ponV4wvASOhjy2iomBlOxISN3MYGBcG1XWLfi+aDBw0TLrVwpbsENk0MtypYGU78OPPjg="),
                ('1T 1/3', '2017-09-16', '2017-09-16T15:58:45', 679.61, "MqvfiYZOh1L1fgfrAXBemPED1xy27MUs79vWxk/0P99Bq+jxvxwjJa3HQdElGfogj5bslcxX3ia9Tps2Oxfw1kH3GnsmfzqHbVagqnNxiI/KMZGfR4XXXNSOf7l7K7iMELz29b/c8u8eRmUwm13sgk9E9yAyk9zLuQ/s5TByG9k="),
            ]:
                with self.subTest(invoice_date=invoice_date, l10n_pt_hashed_on=l10n_pt_hashed_on, amount=amount, expected_hash=expected_hash):
                    move = self.create_invoice('out_invoice', invoice_date, l10n_pt_hashed_on, amount, self.tax_sale_0, do_hash=True)
                    move.flush_recordset()
                    self.assertEqual(move.inalterable_hash.split("$")[2], expected_hash)

            # Now we'll test with a different move_type/InvoiceType (first part of the l10n_pt_document_number is different),
            # Therefore we have a new chain and the following first move has no previous move (i.e. 1T 1/3 is not the previous).
            for (l10n_pt_document_number, l10n_pt_hashed_on, amount, expected_hash) in [
                ('2T A/1', '2017-09-16T16:02:16', 235.15, "CM1pPaqk/pTE5DajJZ3H9VejD00FL455GvHx0FjuNj3UKj1V9EkP5dPsOpB6/KXlttY1WsHGG4dcunSOKULW0FMEWAMQYxBo/HqLcIojedKxrzh6m9+P61VM4BnYxbtEBQRFdVs0MGP8X85uSc4ikPrY4OeO1UOixGR9xLIAtr4="),
                ('2T A/2', '2017-09-16T16:03:11', 2261.34, "Y7kXSvGiS1eCSU9DY1GlWHw+HMmpI/gdZKEv17EXFC7OFdOdSCwcRNPzBUB6QjB1aQ60T8+4jvQb+tSWAQJdsCoiNUMcZl+oQJKJjJTfPJTmDBlrnh0JGXaOrg4sPe1eVvjjtCKxyJ3xoQnwU/bVBjMde2Kx0zXBsBwIWoT0ukg="),
                ('2T A/3', '2017-09-16T16:04:45', 47.03, "W3Z1jj4rNG5CREwXq0ZCjaRHDqrB1U9U6NmyKZZ7VpruDsw+NxcbwUubuMgejYBCVr6OIRrUNlm1UvNuYx/EXFZpzhdoWRc7O1HPBSQFhAfhByE6QxvumsVtxSome95/cG2VmAU1MJUJTVQN4Y//snz8YaCy1/81bB7aGfUs0C0="),
            ]:
                with self.subTest(l10n_pt_hashed_on=l10n_pt_hashed_on, amount=amount, expected_hash=expected_hash):
                    move = self.create_invoice('out_refund', '2017-09-16', l10n_pt_hashed_on, amount, self.tax_sale_0, do_hash=True)
                    move.flush_recordset()
                    self.assertEqual(move.inalterable_hash.split("$")[2], expected_hash)

    def test_l10n_pt_hash_inalterability(self):
        expected_error_msg = "This document is protected by a hash. Therefore, you cannot edit the following fields:*"

        out_invoice = self.create_invoice(invoice_date='2024-01-01', do_hash=True)
        out_invoice.flush_recordset()
        with self.assertRaisesRegex(UserError, expected_error_msg):
            out_invoice.inalterable_hash = 'fake_hash'
        with self.assertRaisesRegex(UserError, expected_error_msg):
            out_invoice.invoice_date = fields.Date.from_string('2000-01-01')
        with self.assertRaisesRegex(UserError, expected_error_msg):
            out_invoice.l10n_pt_hashed_on = fields.Datetime.now()
        with self.assertRaisesRegex(UserError, expected_error_msg):
            out_invoice.amount_total_signed = 666
        with self.assertRaisesRegex(UserError, expected_error_msg):
            out_invoice.name = "new name"
        with self.assertRaisesRegex(UserError, expected_error_msg):
            out_invoice.l10n_pt_document_number = "new number/0001"

        # The following field is not part of the hash so it can be modified
        out_invoice.ref = 'new ref'

    def test_l10n_pt_move_hash_integrity_report(self):
        """Test the hash integrity report"""
        # Reminder: we have at least one chain per move_type in Portugal
        out_invoice1 = self.create_invoice(invoice_date='2024-01-01', do_hash=True)
        self.create_invoice(invoice_date='2024-01-02', do_hash=True)
        out_invoice3 = self.create_invoice(invoice_date='2024-01-03', do_hash=True)
        out_invoice4 = self.create_invoice(invoice_date='2024-01-04', do_hash=True)

        integrity_check = self.company_pt._check_hash_integrity()['results'][0]  # [0] = 'out_invoice'
        self.assertEqual(integrity_check['status'], 'verified')
        self.assertRegex(integrity_check['msg_cover'], 'Entries are correctly hashed')
        self.assertEqual(integrity_check['first_move_date'], format_date(self.env, out_invoice1.date))
        self.assertEqual(integrity_check['last_move_date'], format_date(self.env, out_invoice4.date))

        # Let's change one of the fields used by the hash. It should be detected by the integrity report.
        # We need to bypass the write method of account.move to do so.
        Model.write(out_invoice3, {'invoice_date': fields.Date.from_string('2024-01-07')})
        integrity_check = self.company_pt._check_hash_integrity()['results'][0]
        self.assertEqual(integrity_check['status'], 'corrupted')
        self.assertEqual(integrity_check['msg_cover'], f'Corrupted data on journal entry with id {out_invoice3.id} ({out_invoice3.name}).')

        # Let's try with the inalterable_hash field itself
        Model.write(out_invoice3, {'invoice_date': fields.Date.from_string("2024-01-03")})  # Revert the previous change
        Model.write(out_invoice4, {'inalterable_hash': 'fake_hash'})
        integrity_check = self.company_pt._check_hash_integrity()['results'][0]
        self.assertEqual(integrity_check['status'], 'corrupted')
        self.assertEqual(integrity_check['msg_cover'], f'Corrupted data on journal entry with id {out_invoice4.id} ({out_invoice4.name}).')


@tagged('external_l10n', '-at_install', 'post_install', '-standard', 'external')
class TestL10nPtMiscRequirements(TestL10nPtCommon):
    def test_l10n_pt_document_no(self):
        """
        Test that the document number for out_invoice, out_refund and out_receipt in Portugal
        follows this format: [^ ]+ [^/^ ]+/[0-9]+
        """
        for (move_type, date, expected) in [
            ('out_invoice', '2024-01-01', 'INV 2024/00001'),
            ('out_invoice', '2024-01-02', 'INV 2024/00002'),
            ('in_invoice', '2024-01-01', False),
            ('out_invoice', '2024-01-03', 'INV 2024/00003'),
            ('out_refund', '2024-01-01', 'RINV 2024/00001'),
            ('in_refund', '2024-01-01', False),
            ('out_invoice', '2024-01-04', 'INV 2024/00004'),
            ('in_refund', '2024-01-02', False),
        ]:
            move = self.create_invoice(move_type, date)
            self.assertEqual(move._get_l10n_pt_document_number(), expected)

    def test_l10n_pt_invoice_lines(self):
        """
        Test that invoices without taxes or non-positive lines cannot be posted
        """
        with self.assertRaisesRegex(UserError, "You cannot create a move line without VAT tax."):
            move = self.env['account.move'].with_company(self.company_pt).create({
                'company_id': self.company_pt.id,
                'move_type': 'out_invoice',
                'partner_id': self.partner_a.id,
                'invoice_date': fields.Date.from_string('2024-02-04'),
                'line_ids': [
                    Command.create({
                        'name': 'Product A',
                        'quantity': 1,
                        'price_unit': 1000,
                        'tax_ids': [],
                    }),
                ],
            })
            move.action_post()

        with self.assertRaisesRegex(UserError, "Invoice lines with an amount of 0 are not allowed."):
            self.create_invoice(amount=0)

        with self.assertRaisesRegex(UserError, "You cannot create an invoice with negative lines on it"):
            self.create_invoice(amount=-10)

    def test_l10n_pt_partner(self):
        """Test misc requirements for partner"""
        # Cannot change tax number of an existing client with already issued documents, except in the cases
        # where the VAT field is empty or filled with generic client tax 999999990
        self.partner_a.write({
            'vat': "PT123456789",
            'company_id': self.company_pt.id,
        })
        self.partner_a.vat = "999999990"

        self.create_invoice()

        self.partner_a.vat = "PT123456789"
        with self.assertRaisesRegex(UserError, "change the VAT number of a partner that already has issued documents"):
            self.partner_a.vat = "PT987654321"

        # Do not allow change the name of client (if it already has issued docs) who has no tax number.
        # Limitation ends when client has a tax number.

        partner_b = self.env['res.partner'].create({
            'name': 'Partner B',
            'company_id': self.company_pt.id,
        })
        with self.assertRaisesRegex(UserError, "You cannot change the name of a partner without a VAT number"):
            partner_b.name = "Partner B2"

        partner_b.vat = "PT123456789"
        partner_b.name = "Partner B2"

    def test_l10n_pt_product(self):
        """
        Test that Product names shorter than two characters cannot be created and that
        we do not allow changing the ProductDescription if there are already issued docs
        """

        with self.assertRaisesRegex(UserError, "Product names have to be at least 2 characters long."):
            self.env['product.product'].create({'name': 'A'})

        # Create a product with len(name) > 2. After it's used in a move, product name cannot be changed
        product = self.env['product.product'].create({'name': 'Product A'})
        product.name = "Product A2"  # OK

        self.create_invoice(product_id=product.id)

        with self.assertRaisesRegex(UserError, "You cannot modify the name of a product that has been used"):
            product.name = "Product A3"

    def test_l10n_pt_invoice_date_validation(self):
        """
        Test that, if an invoice is posted in a future date, no other invoices can be posted in the same series.
        """
        self.create_invoice(invoice_date=fields.Date.today() + timedelta(days=1))
        with self.assertRaisesRegex(UserError, "You cannot create an invoice with a date earlier than the date"):
            self.create_invoice(invoice_date=fields.Date.today())

    def test_l10n_pt_payment_date_validation(self):
        """
        Test that, if a payment is posted in a future date, no other payments can be posted in the same series.
        """
        payment_vals = {
            'company_id': self.company_pt.id,
            'payment_type': 'inbound',
            'partner_id': self.partner_a.id,
            'journal_id': self.company_data['default_journal_bank'].id,
            'date': fields.Date.from_string(fields.Date.today() + timedelta(days=1)),
            'amount': 100.0,
            'l10n_pt_at_series_id': self.series_2024.id
        }
        self.env['account.payment'].create(payment_vals).action_post()

        payment_vals['date'] = fields.Date.today()
        with self.assertRaisesRegex(UserError, "You cannot create a payment with a date earlier than the date"):
            self.env['account.payment'].create(payment_vals).action_post()

    def test_l10n_pt_hashed_on_date_validation(self):
        """
        Test that an error is thrown if an invoice has a hashed_on date ahead of the system date.
        """
        self.create_invoice(l10n_pt_hashed_on=fields.Datetime.now() + timedelta(hours=1), do_hash=True)
        with self.assertRaisesRegex(UserError, "exists secured invoices with a lock date ahead of the present time."):
            self.create_invoice()

    def test_l10n_pt_refund_validation(self):
        """
        Test that, if a refund is created, no line of the reversal move exceeds the value of the original move lines
        and that the reversal move does not have more lines than the original move.
        """
        invoice = self.create_invoice(product_id=self.product_a.id)
        credit_note = invoice._reverse_moves()
        # Check CN quantity > invoice quantity
        credit_note.invoice_line_ids.quantity = 2
        with self.assertRaisesRegex(UserError, "quantity exceeding that of the original customer invoice"):
            credit_note.action_post()

        # Check CN amount > invoice amount
        credit_note.invoice_line_ids.quantity = 1
        credit_note.invoice_line_ids.price_unit = 2000
        with self.assertRaisesRegex(UserError, "exceeds the amount of the original customer invoice"):
            credit_note.action_post()

    def test_l10n_pt_discount(self):
        """
        Test that global and line discounts are applied correctly.
        """
        move = self.env['account.move'].with_company(self.company_pt).create({
            'company_id': self.company_pt.id,
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': fields.Date.from_string('2024-02-04'),
            'l10n_pt_global_discount': 10.0,
            'line_ids': [
                Command.create({
                    'name': 'Product A',
                    'quantity': 1,
                    'price_unit': 1234.568,
                    'l10n_pt_line_discount': 10.0,
                    'tax_ids': self.tax_sale_23.ids,
                }),
                Command.create({
                    'name': 'Product A',
                    'quantity': 1,
                    'price_unit': 756.81,
                    'tax_ids': self.tax_sale_23.ids,
                }),
            ],
        })
        move.action_post()
        self.assertInvoiceValues(move, [
            {
                'price_unit': 1234.57,
                'price_subtotal': 1000.00,  # 10% global discount + 10% line discount
                'price_total': 1230.00,
                'debit': 0.0,
                'credit': 1000.0,
            },
            {
                'price_unit': 756.81,
                'price_subtotal': 681.13,  # 10% global discount, no line discount
                'price_total': 837.79,
                'debit': 0.0,
                'credit': 681.13,
            },
            {
                'price_unit': 0.0,
                'price_subtotal': 0.0,
                'price_total': 0.0,
                'debit': 0.0,
                'credit': 386.66,
            },
            {
                'price_unit': 0.0,
                'price_subtotal': 0.0,
                'price_total': 0.0,
                'debit': 2067.79,
                'credit': 0.0,
            },
        ], {
             'amount_untaxed': 1681.13,
             'amount_tax': 386.66,
             'amount_total': 2067.79,
         })
