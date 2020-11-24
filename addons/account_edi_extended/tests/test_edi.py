
# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.account_edi_extended.tests.common import AccountEdiExtendedTestCommon, _mocked_post, _mocked_post_two_steps, _generate_mocked_needs_web_services, _mocked_cancel_failed, _generate_mocked_support_batching


class TestAccountEdi(AccountEdiExtendedTestCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None, edi_format_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref, edi_format_ref=edi_format_ref)

        cls.invoice = cls.init_invoice('out_invoice', products=cls.product_a + cls.product_b)

    def test_edi_flow(self):
        with self.mock_edi():
            doc = self.invoice._get_edi_document(self.edi_format)
            self.assertFalse(doc)
            self.invoice.action_post()
            doc = self.invoice._get_edi_document(self.edi_format)
            self.assertEqual(len(doc), 1)
            self.assertEqual(doc.state, 'sent')
            self.invoice.button_draft()
            self.invoice.button_cancel()
            self.assertEqual(doc.state, 'cancelled')

    def test_edi_flow_two_steps(self):
        with self.mock_edi(_post_invoice_edi_method=_mocked_post_two_steps,
                           _needs_web_services_method=_generate_mocked_needs_web_services(True)):
            doc = self.invoice._get_edi_document(self.edi_format)
            self.assertFalse(doc)
            self.invoice.action_post()
            doc = self.invoice._get_edi_document(self.edi_format)
            self.assertEqual(len(doc), 1)
            self.assertEqual(doc.state, 'to_send')
            doc._process_documents_web_services(with_commit=False)
            self.assertEqual(doc.state, 'to_send')
            doc._process_documents_web_services(with_commit=False)
            self.assertEqual(doc.state, 'sent')

    def test_edi_flow_request_cancel_success(self):
        with self.mock_edi(_needs_web_services_method=_generate_mocked_needs_web_services(True)):
            self.assertEqual(self.invoice.state, 'draft')
            self.invoice.action_post()
            doc = self.invoice._get_edi_document(self.edi_format)
            self.assertEqual(doc.state, 'to_send')
            self.assertEqual(self.invoice.state, 'posted')
            doc._process_documents_web_services(with_commit=False)
            self.assertEqual(doc.state, 'sent')
            self.assertEqual(self.invoice.state, 'posted')
            self.invoice.button_cancel_posted_moves()
            self.assertEqual(doc.state, 'to_cancel')
            self.assertEqual(self.invoice.state, 'posted')
            doc._process_documents_web_services()
            self.assertEqual(doc.state, 'cancelled')
            self.assertEqual(self.invoice.state, 'cancel')

    def test_edi_flow_request_cancel_failed(self):
        with self.mock_edi(_needs_web_services_method=_generate_mocked_needs_web_services(True),
                           _cancel_invoice_edi_method=_mocked_cancel_failed):
            self.assertEqual(self.invoice.state, 'draft')
            self.invoice.action_post()
            doc = self.invoice._get_edi_document(self.edi_format)
            self.assertEqual(doc.state, 'to_send')
            self.assertEqual(self.invoice.state, 'posted')
            doc._process_documents_web_services(with_commit=False)
            self.assertEqual(doc.state, 'sent')
            self.assertEqual(self.invoice.state, 'posted')
            self.invoice.button_cancel_posted_moves()
            self.assertEqual(doc.state, 'to_cancel')
            self.assertEqual(self.invoice.state, 'posted')
            # Call off edi Cancellation
            self.invoice.button_abandon_cancel_posted_posted_moves()
            self.assertEqual(doc.state, 'sent')
            self.assertFalse(doc.error)

            # Failed cancel
            self.invoice.button_cancel_posted_moves()
            self.assertEqual(doc.state, 'to_cancel')
            self.assertEqual(self.invoice.state, 'posted')
            doc._process_documents_web_services()
            self.assertEqual(doc.state, 'to_cancel')
            self.assertEqual(self.invoice.state, 'posted')

            # Call off edi Cancellation
            self.invoice.button_abandon_cancel_posted_posted_moves()
            self.assertEqual(doc.state, 'sent')
            self.assertIsNotNone(doc.error)

    def test_edi_flow_two_step_cancel_with_call_off_request(self):
        def _mock_cancel(edi_format, invoices, test_mode):
            invoices_no_ref = invoices.filtered(lambda i: not i.ref)
            if len(invoices_no_ref) == len(invoices):  # first step
                invoices_no_ref.ref = 'test_ref_cancel'
                return {invoice: {} for invoice in invoices}
            elif len(invoices_no_ref) == 0:  # second step
                for invoice in invoices:
                    invoice.ref = None
                return {invoice: {'success': True} for invoice in invoices}
            else:
                raise ValueError('wrong use of "_mocked_post_two_steps"')

        def _is_needed_for_invoice(edi_format, invoice):
            return not bool(invoice.ref)

        with self.mock_edi(_needs_web_services_method=_generate_mocked_needs_web_services(True),
                           _is_required_for_invoice_method=_is_needed_for_invoice,
                           _cancel_invoice_edi_method=_mock_cancel):
            self.invoice.action_post()
            doc = self.invoice._get_edi_document(self.edi_format)
            doc._process_documents_web_services(with_commit=False)
            self.assertEqual(doc.state, 'sent')

            # Request Cancellation
            self.invoice.button_cancel_posted_moves()
            doc._process_documents_web_services(with_commit=False)  # first step of cancel
            self.assertEqual(doc.state, 'to_cancel')

            # Call off edi Cancellation
            self.invoice.button_abandon_cancel_posted_posted_moves()
            self.assertEqual(doc.state, 'to_cancel')

            # If we cannot call off edi cancellation, only solution is to post again
            doc._process_documents_web_services(with_commit=False)  # second step of cancel
            self.assertEqual(doc.state, 'cancelled')
            self.invoice.action_post()
            doc._process_documents_web_services(with_commit=False)
            self.assertEqual(doc.state, 'sent')

    def test_batches(self):
        def _get_batch_key_method(edi_format, move, state):
            return (move.ref)

        with self.mock_edi(_get_batch_key_method=_get_batch_key_method,
                           _support_batching_method=_generate_mocked_support_batching(True)):
            edi_docs = self.env['account.edi.document']
            doc1 = self.create_edi_document(self.edi_format, 'to_send')
            edi_docs |= doc1
            doc2 = self.create_edi_document(self.edi_format, 'to_send')
            edi_docs |= doc2
            doc3 = self.create_edi_document(self.edi_format, 'to_send')
            edi_docs |= doc3

            to_process = edi_docs._prepare_jobs()
            self.assertEqual(len(to_process), 1)

            doc1.move_id.ref = 'batch1'
            doc2.move_id.ref = 'batch2'
            doc3.move_id.ref = 'batch3'

            to_process = edi_docs._prepare_jobs()
            self.assertEqual(len(to_process), 3)

            doc2.move_id.ref = 'batch1'
            to_process = edi_docs._prepare_jobs()
            self.assertEqual(len(to_process), 2)
