# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class MailMessage(models.Model):
    _inherit = 'mail.message'

    @api.multi
    def portal_message_format(self):
        return self._portal_message_format([
            'id', 'body', 'date', 'author_id', 'email_from',  # base message fields
            'message_type', 'subtype_id', 'subject',  # message specific
            'model', 'res_id', 'record_name',  # document related
        ])

    @api.multi
    def _portal_message_format(self, fields_list):
        message_values = self.read(fields_list)
        message_tree = dict((m.id, m) for m in self.sudo())
        self._message_read_dict_postprocess(message_values, message_tree)
        for value in message_values:
            for attach in value.get('attachment_ids', False):
                attachment = self.env['ir.attachment'].browse(attach['id'])
                access_token = attachment.sudo().generate_access_token()
                attach.update({'access_token': access_token})
        return message_values

    @api.model
    def _non_employee_message_domain(self):
        return ['&', ('subtype_id', '!=', False), ('subtype_id.internal', '=', False)]

    @api.multi
    def _post_process_portal_attachments(self, res_model, res_id, attachment_tokens):
        self.ensure_one()
        if not attachment_tokens:
            return False
        attachment_ids = self.env['ir.attachment'].sudo().search([
            ('res_model', '=', 'mail.compose.message'),
            ('res_id', '=', 0),
            ('access_token', 'in', attachment_tokens)])
        if attachment_ids:
            attachment_ids.write({'res_model': res_model, 'res_id': res_id})
            self.attachment_ids = [(4, attachment_id) for attachment_id in attachment_ids.ids]
