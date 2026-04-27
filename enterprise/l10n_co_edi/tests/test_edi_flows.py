# -*- coding: utf-8 -*-
from datetime import timedelta

from .common import TestCoEdiCommon

from odoo import fields
from odoo.tests import tagged
from odoo.exceptions import UserError, ValidationError


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestEdiFlows(TestCoEdiCommon):

    def test_invoice_flow_not_sent(self):
        with self.mock_carvajal():
            self.invoice.action_post()

            document = self.invoice._get_edi_document(self.edi_format)

            self.assertEqual(len(document), 1)

            self.assertRecordValues(self.invoice, [{'edi_state': 'to_send'}])
            self.assertRecordValues(document, [{'state': 'to_send'}])

            self.invoice.button_cancel()

            self.assertFalse(self.invoice.edi_state)

            self.assertRaises(ValidationError, self.company_data['default_journal_sale'].write, {'l10n_co_edi_debit_note': True})

    def test_invoice_flow_sent(self):
        with self.mock_carvajal():
            self.invoice.action_post()

            document = self.invoice._get_edi_document(self.edi_format)

            self.assertEqual(len(document), 1)

            self.assertRecordValues(self.invoice, [{'edi_state': 'to_send'}])
            self.assertRecordValues(document, [{'state': 'to_send'}])

            # to_send first step
            self._process_documents_web_services(self.invoice)

            self.assertRecordValues(self.invoice, [{'edi_state': 'to_send', 'l10n_co_edi_transaction': 'mocked_success'}])
            self.assertRecordValues(document, [{'state': 'to_send'}])

            # to_send second step
            self._process_documents_web_services(self.invoice)

            self.assertRecordValues(self.invoice, [{'edi_state': 'sent'}])
            self.assertRecordValues(document, [{'state': 'sent'}])
            self.assertTrue(document.attachment_id)

            # Test that we can cancel the invoice
            with self.assertRaises(UserError), self.cr.savepoint():
                self.invoice.button_draft()

    def test_invoice_date_constraints_carvajal(self):
        """Test that invoices date older than 6 days or more than 6 days ahead trigger the warning."""
        with self.mock_carvajal():
            today = fields.Date.today()
            msg = "The issue date can not be older than 6 days or more than 6 days in the future."
            for days, assertion in [(6, self.assertNotIn), (7, self.assertIn)]:
                inv = self.invoice.copy({'invoice_date': today - timedelta(days=days)})
                inv.action_post()
                assertion(msg, inv.message_ids.mapped('preview'))
