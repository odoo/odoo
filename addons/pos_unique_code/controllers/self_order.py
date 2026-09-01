# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request

from odoo.addons.pos_self_order.controllers.orders import PosSelfOrderController


class PosUniqueCodeController(PosSelfOrderController):
    @http.route('/pos-self-order/consume-unique-code', auth='public', type='jsonrpc', website=True)
    def consume_unique_code(self, access_token, code):
        """Consume a one-time code from the kiosk.

        The access token is verified the same way as for the other self order
        routes, so an anonymous visitor cannot burn codes without a valid kiosk.
        """
        self._verify_pos_config(access_token)
        return request.env['pos.unique.code'].sudo().consume_code(code)
