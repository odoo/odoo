# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    def _message_post_process_attachments(self, attachments, attachment_ids, message_values):
        """ This method extension ensures that, when using the "Send & Print" feature, if the user
        adds an attachment, the latter will be linked to the record.

        # Task-2792146: will move to model-based method
        """
        record = self.env.context.get('attached_to')
        # link mail.compose.message attachments to attached_to
        if record and record._name in ('account.move', 'account.payment'):
            message_values['model'] = record._name
            message_values['res_id'] = record.id
        res = super()._message_post_process_attachments(attachments, attachment_ids, message_values)
        # link account.invoice.send attachments to attached_to
        model = message_values['model']
        res_id = message_values['res_id']
        att_ids = [att[1] for att in res.get('attachment_ids') or []]
        if att_ids and model == 'account.move':
            filtered_attachment_ids = self.env['ir.attachment'].sudo().browse(att_ids).filtered(
                lambda a: a.res_model in ('account.invoice.send',) and a.create_uid.id == self._uid)
            if filtered_attachment_ids:
                filtered_attachment_ids.write({'res_model': model, 'res_id': res_id})
        elif model == 'account.payment':
            attachments_to_link = self.env['ir.attachment'].sudo().browse(att_ids).filtered(
                lambda a: a.res_model in ('mail.message',) and a.create_uid.id == self._uid)
            attachments_to_link.write({'res_model': model, 'res_id': res_id})
        return res
