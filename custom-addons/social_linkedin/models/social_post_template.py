# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api, fields
from odoo.addons.mail.tools.link_preview import get_link_preview_from_url


class SocialPostTemplate(models.Model):
    _inherit = 'social.post.template'

    display_linkedin_preview = fields.Boolean('Display LinkedIn Preview', compute='_compute_display_linkedin_preview')
    linkedin_preview = fields.Html('LinkedIn Preview', compute='_compute_linkedin_preview')

    @api.depends('message', 'account_ids.media_id.media_type')
    def _compute_display_linkedin_preview(self):
        for post in self:
            post.display_linkedin_preview = (
                post.message and
                'linkedin' in post.account_ids.media_id.mapped('media_type'))

    @api.depends(lambda self: ['message', 'image_ids', 'display_linkedin_preview'] + self._get_post_message_modifying_fields())
    def _compute_linkedin_preview(self):
        for post in self:
            if not post.display_linkedin_preview:
                post.linkedin_preview = False
                continue

            image_urls = []
            link_preview = {}
            if post.image_ids:
                image_urls = [
                    f'/web/image/{image._origin.id or image.id}'
                    for image in post.image_ids.sorted(lambda image: image._origin.id or image.id, reverse=True)
                ]
            elif url_in_message := self.env['social.post']._extract_url_from_message(post.message):
                preview = get_link_preview_from_url(url_in_message) or {}
                link_preview['url'] = url_in_message
                if image_url := preview.get('og_image'):
                    image_urls.append(image_url)
                if title := preview.get('og_title'):
                    link_preview['title'] = title

            post.linkedin_preview = self.env['ir.qweb']._render('social_linkedin.linkedin_preview', {
                **post._prepare_preview_values("instagram"),
                'message': post._prepare_post_content(
                    post.message,
                    'linkedin',
                    **{field: post[field] for field in post._get_post_message_modifying_fields()}),
                'image_urls': image_urls,
                'link_preview': link_preview,
            })
