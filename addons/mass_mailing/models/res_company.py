# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.addons import mail, social_media


class ResCompany(mail.ResCompany, social_media.ResCompany):

    def _get_social_media_links(self):
        self.ensure_one()
        return {
            'social_facebook': self.social_facebook,
            'social_linkedin': self.social_linkedin,
            'social_twitter': self.social_twitter,
            'social_instagram': self.social_instagram,
            'social_tiktok': self.social_tiktok,
        }
