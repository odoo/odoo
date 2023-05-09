# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    def action_process_edi_web_services(self):
        return self.move_id.action_process_edi_web_services()

    def action_retry_edi_documents_error(self):
        self.ensure_one()
        return self.move_id.action_retry_edi_documents_error()

    ####################################################
    # Mailing
    ####################################################

    def _process_attachments_for_template_post(self, mail_template):
        """ Add Edi attachments to templates. """
        result = super()._process_attachments_for_template_post(mail_template)
        for payment in self.filtered('edi_document_ids'):
            payment_result = result.setdefault(payment.id, {})
            for edi_doc in payment.edi_document_ids:
                edi_attachments = edi_doc._filter_edi_attachments_for_mailing()
                payment_result.setdefault('attachment_ids', []).extend(edi_attachments.get('attachment_ids', []))
                payment_result.setdefault('attachments', []).extend(edi_attachments.get('attachments', []))
        return result
