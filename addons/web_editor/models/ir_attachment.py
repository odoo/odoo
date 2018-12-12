# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug import url_quote

from odoo import api, models, fields, tools


class IrAttachment(models.Model):

    _inherit = "ir.attachment"

    local_url = fields.Char("Attachment URL", compute='_compute_local_url')
    image_src = fields.Char(compute='_compute_image_src')
    image_width = fields.Integer(compute='_compute_image_size')
    image_height = fields.Integer(compute='_compute_image_size')

    def _compute_local_url(self):
        for attachment in self:
            if attachment.url:
                attachment.local_url = attachment.url
            else:
                attachment.local_url = '/web/image/%s?unique=%s' % (attachment.id, attachment.checksum)

    @api.multi
    @api.depends('mimetype', 'url', 'name')
    def _compute_image_src(self):
        for attachment in self:
            if attachment.mimetype not in ['image/gif', 'image/jpe', 'image/jpeg', 'image/jpg', 'image/gif', 'image/png', 'image/svg+xml']:
                attachment.image_src = False
            else:
                attachment.image_src = attachment.url or '/web/image/%s/%s' % (
                    attachment.id,
                    url_quote(attachment.name or ''),
                )

    @api.multi
    @api.depends('datas')
    def _compute_image_size(self):
        for attachment in self:
            try:
                image = tools.base64_to_image(attachment.datas)
                attachment.image_width = image.width
                attachment.image_height = image.height
            except Exception:
                attachment.image_width = 0
                attachment.image_height = 0

    @api.multi
    def _get_media_info(self):
        """Return a dict with the values that we need on the media dialog."""
        self.ensure_one()
        return self.read(['id', 'name', 'mimetype', 'checksum', 'url', 'type', 'res_id', 'res_model', 'public', 'access_token', 'image_src', 'image_width', 'image_height'])[0]
