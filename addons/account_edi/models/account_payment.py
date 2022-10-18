# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    edi_show_cancel_button = fields.Boolean(
        compute='_compute_edi_show_cancel_button')

    @api.depends(
        'state',
        'move_id.edi_document_ids.state',
        'move_id.edi_document_ids.attachment_id')
    def _compute_edi_show_cancel_button(self):
        for payment in self:
            if payment.state != 'posted':
                payment.edi_show_cancel_button = False
                continue

            payment.edi_show_cancel_button = any([doc.edi_format_id._needs_web_services()
                                                  and doc.attachment_id
                                                  and doc.state == 'sent'
                                                  and payment.reconciled_invoice_ids.is_invoice(include_receipts=True)
                                                  and doc.edi_format_id._is_required_for_invoice(payment.reconciled_invoice_ids)
                                                  for doc in payment.edi_document_ids])

    def action_process_edi_web_services(self):
        return self.move_id.action_process_edi_web_services()

    def button_cancel_posted_payments(self):
        """
        Mark the edi.document related to this payment to be canceled.
        """
        to_cancel_documents = self.env['account.edi.document']
        for payment in self:
            is_payment_marked = False
            for doc in payment.edi_document_ids:
                if doc.edi_format_id._needs_web_services() \
                        and doc.attachment_id \
                        and doc.state == 'sent' \
                        and payment.reconciled_invoice_ids.is_invoice(include_receipts=True) \
                        and doc.edi_format_id._is_required_for_invoice(payment.reconciled_invoice_ids):
                    to_cancel_documents |= doc
                    is_payment_marked = True
            if is_payment_marked:
                payment.message_post(body=_("A cancellation of the EDI has been requested."))
            payment.move_id.line_ids.remove_move_reconcile()
            payment.action_draft()
            payment.action_cancel()
        to_cancel_documents.write({'state': 'to_cancel', 'error': False, 'blocking_level': False})
