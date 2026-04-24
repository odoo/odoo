# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import requests

from odoo import api, models
from odoo.exceptions import ValidationError

from odoo.addons.web_unsplash.controllers.main import (
    UNSPLASH_ACCESS_KEY_ICP,
    UNSPLASH_APP_ID_ICP,
)


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    @api.constrains("url", "mimetype")
    def _check_unsplash(self):
        if any(a.url and a.url.startswith("/unsplash/") and not (a.mimetype or "").startswith("image/") for a in self):
            raise ValidationError(self.env._("Unsplash attachments must be images."))

    @api.model
    def _fetch_unsplash_images(self, **post):
        IrConfigParameter = self.env["ir.config_parameter"].sudo()
        access_key = IrConfigParameter.get_str(UNSPLASH_ACCESS_KEY_ICP)
        app_id = IrConfigParameter.get_str(UNSPLASH_APP_ID_ICP)

        if not access_key or not app_id:
            if not self.env.user._can_manage_unsplash_settings():
                return {'error': 'no_access'}
            return {'error': 'key_not_found'}

        allowed_keys = {'query', 'page', 'per_page', 'orientation'}
        payload = {key: value for key, value in post.items() if key in allowed_keys}
        headers = {'Authorization': f'Client-ID {access_key}'}

        response = requests.get(
            'https://api.unsplash.com/search/photos/',
            params=payload,
            headers=headers,
            timeout=10,
        )

        if response.status_code == requests.codes.ok:
            return response.json()

        if not self.env.user._can_manage_unsplash_settings():
            return {'error': 'no_access'}
        return {'error': response.status_code}
