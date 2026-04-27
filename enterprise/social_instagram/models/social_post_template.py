# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import uuid

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.image import base64_to_image


class SocialPostTemplate(models.Model):
    _inherit = 'social.post.template'

    def _get_default_access_token(self):
        return str(uuid.uuid4())

    instagram_message = fields.Text(
        'Instagram Message', compute='_compute_message_by_media',
        store=True, readonly=False)
    instagram_image_ids = fields.Many2many(
        'ir.attachment', 'template_instagram_image_ids_rel', string='Instagram Images',
        help='Will attach images to your posts.',
        compute='_compute_images_by_media', store=True, readonly=False)

    instagram_access_token = fields.Char('Access Token', default=lambda self: self._get_default_access_token(), copy=False,
        help="Used to allow access to Instagram to retrieve the post image")
    has_instagram_account = fields.Boolean('Has Instagram Account', compute='_compute_has_instagram_account')
    display_instagram_preview = fields.Boolean('Display Instagram Preview', compute='_compute_display_instagram_preview')
    instagram_preview = fields.Html('Instagram Preview', compute='_compute_instagram_preview')

    @api.constrains('instagram_message', 'instagram_image_ids')
    def _check_has_instagram_message_or_image(self):
        for post in self:
            if (post.has_instagram_account
                and not post.instagram_message
                and not post.instagram_image_ids):
                raise UserError(_("Please specify either a Instagram Message or upload some Instagram Images."))

    @api.depends('account_ids.media_id.media_type')
    def _compute_has_instagram_account(self):
        for post in self:
            post.has_instagram_account = 'instagram' in post.account_ids.media_id.mapped('media_type')

    @api.depends('instagram_message', 'has_instagram_account', 'instagram_image_ids')
    def _compute_display_instagram_preview(self):
        for post in self:
            post.display_instagram_preview = (post.instagram_message or post.instagram_image_ids) and post.has_instagram_account

    @api.depends(lambda self: ['instagram_message', 'instagram_image_ids', 'display_instagram_preview'] + self._get_post_message_modifying_fields())
    def _compute_instagram_preview(self):
        """ We want to display various error messages if the image is not appropriate.
        See #_get_instagram_image_error() for more information. """

        for post in self:
            if not post.display_instagram_preview:
                post.instagram_preview = False
                continue
            faulty_images, error_code = post._get_instagram_image_error()
            post.instagram_preview = self.env['ir.qweb']._render('social_instagram.instagram_preview', {
                **post._prepare_preview_values("instagram"),
                'faulty_images': faulty_images,
                'error_code': error_code,
                'image_urls': [
                    f'/web/image/{image._origin.id or image.id}'
                    for image in post.instagram_image_ids.sorted(lambda image: image._origin.id or image.id, reverse=True)
                ],
                'message': post._prepare_post_content(
                    post.instagram_message,
                    'instagram',
                    **{field: post[field] for field in post._get_post_message_modifying_fields()}),
            })

    def _get_instagram_image_error(self):
        """ Allows verifying that the post within self contains a valid Instagram image.

        Returns: faulty image names along with error_code
        Errors:              Causes:
        - 'missing'          If there is no image
        - 'wrong_extension'  If the image in not in the JPEG format
        - 'incorrect_ratio'  If the image in not between 4:5 and 1.91:1 ratio'
        - 'max_limit'        If the number of images is greater than 10 (Carousels are limited to 10 images)
        - 'corrupted'        If the image is corrupted
        - False              If everything is correct.

        Those various rules are imposed by Instagram.
        See: https://developers.facebook.com/docs/instagram-api/reference/ig-user/media

        We want to avoid any kind of dynamic resizing / format change to make sure what the user
        uploads and sees in the preview is as close as possible to what they will get as a result on
        Instagram. """

        self.ensure_one()
        error_code = False
        faulty_images = self.env['ir.attachment']
        jpeg_images = self.instagram_image_ids.filtered(lambda image: image.mimetype == 'image/jpeg')
        non_jpeg_images = self.instagram_image_ids - jpeg_images

        if not self.instagram_image_ids:
            error_code = 'missing'
        else:
            if len(jpeg_images) > 10:
                error_code = 'max_limit'
            if non_jpeg_images:
                error_code = 'wrong_extension'
                faulty_images += non_jpeg_images
            if jpeg_images and not non_jpeg_images:
                for jpeg_image in jpeg_images:
                    try:
                        image = base64_to_image(jpeg_image.with_context(bin_size=False).datas)
                    except UserError:
                        # image could not be loaded
                        error_code = 'corrupted'
                        return jpeg_image.name, error_code

                    image_ratio = image.width / image.height if image.height else 0
                    if image_ratio < 0.8 or image_ratio > 1.91:
                        error_code = 'incorrect_ratio'
                        faulty_images += jpeg_image

        return faulty_images.mapped('name'), error_code

    @api.model
    def _message_fields(self):
        """Return the message field per media."""
        return {**super()._message_fields(), 'instagram': 'instagram_message'}

    @api.model
    def _images_fields(self):
        """Return the images field per media."""
        return {**super()._images_fields(), 'instagram': 'instagram_image_ids'}
