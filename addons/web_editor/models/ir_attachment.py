# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug import url_quote

from odoo import api, models, fields


class IrAttachment(models.Model):

    _inherit = "ir.attachment"

    local_url = fields.Char("Attachment URL", compute='_compute_local_url')
    image_src = fields.Char(compute='_compute_image_src')

    @api.one
    def _compute_local_url(self):
        if self.url:
            self.local_url = self.url
        else:
            self.local_url = '/web/image/%s?unique=%s' % (self.id, self.checksum)

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
    def _get_media_info(self):
        """Return a dict with the values that we need on the media dialog."""
        self.ensure_one()
        return self.read(['id', 'name', 'mimetype', 'checksum', 'url', 'type', 'res_id', 'res_model', 'public', 'access_token', 'image_src'])[0]
