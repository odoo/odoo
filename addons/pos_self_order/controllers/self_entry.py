# -*- coding: utf-8 -*-
import werkzeug

from odoo import http
from odoo.http import request


class PosSelfKiosk(http.Controller):
    @http.route(["/pos-self/<config_id>", "/pos-self/<config_id>/<path:subpath>"], auth="public", website=True, sitemap=True)
    def start_self_ordering(self, config_id=None, access_token=None, table_identifier=None, subpath=None):
        pos_config, _, config_access_token = self._verify_entry_access(config_id, access_token, table_identifier)
        return request.render(
                'pos_self_order.index',
                {
                    'session_info': {
                        **request.env["ir.http"].get_frontend_session_info(),
                        'currencies': request.env["ir.http"].get_currencies(),
                        'data': {
                            'config_id': pos_config.id,
                            'access_token': config_access_token,
                            'self_ordering_mode': pos_config.self_ordering_mode,
                        },
                        "base_url": request.env['pos.session'].get_base_url(),
                    }
                }
            )

    @http.route("/pos-self/data/<config_id>", type='json', auth='public')
    def get_self_ordering_data(self, config_id=None, access_token=None, table_identifier=None):
        pos_config, _, _ = self._verify_entry_access(config_id, access_token, table_identifier)
        data = pos_config.load_self_data()
        return data

    def _verify_entry_access(self, config_id=None, access_token=None, table_identifier=None):
        table_sudo = False

        if not config_id or not config_id.isnumeric():
            raise werkzeug.exceptions.NotFound()

        if access_token:
            config_access_token = True
            pos_config_sudo = request.env["pos.config"].sudo().search([
                ("id", "=", config_id), ('access_token', '=', access_token)], limit=1)
        else:
            config_access_token = False
            pos_config_sudo = request.env["pos.config"].sudo().search([
                ("id", "=", config_id)], limit=1)

        if not pos_config_sudo or pos_config_sudo.self_ordering_mode == 'nothing':
            raise werkzeug.exceptions.NotFound()

        company = pos_config_sudo.company_id
        user = pos_config_sudo.self_ordering_default_user_id
        pos_config = pos_config_sudo.sudo(False).with_company(company).with_user(user).with_context(allowed_company_ids=company.ids)

        if not pos_config:
            raise werkzeug.exceptions.NotFound()

        if pos_config and pos_config.has_active_session and pos_config.self_ordering_mode == 'mobile':
            if config_access_token:
                config_access_token = pos_config.access_token
            table_sudo = table_identifier and (
                request.env["restaurant.table"]
                .sudo()
                .search([("identifier", "=", table_identifier), ("active", "=", True)], limit=1)
            )
            if table_sudo and table_sudo.parent_id:
                table_sudo = table_sudo.parent_id
        elif pos_config.self_ordering_mode == 'kiosk':
            if config_access_token:
                config_access_token = pos_config.access_token
        else:
            config_access_token = ''

        table = table_sudo.sudo(False).with_company(company).with_user(user) if table_sudo else False
        return pos_config, table, config_access_token
