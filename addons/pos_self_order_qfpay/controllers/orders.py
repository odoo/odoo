# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.addons.pos_self_order.controllers.orders import PosSelfOrderController
from werkzeug.exceptions import NotFound


class PosSelfOrderQFPayController(PosSelfOrderController):
    @http.route('/pos-self-order/qfpay-sign-trade', auth='public', type='jsonrpc', website=True)
    def qfpay_sign_trade(self, access_token, order_id, order_access_token, payment_method_id):
        pos_config = self._verify_pos_config(access_token)
        order = pos_config.env['pos.order'].search([
            ('id', '=', order_id), ('config_id', '=', pos_config.id), ('access_token', '=', order_access_token), ('state', '=', 'draft'),
        ], limit=1)
        payment_method = pos_config.env['pos.payment.method'].browse(payment_method_id)
        if not order or payment_method not in pos_config.payment_method_ids:
            raise NotFound()

        amount = order.amount_total
        return payment_method.qfpay_sign_request({
            'func_type': 1001,
            'amt': int(amount) if amount.is_integer() else amount,
            'channel': payment_method.qfpay_payment_type,
            'out_trade_no': f'{order.uuid}--{order.session_id.id}--{payment_method.id}',
            'wait_card_timeout': 30,
            'camera_id': 1,
        })
