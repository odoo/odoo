# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
from odoo import api, models, fields
from odoo.http import request
from odoo.addons.mail.tools.discuss import Store


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    def session_info(self):
        """Override to add the current user data (partner or guest) if applicable."""
        result = super().session_info()
        store = Store()
        ResUsers = self.env["res.users"]
        if cids := request.cookies.get("cids", False):
            allowed_company_ids = []
            for company_id in [int(cid) for cid in cids.split("-")]:
                if company_id in self.env.user.company_ids.ids:
                    allowed_company_ids.append(company_id)
            ResUsers = self.with_context(allowed_company_ids=allowed_company_ids).env["res.users"]
        ResUsers._init_store_data(store)
        result["storeData"] = store.get_result()
        guest = self.env['mail.guest']._get_guest_from_context()
        if not request.session.uid and guest:
            user_context = {'lang': guest.lang}
            mods = odoo.conf.server_wide_modules or []
            lang = user_context.get("lang")
            translation_hash = self.env['ir.http'].sudo().get_web_translations_hash(mods, lang)
            result['cache_hashes']['translations'] = translation_hash
            result["user_context"] = user_context
        return result
