# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging
import pprint
import requests
import werkzeug

from odoo import http
from odoo.http import request
from odoo.addons.payment.models.payment_acquirer import ValidationError

_logger = logging.getLogger(__name__)


class WepayController(http.Controller):
    _notify_url = '/payment/wepay/ipn'
    _return_url = '/payment/wepay/dpn'

    def _wepay_validate_data(self, **post):
        """ WePay Validate: validate post data received from WePay """
        res = False
        if post.get('reference_id'):
            wepay = request.env['payment.transaction'].search([('reference', '=', post.get('reference_id'))]).acquirer_id
            post.pop('reference_id', False)
        else:
            wepay = request.env['payment.acquirer'].sudo().search([('provider', '=', 'wepay')], limit=1)
        response = requests.post(wepay.wepay_get_form_action_url()['checkout'], data=json.dumps(post), headers=wepay.get_wepay_header())
        response.raise_for_status()
        vals = json.loads(response.text)
        resp = vals.get('state')
        if resp in ['authorized', 'captured']:
            _logger.info('WePay: validated data')
        elif resp in ['cancelled', 'falled', 'failed']:
            _logger.warning('WePay: answered INVALID/FAIL on data verification')
        elif resp == 'released':
            _logger.warning('WePay: answered pending on data verification')
        else:
            _logger.warning('WePay: unrecognized WePay answer, received %s instead of authorized/captured or cancelled/falled or released (validation: %s)' % resp)
        if vals.get('checkout_id'):
            res = request.env['payment.transaction'].sudo().form_feedback(vals, 'wepay')
        return res

    @http.route('/payment/wepay/dpn', type='http', auth="none", methods=['POST', 'GET'], csrf=False)
    def wepay_dpn(self, redirect_url=False, **post):
        """ wepay DPN """
        _logger.info('Beginning wepay DPN form_feedback with post data %s', pprint.pformat(post))
        try:
            self._wepay_validate_data(**post)
        except ValidationError:
            _logger.exception('Unable to validate the WePay payment')
        return werkzeug.utils.redirect(redirect_url or "/")

    @http.route('/payment/wepay/ipn', type='http', auth="none", methods=['POST', 'GET'], csrf=False)
    def wepay_ipn(self, **post):
        """ wepay IPN """
        _logger.info('Beginning wepay IPN form_feedback with post data %s', pprint.pformat(post))
        try:
            self._wepay_validate_data(**post)
        except ValidationError:
            _logger.exception('Unable to validate the WePay payment')
        return ''

    @http.route(['/payment/wepay/s2s/create_credit_card_id'], type='json', auth='public', csrf=False)
    def wepay_s2s_create_json_3ds(self, verify_validity=False, **kwargs):
        token = request.env['payment.acquirer'].browse(int(kwargs.get('acquirer_id'))).s2s_process(kwargs)
        res = {
            'result': False,
        }
        if token:
            res.update({
                'result': True,
                'id': token.id,
                'short_name': token.short_name,
                '3d_secure': False,
                'verified': False,
            })
            if verify_validity:
                token.validate()
                res['verified'] = token.verified
        return res
