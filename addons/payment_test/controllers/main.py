# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http, _
from odoo.http import request
from odoo.exceptions import UserError


class PaymentTestController(http.Controller):

    @http.route(['/payment/test/s2s/create_json_3ds'], type='json', auth='public', csrf=False)
    def payment_test_s2s_create_json_3ds(self, verify_validity=False, **kwargs):
        if not kwargs.get('partner_id'):
            kwargs = dict(kwargs, partner_id=request.env.user.partner_id.id)
        acquirer = request.env['payment.acquirer'].browse(int(kwargs.get('acquirer_id')))
        if acquirer.state != 'test':
            raise UserError(_("Please do not use this acquirer for a production environment!"))
        token = acquirer.s2s_process(kwargs)

        return {
            'result': True,
            'id': token.id,
            'short_name': 'short_name',
            '3d_secure': False,
            'verified': True,
        }
