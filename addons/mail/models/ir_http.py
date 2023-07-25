# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
from odoo import models
from odoo.http import request


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    def session_info(self):
        user = self.env.user
        result = super(IrHttp, self).session_info()
        if self.env.user._is_internal():
            result['notification_type'] = user.notification_type
        guest = self.env['mail.guest']._get_guest_from_context()
        if not request.session.uid and guest:
            user_context = {'lang': guest.lang}
            mods = odoo.conf.server_wide_modules or []
            lang = user_context.get("lang")
            translation_hash = self.env['ir.http'].sudo().get_web_translations_hash(mods, lang)
            result['cache_hashes']['translations'] = translation_hash
            result.update({
                'name': guest.name,
                'user_context': user_context,
            })
        return result

    @classmethod
    def _pre_dispatch(cls, rule, args):
        """Overriden to add the guest to the context if any."""
        super()._pre_dispatch(rule, args)
        guest = request.env["mail.guest"]._get_guest_from_request(request)
        if guest:
            request.update_context(guest=guest)
