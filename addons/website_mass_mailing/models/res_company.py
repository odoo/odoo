# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ResCompany(models.Model):
    _inherit = "res.company"

    def _get_social_media_links(self):
        social_media_links = super()._get_social_media_links()
        social_media_links.update({
            'social_facebook': social_media_links.get('social_facebook'),
            'social_linkedin': social_media_links.get('social_linkedin'),
            'social_twitter': social_media_links.get('social_twitter'),
            'social_instagram': social_media_links.get('social_instagram'),
            'social_tiktok': social_media_links.get('social_tiktok'),
        })
        return social_media_links
