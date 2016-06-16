import json

import openerp
from openerp import models
from openerp.http import request


class Http(models.Model):
    _inherit = 'ir.http'

    def webclient_rendering_context(self):
        return {
            'menu_data': request.registry['ir.ui.menu'].load_menus(request.cr, request.uid, request.debug, context=request.context),
            'session_info': json.dumps(self.session_info()),
        }

    def session_info(self):
        user = request.env.user
        display_switch_company_menu = user.has_group('base.group_multi_company') and len(user.company_ids) > 1
        version_info = openerp.service.common.exp_version()
        return {
            "session_id": request.session_id,
            "uid": request.session.uid,
            "is_admin": request.env.user.has_group('base.group_system'),
            "user_context": request.session.get_context() if request.session.uid else {},
            "db": request.session.db,
            "server_version": version_info.get('server_version'),
            "server_version_info": version_info.get('server_version_info'),
            "name": user.name,
            "company_id": request.env.user.company_id.id if request.session.uid else None,
            "partner_id": request.env.user.partner_id.id if request.session.uid and request.env.user.partner_id else None,
            "user_companies": {'current_company': (user.company_id.id, user.company_id.name), 'allowed_companies': [(comp.id, comp.name) for comp in user.company_ids]} if display_switch_company_menu else False,
            "currencies": self.get_currencies(),
        }

    def get_currencies(self):
        Currency = request.env['res.currency']
        currencies = Currency.search([]).read(['symbol', 'position', 'decimal_places'])
        return { c['id']: {'symbol': c['symbol'], 'position': c['position'], 'digits': [69,c['decimal_places']]} for c in currencies} 
