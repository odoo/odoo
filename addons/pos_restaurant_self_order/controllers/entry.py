# -*- coding: utf-8 -*-


from odoo.addons.pos_self_order.controllers.entry import PosQRMenuController
from odoo.addons.pos_self_order.controllers.utils import get_any_pos_config_sudo

from odoo.http import route
from odoo.http import request


class PosRestQRMenuController(PosQRMenuController):
    @route(
            [
                "/menu/",
                "/menu/<config_id>",
                "/menu/<config_id>/<path:subpath>"
            ],
        auth="public", website=True, sitemap=True,
    )
    def pos_self_order_start(self, config_id=None, access_token=None):
        return request.render(
            'pos_self_order.index',
            self._prepare_self_order_data(config_id, access_token),
        )

    def _prepare_self_order_data(self, config_id=None, access_token=None):
        self_order_mode = 'qr_code'
        table_ids = False
        pos_config_sudo = False
        pos_config_access_token = False

        if config_id and config_id.isnumeric() and access_token:
            pos_config_sudo = request.env["pos.config"].sudo().search([
                ("id", "=", config_id),
                ('access_token', '=', access_token)], limit=1)

        if pos_config_sudo and pos_config_sudo.has_active_session and pos_config_sudo.self_order_ordering_mode:
            self_order_mode = pos_config_sudo.self_order_pay_after
            pos_config_access_token = pos_config_sudo.access_token
            table_ids = request.env["restaurant.table"].sudo().search([]).read(["id", "name", "identifier"])
        elif config_id and config_id.isnumeric():
            pos_config_sudo = request.env["pos.config"].sudo().search([
                ("id", "=", config_id), ("self_order_view_mode", "=", True)], limit=1)
        else:
            pos_config_sudo = get_any_pos_config_sudo()

        return {
                'session_info': {
                    **request.env["ir.http"].get_frontend_session_info(),
                    'currencies': request.env["ir.http"].get_currencies(),
                    'pos_self_order_data': {
                        'table_ids': table_ids,
                        'self_order_mode': self_order_mode,
                        'access_token': pos_config_access_token,
                        **pos_config_sudo._get_self_order_data(),
                    },
                }
            }
