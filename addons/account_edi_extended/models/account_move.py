# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields, _


class AccountMove(models.Model):
    _inherit = 'account.move'

    edi_show_abandon_cancel_button = fields.Boolean(
        compute='_compute_edi_show_abandon_cancel_button')

    @api.depends(
        'edi_document_ids',
        'edi_document_ids.state',
        'edi_document_ids.blocked_level',
        'edi_document_ids.edi_format_id',
        'edi_document_ids.edi_format_id.name')
    def _compute_edi_web_services_to_process(self):
        # OVERRIDE to take blocked_level into account
        for move in self:
            to_process = move.edi_document_ids.filtered(lambda d: d.state in ['to_send', 'to_cancel'] and d.blocked_level != 'error')
            format_web_services = to_process.edi_format_id.filtered(lambda f: f._needs_web_services())
            move.edi_web_services_to_process = ', '.join(f.name for f in format_web_services)

    @api.depends(
        'state',
        'edi_document_ids.state',
        'edi_document_ids.attachment_id')
    def _compute_edi_show_abandon_cancel_button(self):
        for move in self:
            move.edi_show_abandon_cancel_button = any([doc.edi_format_id._needs_web_services()
                                                       and doc.state == 'to_cancel'
                                                       and move.is_invoice(include_receipts=True)
                                                       and doc.edi_format_id._is_required_for_invoice(move)
                                                       for doc in move.edi_document_ids])

    def action_retry_edi_documents_error(self):
        self.edi_document_ids.write({'error': False, 'blocked_level': False})
        self.action_process_edi_web_services()

    def button_abandon_cancel_posted_posted_moves(self):
        '''Mark the edi.document related to this move to be canceled.
        '''
        documents = self.env['account.edi.document']
        for move in self:
            is_move_marked = False
            for doc in move.edi_document_ids:
                if doc.state == 'to_cancel' \
                        and move.is_invoice(include_receipts=True) \
                        and doc.edi_format_id._is_required_for_invoice(move):
                    documents |= doc
                    is_move_marked = True
            if is_move_marked:
                move.message_post(body=_("A request for cancellation of the EDI has been called off."))

        documents.write({'state': 'sent'})
