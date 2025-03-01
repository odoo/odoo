# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ResCompany(models.Model):
    _inherit = "res.company"

    def _get_social_media_links(self):
        self.ensure_one()
        return {
            'social_facebook': "https://www.facebook.com/Odoo",
            'social_linkedin': "https://www.linkedin.com/company/odoo",
            'social_twitter': "https://twitter.com/Odoo",
            'social_instagram': "https://www.instagram.com/explore/tags/odoo/",
            'social_tiktok': "https://www.tiktok.com/@odoo_official",
        }
