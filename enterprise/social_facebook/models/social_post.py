# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import requests

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.osv import expression
from werkzeug.urls import url_join


class SocialPostFacebook(models.Model):
    _inherit = 'social.post'

    facebook_image_ids = fields.Many2many(relation='facebook_image_ids_rel')

    @api.depends('live_post_ids.facebook_post_id')
    def _compute_stream_posts_count(self):
        super(SocialPostFacebook, self)._compute_stream_posts_count()

    def _get_stream_post_domain(self):
        domain = super(SocialPostFacebook, self)._get_stream_post_domain()
        facebook_post_ids = [facebook_post_id for facebook_post_id in self.live_post_ids.mapped('facebook_post_id') if facebook_post_id]
        if facebook_post_ids:
            return expression.OR([domain, [('facebook_post_id', 'in', facebook_post_ids)]])
        else:
            return domain

    def _format_images_facebook(self, facebook_account_id, facebook_access_token):
        self.ensure_one()

        formatted_images = []
        for image in self.facebook_image_ids:
            facebook_photo_endpoint_url = url_join(self.env['social.media']._FACEBOOK_ENDPOINT_VERSIONED, '%s/photos' % facebook_account_id)

            post_result = requests.request('POST', facebook_photo_endpoint_url,
                params={
                    'published': 'false',
                    'access_token': facebook_access_token
                },
                files={'source': ('source', image.with_context(bin_size=False).raw, image.mimetype)},
                timeout=15
            )

            if post_result.ok:
                formatted_images.append({'media_fbid': post_result.json().get('id')})
            else:
                generic_api_error = json.loads(post_result.text or '{}').get('error', {}).get('message', '')
                raise UserError(_("We could not upload your image, try reducing its size and posting it again (error: %s).", generic_api_error))

        return formatted_images
