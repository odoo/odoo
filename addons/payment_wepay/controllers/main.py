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

    @http.route("/wepay/account_create/<model('payment.acquirer'):acquirer>", auth="user")
    def create_wepay_account(self, acquirer):
        get_param = request.env['ir.config_parameter'].sudo().get_param
        redirect_url = get_param('web.base.url') + "/wepay/account_done/"+str(acquirer.id)
        client_id = get_param('payment_wepay_%s_client_id' % acquirer.environment)
        return werkzeug.utils.redirect(acquirer.wepay_get_form_action_url()['authorization']+"?client_id="+client_id+"&redirect_uri="+redirect_url+"&scope=manage_accounts,collect_payments,view_user,preapprove_payments,send_money")

    @http.route("/wepay/account_done/<model('payment.acquirer'):acquirer>", auth="user")
    def wepay_account_done(self, acquirer, **post):
        get_param = request.env['ir.config_parameter'].sudo().get_param
        client_id = get_param('payment_wepay_%s_client_id' % acquirer.environment)
        client_secret = get_param('payment_wepay_%s_client_secret' % acquirer.environment)

        # Get access token of user
        val = {
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": get_param('web.base.url') + "/wepay/account_done/"+str(acquirer.id),
            "code": post['code'],
        }
        response = requests.post(acquirer.wepay_get_form_action_url()['token'], val)
        response.raise_for_status()
        vals = json.loads(response.text)
        acquirer.write({
            'wepay_access_token': vals.get('access_token'),
            'website_published': True,
            'wepay_user_type': 'existinguser',
            'wepay_client_id': client_id
        })

        # get user details from access token
        user_details_response = requests.post(acquirer.wepay_get_form_action_url()['user'], headers=acquirer.get_wepay_header())
        user_details_response.raise_for_status()
        user_details = json.loads(user_details_response.text)

        # Create account for user to accept payment
        user_create_account = json.dumps({
            'name': user_details.get('user_name'),
            'description': 'New User Account'
        })
        response = requests.post(acquirer.wepay_get_form_action_url()['create_account'], data=user_create_account, headers=acquirer.get_wepay_header())
        response.raise_for_status()
        vals = json.loads(response.text)
        acquirer.write({'wepay_account_id': vals.get('account_id')})
        return werkzeug.utils.redirect("/web#id="+str(acquirer.id)+"&model=payment.acquirer&view_type=form")
