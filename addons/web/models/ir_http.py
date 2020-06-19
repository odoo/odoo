# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import hashlib
import json

from odoo import api, models
from odoo.http import request
from odoo.tools import ustr

from odoo.addons.web.controllers.main import module_boot, HomeStaticTemplateHelpers

import odoo


class Http(models.AbstractModel):
    _inherit = 'ir.http'

    def webclient_rendering_context(self):
        return {
            'menu_data': request.env['ir.ui.menu'].load_menus(request.session.debug),
            'session_info': self.session_info(),
        }

    def session_info(self):
        user = request.env.user
        version_info = odoo.service.common.exp_version()

        user_context = request.session.get_context() if request.session.uid else {}
        IrConfigSudo = self.env['ir.config_parameter'].sudo()
        session_info = {
            "uid": request.session.uid,
            "is_system": user._is_system() if request.session.uid else False,
            "is_admin": user._is_admin() if request.session.uid else False,
            "user_context": request.session.get_context() if request.session.uid else {},
            "db": request.session.db,
            "server_version": version_info.get('server_version'),
            "server_version_info": version_info.get('server_version_info'),
            "name": user.name,
            "username": user.login,
            "partner_display_name": user.partner_id.display_name,
            "company_id": user.company_id.id if request.session.uid else None,  # YTI TODO: Remove this from the user context
            "partner_id": user.partner_id.id if request.session.uid and user.partner_id else None,
            "web.base.url": IrConfigSudo.get_param('web.base.url', default=''),
            "active_ids_limit": int(IrConfigSudo.get_param('web.active_ids_limit', default='20000')),
        }
        if self.env.user.has_group('base.group_user'):
            # the following is only useful in the context of a webclient bootstrapping
            # but is still included in some other calls (e.g. '/web/session/authenticate')
            # to avoid access errors and unnecessary information, it is only included for users
            # with access to the backend ('internal'-type users)
            mods = module_boot()
            qweb_checksum = HomeStaticTemplateHelpers.get_qweb_templates_checksum(addons=mods, debug=request.session.debug)
            lang = user_context.get("lang")
            translation_hash = request.env['ir.translation'].get_web_translations_hash(mods, lang)
            menu_json_utf8 = json.dumps(request.env['ir.ui.menu'].load_menus(request.session.debug), default=ustr, sort_keys=True).encode()
            cache_hashes = {
                "load_menus": hashlib.sha512(menu_json_utf8).hexdigest()[:64], # sha512/256
                "qweb": qweb_checksum,
                "translations": translation_hash,
            }
            session_info.update({
                # current_company should be default_company
                "user_companies": {'current_company': (user.company_id.id, user.company_id.name), 'allowed_companies': [(comp.id, comp.name) for comp in user.company_ids]},
                "currencies": self.get_currencies(),
                "show_effect": True,
                "display_switch_company_menu": user.has_group('base.group_multi_company') and len(user.company_ids) > 1,
                "cache_hashes": cache_hashes,
            })
        return session_info

    @api.model
    def get_frontend_session_info(self):
        session_info = {
            'is_admin': request.session.uid and self.env.user._is_admin() or False,
            'is_system': request.session.uid and self.env.user._is_system() or False,
            'is_website_user': request.session.uid and self.env.user._is_public() or False,
            'user_id': request.session.uid and self.env.user.id or False,
            'is_frontend': True,
        }
        if request.session.uid:
            version_info = odoo.service.common.exp_version()
            session_info.update({
                'server_version': version_info.get('server_version'),
                'server_version_info': version_info.get('server_version_info')
            })
        return session_info

    def get_currencies(self):
        Currency = request.env['res.currency']
        currencies = Currency.search([]).read(['symbol', 'position', 'decimal_places'])
        return {c['id']: {'symbol': c['symbol'], 'position': c['position'], 'digits': [69,c['decimal_places']]} for c in currencies}
