# Part of Odoo. See LICENSE file for full copyright and licensing details.

from urllib.parse import quote

from odoo import api, models, fields
from odoo.tools.image import base64_to_image
from odoo.exceptions import UserError

SUPPORTED_IMAGE_MIMETYPES = {
    'image/gif': '.gif',
    'image/jpe': '.jpe',
    'image/jpeg': '.jpeg',
    'image/jpg': '.jpg',
    'image/png': '.png',
    'image/svg+xml': '.svg',
    'image/webp': '.webp',
}


class IrAttachment(models.Model):

    _inherit = "ir.attachment"

    local_url = fields.Char("Attachment URL", compute='_compute_local_url')
    image_src = fields.Char(compute='_compute_image_src')
    image_width = fields.Integer(compute='_compute_image_size')
    image_height = fields.Integer(compute='_compute_image_size')
    original_id = fields.Many2one('ir.attachment', string="Original (unoptimized, unresized) attachment")

    def _compute_local_url(self):
        for attachment in self:
            if attachment.url:
                attachment.local_url = attachment.url
            else:
                attachment.local_url = '/web/image/%s?unique=%s' % (attachment.id, attachment.checksum)

    @api.depends('mimetype', 'url', 'name')
    def _compute_image_src(self):
        for attachment in self:
            # Only add a src for supported images
            if attachment.mimetype not in SUPPORTED_IMAGE_MIMETYPES:
                attachment.image_src = False
                continue

            if attachment.type == 'url':
                if attachment.url.startswith('/'):
                    # Local URL
                    attachment.image_src = attachment.url
                else:
                    name = quote(attachment.name)
                    attachment.image_src = '/web/image/%s-redirect/%s' % (attachment.id, name)
            else:
                # Adding unique in URLs for cache-control
                unique = attachment.checksum[:8]
                if attachment.url:
                    # For attachments-by-url, unique is used as a cachebuster. They
                    # currently do not leverage max-age headers.
                    separator = '&' if '?' in attachment.url else '?'
                    attachment.image_src = '%s%sunique=%s' % (attachment.url, separator, unique)
                else:
                    name = quote(attachment.name)
                    attachment.image_src = '/web/image/%s-%s/%s' % (attachment.id, unique, name)

    @api.depends('datas')
    def _compute_image_size(self):
        for attachment in self:
            try:
                image = base64_to_image(attachment.datas)
                attachment.image_width = image.width
                attachment.image_height = image.height
            except UserError:
                attachment.image_width = 0
                attachment.image_height = 0
