# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request


class PosMollieController(http.Controller):

    @http.route('/pos_mollie/webhook/<string:payment_type>/<int:payment_method_id>', type='http', methods=['POST'], auth='public', csrf=False, save_session=False)
    def pos_mollie_webhook(self, payment_type, payment_method_id, **post):
        if not post.get('id'):
            return
        payment_method_sudo = request.env['pos.payment.method'].sudo().browse(payment_method_id)
        if payment_method_sudo.exists() and payment_method_sudo.use_payment_terminal == 'mollie':
            payment_method_sudo._mollie_process_webhook(post, payment_type)
        return request.make_json_response({'status': 'ok'}, status=200)  # send 200 response to mark it as successful
