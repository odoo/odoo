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
    _notify_url = '/payment/alipay/notify'  # TODO ARJ simple nitpicking, but wouldn't it be cleaner to make those constants?
    _return_url = '/payment/alipay/return'  # If these are constant, they should be modified in all modules

    def _alipay_validate_notification(self, **post):
        alipay = request.env['payment.acquirer'].sudo().search([('provider', '=', 'alipay')], limit=1)
        val = {
            'service': 'notify_verify',
            'partner': alipay.alipay_merchant_partner_id,
            'notify_id': post['notify_id']
        }
        # https://global.alipay.com/docs/ac/hk_auto_debit/notif
        response = requests.post(alipay._get_alipay_urls(), val)
        response.raise_for_status()
        _logger.info('Validate alipay Notification %s' % response.text)
        # After program is executed, the page must print “success” (without quote). If not, Alipay server would
        # keep re-sending notification, until over 24 hour 22 minutes
        # Generally, there are 8 notifications within 25 hours (Frequency: 2m,10m,15m,1h,2h,6h,15h).
        if response.text == 'true':
            request.env['payment.transaction'].sudo()._handle_feedback_data('alipay', post)
            return 'success'
        return "fail"

    # TODO ARJ there is still the not so likely eventuality of an HTTP 307 but I think that we can safely drop the POST
    @http.route('/payment/alipay/return', type='http', auth="public", methods=['GET', 'POST'])
    def return_from_redirect(self, **post):
        """ Alipay return """
        _logger.info('Beginning Alipay _handle_feedback_data with post data %s', pprint.pformat(post))
        request.env['payment.transaction'].sudo()._handle_feedback_data('alipay', post)
        return werkzeug.utils.redirect('/payment/status')

    @http.route('/payment/alipay/notify', type='http', auth='public', methods=['POST'], csrf=False)
    def alipay_notify(self, **post):
        """ Alipay Notify """
        _logger.info('Beginning Alipay notification form_feedback with post data %s', pprint.pformat(post))
        return self._alipay_validate_notification(**post)
