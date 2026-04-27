# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from urllib.parse import urlparse

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SocialPostTemplate(models.Model):
    _inherit = 'social.post.template'

    twitter_message = fields.Text(
        'X Message', compute='_compute_message_by_media',
        store=True, readonly=False)
    twitter_image_ids = fields.Many2many(
        'ir.attachment', 'template_twitter_image_ids_rel', string='X Images',
        help='Will attach images to your posts.',
        compute='_compute_images_by_media', store=True, readonly=False)

    twitter_preview = fields.Html('X Preview', compute='_compute_twitter_preview')
    has_twitter_account = fields.Boolean('Has X Account', compute='_compute_has_twitter_account')
    display_twitter_preview = fields.Boolean('Display X Preview', compute='_compute_display_twitter_preview')
    twitter_post_limit_message = fields.Char('X Post Limit Message', compute="_compute_twitter_post_limit_message")
    is_twitter_post_limit_exceed = fields.Boolean('X Post Limit Exceeded', compute="_compute_twitter_post_limit_message")

    @api.constrains('twitter_message', 'twitter_image_ids')
    def _check_has_twitter_message_or_image(self):
        for post in self:
            if (post.has_twitter_account
                and not post.twitter_message
                and not post.twitter_image_ids):
                raise UserError(_("Please specify either an X Message or upload some X Images.", post.id))

    @api.depends('account_ids.media_id.media_type')
    def _compute_has_twitter_account(self):
        for post in self:
            post.has_twitter_account = 'twitter' in post.account_ids.media_id.mapped('media_type')

    @api.depends('has_twitter_account', 'twitter_message', 'twitter_image_ids')
    def _compute_display_twitter_preview(self):
        for post in self:
            post.display_twitter_preview = post.has_twitter_account and (post.twitter_message or post.twitter_image_ids)

    @api.depends('twitter_message', 'has_twitter_account')
    def _compute_twitter_post_limit_message(self):
        self.twitter_post_limit_message = False
        self.is_twitter_post_limit_exceed = False
        for post in self.filtered('has_twitter_account'):
            message_length = len(post.twitter_message or '')
            twitter_account = post.account_ids._filter_by_media_types(['twitter'])
            post.twitter_post_limit_message = _("%(current_length)s / %(max_length)s characters to fit in a Post", current_length=message_length, max_length=twitter_account.media_id.max_post_length)
            post.is_twitter_post_limit_exceed = twitter_account.media_id.max_post_length and message_length > twitter_account.media_id.max_post_length

    @api.depends(lambda self: ['twitter_message', 'twitter_image_ids', 'is_twitter_post_limit_exceed', 'has_twitter_account'] + self._get_post_message_modifying_fields())
    def _compute_twitter_preview(self):
        self.twitter_preview = False
        for post in self.filtered('has_twitter_account'):
            twitter_account = post.account_ids._filter_by_media_types(['twitter'])

            image_urls = []
            link_preview = {}
            if post.twitter_image_ids:
                image_urls = [
                    f'/web/image/{image._origin.id or image.id}'
                    for image in post.twitter_image_ids.sorted(lambda image: image._origin.id or image.id, reverse=True)
                ]
            elif url := self.env["social.post"]._extract_url_from_message(post.twitter_message):
                preview = self.env["mail.link.preview"].sudo()._search_or_create_from_url(url)
                link_preview["url"] = url
                link_preview["domain"] = urlparse(url).hostname
                if image_url := preview.og_image:
                    image_urls.append(image_url)

            post.twitter_preview = self.env['ir.qweb']._render('social_twitter.twitter_preview', {
                **post._prepare_preview_values('twitter'),
                'message': post._prepare_post_content(
                    post.twitter_message,
                    'twitter',
                    **{field: post[field] for field in post._get_post_message_modifying_fields()}),
                'image_urls': image_urls,
                'limit': twitter_account.media_id.max_post_length,
                'is_twitter_post_limit_exceed': post.is_twitter_post_limit_exceed,
                'link_preview': link_preview,
            })

    @api.model
    def _message_fields(self):
        """Return the message field per media."""
        return {**super()._message_fields(), 'twitter': 'twitter_message'}

    @api.model
    def _images_fields(self):
        """Return the images field per media."""
        return {**super()._images_fields(), 'twitter': 'twitter_image_ids'}
