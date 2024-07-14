# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, models, api
from odoo.exceptions import ValidationError
from odoo.osv import expression


class SocialPostInstagram(models.Model):
    _inherit = 'social.post'

    @api.depends('live_post_ids.instagram_post_id')
    def _compute_stream_posts_count(self):
        super(SocialPostInstagram, self)._compute_stream_posts_count()

    def _check_post_access(self):
        """ See #_get_instagram_image_error() for more information. """
        super(SocialPostInstagram, self)._check_post_access()

        for post in self:
            if 'instagram' in post.media_ids.mapped('media_type'):
                image_error_code = post._get_instagram_image_error()
                if image_error_code == 'missing':
                    raise ValidationError(_('An image is required when posting on Instagram.'))
                elif image_error_code == 'wrong_extension':
                    raise ValidationError(_('Only .jpg/.jpeg images can be posted on Instagram.'))
                elif image_error_code == 'incorrect_ratio':
                    raise ValidationError(_('Your image has to be within the 4:5 and the 1.91:1 aspect ratio as required by Instagram.'))
                elif image_error_code == 'corrupted':
                    raise ValidationError(_('Your image appears to be corrupted, please try loading it again.'))

    def _get_stream_post_domain(self):
        domain = super(SocialPostInstagram, self)._get_stream_post_domain()
        instagram_post_ids = [instagram_post_id for instagram_post_id in self.live_post_ids.mapped('instagram_post_id') if instagram_post_id]
        if instagram_post_ids:
            return expression.OR([domain, [('instagram_post_id', 'in', instagram_post_ids)]])
        else:
            return domain
