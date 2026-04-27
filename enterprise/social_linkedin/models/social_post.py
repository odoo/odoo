# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.osv import expression


class SocialPostLinkedin(models.Model):
    _inherit = 'social.post'

    linkedin_image_ids = fields.Many2many(relation='linkedin_image_ids_rel')

    @api.depends('live_post_ids.linkedin_post_id')
    def _compute_stream_posts_count(self):
        super(SocialPostLinkedin, self)._compute_stream_posts_count()

    def _get_stream_post_domain(self):
        domain = super(SocialPostLinkedin, self)._get_stream_post_domain()
        linkedin_post_ids = [linkedin_post_id for linkedin_post_id in self.live_post_ids.mapped('linkedin_post_id') if linkedin_post_id]
        if linkedin_post_ids:
            return expression.OR([domain, [('linkedin_post_urn', 'in', linkedin_post_ids)]])
        else:
            return domain
