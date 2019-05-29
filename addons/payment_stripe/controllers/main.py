# -*- coding: utf-8 -*-
import logging
import werkzeug

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class StripeController(http.Controller):
    _success_url = '/payment/stripe/success'
    _cancel_url = '/payment/stripe/cancel'

    @http.route(['/payment/stripe/success', '/payment/stripe/cancel'], type='http', auth='public')
    def stripe_success(self, **kwargs):
        request.env['payment.transaction'].sudo().form_feedback(kwargs, 'stripe')
        return werkzeug.utils.redirect('/payment/process')

    @http.route(['/payment/stripe/s2s/create_json_3ds'], type='json', auth='public', csrf=False)
    def stripe_s2s_create_json_3ds(self, verify_validity=False, **kwargs):
        if not kwargs.get('partner_id'):
            kwargs = dict(kwargs, partner_id=request.env.user.partner_id.id)
        token = request.env['payment.acquirer'].browse(int(kwargs.get('acquirer_id'))).s2s_process(kwargs)

        if not token:
            res = {
                'result': False,
            }
            return res

        res = {
            'result': True,
            'id': token.id,
            'short_name': token.short_name,
            '3d_secure': False,
            'verified': False,
        }

        if verify_validity != False:
            token.validate()
            res['verified'] = token.verified

        return res
