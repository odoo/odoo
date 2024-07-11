# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class MailMainAttachmentMixin(models.AbstractModel):
    """ Mixin that adds main attachment support to the MailThread class. """

    _name = 'mail.thread.main.attachment'
    _inherit = 'mail.thread'
    _description = 'Mail Main Attachment management'

    message_main_attachment_id = fields.Many2one(string="Main Attachment", comodel_name='ir.attachment', copy=False)

    def _message_post_after_hook(self, message, msg_values):
        """ Set main attachment field if necessary """
        super()._message_post_after_hook(message, msg_values)
        self.sudo()._message_set_main_attachment_id([
            attachment_command[1]
            for attachment_command in (msg_values['attachment_ids'] or [])
        ])

    def _message_set_main_attachment_id(self, attachment_ids):
        if attachment_ids and not self.message_main_attachment_id:
            # we filter out attachment with 'xml' and 'octet' types
            attachments = self.env['ir.attachment'].browse(attachment_ids).filtered(lambda r: not r.mimetype.endswith('xml')
                                                                                              and not r.mimetype.endswith('application/octet-stream'))

            # Assign one of the attachments as the main according to the following priority: pdf, image, other types.
            if attachments:
                self.with_context(tracking_disable=True).message_main_attachment_id = max(
                    attachments,
                    key=lambda r: (r.mimetype.endswith('pdf'), r.mimetype.startswith('image'))
                ).id

    def _get_mail_thread_data(self, request_list):
        res = super()._get_mail_thread_data(request_list)
        if 'attachments' in request_list:
            res['mainAttachment'] = {'id': self.message_main_attachment_id.id} if self.message_main_attachment_id else False
        return res
