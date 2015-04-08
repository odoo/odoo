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
from openerp.addons.payment_tenpay.models import util

_logger = logging.getLogger(__name__)


class TenpayController(http.Controller):
    _notify_url = '/payment/tenpay/notify/'
    _return_url = '/payment/tenpay/return/'



    def tenpay_validate_data(self, **post):
        res = False
        cr, uid, context = request.cr, request.uid, request.context
        ALIPAY_KEY = request.registry['payment.transaction']._get_partner_key()
        _, prestr = util.params_filter(post)
        mysign = util.build_mysign(prestr, ALIPAY_KEY)
        if mysign != post.get('sign'):
            return 'false'

        _logger.info('Tenpay: validated data')
        res = request.registry['payment.transaction'].form_feedback(cr, SUPERUSER_ID, post, 'tenpay',
                                                                    context=context)

        return res

    @http.route('/payment/tenpay/notify', type='http', auth='none', methods=['POST'])
    def tenpay_notify(self, **post):
        """ Tenpay Notify. """
        _logger.info('Beginning Tenpay notify form_feedback with post data %s', pprint.pformat(post))  # debug
        if self.tenpay_validate_data(**post):
            return 'success'
        else:
            return ''

    @http.route('/payment/tenpay/return', type='http', auth="none", methods=['GET'])
    def tenpay_return(self, **get):
        """ Tenpay Return """
        _logger.info('Beginning Tenpay return form_feedback with post data %s', pprint.pformat(get))  # debug
        res = request.registry['payment.transaction'].form_feedback(cr, SUPERUSER_ID, get, 'tenpay', context=context)
        return ''

