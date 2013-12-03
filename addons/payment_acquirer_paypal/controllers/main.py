# -*- coding: utf-8 -*-

try:
    import simplejson as json
except ImportError:
    import json
import logging
import pprint
import urllib
import urllib2

from openerp.addons.web import http
from openerp.addons.web.http import request
from openerp.addons.website.models import website

_logger = logging.getLogger(__name__)


class PaypalController(http.Controller):
    _notify_url = '/payment/paypal/ipn/'
    _return_url = '/payment/paypal/dpn/'
    _cancel_url = '/payment/paypal/cancel/'

    def paypal_validate_data(self, **post):
        """ Paypal IPN: three steps validation to ensure data correctness

         - step 1: return an empty HTTP 200 response -> will be done at the end
           by returning ''
         - step 2: POST the complete, unaltered message back to Paypal (preceded
           by cmd=_notify-validate), with same encoding
         - step 3: paypal send either VERIFIED or INVALID (single word)

        Once data is validated, process it. """
        res = False
        new_post = dict(post, cmd='_notify-validate')
        urequest = urllib2.Request("https://www.sandbox.paypal.com/cgi-bin/webscr", urllib.urlencode(new_post))
        uopen = urllib2.urlopen(urequest)
        resp = uopen.read()
        if resp.text == 'VERIFIED':
            _logger.info('Paypal: validated data')
            cr, uid, context = request.cr, request.uid, request.context
            res = request.registry['payment.transaction'].form_feedback(cr, uid, post, 'paypal', context=context)
        elif resp.text == 'INVALID':
            _logger.warning('Paypal: answered INVALID on data verification')
        else:
            _logger.warning('Paypal: unrecognized paypal answer, received %s instead of VERIFIED or INVALID' % resp.text)
        return res

    @website.route([
        '/payment/paypal/ipn/',
    ], type='http', auth='public')
    def paypal_ipn(self, **post):
        """ Paypal IPN. """
        _logger.info('Beginning Paypal IPN form_feedback with post data %s', pprint.pformat(post))  # debug
        self.paypal_validate_data(**post)
        return ''

    @website.route([
        '/payment/paypal/dpn',
    ], type='http', auth="public")
    def paypal_dpn(self, **post):
        """ Paypal DPN """
        _logger.info('Beginning Paypal DPN form_feedback with post data %s', pprint.pformat(post))  # debug
        return_url = post.pop('return_url', '')
        if not return_url:
            custom = json.loads(post.pop('custom', '{}'))
            return_url = custom.pop('return_url', '/')
        self.paypal_validate_data(**post)
        return request.redirect(return_url)

    @website.route([
        '/payment/paypal/cancel',
    ], type='http', auth="public")
    def paypal_cancel(self, **post):
        """ TODO
        """
        cr, uid, context = request.cr, request.uid, request.context
        print 'Entering paypal_cancel with post', post

        return_url = post.pop('return_url', '/')
        print 'return_url', return_url
        return request.redirect(return_url)
