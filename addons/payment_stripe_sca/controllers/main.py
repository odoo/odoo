# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import werkzeug

from odoo.http import route, request
from odoo.addons.payment_stripe.controllers.main import StripeController

_logger = logging.getLogger(__name__)


class StripeControllerSCA(StripeController):
    _success_url = '/payment/stripe/success'
    _cancel_url = '/payment/stripe/cancel'

    @route(['/payment/stripe/success', '/payment/stripe/cancel'], type='http', auth='public')
    def stripe_success(self, **kwargs):
        request.env['payment.transaction'].sudo().form_feedback(kwargs, 'stripe')
        return werkzeug.utils.redirect(kwargs.get('return_url', '/'))

    @route(['/payment/stripe/s2s/create_json_3ds'], type='json', auth='public', csrf=False)
    def stripe_s2s_create_json_3ds(self, **kwargs):
        if not kwargs.get('partner_id'):
            kwargs = dict(kwargs, partner_id=request.env.user.partner_id.id)
        token = request.env['payment.acquirer'].browse(int(kwargs.get('acquirer_id'))).s2s_process(kwargs)

        if not token:
            return {
                'result': False,
            }

        return {
            'result': True,
            'id': token.id,
            'short_name': token.short_name,
            '3d_secure': False,
        }

    @route('/payment/stripe/s2s/create_setup_intent', type='json', auth='public', csrf=False)
    def stripe_s2s_create_setup_intent(self, acquirer_id, **kwargs):
        acquirer = request.env['payment.acquirer'].browse(int(acquirer_id))
        res = acquirer._create_setup_intent(kwargs)
        return res.get('client_secret')

    @route('/payment/stripe/set_payment_intent', type='json', auth='public')
    def stripe_create_payment_intent(self, tx_id, stripe_session_id, **post):
        tx = request.env['payment.transaction'].browse(int(tx_id))
        if tx.acquirer_id.provider != 'stripe':
            return False
        tx.sudo()._stripe_retrieve_payment_intent(stripe_session_id)
        return True

    @route('/payment/stripe/s2s/process_payment_intent', type='json', auth='public')
    def stripe_s2s_confirm_payment_intent(self, **post):
        return request.env['payment.transaction'].sudo().form_feedback(post, 'stripe')

    @route('/payment/stripe/token_uses_stripe', type='json', auth='public')
    def stripe_token_check(self, pm_id, **kwargs):
        token = request.env['payment.token'].browse(int(pm_id))
        return token.acquirer_id.provider == 'stripe'

    # These routes are deprecated, let's remove them for security's sake
    def stripe_s2s_create_json(self, **post):
        raise werkzeug.exceptions.NotFound()

    def stripe_s2s_create(self, **post):
        raise werkzeug.exceptions.NotFound()

    def stripe_create_charge(self, **post):
        raise werkzeug.exceptions.NotFound()
