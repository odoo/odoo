# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.account_edi.tests.common import AccountEdiTestCommon
from unittest.mock import patch


class TestAccountEdi(AccountEdiTestCommon):

    def test_export_edi(self):
        invoice = self.init_invoice('out_invoice', products=self.product_a)
        self.assertEqual(len(invoice.edi_document_ids), 0)
        invoice.action_post()
        self.assertEqual(len(invoice.edi_document_ids), 1)

    def test_prepare_jobs(self):

        edi_docs = self.env['account.edi.document']
        edi_docs |= self.create_edi_document(self.edi_format, 'to_send')
        edi_docs |= self.create_edi_document(self.edi_format, 'to_send')

        to_process = edi_docs._prepare_jobs()
        self.assertEqual(len(to_process), 2)

        with patch('odoo.addons.account_edi.models.account_edi_format.AccountEdiFormat._support_batching', return_value=True):
            to_process = edi_docs._prepare_jobs()
            self.assertEqual(len(to_process), 1)

        other_edi = self.env['account.edi.format'].sudo().create({
            'name': 'Batchable EDI format 2',
            'code': 'test_batch_edi_2',
        })

        edi_docs |= self.create_edi_document(other_edi, 'to_send')
        edi_docs |= self.create_edi_document(other_edi, 'to_send')

        with patch('odoo.addons.account_edi.models.account_edi_format.AccountEdiFormat._support_batching', return_value=True):
            to_process = edi_docs._prepare_jobs()
            self.assertEqual(len(to_process), 2)

    @patch('odoo.addons.account_edi.models.account_edi_format.AccountEdiFormat._post_invoice_edi')
    def test_error(self, patched):
        with patch('odoo.addons.account_edi.models.account_edi_format.AccountEdiFormat._needs_web_services',
                   new=lambda edi_format: True):
            edi_docs = self.create_edi_document(self.edi_format, 'to_send')
            edi_docs.error = 'Test Error'

            edi_docs.move_id.action_process_edi_web_services()
            patched.assert_called_once()
