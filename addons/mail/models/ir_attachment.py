# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields
from odoo.exceptions import AccessError
from odoo.http import request


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    link_preview_ids = fields.One2many('mail.link.preview', 'attachment_id', string='link preview data')

    def _post_add_create(self):
        """ Overrides behaviour when the attachment is created through the controller
        """
        super(IrAttachment, self)._post_add_create()
        for record in self:
            record.register_as_main_attachment(force=False)

    def register_as_main_attachment(self, force=True):
        """ Registers this attachment as the main one of the model it is
        attached to.
        """
        self.ensure_one()
        if not self.res_model:
            return
        related_record = self.env[self.res_model].browse(self.res_id)
        if not related_record.check_access_rights('write', raise_exception=False):
            return
        # message_main_attachment_id field can be empty, that's why we compare to False;
        # we are just checking that it exists on the model before writing it
        if related_record and hasattr(related_record, 'message_main_attachment_id'):
            if force or not related_record.message_main_attachment_id:
                #Ignore AccessError, if you don't have access to modify the document
                #Just don't set the value
                try:
                    related_record.message_main_attachment_id = self
                except AccessError:
                    pass

    def _attachment_format(self):
        safari = request and request.httprequest.user_agent.browser == 'safari'
        attachments = []
        for attachment in self:
            # This will rebuild the link preview that have been deleted by the
            # cron when they are requested again
            if attachment.url and not attachment.sudo().link_preview_ids:
                opengraph = self.env['mail.link.preview'].get_open_graph_data(attachment.url)
                if opengraph:
                    self.env['mail.link.preview'].sudo().create({
                        'attachment_id': attachment.id,
                        'type': opengraph.get('type'),
                        'url': opengraph.get('url'),
                        'title': opengraph.get('title'),
                        'image_url': opengraph.get('image'),
                        'description': opengraph.get('description'),
                    })
            attachments.append({
                'checksum': attachment.checksum,
                'id': attachment.id,
                'filename': attachment.name,
                'name': attachment.name,
                'mimetype': 'application/octet-stream' if safari and attachment.mimetype and 'video' in attachment.mimetype else attachment.mimetype,
                'res_id': attachment.res_id,
                'res_model': attachment.res_model,
                'url': attachment.url,
                'link_preview': attachment.sudo().link_preview_ids._link_preview_format()
            })
        return attachments
