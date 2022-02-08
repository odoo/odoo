# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.addons.account_edi.tests.common import AccountEdiTestCommon, _mocked_post_two_steps, _generate_mocked_needs_web_services, _mocked_cancel_failed, _generate_mocked_support_batching
from unittest.mock import patch
from odoo.addons.base.tests.test_ir_cron import CronMixinCase


class TestAccountEdi(AccountEdiTestCommon, CronMixinCase):

    @classmethod
    def setUpClass(cls, chart_template_ref=None, edi_format_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref, edi_format_ref=edi_format_ref)

        cls.invoice = cls.init_invoice('out_invoice', products=cls.product_a + cls.product_b)

    def test_export_edi(self):
        self.assertEqual(len(self.invoice.edi_document_ids), 0)
        self.invoice.action_post()
        self.assertEqual(len(self.invoice.edi_document_ids), 1)

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

    @patch('odoo.addons.account_edi.models.account_edi_format.AccountEdiFormat._post_invoice_edi', return_value={})
    def test_warning_is_retried(self, patched):
        with patch('odoo.addons.account_edi.models.account_edi_format.AccountEdiFormat._needs_web_services',
                   new=lambda edi_format: True):
            edi_docs = self.create_edi_document(self.edi_format, 'to_send')
            edi_docs.error = 'Test Error'
            edi_docs.blocking_level = 'warning'

            edi_docs.move_id.action_process_edi_web_services()
            patched.assert_called_once()

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
            doc._process_documents_web_services(with_commit=False)
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
            doc._process_documents_web_services(with_commit=False)
            self.assertEqual(doc.state, 'to_cancel')
            self.assertEqual(self.invoice.state, 'posted')

            # Call off edi Cancellation
            self.invoice.button_abandon_cancel_posted_posted_moves()
            self.assertEqual(doc.state, 'sent')
            self.assertIsNotNone(doc.error)

    def test_edi_flow_two_step_cancel_with_call_off_request(self):
        def _mock_cancel(edi_format, invoices):
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

    def test_cron_triggers(self):
        with self.capture_triggers('account_edi.ir_cron_edi_network') as capt, \
         self.mock_edi(_needs_web_services_method=_generate_mocked_needs_web_services(True)):
            self.invoice._get_edi_document(self.edi_format)
            self.invoice.action_post()
            capt.records.ensure_one()

    def test_cron_self_trigger(self):
        # Process single job by CRON call (and thus, disable the auto-commit).
        edi_cron = self.env.ref('account_edi.ir_cron_edi_network')
        edi_cron.code = 'model._cron_process_documents_web_services(job_count=1)'

        # Create invoices.
        invoices = self.env['account.move'].create([{
            'move_type': 'out_invoice',
            'invoice_date': '2019-01-01',
            'date': '2019-01-01',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({'product_id': self.product_a.id})],
        } for i in range(4)])

        with self.capture_triggers('account_edi.ir_cron_edi_network') as capt, \
             self.mock_edi(_needs_web_services_method=_generate_mocked_needs_web_services(True)):
            invoices.action_post()

            self.env.ref('account_edi.ir_cron_edi_network').method_direct_trigger()
            self.assertEqual(len(capt.records), 2, "Not all records have been processed in this run, the cron should "
                                                   "re-trigger itself to process some more later")

    def test_prepare_edi_vals_to_export(self):
        """
            Test _prepare_edi_vals_to_export return values
            in the proper format

            tag_ids should be a set of id and tags a proper recordset
        """
        account_tag = self.env['account.account.tag'].create({
            "applicability": "taxes",
            "country_id": self.env.ref('base.us').id,
            "name": "Test Tag",
        })
        tax = self.env['account.tax'].create({
            "amount": 15,
            "amount_type": "percent",
            "description": "15%",
            "country_id": self.env.ref('base.us').id,
            "invoice_repartition_line_ids": [
                Command.create({
                    "factor_percent": 100,
                    "repartition_type": "base",
                    "sequence": 1,
                }),
                Command.create({
                    "factor_percent": 100,
                    "repartition_type": "tax",
                    "sequence": 1,
                    "tag_ids": [Command.link(account_tag.id)]
                })
            ],
            "name": "Test",
            "tax_exigibility": "on_invoice",
            "type_tax_use": "sale"
        })

        invoices = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'invoice_date': '2019-01-01',
            'date': '2019-01-01',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
                'tax_ids': [Command.link(tax.id)]
            })],
        })
        vals = invoices._prepare_edi_vals_to_export()
        self.assertEqual(
            vals['invoice_line_vals_list'][0]['tax_detail_vals_list'][0]['tag_ids'], set(account_tag.ids))
        self.assertEqual(
            vals['invoice_line_vals_list'][0]['tax_detail_vals_list'][0]['tags'].name, "Test Tag")

    def test_invoice_ready_to_be_sent(self):
        def _is_needed_for_invoice(edi_format, invoice):
            return True

        with self.mock_edi(
                _needs_web_services_method=_generate_mocked_needs_web_services(True),
                _is_required_for_invoice_method=_is_needed_for_invoice,
        ):
            self.invoice.action_post()
            doc = self.invoice._get_edi_document(self.edi_format)
            self.assertFalse(self.invoice._is_ready_to_be_sent())
            doc._process_documents_web_services(with_commit=False)
            self.assertTrue(self.invoice._is_ready_to_be_sent())
