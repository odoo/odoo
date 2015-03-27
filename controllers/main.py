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


class AlipayController(http.Controller):
    _notify_url = '/payment/alipay/ipn/'
    _return_url = '/payment/alipay/dpn/'
    _cancel_url = '/payment/alipay/cancel/'

    def _get_return_url(self, **post):
        """ Extract the return URL from the data coming from alipay. """
        return_url = post.pop('return_url', '')
        if not return_url:
            custom = json.loads(post.pop('custom', False) or '{}')
            return_url = custom.get('return_url', '/')
        return return_url

    def alipay_validate_data(self, **post):
        """ Alipay IPN: three steps validation to ensure data correctness

         - step 1: return an empty HTTP 200 response -> will be done at the end
           by returning ''
         - step 2: POST the complete, unaltered message back to Alipay (preceded
           by cmd=_notify-validate), with same encoding
         - step 3: alipay send either VERIFIED or INVALID (single word)

        Once data is validated, process it. """
        res = False
        new_post = dict(post, cmd='_notify-validate')
        cr, uid, context = request.cr, request.uid, request.context
        reference = post.get('item_number')
        tx = None
        if reference:
            tx_ids = request.registry['payment.transaction'].search(cr, uid, [('reference', '=', reference)], context=context)
            if tx_ids:
                tx = request.registry['payment.transaction'].browse(cr, uid, tx_ids[0], context=context)
        alipay_urls = request.registry['payment.acquirer']._get_alipay_urls(cr, uid, tx and tx.acquirer_id and tx.acquirer_id.environment or 'prod', context=context)
        validate_url = alipay_urls['alipay_form_url']
        urequest = urllib2.Request(validate_url, werkzeug.url_encode(new_post))
        uopen = urllib2.urlopen(urequest)
        resp = uopen.read()
        if resp == 'VERIFIED':
            _logger.info('Alipay: validated data')
            res = request.registry['payment.transaction'].form_feedback(cr, SUPERUSER_ID, post, 'alipay', context=context)
        elif resp == 'INVALID':
            _logger.warning('Alipay: answered INVALID on data verification')
        else:
            _logger.warning('Alipay: unrecognized alipay answer, received %s instead of VERIFIED or INVALID' % resp.text)
        return res

    @http.route('/payment/alipay/ipn/', type='http', auth='none', methods=['POST'])
    def alipay_ipn(self, **post):
        """ Alipay IPN. """
        _logger.info('Beginning Alipay IPN form_feedback with post data %s', pprint.pformat(post))  # debug
        self.alipay_validate_data(**post)
        return ''

    @http.route('/payment/alipay/dpn', type='http', auth="none", methods=['POST'])
    def alipay_dpn(self, **post):
        """ Alipay DPN """
        _logger.info('Beginning Alipay DPN form_feedback with post data %s', pprint.pformat(post))  # debug
        return_url = self._get_return_url(**post)
        self.alipay_validate_data(**post)
        return werkzeug.utils.redirect(return_url)

    @http.route('/payment/alipay/cancel', type='http', auth="none")
    def alipay_cancel(self, **post):
        """ When the user cancels its Alipay payment: GET on this route """
        cr, uid, context = request.cr, SUPERUSER_ID, request.context
        _logger.info('Beginning Alipay cancel with post data %s', pprint.pformat(post))  # debug
        return_url = self._get_return_url(**post)
        return werkzeug.utils.redirect(return_url)
