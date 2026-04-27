# -*- coding: utf-8 -*-
from odoo.tests import tagged
from .common import TestPeEdiCommon, _get_pe_current_datetime

from datetime import timedelta

@tagged('external_l10n', 'post_install', '-at_install', '-standard', 'external')
class TestEdiSunat(TestPeEdiCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.company_data['company'].l10n_pe_edi_provider = 'sunat'

    def test_10_invoice_edi_flow(self):
        yesterday = _get_pe_current_datetime().date() - timedelta(1)
        move = self._create_invoice(invoice_date=yesterday, date=yesterday)
        move.action_post()

        # Send
        doc = move.edi_document_ids.filtered(lambda d: d.state in ('to_send', 'to_cancel'))
        move.action_process_edi_web_services(with_commit=False)
        self.assertRecordValues(doc, [{'error': False}])
        self.assertRecordValues(move, [{'edi_state': 'sent'}])

        # Cancel step 1
        move.l10n_pe_edi_cancel_reason = 'abc'
        move.button_cancel_posted_moves()
        self.assertFalse(move.l10n_pe_edi_cancel_cdr_number)
        doc = move.edi_document_ids.filtered(lambda d: d.state in ('to_send', 'to_cancel'))
        move.action_process_edi_web_services(with_commit=False)
        self.assertTrue(move.l10n_pe_edi_cancel_cdr_number)
        self.assertRecordValues(move, [{'edi_state': 'to_cancel'}])

        # Cancel step 2
        doc = move.edi_document_ids.filtered(lambda d: d.state in ('to_send', 'to_cancel'))
        move.action_process_edi_web_services(with_commit=False)
        self.assertRecordValues(doc, [{'error': False}])
        self.assertRecordValues(move, [{'edi_state': 'cancelled'}])

    def test_20_refund_edi_flow(self):
        today = _get_pe_current_datetime().date()
        move = self._create_refund(invoice_date=today, date=today)
        (move.reversed_entry_id + move).action_post()

        # Send
        doc = move.edi_document_ids.filtered(lambda d: d.state in ('to_send', 'to_cancel'))
        doc_reversed_entry = move.reversed_entry_id.edi_document_ids.filtered(lambda d: d.state in ('to_send', 'to_cancel'))
        (move.reversed_entry_id + move).action_process_edi_web_services(with_commit=False)
        self.assertRecordValues(doc, [{'error': False}])
        self.assertTrue(doc_reversed_entry)
        self.assertRecordValues(doc_reversed_entry, [{'error': False}])
        self.assertRecordValues(move, [{'edi_state': 'sent'}])

        # Cancel step 1
        move.l10n_pe_edi_cancel_reason = 'abc'
        move.button_cancel_posted_moves()
        self.assertFalse(move.l10n_pe_edi_cancel_cdr_number)
        doc = move.edi_document_ids.filtered(lambda d: d.state in ('to_send', 'to_cancel'))
        move.action_process_edi_web_services(with_commit=False)
        self.assertTrue(move.l10n_pe_edi_cancel_cdr_number)
        self.assertRecordValues(move, [{'edi_state': 'to_cancel'}])

        # Cancel step 2
        doc = move.edi_document_ids.filtered(lambda d: d.state in ('to_send', 'to_cancel'))
        move.action_process_edi_web_services(with_commit=False)
        self.assertRecordValues(doc, [{'error': False}])
        self.assertRecordValues(move, [{'edi_state': 'cancelled'}])

    def test_30_debit_note_edi_flow(self):
        today = _get_pe_current_datetime().date()
        move = self._create_debit_note(invoice_date=today, date=today)
        (move.debit_origin_id + move).action_post()

        # Send
        doc = move.edi_document_ids.filtered(lambda d: d.state in ('to_send', 'to_cancel'))
        doc_debit_origin = move.debit_origin_id.edi_document_ids.filtered(lambda d: d.state in ('to_send', 'to_cancel'))
        (move.debit_origin_id + move).action_process_edi_web_services(with_commit=False)
        self.assertRecordValues(doc, [{'error': False}])
        self.assertRecordValues(doc_debit_origin, [{'error': False}])
        self.assertRecordValues(move, [{'edi_state': 'sent'}])

        # Cancel step 1
        move.l10n_pe_edi_cancel_reason = 'abc'
        move.button_cancel_posted_moves()
        self.assertFalse(move.l10n_pe_edi_cancel_cdr_number)
        doc = move.edi_document_ids.filtered(lambda d: d.state in ('to_send', 'to_cancel'))
        move.action_process_edi_web_services(with_commit=False)
        self.assertTrue(move.l10n_pe_edi_cancel_cdr_number)
        self.assertRecordValues(move, [{'edi_state': 'to_cancel'}])

        # Cancel step 2
        doc = move.edi_document_ids.filtered(lambda d: d.state in ('to_send', 'to_cancel'))
        move.action_process_edi_web_services(with_commit=False)
        self.assertRecordValues(doc, [{'error': False}])
        self.assertRecordValues(move, [{'edi_state': 'cancelled'}])
