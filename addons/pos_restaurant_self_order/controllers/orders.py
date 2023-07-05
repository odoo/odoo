# -*- coding: utf-8 -*-


from odoo.addons.pos_self_order.controllers.orders import PosSelfOrderController
from odoo.http import request, route
from werkzeug.exceptions import Unauthorized


class PosRestaurantSelfOrderController(PosSelfOrderController):
    def _prepare_order_data(self, unique_id, order, pos_session_sudo, sequence_number, pos_config_sudo):
        data = super()._prepare_order_data(unique_id, order, pos_session_sudo, sequence_number, pos_config_sudo)
        data['data']["table_id"] = order['table_id']
        return data

    @route('/pos-self-order/get-tables', auth='public', type='json', website=True)
    def get_tables(self, access_token):
        pos_config_sudo = request.env['pos.config'].sudo().search([('access_token', '=', access_token)], limit=1)

        if not pos_config_sudo or not pos_config_sudo.self_order_ordering_mode or not pos_config_sudo.has_active_session:
            raise Unauthorized("Invalid access token")

        tables = pos_config_sudo.floor_ids.table_ids.filtered(lambda t: t.active).read(['id', 'name', 'identifier', 'floor_id'])

        for table in tables:
            table['floor_name'] = table.get('floor_id')[1]

        return tables
