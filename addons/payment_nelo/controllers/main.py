# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import json
import logging
import requests
import werkzeug

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class NeloController(http.Controller):
    _confirm_url = '/payment/nelo/confirm'
    _cancel_url = '/payment/nelo/cancel'

    def _nelo_auth_payment(self, **post):
        claims = self._get_claims(post['checkoutToken'])

        if claims.get('order_id'):
            acquirer = request.env['payment.acquirer'].sudo().search([('provider', '=', 'nelo')])
            payload = json.dumps({
                'checkoutToken': post['checkoutToken']
            })
            headers = {
                'Authorization': 'Bearer %s' % (acquirer.nelo_merchant_secret),
                'Content-Type': 'application/json'
            }
            url = '%s/charge/auth' % (acquirer._get_nelo_urls()['rest_url'])
            response = requests.request("POST", url, headers=headers, data=payload)
            _logger.info('Response for url %s\n %s\n', url, response)  # debug
            response.raise_for_status()

            url = '%s/charge/capture' % (acquirer._get_nelo_urls()['rest_url'])
            response = requests.request("POST", url, headers=headers, data=payload)
            _logger.info('Response for url %s\n %s\n', url, response)  # debug
            response.raise_for_status()
            
            data = {
                'reference': claims.get('order_id')
            }
            return request.env['payment.transaction'].sudo().form_feedback(data, 'nelo')
        return False
    
    def _get_claims(self, checkoutToken):
        claims_base64 = checkoutToken.split(".")[1]
        claims_base64 += "=" * ((4 - len(claims_base64) % 4) % 4) # add padding
        claims_bytes = base64.b64decode(claims_base64, validate=False)
        return json.loads(claims_bytes.decode('ascii'))

    @http.route('/payment/nelo/confirm', type='http', auth="public", methods=['GET', 'POST'], csrf=False)
    def nelo_return(self, **post):
        if post and post['checkoutToken']:
            self._nelo_auth_payment(**post)
        return werkzeug.utils.redirect('/payment/process')

    @http.route('/payment/nelo/cancel', type='http', auth='public', methods=['GET', 'POST'], csrf=False)
    def nelo_notify(self, **post):
        return werkzeug.utils.redirect('/payment/process')
