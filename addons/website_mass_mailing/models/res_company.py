# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ResCompany(models.Model):
    _inherit = "res.company"

    def _get_social_media_links(self):
        social_media_links = super()._get_social_media_links()
        website_id = self.env['website'].get_current_website()
        social_media_links.update({
            'social_facebook': website_id.social_facebook or social_media_links.get('social_facebook'),
            'social_linkedin': website_id.social_linkedin or social_media_links.get('social_linkedin'),
            'social_twitter': website_id.social_twitter or social_media_links.get('social_twitter'),
            'social_instagram': website_id.social_instagram or social_media_links.get('social_instagram'),
            'social_tiktok': website_id.social_tiktok or social_media_links.get('social_tiktok'),
            'social_threads': website_id.social_threads or social_media_links.get('social_threads'),
        })
        return social_media_links
