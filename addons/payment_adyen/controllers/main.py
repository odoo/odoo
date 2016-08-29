# -*- coding: utf-8 -*-

import json
import logging
import pprint
import werkzeug

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class AdyenController(http.Controller):
    _return_url = '/payment/adyen/return/'

    @http.route([
        '/payment/adyen/return',
    ], type='http', auth='none', csrf=False)
    def adyen_return(self, **post):
        _logger.info('Beginning Adyen form_feedback with post data %s', pprint.pformat(post))  # debug
        if post.get('authResult') not in ['CANCELLED']:
            request.env['payment.transaction'].sudo().form_feedback(post, 'adyen')
        return_url = post.pop('return_url', '')
        if not return_url:
            custom = json.loads(post.pop('merchantReturnData', '{}'))
            return_url = custom.pop('return_url', '/')
        return werkzeug.utils.redirect(return_url)

    @http.route([
        '/payment/adyen/notification',
    ], type='http', auth='none', methods=['POST'], csrf=False)
    def adyen_notification(self, **post):
        tx = post.get('merchantReference') and request.env['payment.transaction'].sudo().search([('reference', 'in', [post.get('merchantReference')])], limit=1)
        if post.get('eventCode') in ['AUTHORISATION'] and tx:
            states = (post.get('merchantReference'), post.get('success'), tx.state)
            if (post.get('success') == 'true' and tx.state == 'done') or (post.get('success') == 'false' and tx.state in ['cancel', 'error']):
                _logger.info('Notification from Adyen for the reference %s: received %s, state is %s', states)
            else:
                _logger.warning('Notification from Adyen for the reference %s: received %s but state is %s', states)
        return '[accepted]'
