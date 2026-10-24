# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from urllib.parse import quote

import requests

from odoo import api, models
from odoo.exceptions import ValidationError

from odoo.addons.web_unsplash import utils as unsplash_utils


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    @api.constrains("url", "mimetype")
    def _check_unsplash(self):
        if any(a.url and a.url.startswith("/unsplash/") and not (a.mimetype or "").startswith("image/") for a in self):
            raise ValidationError(self.env._("Unsplash attachments must be images."))

    @api.model
    def _fetch_unsplash_images(self, **post):
        access_key = unsplash_utils.get_unsplash_access_key(self.env["ir.config_parameter"])
        app_id = unsplash_utils.get_unsplash_app_id(self.env["ir.config_parameter"])

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

    @api.model
    def _fetch_unsplash_photo(self, photo_id):
        """Get from the Unsplash API the photo with the given ID.

        :param str photo_id: the Unsplash ID of the photo
        :return: the photo as the API returns it, or ``{'error': code}``. The
            ``rate_limit`` and ``unavailable`` codes tell that the same call can
            succeed later.
        """
        access_key = unsplash_utils.get_unsplash_access_key(self.env["ir.config_parameter"])
        app_id = unsplash_utils.get_unsplash_app_id(self.env["ir.config_parameter"])

        if not access_key or not app_id:
            if not self.env.user._can_manage_unsplash_settings():
                return {'error': 'no_access'}
            return {'error': 'key_not_found'}

        if not isinstance(photo_id, str) or not photo_id.strip():
            return {'error': 'invalid_id'}

        try:
            response = requests.get(
                f"https://api.unsplash.com/photos/{quote(photo_id, safe='')}",
                headers={'Authorization': f'Client-ID {access_key}'},
                timeout=10,
            )
        except requests.RequestException:
            return {'error': 'unavailable'}

        if response.status_code == requests.codes.ok:
            return response.json()

        if (
            response.status_code == requests.codes.too_many_requests
            or response.headers.get('X-Ratelimit-Remaining') == '0'
            or 'Rate Limit Exceeded' in response.text
        ):
            return {'error': 'rate_limit'}

        if response.status_code >= requests.codes.internal_server_error:
            return {'error': 'unavailable'}

        if not self.env.user._can_manage_unsplash_settings():
            return {'error': 'no_access'}
        return {'error': response.status_code}
