# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.addons.edi.models.edi_flow import DEFAULT_BLOCKING_LEVEL


class EdiFlow(models.Model):
    _inherit = 'edi.flow'

    @api.model
    def _process_job(self, flows, document_type):
        """Post or cancel move_id (invoice or payment) by calling the related methods on edi_format_id.
        Invoices are processed before payments.
        """
        if flows.edi_format_id.applicability != "accounting":
            return super()._process_job(flows, document_type)
        flows.edi_format_id.ensure_one()  # All account.edi.document of a job should have the same edi_format_id
        if len(set(flow.state for flow in flows)) != 1:
            raise ValueError('All edi.flows of a job should have the same state')
        for flow in flows:
            if flow.flow_type == 'send':
                if document_type == 'invoice':
                    with flows._get_documents().filtered(lambda m: m.id == flow.res_id)._send_only_when_ready():
                        edi_result = flows._do_stage()
                        self._postprocess_post_edi_results(flows, edi_result)
                elif document_type == 'payment':
                    edi_result = flows._do_stage()
                    self._postprocess_post_edi_results(flows, edi_result)
            elif flow.flow_type == 'cancel':
                edi_result = flows._do_stage()
                self._postprocess_cancel_edi_results(flows, edi_result)

    @api.model
    def _postprocess_post_edi_results(self, flows, edi_result):
        if flows.edi_format_id.applicability != "accounting":
            return super()._postprocess_cancel_edi_results(flows, edi_result)
        for flow in flows:
            result = (edi_result or {}).get(flow.res_id, {})
            if result.get('success'):
                flow._move_to_next_stage()
            else:
                flows.write({
                    'error': result.get('error', False),
                    'blocking_level': result.get('blocking_level', DEFAULT_BLOCKING_LEVEL) if 'error' in result else False,
                })

    @api.model
    def _postprocess_cancel_edi_results(self, flows, edi_result):
        if flows.edi_format_id.applicability != "accounting":
            return super()._postprocess_cancel_edi_results(flows, edi_result)

        invoices_to_cancel = self.env['account.move']
        moves = flows._get_documents()
        for flow in flows:
            move = moves.filtered(lambda m: m.id == flow.res_id)
            move_result = (edi_result or {}).get(move.id, {})
            if move_result.get('success'):
                flow._move_to_next_stage()
                if move.is_invoice(include_receipts=True) and move.state == 'posted':
                    # The user requested a cancellation of the EDI, and it has been approved. Then, the invoice
                    # can be safely cancelled.
                    invoices_to_cancel | move
            else:
                flow.write({
                    'error': move_result.get('error', False),
                    'blocking_level': move_result.get('blocking_level', DEFAULT_BLOCKING_LEVEL) if move_result.get(
                        'error') else False,
                })

        if invoices_to_cancel:
            invoices_to_cancel.button_draft()
            invoices_to_cancel.button_cancel()

    @api.model
    def _abandon_cancel_flow_conditions(self, document):
        """ Check if the document can be cancelled.
        To override for specific cases.
        :param document: The document to check.
        :return: True if the document can be cancelled, False otherwise.
        """
        if document._name != 'account.move':
            return super()._abandon_cancel_flow_conditions(document)
        return document.is_invoice(include_receipts=True) and self.edi_format_id._is_format_required(document, document._get_document_type())
