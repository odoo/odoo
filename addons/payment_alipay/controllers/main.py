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
from openerp.addons.payment_alipay.models import util

_logger = logging.getLogger(__name__)


class AlipayController(http.Controller):
    _notify_url = '/payment/alipay/notify/'
    _return_url = '/payment/alipay/return/'
    _cancel_url = '/payment/alipay/cancel/'

    def alipay_validate_data(self, **post):
        res = False
        cr, uid, context = request.cr, request.uid, request.context
        _KEY = request.registry['payment.acquirer']._get_alipay_partner_key()
        _, prestr = util.params_filter(post)
        mysign = util.build_mysign(prestr, _KEY, 'MD5')
        if mysign != post.get('sign'):
            return 'false'

        reference = post.get('out_trade_no')
        notify_id = post.get('notify_id')
        seller_id = post.get('seller_id')
        tx = None
        if reference:
            tx_ids = request.registry['payment.transaction'].search(cr, uid, [('reference', '=', reference)], context=context)
            if tx_ids:
                tx = request.registry['payment.transaction'].browse(cr, uid, tx_ids[0], context=context)
        alipay_urls = request.registry['payment.acquirer']._get_alipay_urls(cr, uid, tx and tx.acquirer_id and tx.acquirer_id.environment or 'prod', context=context)
        validate_url = alipay_urls['alipay_url']
        new_post = {
            'service':'notify_verify',
            'partner': seller_id ,
            'notify_id': notify_id,
        }
        urequest = urllib2.Request(validate_url, werkzeug.url_encode(new_post))
        uopen = urllib2.urlopen(urequest)
        resp = uopen.read()
        if resp == 'true':
            _logger.info('Alipay: validated data')
            res = request.registry['payment.transaction'].form_feedback(cr, SUPERUSER_ID, post, 'alipay', context=context)
        else:
            _logger.warning('Alipay: unrecognized alipay answer, received %s instead of VERIFIED or INVALID' % resp.text)
        return res

    @http.route('/payment/alipay/notify', type='http', auth='none', methods=['POST'])
    def alipay_notify(self, **post):
        """ Alipay Notify. """
        _logger.info('Beginning Alipay notify form_feedback with post data %s', pprint.pformat(post))  # debug
        if self.alipay_validate_data(**post):
            return 'success'
        else:
            return ''

    @http.route('/payment/alipay/return', type='http', auth="none", methods=['GET'])
    def alipay_return(self, **get):
        """ Alipay Return """
        _logger.info('Beginning Alipay return form_feedback with post data %s', pprint.pformat(get))  # debug
        res = request.registry['payment.transaction'].form_feedback(cr, SUPERUSER_ID, get, 'alipay', context=context)
        return ''

    @http.route('/payment/alipay/cancel', type='http', auth="none")
    def alipay_cancel(self, **post):
        """ When the user cancels its Alipay payment: GET on this route """
        cr, uid, context = request.cr, SUPERUSER_ID, request.context
        _logger.info('Beginning Alipay cancel with post data %s', pprint.pformat(post))  # debug

        return ''
