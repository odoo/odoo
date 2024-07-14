# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import uuid

from odoo import api, fields, models, tools


class SocialPostTemplate(models.Model):
    _inherit = 'social.post.template'

    def _get_default_access_token(self):
        return str(uuid.uuid4())

    instagram_image_id = fields.Many2one('ir.attachment', compute='_compute_instagram_image_id')
    instagram_access_token = fields.Char('Access Token', default=lambda self: self._get_default_access_token(), copy=False,
        help="Used to allow access to Instagram to retrieve the post image")
    display_instagram_preview = fields.Boolean('Display Instagram Preview', compute='_compute_display_instagram_preview')
    instagram_preview = fields.Html('Instagram Preview', compute='_compute_instagram_preview')

    @api.depends('message', 'account_ids.media_id.media_type')
    def _compute_display_instagram_preview(self):
        for post in self:
            post.display_instagram_preview = post.message and ('instagram' in post.account_ids.media_id.mapped('media_type'))

    @api.depends('image_ids')
    def _compute_instagram_image_id(self):
        for post in self:
            jpeg_images = post.image_ids.filtered(lambda image: image.mimetype == 'image/jpeg')
            post.instagram_image_id = jpeg_images[0] if jpeg_images else False

    @api.depends(lambda self: ['message', 'image_ids', 'display_instagram_preview'] + self._get_post_message_modifying_fields())
    def _compute_instagram_preview(self):
        """ We want to display various error messages if the image is not appropriate.
        See #_get_instagram_image_error() for more information. """

        for post in self:
            if not post.display_instagram_preview:
                post.instagram_preview = False
                continue
            image = post.instagram_image_id
            post.instagram_preview = self.env['ir.qweb']._render('social_instagram.instagram_preview', {
                **post._prepare_preview_values("instagram"),
                'error_code': post._get_instagram_image_error(),
                'image_url': f'/web/image/{image._origin.id or image.id}' if image else False,
                'image_multiple': len(post.image_ids) > 1,
                'message': post._prepare_post_content(
                    post.message,
                    'instagram',
                    **{field: post[field] for field in post._get_post_message_modifying_fields()}),
            })

    def _get_instagram_image_error(self):
        """ Allows verifying that the post within self contains a valid Instagram image.

        Returns:
        - 'missing'          If there is no image
        - 'wrong_extension'  If the image in not in the JPEG format
        - 'incorrect_ratio'  If the image in not between 4:5 and 1.91:1 ratio'
        - False              If everything is correct.

        Those various rules are imposed by Instagram.
        See: https://developers.facebook.com/docs/instagram-api/reference/ig-user/media

        We want to avoid any kind of dynamic resizing / format change to make sure what the user
        uploads and sees in the preview is as close as possible to what they will get as a result on
        Instagram. """

        self.ensure_one()
        error_code = False

        if not self.image_ids:
            error_code = 'missing'
        else:
            if not self.instagram_image_id:
                error_code = 'wrong_extension'
            else:
                try:
                    image_base64 = self.instagram_image_id.with_context(bin_size=False).datas
                    image = tools.base64_to_image(image_base64)
                    image_ratio = image.width / image.height if image.height else 0
                    if image_ratio < 0.8 or image_ratio > 1.91:
                        error_code = 'incorrect_ratio'
                except Exception:
                    # image could not be loaded
                    error_code = 'corrupted'

        return error_code
