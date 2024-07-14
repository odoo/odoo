# -*- coding: utf-8 -*-

from odoo.http import request
from odoo.addons.pos_online_payment.controllers.payment_portal import PaymentPortal

class PosSelfOrderPaymentPortal(PaymentPortal):

    def _render_pay_confirmation(self, rendering_context):
        if rendering_context.get('state') == 'success':
            request.env['pos_preparation_display.order'].sudo().process_order(rendering_context.get('pos_order_id'))
        return super()._render_pay_confirmation(rendering_context)
