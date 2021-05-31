# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import hashlib
import json

from odoo import api, models
from odoo.http import request
from odoo.tools import ustr

from odoo.addons.web.controllers.main import HomeStaticTemplateHelpers

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
        max_file_upload_size = int(IrConfigSudo.get_param(
            'web.max_file_upload_size',
            default=128 * 1024 * 1024,  # 128MiB
        ))

        session_info = {
            "uid": request.session.uid,
            "is_system": user._is_system() if request.session.uid else False,
            "is_admin": user._is_admin() if request.session.uid else False,
            "user_context": request.session.get_context() if request.session.uid else {},
            "db": request.session.db,
            "server_version": version_info.get('server_version'),
            "server_version_info": version_info.get('server_version_info'),
            "support_url": "https://www.odoo.com/buy",
            "name": user.name,
            "username": user.login,
            "partner_display_name": user.partner_id.display_name,
            "company_id": user.company_id.id if request.session.uid else None,  # YTI TODO: Remove this from the user context
            "partner_id": user.partner_id.id if request.session.uid and user.partner_id else None,
            "web.base.url": IrConfigSudo.get_param('web.base.url', default=''),
            "active_ids_limit": int(IrConfigSudo.get_param('web.active_ids_limit', default='20000')),
            'profile_session': request.session.profile_session,
            'profile_collectors': request.session.profile_collectors,
            'profile_params': request.session.profile_params,
            "max_file_upload_size": max_file_upload_size,
            "home_action_id": user.action_id.id,
        }
        if self.env.user.has_group('base.group_user'):
            # the following is only useful in the context of a webclient bootstrapping
            # but is still included in some other calls (e.g. '/web/session/authenticate')
            # to avoid access errors and unnecessary information, it is only included for users
            # with access to the backend ('internal'-type users)
            mods = odoo.conf.server_wide_modules or []
            if request.db:
                mods = list(request.registry._init_modules) + mods
            qweb_checksum = HomeStaticTemplateHelpers.get_qweb_templates_checksum(debug=request.session.debug, bundle="web.assets_qweb")
            lang = user_context.get("lang")
            translation_hash = request.env['ir.translation'].get_web_translations_hash(mods, lang)
            menus = request.env['ir.ui.menu'].load_menus(request.session.debug)
            ordered_menus = {str(k): v for k, v in menus.items()}
            menu_json_utf8 = json.dumps(ordered_menus, default=ustr, sort_keys=True).encode()
            cache_hashes = {
                "load_menus": hashlib.sha512(menu_json_utf8).hexdigest()[:64], # sha512/256
                "qweb": qweb_checksum,
                "translations": translation_hash,
            }
            session_info.update({
                # current_company should be default_company
                "user_companies": {
                    'current_company': user.company_id.id,
                    'allowed_companies': {
                        comp.id: {
                            'id': comp.id,
                            'name': comp.name,
                        } for comp in user.company_ids
                    },
                },
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
            'profile_session': request.session.profile_session,
            'profile_collectors': request.session.profile_collectors,
            'profile_params': request.session.profile_params,
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
