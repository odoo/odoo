# -*- coding: utf-8 -*-
import base64
import json
import logging
import pprint
import requests
import werkzeug

from reportlab.graphics.barcode import createBarcodeDrawing

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class StripeController(http.Controller):

    def _get_stripe_transaction(self, reference=None):
        TX = request.env['payment.transaction']
        tx = None
        if reference:
            tx = TX.sudo().search([('reference', '=', reference)])
        if not tx:
            tx_id = (request.session.get('sale_transaction_id') or request.session.get('website_payment_tx_id'))
            tx = TX.sudo().browse(int(tx_id))
        if not tx:
            raise werkzeug.exceptions.NotFound()
        return tx

    def _stripe_validate_payment(self, acquirer_id, **kwargs):
        acquirer = request.env['payment.acquirer'].browse(int(acquirer_id)).sudo()
        url = acquirer.get_stripe_url() + "/sources/" + kwargs.get('source')
        headers = {'AUTHORIZATION': 'Bearer %s' % acquirer.stripe_secret_key}
        resp = requests.post(url, headers=headers)
        data = json.loads(resp.text)
        if data.get('status') == 'chargeable':
            TX = self._get_stripe_transaction(data.get('metadata', {}).get('reference'))
            data = TX._create_stripe_charge(source=data.get('id'))
            data = data.get('source') or data
        _logger.info('Stripe: entering form_feedback with post data %s' % pprint.pformat(data))
        return_url = "/"
        if data:
            request.env['payment.transaction'].sudo().form_feedback(data, 'stripe')
            return_url = data.get('metadata', {}).get('return_url')
        return return_url

    @http.route(['/payment/stripe/return'], type='http', auth='public')
    def stripe_return(self, acquirer_id=False, **kwargs):
        return_url = self._stripe_validate_payment(acquirer_id, **kwargs)
        return werkzeug.utils.redirect(return_url)

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
        tx = self._get_stripe_transaction(post.get('reference'))
        response = None
        if tx.type == 'form_save' and tx.partner_id:
            payment_token_id = request.env['payment.token'].sudo().create({
                'acquirer_id': tx.acquirer_id.id,
                'partner_id': tx.partner_id.id,
                'stripe_token': post['stripeToken']
            })
            tx.payment_token_id = payment_token_id
            response = tx._create_stripe_charge(acquirer_ref=payment_token_id.acquirer_ref)
        else:
            response = tx._create_stripe_charge(source=post['stripeToken'])
        _logger.info('Stripe: entering form_feedback with post data %s', pprint.pformat(response))
        if response:
            request.env['payment.transaction'].sudo().with_context(lang=None).form_feedback(response, 'stripe')
        return werkzeug.utils.redirect(post.pop('return_url', '/'))

    @http.route(['/stripe/generate_qrcode'], type='json', auth='public')
    # create the QR code for Wechat payment
    def generate_qrcode(self, **kw):
        qr_img = createBarcodeDrawing('QR', value=kw.get('qr_code_url'), format='png', width=200, height=200, humanReadable=0)
        return base64.b64encode(qr_img.asString('png'))
