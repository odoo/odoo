# -*- coding: utf-8 -*-
import base64
import logging
import pprint
import werkzeug

from reportlab.graphics.barcode import createBarcodeDrawing

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class StripeController(http.Controller):

    @http.route(['/payment/stripe/return'], type='http', auth='public')
    def stripe_return(self, acquirer_id=False, **kwargs):
        kwargs['acquirer_id'] = acquirer_id
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

    @http.route(['/payment/stripe/create_charge'], type='http', auth='public')
    def stripe_create_charge(self, **post):
        """ Create a payment transaction

        Expects the result from the user input from stripe element popup"""
        TX = request.env['payment.transaction']
        tx = None
        if post.get('reference'):
            tx = TX.sudo().search([('reference', '=', post['reference'])])
        if not tx:
            tx_id = (post.get('tx_id') or request.session.get('sale_transaction_id') or
                     request.session.get('website_payment_tx_id'))
            tx = TX.sudo().browse(int(tx_id))
        if not tx:
            raise werkzeug.exceptions.NotFound()

        response = tx._create_stripe_charge(source=post['stripeToken'])
        _logger.info('Stripe: entering form_feedback with post data %s', pprint.pformat(response))
        if response:
            request.env['payment.transaction'].sudo().with_context(lang=None).form_feedback(response, 'stripe')
        return werkzeug.utils.redirect('/payment/process')

    @http.route(['/stripe/generate_qrcode'], type='json', auth='public')
    # create the QR code for Wechat payment
    def generate_qrcode(self, **kw):
        qr_img = createBarcodeDrawing('QR', value=kw.get('qr_code_url'), format='png', width=200, height=200, humanReadable=0)
        return base64.b64encode(qr_img.asString('png'))
