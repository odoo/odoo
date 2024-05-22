# -*- coding: utf-8 -*-
import json
import logging
import pprint
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
        token = request.env['payment.acquirer'].browse(int(kwargs.get('acquirer_id'))).with_context(stripe_manual_payment=True).s2s_process(kwargs)

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

    @http.route('/payment/stripe/s2s/create_setup_intent', type='json', auth='public', csrf=False)
    def stripe_s2s_create_setup_intent(self, acquirer_id, **kwargs):
        acquirer = request.env['payment.acquirer'].browse(int(acquirer_id))
        res = acquirer.with_context(stripe_manual_payment=True)._create_setup_intent(kwargs)
        return res.get('client_secret')

    @http.route('/payment/stripe/s2s/process_payment_intent', type='json', auth='public', csrf=False)
    def stripe_s2s_process_payment_intent(self, **post):
        return request.env['payment.transaction'].sudo().form_feedback(post, 'stripe')

    @http.route('/payment/stripe/s2s/process_payment_error', type='json', auth='public', csrf=False)
    def stripe_s2s_process_payment_error(self, **post):
        transaction_sudo = request.env['payment.transaction'].sudo().search([('reference', '=', post['reference']),
                                                                            ('provider', '=', 'stripe'),
                                                                            ('stripe_payment_intent_secret', '=', post['stripe_payment_intent_secret'])])
        transaction_sudo.write({'state': 'error', 'state_message': post['error']})

    @http.route('/payment/stripe/webhook', type='json', auth='public', csrf=False)
    def stripe_webhook(self, **kwargs):
        data = json.loads(request.httprequest.data)
        request.env['payment.acquirer'].sudo()._handle_stripe_webhook(data)
        return 'OK'