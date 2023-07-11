# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
from odoo import models
from odoo.addons.web.controllers.main import HomeStaticTemplateHelpers
from odoo.http import request


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    def session_info(self):
        user = request.env.user
        result = super(IrHttp, self).session_info()
        if self.env.user.has_group('base.group_user'):
            result['notification_type'] = user.notification_type
        assets_discuss_public_hash = HomeStaticTemplateHelpers.get_qweb_templates_checksum(debug=request.session.debug, bundle='mail.assets_discuss_public')
        result['cache_hashes']['assets_discuss_public'] = assets_discuss_public_hash
        guest = self.env['mail.guest']._get_guest_from_context()
        if not request.session.uid and guest:
            user_context = {'lang': guest.lang}
            mods = odoo.conf.server_wide_modules or []
            lang = user_context.get("lang")
            translation_hash = request.env['ir.translation'].sudo().get_web_translations_hash(mods, lang)
            result['cache_hashes']['translations'] = translation_hash
            result.update({
                'name': guest.name,
                'user_context': user_context,
            })
        return result
