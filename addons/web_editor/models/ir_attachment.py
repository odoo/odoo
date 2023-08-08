# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.urls import url_quote

from odoo import api, models, fields, tools
from odoo.addons.web_editor.tools import extract_video_thumbnail, fetch_web_video_thumbnail,get_video_source_data

import tempfile


SUPPORTED_IMAGE_MIMETYPES = {
    'image/gif': '.gif',
    'image/jpe': '.jpe',
    'image/jpeg': '.jpeg',
    'image/jpg': '.jpg',
    'image/png': '.png',
    'image/svg+xml': '.svg',
    'image/webp': '.webp',
}

SUPPORTED_VIDEO_MIMETYPES = [
    'video/mp4',
    'video/webm',
    'application/vnd.odoo.video-embed',
]


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    local_url = fields.Char("Attachment URL", compute='_compute_local_url')
    image_src = fields.Char(compute='_compute_image_src')
    image_width = fields.Integer(compute='_compute_image_size')
    image_height = fields.Integer(compute='_compute_image_size')
    thumbnail = fields.Many2one('ir.attachment', ondelete='cascade', compute='_compute_thumbnail', store=True, precompute=False)
    platform = fields.Char(compute='_compute_platform')
    original_id = fields.Many2one(
        'ir.attachment', string="Original (unoptimized, unresized) attachment")
    hidden = fields.Boolean(default=False, string="Hidden", help="Hide the attachment from the user interface")

    def create(self, vals_list):
        attachments = super(IrAttachment, self).create(vals_list)
        for attachment in attachments:
            attachment._update_url()
        return attachments

    @api.depends('url', 'checksum')
    def _compute_local_url(self):
        for attachment in self:
            if attachment.url:
                attachment.local_url = attachment.url
            else:
                attachment.local_url = '/web/image/%s?unique=%s' % (
                    attachment.id, attachment.checksum)

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
                    name = url_quote(attachment.name)
                    attachment.image_src = '/web/image/%s-redirect/%s' % (attachment.id, name)
            else:
                # Adding unique in URLs for cache-control
                unique = attachment.checksum[:8]
                if attachment.url:
                    # For attachments-by-url, unique is used as a cachebuster. They
                    # currently do not leverage max-age headers.
                    separator = '&' if '?' in attachment.url else '?'
                    attachment.image_src = '%s%sunique=%s' % (
                        attachment.url, separator, unique)
                else:
                    name = url_quote(attachment.name)
                    attachment.image_src = '/web/image/%s-%s/%s' % (
                        attachment.id, unique, name)

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

    @api.depends('datas')
    def _compute_thumbnail(self):
        """Create a thumbnail for supported videos by either extracting it from
        the video or downloading it from the web.
        """
        for attachment in self:
            if attachment.mimetype in SUPPORTED_VIDEO_MIMETYPES and not attachment.hidden:
                thumbnail_data = None

                try:
                    if attachment.store_fname:
                        thumbnail_path = tempfile.mktemp(suffix='.jpeg')
                        extract_video_thumbnail(self._full_path(
                            attachment.store_fname), thumbnail_path)
                        with open(thumbnail_path, 'rb') as f:
                            thumbnail_data = f.read()
                    else:
                        thumbnail_data = fetch_web_video_thumbnail(attachment.url)
                except Exception:
                    pass

                if thumbnail_data:
                    thumbnail = self.create({
                        'name': f'video-thumbnail-for-{attachment.id}',
                        'mimetype': 'image/jpeg',
                        'res_model': 'ir.attachment',
                        'public': attachment.public,
                        'raw': thumbnail_data,
                        'hidden': True,
                    })
                    attachment.thumbnail = thumbnail

    @api.depends('url')
    def _compute_platform(self):
        for attachment in self:
            if attachment.store_fname:
                attachment.platform = 'selfhosted'
            else:
                source = get_video_source_data(attachment.url)
                if not source:
                    attachment.platform = 'unknown'
                else:
                    attachment.platform = source[0]



    def _update_url(self):
        """Update the URL of local attachments if it's a supported video to use our video player."""
        for attachment in self:
            if attachment.mimetype in SUPPORTED_VIDEO_MIMETYPES and attachment.store_fname:
                attachment.update({
                    'url': '/watch/%i' % attachment.id,
                })


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
