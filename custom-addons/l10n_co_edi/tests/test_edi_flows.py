# -*- coding: utf-8 -*-
from .common import TestCoEdiCommon

from odoo.tests import tagged
from odoo.exceptions import UserError


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
