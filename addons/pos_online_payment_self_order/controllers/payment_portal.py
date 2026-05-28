# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request
from odoo.addons.pos_online_payment.controllers.payment_portal import PaymentPortal

import re
from werkzeug.urls import url_parse

class PaymentPortalSelfOrder(PaymentPortal):
    @http.route()
    def pos_order_pay(self, pos_order_id, access_token=None, exit_route=None):
        self._send_notification_payment_status(pos_order_id, 'progress')
        request.session['pos_order_id'] = pos_order_id
        return super().pos_order_pay(pos_order_id, access_token=access_token, exit_route=exit_route)

    @http.route()
    def pos_order_pay_confirmation(self, pos_order_id, tx_id=None, access_token=None, exit_route=None, **kwargs):
        result = super().pos_order_pay_confirmation(pos_order_id, tx_id=tx_id, access_token=access_token, exit_route=exit_route, **kwargs)
        tx_sudo = request.env['payment.transaction'].sudo().search([('id', '=', tx_id)])

        if tx_sudo.state not in ('authorized', 'done'):
            self._send_notification_payment_status(pos_order_id, 'fail')

        return result

    @http.route('/pos/pay/dummy', type='http', auth='public', methods=['POST'], csrf=False)
    def pos_pay_dummy(self, **kwargs):
        reference = kwargs.get('reference')
        tx_sudo = request.env['payment.transaction'].sudo()
        if reference:
            tx_sudo = tx_sudo.search([('reference', '=', reference)])
        else:
            pos_order_id = request.session.pop('pos_order_id', None)
            if not pos_order_id:
                referer = request.httprequest.headers.get('Referer')
                if referer:
                    try:
                        path = url_parse(referer).path
                        match = re.search(r'/pos/pay/(\d+)', path)
                        if match:
                            pos_order_id = int(match.group(1))
                    except Exception:  # noqa: BLE001
                        pass

            if pos_order_id:
                tx_sudo = tx_sudo.search([('pos_order_id', '=', pos_order_id), ('state', 'in', ('draft', 'pending'))], limit=1, order='id desc')

            if not tx_sudo:
                tx_sudo = tx_sudo.search([('state', 'in', ('draft', 'pending'))], limit=1, order='id desc')

        tx_sudo._set_done()
        request.env.ref('payment.cron_post_process_payment_tx').sudo().method_direct_trigger()
        return request.redirect(tx_sudo.landing_route)

    def _send_notification_payment_status(self, pos_order_id, status):
        pos_order = request.env['pos.order'].sudo().browse(pos_order_id)
        pos_order._send_notification_online_payment_status(status)
        if status == 'success':
            pos_order._send_order()
