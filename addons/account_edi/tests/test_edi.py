# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.account_edi.tests.common import AccountEdiTestCommon
from unittest.mock import patch


class TestAccountEdi(AccountEdiTestCommon):

    def test_export_edi(self):
        invoice = self.init_invoice('out_invoice')
        self.assertEqual(len(invoice.edi_document_ids), 0)
        invoice.action_post()
        self.assertEqual(len(invoice.edi_document_ids), 1)

    def test_prepare_jobs(self):
        def create_edi_document(edi_format, state, move=None, move_type=None):
            move = move or self.init_invoice(move_type or 'out_invoice')
            return self.env['account.edi.document'].create({
                'edi_format_id': edi_format.id,
                'move_id': move.id,
                'state': state
            })

        edi_docs = self.env['account.edi.document']
        edi_docs |= create_edi_document(self.edi_format, 'to_send')
        edi_docs |= create_edi_document(self.edi_format, 'to_send')

        to_process = edi_docs._prepare_jobs()
        self.assertEqual(len(to_process), 2)

        with patch('odoo.addons.account_edi.models.account_edi_format.AccountEdiFormat._support_batching', return_value=True):
            to_process = edi_docs._prepare_jobs()
            self.assertEqual(len(to_process), 1)

        other_edi = self.env['account.edi.format'].sudo().create({
            'name': 'Batchable EDI format 2',
            'code': 'test_batch_edi_2',
        })

        edi_docs |= create_edi_document(other_edi, 'to_send')
        edi_docs |= create_edi_document(other_edi, 'to_send')

        with patch('odoo.addons.account_edi.models.account_edi_format.AccountEdiFormat._support_batching', return_value=True):
            to_process = edi_docs._prepare_jobs()
            self.assertEqual(len(to_process), 2)
