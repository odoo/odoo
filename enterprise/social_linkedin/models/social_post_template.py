# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from urllib.parse import urlparse

from odoo import _, api, models, fields
from odoo.exceptions import UserError


class SocialPostTemplate(models.Model):
    _inherit = 'social.post.template'

    linkedin_message = fields.Text(
        'LinkedIn Message', compute='_compute_message_by_media',
        store=True, readonly=False)
    linkedin_image_ids = fields.Many2many(
        'ir.attachment', 'template_linkedin_image_ids_rel', string='LinkedIn Images',
        help='Will attach images to your posts.',
        compute='_compute_images_by_media', store=True, readonly=False)

    display_linkedin_preview = fields.Boolean('Display LinkedIn Preview', compute='_compute_display_linkedin_preview')
    has_linkedin_account = fields.Boolean('Has LinkedIn Account', compute='_compute_has_linkedin_account')
    linkedin_preview = fields.Html('LinkedIn Preview', compute='_compute_linkedin_preview')

    @api.constrains('linkedin_message', 'linkedin_image_ids')
    def _check_has_linkedin_message_or_image(self):
        for post in self:
            if (post.has_linkedin_account
                and not post.linkedin_message
                and not post.linkedin_image_ids):
                raise UserError(_("Please specify either a LinkedIn Message or upload some LinkedIn Images.", post.id))

    @api.depends('account_ids.media_id.media_type')
    def _compute_has_linkedin_account(self):
        for post in self:
            post.has_linkedin_account = 'linkedin' in post.account_ids.media_id.mapped('media_type')

    @api.depends('linkedin_message', 'has_linkedin_account', 'linkedin_image_ids')
    def _compute_display_linkedin_preview(self):
        for post in self:
            post.display_linkedin_preview = (
                (post.linkedin_message or post.linkedin_image_ids)
                and post.has_linkedin_account
            )

    @api.depends(lambda self: ['linkedin_message', 'linkedin_image_ids', 'display_linkedin_preview'] + self._get_post_message_modifying_fields())
    def _compute_linkedin_preview(self):
        for post in self:
            if not post.display_linkedin_preview:
                post.linkedin_preview = False
                continue

            image_urls = []
            link_preview = {}
            if post.linkedin_image_ids:
                image_urls = [
                    f'/web/image/{image._origin.id or image.id}'
                    for image in post.linkedin_image_ids.sorted(lambda image: image._origin.id or image.id, reverse=True)
                ]
            elif url := self.env["social.post"]._extract_url_from_message(post.linkedin_message):
                preview = self.env["mail.link.preview"].sudo()._search_or_create_from_url(url)
                link_preview["url"] = url
                link_preview["domain"] = urlparse(url).hostname
                if image_url := preview.og_image:
                    image_urls.append(image_url)
                if title := preview.og_title:
                    link_preview['title'] = title

            post.linkedin_preview = self.env['ir.qweb']._render('social_linkedin.linkedin_preview', {
                **post._prepare_preview_values("linkedin"),
                'message': post._prepare_post_content(
                    post.linkedin_message,
                    'linkedin',
                    **{field: post[field] for field in post._get_post_message_modifying_fields()}),
                'image_urls': image_urls,
                'link_preview': link_preview,
            })

    @api.model
    def _message_fields(self):
        """Return the message field per media."""
        return {**super()._message_fields(), 'linkedin': 'linkedin_message'}

    @api.model
    def _images_fields(self):
        """Return the images field per media."""
        return {**super()._images_fields(), 'linkedin': 'linkedin_image_ids'}
