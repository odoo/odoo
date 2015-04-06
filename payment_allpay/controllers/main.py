# -*- coding: utf-8 -*-

try:
    import simplejson as json
except ImportError:
    import json
import logging
import pprint
import urllib2
import werkzeug

from openerp import http, SUPERUSER_ID
from openerp.http import request

_logger = logging.getLogger(__name__)


class allPayController(http.Controller):

    _return_url = '/payment/allpay/return/'

    @http.route('/payment/allpay/return', type='http', auth="none", methods=['POST'])
    def allpay_return(self, **post):
        """ allPay Return """

        _logger.info('Beginning allPay return form_feedback with post data %s', pprint.pformat(post))  # debug
        returns = request.registry['payment.acquirer'].checkout_feedback(post)
        if returns:
            if returns['RtnCode'] == '1':
                res = request.registry['payment.transaction'].form_feedback(cr, SUPERUSER_ID, post, 'allpay',
                                                                            context=context)
            else:
                return '0|Bad Request'
        else:
            return '0|Bad Request'
