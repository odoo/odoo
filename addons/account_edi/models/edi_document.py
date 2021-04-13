# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
from psycopg2 import OperationalError
import logging

_logger = logging.getLogger(__name__)

DEFAULT_BLOCKING_LEVEL = 'error'


class EdiDocument(models.Model):
    _inherit = 'edi.document'
    _description = 'Electronic Document for an account.move'

    # == Stored fields ==
    move_id = fields.Many2one('account.move', required=True, ondelete='cascade')


    def _prepare_jobs(self):
        """Creates a list of jobs to be performed by '_process_job' for the documents in self.
        Each document represent a job, BUT if multiple documents have the same state, edi_format_id,
        doc_type (invoice or payment) and company_id AND the edi_format_id supports batching, they are grouped
        into a single job.

        :returns:         A list of tuples (documents, doc_type)
        * documents:      The documents related to this job. If edi_format_id does not support batch, length is one
        * doc_type:       Are the moves of this job invoice or payments ?
        """

        # Classify jobs by (edi_format, edi_doc.state, doc_type, move.company_id, custom_key)
        to_process = {}
        documents = self.filtered(lambda d: d.state in ('to_send', 'to_cancel') and d.blocking_level != 'error')
        for edi_doc in documents:
            move = edi_doc.move_id
            edi_format = edi_doc.edi_format_id
            if move.is_invoice(include_receipts=True):
                doc_type = 'invoice'
            elif move.payment_id or move.statement_line_id:
                doc_type = 'payment'
            else:
                continue

            custom_key = edi_format._get_batch_key(edi_doc.move_id, edi_doc.state)
            key = (edi_format, edi_doc.state, doc_type, move.company_id, custom_key)
            to_process.setdefault(key, self.env['edi.document'])
            to_process[key] |= edi_doc

        # Order payments/invoice and create batches.
        invoices = []
        payments = []
        for key, documents in to_process.items():
            edi_format, state, doc_type, company_id, custom_key = key
            target = invoices if doc_type == 'invoice' else payments
            batch = self.env['edi.document']
            for doc in documents:
                if edi_format._support_batching(move=doc.move_id, state=state, company=company_id):
                    batch |= doc
                else:
                    target.append((doc, doc_type))
            if batch:
                target.append((batch, doc_type))
        return invoices + payments

    @api.model
    def _process_job(self, documents, doc_type):
        """Post or cancel move_id (invoice or payment) by calling the related methods on edi_format_id.
        Invoices are processed before payments.

        :param documents: The documents related to this job. If edi_format_id does not support batch, length is one
        :param doc_type:  Are the moves of this job invoice or payments ?
        """
        def _postprocess_post_edi_results(documents, edi_result):
            attachments_to_unlink = self.env['ir.attachment']
            for document in documents:
                move = document.move_id
                move_result = edi_result.get(move, {})
                if move_result.get('attachment'):
                    old_attachment = document.attachment_id
                    values = {
                        'attachment_id': move_result['attachment'].id,
                        'error': move_result.get('error', False),
                        'blocking_level': move_result.get('blocking_level', DEFAULT_BLOCKING_LEVEL) if 'error' in move_result else False,
                    }
                    if not values.get('error'):
                        values.update({'state': 'sent'})
                    document.write(values)
                    if not old_attachment.res_model or not old_attachment.res_id:
                        attachments_to_unlink |= old_attachment
                else:
                    document.write({
                        'error': move_result.get('error', False),
                        'blocking_level': move_result.get('blocking_level', DEFAULT_BLOCKING_LEVEL) if 'error' in move_result else False,
                    })

            # Attachments that are not explicitly linked to a business model could be removed because they are not
            # supposed to have any traceability from the user.
            attachments_to_unlink.unlink()

        def _postprocess_cancel_edi_results(documents, edi_result):
            invoice_ids_to_cancel = set()  # Avoid duplicates
            attachments_to_unlink = self.env['ir.attachment']
            for document in documents:
                move = document.move_id
                move_result = edi_result.get(move, {})
                if move_result.get('success') is True:
                    old_attachment = document.attachment_id
                    document.write({
                        'state': 'cancelled',
                        'error': False,
                        'attachment_id': False,
                        'blocking_level': False,
                    })

                    if move.is_invoice(include_receipts=True) and move.state == 'posted':
                        # The user requested a cancellation of the EDI and it has been approved. Then, the invoice
                        # can be safely cancelled.
                        invoice_ids_to_cancel.add(move.id)

                    if not old_attachment.res_model or not old_attachment.res_id:
                        attachments_to_unlink |= old_attachment

                elif not move_result.get('success'):
                    document.write({
                        'error': move_result.get('error', False),
                        'blocking_level': move_result.get('blocking_level', DEFAULT_BLOCKING_LEVEL) if move_result.get('error') else False,
                    })

            if invoice_ids_to_cancel:
                invoices = self.env['account.move'].browse(list(invoice_ids_to_cancel))
                invoices.button_draft()
                invoices.button_cancel()

            # Attachments that are not explicitly linked to a business model could be removed because they are not
            # supposed to have any traceability from the user.
            attachments_to_unlink.unlink()

        test_mode = self._context.get('edi_test_mode', False)

        documents.edi_format_id.ensure_one()  # All edi.document of a job should have the same edi_format_id
        documents.move_id.company_id.ensure_one()  # All edi.document of a job should be from the same company
        if len(set(doc.state for doc in documents)) != 1:
            raise ValueError('All edi.document of a job should have the same state')

        edi_format = documents.edi_format_id
        state = documents[0].state
        if doc_type == 'invoice':
            if state == 'to_send':
                edi_result = edi_format._post_invoice_edi(documents.move_id, test_mode=test_mode)
                _postprocess_post_edi_results(documents, edi_result)
            elif state == 'to_cancel':
                edi_result = edi_format._cancel_invoice_edi(documents.move_id, test_mode=test_mode)
                _postprocess_cancel_edi_results(documents, edi_result)

        elif doc_type == 'payment':
            if state == 'to_send':
                edi_result = edi_format._post_payment_edi(documents.move_id, test_mode=test_mode)
                _postprocess_post_edi_results(documents, edi_result)
            elif state == 'to_cancel':
                edi_result = edi_format._cancel_payment_edi(documents.move_id, test_mode=test_mode)
                _postprocess_cancel_edi_results(documents, edi_result)

    def _process_documents_no_web_services(self):
        """ Post and cancel all the documents that don't need a web service.
        """
        jobs = self.filtered(lambda d: not d.edi_format_id._needs_web_services())._prepare_jobs()
        for documents, doc_type in jobs:
            self._process_job(documents, doc_type)

    def _process_documents_web_services(self, job_count=None, with_commit=True):
        ''' Post and cancel all the documents that need a web service.

        :param job_count:   The maximum number of jobs to process if specified.
        :param with_commit: Flag indicating a commit should be made between each job.
        :return:            The number of remaining jobs to process.
        '''
        all_jobs = self.filtered(lambda d: d.edi_format_id._needs_web_services())._prepare_jobs()
        jobs_to_process = all_jobs[0:job_count] if job_count else all_jobs

        for documents, doc_type in jobs_to_process:
            move_to_cancel = documents.filtered(lambda doc: doc.attachment_id \
                                                    and doc.state == 'to_cancel' \
                                                    and doc.move_id.is_invoice(include_receipts=True) \
                                                    and doc.edi_format_id._is_required_for_invoice(doc.move_id)).move_id
            attachments_potential_unlink = documents.attachment_id.filtered(lambda a: not a.res_model and not a.res_id)
            try:
                with self.env.cr.savepoint(flush=False):
                    self._cr.execute('SELECT * FROM account_edi_document WHERE id IN %s FOR UPDATE NOWAIT', [tuple(documents.ids)])
                    # Locks the move that will be cancelled.
                    if move_to_cancel:
                        self._cr.execute('SELECT * FROM account_move WHERE id IN %s FOR UPDATE NOWAIT', [tuple(move_to_cancel.ids)])

                    # Locks the attachments that might be unlinked
                    if attachments_potential_unlink:
                        self._cr.execute('SELECT * FROM ir_attachment WHERE id IN %s FOR UPDATE NOWAIT', [tuple(attachments_potential_unlink.ids)])

                    self._process_job(documents, doc_type)
            except OperationalError as e:
                if e.pgcode == '55P03':
                    _logger.debug('Another transaction already locked documents rows. Cannot process documents.')
                else:
                    raise e
            else:
                if with_commit and len(jobs_to_process) > 1:
                    self.env.cr.commit()

        return len(all_jobs) - len(jobs_to_process)

    @api.model
    def _cron_process_documents_web_services(self, job_count=None):
        ''' Method called by the EDI cron processing all web-services.

        :param job_count: Limit explicitely the number of web service calls. If not provided, process all.
        '''
        edi_documents = self.search([('state', 'in', ('to_send', 'to_cancel'))])
        nb_remaining_jobs = edi_documents._process_documents_web_services(job_count=job_count)

        # Mark the CRON to be triggered again asap since there is some remaining jobs to process.
        if nb_remaining_jobs > 0:
            self.env.ref('account_edi.ir_cron_edi_network')._trigger()
