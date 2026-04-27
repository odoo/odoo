# -*- coding: utf-8 -*-
from odoo.tests import tagged
from .common import TestPeEdiCommon, CODE_98_ERROR_MSG, MAX_WAIT_ITER, _get_pe_current_datetime

from datetime import timedelta
from time import sleep


@tagged('external_l10n', 'post_install', '-at_install', '-standard', 'external')
class TestEdiDigiflow(TestPeEdiCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.company_data['company'].l10n_pe_edi_provider = 'digiflow'

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

        # We need to wait a bit before requesting the cancellation's status
        # to avoid getting a status code 98 (cancellation still being processed).
        for _ in range(MAX_WAIT_ITER):
            sleep(10)
            move.action_process_edi_web_services(with_commit=False)
            if not doc.error or doc.error != CODE_98_ERROR_MSG:
                break

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

        # We need to wait a bit before requesting the cancellation's status
        # to avoid getting a status code 98 (cancellation still being processed).
        for _ in range(MAX_WAIT_ITER):
            sleep(10)
            move.action_process_edi_web_services(with_commit=False)
            if not doc.error or doc.error != CODE_98_ERROR_MSG:
                break

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

        # We need to wait a bit before requesting the cancellation's status
        # to avoid getting a status code 98 (cancellation still being processed).
        for _ in range(MAX_WAIT_ITER):
            sleep(10)
            move.action_process_edi_web_services(with_commit=False)
            if not doc.error or doc.error != CODE_98_ERROR_MSG:
                break

        self.assertRecordValues(doc, [{'error': False}])
        self.assertRecordValues(move, [{'edi_state': 'cancelled'}])

    def test_40_catch_error_in_cdr_cancel(self):
        """
        Check that we correctly detect errors reported in the ResponseCode field of the CDR
        when cancelling an invoice.
        """
        today = _get_pe_current_datetime().date()
        yesterday = today - timedelta(1)
        move = self._create_invoice(invoice_date=yesterday, date=yesterday, name='F FFI-%s4' % self.time_name)
        move.action_post()

        doc = move.edi_document_ids.filtered(lambda d: d.state in ('to_send', 'to_cancel'))
        move.action_process_edi_web_services(with_commit=False)
        self.assertRecordValues(doc, [{'error': False}])
        self.assertRecordValues(move, [{'edi_state': 'sent'}])

        # Slightly tweak the cancellation request template so that SUNAT's response will contain an error in the CDR's ResponseCode.
        cancel_request_template = self.env.ref('l10n_pe_edi.ubl_pe_21_voided_documents')
        arch = cancel_request_template.arch
        arch_new = arch.replace('<cbc:ReferenceDate t-out="reference_date"/>', '<cbc:ReferenceDate>{}</cbc:ReferenceDate>'.format(today))
        cancel_request_template.write({'arch': arch_new})

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

        # We need to wait a bit before requesting the cancellation's status
        # to avoid getting a status code 98 (cancellation still being processed).
        for _ in range(MAX_WAIT_ITER):
            sleep(10)
            move.action_process_edi_web_services(with_commit=False)
            if doc.error and doc.error != CODE_98_ERROR_MSG:
                break

        expected_error = "<p>We got an error response from the OSE. <br><br><b>Original message:</b><br>2375|Fecha de emision del comprobante no coincide con la fecha de emision consignada en la comunicación"
        self.assertTrue(doc.error.startswith(expected_error), 'Error response: %s' % doc.error)
        self.assertRecordValues(move, [{'edi_state': 'to_cancel'}])
