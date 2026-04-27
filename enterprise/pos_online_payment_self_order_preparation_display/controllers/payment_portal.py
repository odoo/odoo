# -*- coding: utf-8 -*-

from odoo.http import request
from odoo.addons.pos_online_payment.controllers.payment_portal import PaymentPortal

class PosSelfOrderPaymentPortal(PaymentPortal):

    def _on_payment_successful(self, order):
        request.env['pos_preparation_display.order'].sudo().process_order(order.id)
        return super()._on_payment_successful(order)
