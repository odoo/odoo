# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _
from odoo.exceptions import UserError


class ResCompany(models.Model):
    _inherit = "res.company"

    def _get_social_media_links(self):
        self.ensure_one()
        return {
            'social_facebook': self.social_facebook,
            'social_linkedin': self.social_linkedin,
            'social_twitter': self.social_twitter,
            'social_instagram': self.social_instagram,
            'social_tiktok': self.social_tiktok,
            'social_youtube': self.social_youtube,
            'social_github': self.social_github,
            'social_discord': self.social_discord,
        }

    def update_social_links(self, social_links):
        """
        Update social media link fields without unnecessarily reloading a view
        (see reload_company_service.js).

        :param dict social_links: Social link field names to URL path.
        :raises UserError: If a provided key is not a valid social media field.
        """
        self.ensure_one()
        authorized_keys = self._get_social_media_links()
        for key in social_links:
            if authorized_keys.get(key) is None:
                raise UserError(_("%(key)s is not a valid social link field name, use `write` instead.", key=key))
        self.write({**social_links})
