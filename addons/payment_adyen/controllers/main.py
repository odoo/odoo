# -*- coding: utf-8 -*-

import json
import logging
import pprint
import werkzeug

from openerp import http, SUPERUSER_ID
from openerp.http import request

_logger = logging.getLogger(__name__)


class AdyenController(http.Controller):
    _return_url = '/payment/adyen/return/'

    @http.route([
        '/payment/adyen/return',
    ], type='http', auth='none')
    def adyen_return(self, **post):
        _logger.info('Beginning Adyen form_feedback with post data %s', pprint.pformat(post))  # debug
        if post.get('authResult') not in ['CANCELLED']:
            request.registry['payment.transaction'].form_feedback(request.cr, SUPERUSER_ID, post, 'adyen', context=request.context)
        return_url = post.pop('return_url', '')
        if not return_url:
            custom = json.loads(post.pop('merchantReturnData', '{}'))
            return_url = custom.pop('return_url', '/')
        return werkzeug.utils.redirect(return_url)

    @http.route([
        '/payment/adyen/notification',
    ], type='http', auth='none', methods=['POST'])
    def adyen_notification(self, **post):
        tx_id = post.get('merchantReference') and request.registry['payment.transaction'].search(request.cr, SUPERUSER_ID, [('reference', 'in', [post.get('merchantReference')])], limit=1, context=request.context)
        if post.get('eventCode') in ['AUTHORISATION'] and tx_id:
            tx = request.registry['payment.transaction'].browse(request.cr, SUPERUSER_ID, tx_id, context=request.context)
            states = (post.get('merchantReference'), post.get('success'), tx.state)
            if (post.get('success') == 'true' and tx.state == 'done') or (post.get('success') == 'false' and tx.state in ['cancel', 'error']):
                _logger.info('Notification from Adyen for the reference %s: received %s, state is %s', states)
            else:
                _logger.warning('Notification from Adyen for the reference %s: received %s but state is %s', states)
        return '[accepted]'
