# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from odoo import api, models
from odoo.http import request


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    @classmethod
    def _get_translation_frontend_modules_name(cls):
        mods = super()._get_translation_frontend_modules_name()
        return mods + ["pos_self_order"]

    # With the website module installed, there is an issue where
    # the default website's languages override the kiosk languages.
    # This override works around the issue.
    @api.model
    def get_nearest_lang(self, lang_code: str) -> str:
        if lang_code and '/pos-self/' in request.httprequest.path:
            config_id_match = re.search(r'/pos-self/(\d+)', request.httprequest.path)
            if config_id_match:
                pos_config = request.env['pos.config'].sudo().browse(int(config_id_match[1]))
                if pos_config.self_ordering_available_language_ids:
                    self_order_langs = pos_config.self_ordering_available_language_ids.mapped('code')
                    if lang_code in self_order_langs:
                        return lang_code
                    short_code = lang_code.partition('_')[0]
                    matched_code = next((code for code in self_order_langs if code.startswith(short_code)), None)
                    if matched_code:
                        return matched_code

        return super().get_nearest_lang(lang_code)
