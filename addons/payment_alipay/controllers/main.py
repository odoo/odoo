# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pprint
import requests
import werkzeug

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class AlipayController(http.Controller):
    _notify_url = '/payment/alipay/notify'
    _return_url = '/payment/alipay/return'

    def _alipay_validate_data(self, **post):
        resp = post.get('trade_status')
        if resp:
            if resp in ['TRADE_FINISHED', 'TRADE_SUCCESS']:
                _logger.info('Alipay: validated data')
            elif resp == 'TRADE_CLOSED':
                _logger.warning('Alipay: payment refunded to user and closed the transaction')
            else:
                _logger.warning('Alipay: unrecognized alipay answer, received %s instead of TRADE_FINISHED/TRADE_SUCCESS and TRADE_CLOSED' % (post['trade_status']))
        if post.get('out_trade_no') and post.get('trade_no'):
            post['reference'] = request.env['payment.transaction'].sudo().search([('reference', '=', post['out_trade_no'])]).reference
            return request.env['payment.transaction'].sudo().form_feedback(post, 'alipay')
        return False

    def _alipay_validate_notification(self, **post):
        if post.get('out_trade_no'):
            alipay = request.env['payment.transaction'].sudo().search([('reference', '=', post.get('out_trade_no'))]).acquirer_id
        else:
            alipay = request.env['payment.acquirer'].sudo().search([('provider', '=', 'alipay')])
        val = {
            'service': 'notify_verify',
            'partner': alipay.alipay_merchant_partner_id,
            'notify_id': post['notify_id']
        }
        response = requests.post(alipay.alipay_get_form_action_url(), val)
        response.raise_for_status()
        _logger.info('Validate alipay Notification %s' % response.text)
        # After program is executed, the page must print “success” (without quote). If not, Alipay server would keep re-sending notification, until over 24 hour 22 minutes Generally, there are 8 notifications within 25 hours (Frequency: 2m,10m,15m,1h,2h,6h,15h)
        if response.text == 'true':
            self._alipay_validate_data(**post)
            return 'success'
        return ""

    @http.route('/payment/alipay/return', type='http', auth="public", methods=['GET', 'POST'])
    def alipay_return(self, **post):
        """ Alipay return """
        _logger.info('Beginning Alipay form_feedback with post data %s', pprint.pformat(post))
        self._alipay_validate_data(**post)
        return werkzeug.utils.redirect('/payment/process')

    @http.route('/payment/alipay/notify', type='http', auth='public', methods=['POST'], csrf=False)
    def alipay_notify(self, **post):
        """ Alipay Notify """
        _logger.info('Beginning Alipay notification form_feedback with post data %s', pprint.pformat(post))
        return self._alipay_validate_notification(**post)
