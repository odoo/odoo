from unittest.mock import patch
import datetime

from odoo import fields, Command
from odoo.exceptions import UserError
from odoo.models import Model
from odoo.tests import tagged
from odoo.tools import format_date

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('external_l10n', '-at_install', 'post_install', '-standard', 'external')
class TestL10nPt(AccountTestInvoicingCommon):
    @classmethod
    @AccountTestInvoicingCommon.setup_country('pt')
    def setUpClass(cls):
        super().setUpClass()
        cls.company_pt = cls.company_data['company']
        cls.company_pt.write({
            'street': '25 Avenida da Liberdade',
            'city': 'Lisboa',
            'zip': '9415-343',
            'company_registry': '123456',
            'phone': '+351 11 11 11 11',
            'country_id': cls.env.ref('base.pt').id,
            'vat': 'PT123456789',
        })
        for move_type, preprefix in (("out_invoice", "INV"), ("out_refund", "RINV")):
            for year in ("2017", "2024"):
                prefix = f'{preprefix}{year}'
                if not cls.env['l10n_pt.at.series'].search_count([("prefix", "=", prefix)]):
                    cls.env['l10n_pt.at.series'].create({
                        'company_id': cls.company_pt.id,
                        'type': move_type,
                        'prefix': prefix,
                        'at_code': f'AT-TEST-{prefix}',
                    })

    @classmethod
    def create_invoice(cls, move_type, invoice_date="2024-01-01", create_date=None, amount=1000.0, post=False):
        move = cls.env['account.move'].create({
            'move_type': move_type,
            'partner_id': cls.partner_a.id,
            'invoice_date': fields.Date.from_string(invoice_date),
            'line_ids': [
                Command.create({
                    'name': 'Product A',
                    'quantity': 1,
                    'price_unit': amount,
                    'tax_ids': [],
                }),
            ],
        })
        # Bypass ORM to update the create_date
        move._cr.execute('''
            UPDATE account_move
               SET create_date = %s
             WHERE id = %s
        ''', (datetime.datetime.strptime(create_date, '%Y-%m-%dT%H:%M:%S') if create_date else invoice_date, move.id))
        move.invalidate_model(['create_date'])
        if post:
            move.action_post()
            move.button_hash()
        return move

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

        with patch('odoo.addons.l10n_pt.models.account_move.AccountMove._get_l10n_pt_document_number', _get_l10n_pt_document_number_patched):
            for (l10n_pt_document_number, invoice_date, create_date, amount, expected_hash) in [
                ('1T 1/1', '2017-03-10', '2017-03-10T15:58:01', 28.07, "vfinNfF+rToGp3dWF1LV6mEctQ76hAeZm+PlhBnV4wokN//N79L7fTNvi71ONnMHzfIzVR/Iz2zOOo9MUrYfYYZhqtpcEgFNHMdET6ZqbVVke7HbfqSACzaKXNdgWZt7lm7AFOfhcizQgC4a66SNvJvPJUqF7bCTUMIJFR9Zfro="),
                ('1T 1/2', '2017-09-16', '2017-09-16T15:58:10', 235.15, "jABYv0ThJHWoocmbzuLPOJXknl2WHBpLRBPqhIBSYP6GRzo3WiMxh6ryFiaa8rQD2BM9tdLxjhPHOZo1XPeGR5hFGK5BI/NzTXBu9+ponV4wvASOhjy2iomBlOxISN3MYGBcG1XWLfi+aDBw0TLrVwpbsENk0MtypYGU78OPPjg="),
                ('1T 1/3', '2017-09-16', '2017-09-16T15:58:45', 679.61, "MqvfiYZOh1L1fgfrAXBemPED1xy27MUs79vWxk/0P99Bq+jxvxwjJa3HQdElGfogj5bslcxX3ia9Tps2Oxfw1kH3GnsmfzqHbVagqnNxiI/KMZGfR4XXXNSOf7l7K7iMELz29b/c8u8eRmUwm13sgk9E9yAyk9zLuQ/s5TByG9k="),
            ]:
                move = self.create_invoice('out_invoice', invoice_date, create_date, amount, post=True)
                move.flush_recordset()
                self.assertEqual(move.inalterable_hash.split("$")[2], expected_hash)

            # Now we'll test with a different move_type/InvoiceType (first part of the l10n_pt_document_number is different),
            # Therefore we have a new chain and the following first move has no previous move (i.e. 1T 1/3 is not the previous).
            for (l10n_pt_document_number, invoice_date, create_date, amount, expected_hash) in [
                ('2T A/1', '2017-09-16', '2017-09-16T16:02:16', 235.15, "CM1pPaqk/pTE5DajJZ3H9VejD00FL455GvHx0FjuNj3UKj1V9EkP5dPsOpB6/KXlttY1WsHGG4dcunSOKULW0FMEWAMQYxBo/HqLcIojedKxrzh6m9+P61VM4BnYxbtEBQRFdVs0MGP8X85uSc4ikPrY4OeO1UOixGR9xLIAtr4="),
                ('2T A/2', '2017-09-16', '2017-09-16T16:03:11', 2261.34, "Y7kXSvGiS1eCSU9DY1GlWHw+HMmpI/gdZKEv17EXFC7OFdOdSCwcRNPzBUB6QjB1aQ60T8+4jvQb+tSWAQJdsCoiNUMcZl+oQJKJjJTfPJTmDBlrnh0JGXaOrg4sPe1eVvjjtCKxyJ3xoQnwU/bVBjMde2Kx0zXBsBwIWoT0ukg="),
                ('2T A/3', '2017-09-16', '2017-09-16T16:04:45', 47.03, "W3Z1jj4rNG5CREwXq0ZCjaRHDqrB1U9U6NmyKZZ7VpruDsw+NxcbwUubuMgejYBCVr6OIRrUNlm1UvNuYx/EXFZpzhdoWRc7O1HPBSQFhAfhByE6QxvumsVtxSome95/cG2VmAU1MJUJTVQN4Y//snz8YaCy1/81bB7aGfUs0C0="),
            ]:
                move = self.create_invoice('out_refund', invoice_date, create_date, amount, post=True)
                move.flush_recordset()
                self.assertEqual(move.inalterable_hash.split("$")[2], expected_hash)

    def test_l10n_pt_hash_inalterability(self):
        expected_error_msg = "This document is protected by a hash. Therefore, you cannot edit the following fields:*"

        out_invoice = self.create_invoice('out_invoice', '2024-01-01', post=True)
        out_invoice.flush_recordset()
        with self.assertRaisesRegex(UserError, expected_error_msg):
            out_invoice.inalterable_hash = 'fake_hash'
        with self.assertRaisesRegex(UserError, expected_error_msg):
            out_invoice.invoice_date = fields.Date.from_string('2000-01-01')
        with self.assertRaisesRegex(UserError, expected_error_msg):
            out_invoice.create_date = fields.Datetime.now()
        with self.assertRaisesRegex(UserError, expected_error_msg):
            out_invoice.amount_total = 666
        with self.assertRaisesRegex(UserError, expected_error_msg):
            out_invoice.sequence_number = 666  # Sequence number is used by l10n_pt_document_number so it cannot be modified either
        with self.assertRaisesRegex(UserError, expected_error_msg):
            out_invoice.sequence_prefix = "FAKE"  # Sequence prefix is used by l10n_pt_document_number so it cannot be modified either

        # The following field is not part of the hash so it can be modified
        out_invoice.ref = 'new ref'

    def test_l10n_pt_document_no(self):
        """
        Test that the document number for Portugal follows this format: [^ ]+ [^/^ ]+/[0-9]+
        """
        for (move_type, date, expected) in [
            ('out_invoice', '2024-01-01', 'out_invoice INV2024/1'),
            ('out_invoice', '2024-01-02', 'out_invoice INV2024/2'),
            ('in_invoice', '2024-01-01', 'in_invoice BILL2024/1'),
            ('out_invoice', '2024-01-03', 'out_invoice INV2024/3'),
            ('out_refund', '2024-01-01', 'out_refund RINV2024/1'),
            ('in_refund', '2024-01-01', 'in_refund RBILL2024/1'),
            ('out_invoice', '2024-01-04', 'out_invoice INV2024/4'),
            ('in_refund', '2024-01-02', 'in_refund RBILL2024/2'),
        ]:
            move = self.create_invoice(move_type, date, post=True)
            self.assertEqual(move._get_l10n_pt_document_number(), expected)

    def test_l10n_pt_move_hash_integrity_report(self):
        """Test the hash integrity report"""
        # Everything should be correctly hashed and verified
        # Reminder: we have one chain per move_type in Portugal
        out_invoice1 = self.create_invoice('out_invoice', '2024-01-01', post=True)
        self.create_invoice('out_invoice', '2024-01-02', post=True)
        out_invoice3 = self.create_invoice('out_invoice', '2024-01-03', post=True)
        out_invoice4 = self.create_invoice('out_invoice', '2024-01-04', post=True)

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
