# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64

from werkzeug.urls import url_quote

from odoo import api, models, fields, tools

SUPPORTED_IMAGE_MIMETYPES = {
    'image/gif': '.gif',
    'image/jpe': '.jpe',
    'image/jpeg': '.jpeg',
    'image/jpg': '.jpg',
    'image/png': '.png',
    'image/svg+xml': '.svg',
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
                attachment.image_src = attachment.url
            else:
                # Adding unique in URLs for cache-control
                unique = attachment.checksum[:8]
                if attachment.url:
                    # For attachments-by-url, unique is used as a cachebuster. They
                    # currently do not leverage max-age headers.
                    separator = '&' if '?' in attachment.url else '?'
                    attachment.image_src = '%s%sunique=%s' % (attachment.url, separator, unique)
                else:
                    name = url_quote(attachment.name)
                    attachment.image_src = '/web/image/%s-%s/%s' % (attachment.id, unique, name)

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

    def _get_media_info(self):
        """Return a dict with the values that we need on the media dialog."""
        self.ensure_one()
        return self._read_format(['id', 'name', 'description', 'mimetype', 'checksum', 'url', 'type', 'res_id', 'res_model', 'public', 'access_token', 'image_src', 'image_width', 'image_height', 'original_id'])[0]

    def _can_bypass_rights_on_media_dialog(self, **attachment_data):
        """ This method is meant to be overridden, for instance to allow to
        create image attachment despite the user not allowed to create
        attachment, eg:
        - Portal user uploading an image on the forum (bypass acl)
        - Non admin user uploading an unsplash image (bypass binary/url check)
        """
        return False

    @api.model_create_multi
    def _create_image_attachments(self, vals_list):
        """
        Check if an attachment for the same image does not already exists before
        creating a new one.
        TODO: write this to support batch, adapt mailing.py to use raw instead of datas
        / or support datas here as well 
        """
        recordset = self.env['ir.attachment']
        if not vals_list:
            return recordset
        res_model, res_id = vals_list[0].get('res_model'), vals_list[0].get('res_id')
        record_attachments = recordset.search([
            ('res_model', '=', res_model),
            ('res_id', '=', res_id),
        ])
        attachments = []
        vals_for_new_attachs = []
        for vals in vals_list:
            existing_attach = None
            raw, datas = vals.get('raw'), vals.get('datas')
            if isinstance(raw, str):
                raw = raw.encode()
            bin_data = raw or base64.b64decode(datas or b'')
            if bin_data:
                checksum = self._compute_checksum(bin_data)
                existing_attachs = [attach for attach in record_attachments
                                            if attach.checksum == checksum]
                if existing_attachs:
                    existing_attach = existing_attachs[0]
            attachments.append(existing_attach)
            if not existing_attach:
                vals_for_new_attachs.append(vals)

        new_attachs = list(self.create(vals_for_new_attachs))[::-1]

        for attach in attachments:
            recordset = recordset | (attach or new_attachs.pop())
        return recordset

