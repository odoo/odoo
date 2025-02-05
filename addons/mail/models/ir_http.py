# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
from odoo import models
from odoo.http import request


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    def session_info(self):
        """Override to add the current user data (partner or guest) if applicable."""
        result = super().session_info()
        guest = self.env['mail.guest']._get_guest_from_context()
        if not request.session.uid and guest:
            user_context = {'lang': guest.lang}
            mods = odoo.tools.config['server_wide_modules']
            lang = user_context.get("lang")
            translation_hash = self.env['ir.http'].sudo().get_web_translations_hash(mods, lang)
            result['cache_hashes']['translations'] = translation_hash
            result["user_context"] = user_context
        return result
