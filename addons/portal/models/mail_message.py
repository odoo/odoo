# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class MailMessage(models.Model):
    _inherit = 'mail.message'

    def portal_message_format(self):
        return self._portal_message_format([
            'id', 'body', 'date', 'author_id', 'email_from',  # base message fields
            'message_type', 'subtype_id', 'is_internal', 'subject',  # message specific
            'model', 'res_id', 'record_name',  # document related
        ])

    def _portal_message_format(self, fields_list):
        vals_list = self._message_format(fields_list, legacy=True)
        message_subtype_note_id = self.env['ir.model.data']._xmlid_to_res_id('mail.mt_note')
        IrAttachmentSudo = self.env['ir.attachment'].sudo()
        for vals in vals_list:
            vals['is_message_subtype_note'] = message_subtype_note_id and (vals.get('subtype_id') or [False])[0] == message_subtype_note_id
            for attachment in vals.get('attachment_ids', []):
                if not attachment.get('access_token'):
                    attachment['access_token'] = IrAttachmentSudo.browse(attachment['id']).generate_access_token()[0]
        return vals_list
