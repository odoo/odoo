# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
from odoo import api, models, fields
from odoo.http import request


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    def session_info(self):
        """Override to add the current user data (partner or guest) if applicable."""
        result = super().session_info()
        self._add_self_to_session_info(result)
        guest = self.env['mail.guest']._get_guest_from_context()
        if not request.session.uid and guest:
            user_context = {'lang': guest.lang}
            mods = odoo.conf.server_wide_modules or []
            lang = user_context.get("lang")
            translation_hash = self.env['ir.http'].sudo().get_web_translations_hash(mods, lang)
            result['cache_hashes']['translations'] = translation_hash
            result["user_context"] = user_context
        return result

    @api.model
    def get_frontend_session_info(self):
        """Override to add the current user data (partner or guest) if applicable."""
        res = super().get_frontend_session_info()
        self._add_self_to_session_info(res)
        return res

    def _add_self_to_session_info(self, res):
        user = self.env.user
        guest = self.env["mail.guest"]._get_guest_from_context()
        if request.session.uid:
            res["self"] = {
                "id": user.partner_id.id,
                "isAdmin": user._is_admin(),
                "isInternalUser": not user.share,
                "name": user.partner_id.name,
                "notification_preference": user.notification_type,
                "type": "partner",
                "userId": user.id,
                "write_date": fields.Datetime.to_string(user.write_date),
            }
        elif guest:
            res["self"] = {
                "id": guest.id,
                "name": guest.name,
                "type": "guest",
                "write_date": fields.Datetime.to_string(guest.write_date),
            }
