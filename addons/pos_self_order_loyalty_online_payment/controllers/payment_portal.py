# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request
from odoo.addons.pos_online_payment_self_order.controllers.payment_portal import PaymentPortalSelfOrder


class PaymentPortalSelfOrderLoyalty(PaymentPortalSelfOrder):
    @http.route()
    def pos_order_pay(self, pos_order_id, access_token=None, exit_route=None):
        order = request.env['pos.order'].sudo().browse(pos_order_id)
        order._verify_coupon_validity()
        return super().pos_order_pay(pos_order_id, access_token=access_token, exit_route=exit_route)