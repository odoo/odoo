# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    edi_show_cancel_button = fields.Boolean(
        compute='_compute_edi_show_cancel_button')
    edi_show_abandon_cancel_button = fields.Boolean(
        compute='_compute_edi_show_abandon_cancel_button')

    @api.depends('state', 'edi_document_ids.state')
    def _compute_edi_show_cancel_button(self):
        for payment in self:
            if payment.state != 'posted':
                payment.edi_show_cancel_button = False
                continue

            payment.edi_show_cancel_button = any([doc.edi_format_id._needs_web_services()
                                                  and doc.state == 'sent'
                                                  for doc in payment.edi_document_ids])

    @api.depends('state', 'edi_document_ids.state')
    def _compute_edi_show_abandon_cancel_button(self):
        for payment in self:
            payment.edi_show_abandon_cancel_button = any(doc.edi_format_id._needs_web_services()
                                                         and doc.state == 'to_cancel'
                                                         for doc in payment.edi_document_ids)

    def action_process_edi_web_services(self):
        return self.move_id.action_process_edi_web_services()

    def action_retry_edi_documents_error(self):
        self.ensure_one()
        return self.move_id.action_retry_edi_documents_error()

    def button_cancel_posted_payments(self):
        """
        Mark the edi.document related to this payment to be canceled.
        """
        to_cancel_documents = self.env['account.edi.document']
        for payment in self:
            payment.move_id._check_fiscalyear_lock_date()
            is_payment_marked = False
            for doc in payment.edi_document_ids:
                if doc.edi_format_id._needs_web_services() and doc.attachment_id and doc.state == 'sent':
                    to_cancel_documents |= doc
                    is_payment_marked = True
            if is_payment_marked:
                payment.message_post(body=_("A cancellation of the EDI has been requested."))
        to_cancel_documents.write({'state': 'to_cancel', 'error': False, 'blocking_level': False})

    def button_abandon_cancel_posted_payments(self):
        '''Cancel the request for cancellation of the EDI.
        '''
        documents = self.env['account.edi.document']
        for payment in self:
            is_payment_marked = False
            for doc in payment.edi_document_ids:
                if doc.state == 'to_cancel':
                    documents |= doc
                    is_payment_marked = True
            if is_payment_marked:
                payment.message_post(body=_("A request for cancellation of the EDI has been called off."))

        documents.write({'state': 'sent'})
