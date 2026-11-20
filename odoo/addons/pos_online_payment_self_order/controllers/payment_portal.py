# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request
from odoo.addons.pos_online_payment.controllers.payment_portal import PaymentPortal

class PaymentPortalSelfOrder(PaymentPortal):
    @http.route()
    def pos_order_pay(self, pos_order_id, access_token=None, exit_route=None):
        self._send_notification_payment_status(pos_order_id, 'progress')
        return super().pos_order_pay(pos_order_id, access_token=access_token, exit_route=exit_route)

    @http.route()
    def pos_order_pay_confirmation(self, pos_order_id, tx_id=None, access_token=None, exit_route=None, **kwargs):
        result = super().pos_order_pay_confirmation(pos_order_id, tx_id=tx_id, access_token=access_token, exit_route=exit_route, **kwargs)
        tx_sudo = request.env['payment.transaction'].sudo().search([('id', '=', tx_id)])

        if tx_sudo.state not in ('authorized', 'done'):
            self._send_notification_payment_status(pos_order_id, 'fail')
        else:
            self._send_notification_payment_status(pos_order_id, 'success')

        return result

    def _send_notification_payment_status(self, pos_order_id, status):
        pos_order = request.env['pos.order'].sudo().browse(pos_order_id)

        if pos_order.config_id.self_ordering_mode == 'kiosk':
            request.env['bus.bus']._sendone(f'pos_config-{pos_order.config_id.access_token}', 'ONLINE_PAYMENT_STATUS', {
                'status': status, # progress, success, fail
                'order': pos_order._export_for_self_order(),
            })
