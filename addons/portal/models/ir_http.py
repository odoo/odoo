# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import hashlib
import json

from odoo import api, fields, models
from odoo.osv import expression
from odoo.http import request


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def _get_translation_frontend_modules_domain(cls):
        domain = super(IrHttp, cls)._get_translation_frontend_modules_domain()
        return expression.OR([domain, [('name', '=', 'portal')]])

    @api.model
    def get_portal_session_info(self):
        # see http_routing/main.py
        Modules = request.env['ir.module.module'].sudo()
        IrHttp = request.env['ir.http'].sudo()
        domain = IrHttp._get_translation_frontend_modules_domain()
        modules = Modules.search(
            expression.AND([domain, [('state', '=', 'installed')]])
        ).mapped('name')
        user_context = request.session.get_context() if request.session.uid else {}
        lang = user_context.get('lang')
        translations, _ = request.env['ir.translation'].get_translations_for_webclient(modules, lang)
        return {
            'is_admin': self.env.user._is_admin(),
            'is_system': self.env.user._is_system(),
            'is_website_user': self.env.user._is_public(),
            'user_id': self.env.user.id,
            'is_frontend': True,
            'translationURL': '/website/translations',
            'cache_hashes': {
                'translations': hashlib.sha1(json.dumps(translations, sort_keys=True).encode()).hexdigest(),
            },
        }
