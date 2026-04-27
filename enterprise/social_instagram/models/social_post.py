# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.osv import expression


class SocialPostInstagram(models.Model):
    _inherit = 'social.post'

    instagram_image_ids = fields.Many2many(relation='instagram_image_ids_rel')

    @api.depends('live_post_ids.instagram_post_id')
    def _compute_stream_posts_count(self):
        super(SocialPostInstagram, self)._compute_stream_posts_count()

    def _check_post_access(self):
        """ See #_get_instagram_image_error() for more information. """
        super(SocialPostInstagram, self)._check_post_access()

        for post in self:
            if 'instagram' in post.media_ids.mapped('media_type'):
                faulty_images, image_error_code = post._get_instagram_image_error()
                if image_error_code == 'missing':
                    raise ValidationError(_('At least one image is required when posting on Instagram.'))
                elif image_error_code == 'wrong_extension':
                    raise ValidationError(
                        _(
                            "The following images are not in the correct format (jpg/jpeg).\n\n%(images)s",
                            images="\n".join(f"- {faulty_image}" for faulty_image in faulty_images),
                        ),
                    )
                elif image_error_code == 'incorrect_ratio':
                    raise ValidationError(
                        _(
                            "The following images do not meet the required aspect ratio (between 1.91:1 and 4:5).\n\n%(images)s",
                            images="\n".join(f"- {faulty_image}" for faulty_image in faulty_images),
                        ),
                    )
                elif image_error_code == 'corrupted':
                    raise ValidationError(_('Your image appears to be corrupted, please try loading it again.'))
                elif image_error_code == 'max_limit':
                    raise ValidationError(_('You can only post up to 10 images at once.'))

    def _get_stream_post_domain(self):
        domain = super(SocialPostInstagram, self)._get_stream_post_domain()
        instagram_post_ids = [instagram_post_id for instagram_post_id in self.live_post_ids.mapped('instagram_post_id') if instagram_post_id]
        if instagram_post_ids:
            return expression.OR([domain, [('instagram_post_id', 'in', instagram_post_ids)]])
        else:
            return domain

    @api.model
    def _cron_publish_scheduled(self):
        super()._cron_publish_scheduled()

        instagram_live_posts = self.env['social.live.post'].search([
            ('account_id.media_type', '=', 'instagram'),
            ('state', '=', 'posting'),
            ('instagram_post_id', '=like', 'containerID-%'),
        ])

        for live_post in instagram_live_posts:
            live_post._post_instagram()
