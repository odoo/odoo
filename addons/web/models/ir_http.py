# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo import models
from odoo.http import request

import odoo


class Http(models.AbstractModel):
    _inherit = 'ir.http'

    def webclient_rendering_context(self):
        return {
            'menu_data': request.env['ir.ui.menu'].load_menus(request.debug),
            'session_info': json.dumps(self.session_info()),
        }

    def session_info(self):
        user = request.env.user
        display_switch_company_menu = user.has_group('base.group_multi_company') and len(user.company_ids) > 1
        version_info = odoo.service.common.exp_version()
        return {
            "session_id": request.session.sid,
            "uid": request.session.uid,
            "is_admin": request.env.user.has_group('base.group_system'),
            "is_superuser": request.env.user._is_superuser() if request.session.uid else False,
            "user_context": request.session.get_context() if request.session.uid else {},
            "db": request.session.db,
            "server_version": version_info.get('server_version'),
            "server_version_info": version_info.get('server_version_info'),
            "name": user.name,
            "username": user.login,
            "company_id": request.env.user.company_id.id if request.session.uid else None,
            "partner_id": request.env.user.partner_id.id if request.session.uid and request.env.user.partner_id else None,
            "user_companies": {'current_company': (user.company_id.id, user.company_id.name), 'allowed_companies': [(comp.id, comp.name) for comp in user.company_ids]} if display_switch_company_menu else False,
            "currencies": self.get_currencies() if request.session.uid else {},
        }

    def get_currencies(self):
        Currency = request.env['res.currency']
        currencies = Currency.search([]).read(['symbol', 'position', 'decimal_places'])
        return { c['id']: {'symbol': c['symbol'], 'position': c['position'], 'digits': [69,c['decimal_places']]} for c in currencies} 
