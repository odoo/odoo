# -*- coding: utf-8 -*-

import json
import logging
import pprint
import urllib
import urllib2
import werkzeug

from openerp import http, SUPERUSER_ID
from openerp.http import request

_logger = logging.getLogger(__name__)


class PaypalController(http.Controller):
    _notify_url = '/payment/paypal/ipn/'
    _return_url = '/payment/paypal/dpn/'
    _cancel_url = '/payment/paypal/cancel/'

    def _get_return_url(self, **post):
        """ Extract the return URL from the data coming from paypal. """
        return_url = post.pop('return_url', '')
        if not return_url:
            custom = json.loads(post.pop('custom', False) or post.pop('cm', False) or '{}')
            return_url = custom.get('return_url', '/')
        return return_url

    def _parse_pdt_response(self, response):
        """ Parse a text response for a PDT verification .

            :param response str: text response, structured in the following way:
                STATUS\nkey1=value1\nkey2=value2...\n
            :rtype tuple(str, dict)
            :return: tuple containing the STATUS str and the key/value pairs
                     parsed as a dict
        """
        lines = filter(None, response.split('\n'))
        status = lines.pop(0)
        pdt_post = dict(line.split('=', 1) for line in lines)
        # html unescape
        for post in pdt_post:
            pdt_post[post] = urllib.unquote_plus(pdt_post[post]).decode('utf8')
        return status, pdt_post

    def paypal_validate_data(self, **post):
        """ Paypal IPN: three steps validation to ensure data correctness

         - step 1: return an empty HTTP 200 response -> will be done at the end
           by returning ''
         - step 2: POST the complete, unaltered message back to Paypal (preceded
           by cmd=_notify-validate or _notify-synch for PDT), with same encoding
         - step 3: paypal send either VERIFIED or INVALID (single word) for IPN
                   or SUCCESS or FAIL (+ data) for PDT

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
        pdt_request = bool(new_post.get('amt'))  # check for spefific pdt param
        if pdt_request:
            # this means we are in PDT instead of DPN like before
            # fetch the PDT token
            new_post['at'] = request.registry['ir.config_parameter'].get_param(cr, SUPERUSER_ID, 'payment_paypal.pdt_token')
            new_post['cmd'] = '_notify-synch'  # command is different in PDT than IPN/DPN
        paypal_urls = request.registry['payment.acquirer']._get_paypal_urls(cr, uid, tx and tx.acquirer_id and tx.acquirer_id.environment or 'prod', context=context)
        validate_url = paypal_urls['paypal_form_url']
        urequest = urllib2.Request(validate_url, werkzeug.url_encode(new_post))
        uopen = urllib2.urlopen(urequest)
        resp = uopen.read()
        if pdt_request:
            resp, post = self._parse_pdt_response(resp)
        if resp == 'VERIFIED' or pdt_request and resp == 'SUCCESS':
            _logger.info('Paypal: validated data')
            res = request.registry['payment.transaction'].form_feedback(cr, SUPERUSER_ID, post, 'paypal', context=context)
        elif resp == 'INVALID' or pdt_request and resp == 'FAIL':
            _logger.warning('Paypal: answered INVALID/FAIL on data verification')
        else:
            _logger.warning('Paypal: unrecognized paypal answer, received %s instead of VERIFIED/SUCCESS or INVALID/FAIL (validation: %s)' % (resp, 'PDT' if pdt_request else 'IPN/DPN'))
        return res

    @http.route('/payment/paypal/ipn/', type='http', auth='none', methods=['POST'], csrf=False)
    def paypal_ipn(self, **post):
        """ Paypal IPN. """
        _logger.info('Beginning Paypal IPN form_feedback with post data %s', pprint.pformat(post))  # debug
        self.paypal_validate_data(**post)
        return ''

    @http.route('/payment/paypal/dpn', type='http', auth="none", methods=['POST', 'GET'], csrf=False)
    def paypal_dpn(self, **post):
        """ Paypal DPN """
        _logger.info('Beginning Paypal DPN form_feedback with post data %s', pprint.pformat(post))  # debug
        return_url = self._get_return_url(**post)
        self.paypal_validate_data(**post)
        return werkzeug.utils.redirect(return_url)

    @http.route('/payment/paypal/cancel', type='http', auth="none", csrf=False)
    def paypal_cancel(self, **post):
        """ When the user cancels its Paypal payment: GET on this route """
        cr, uid, context = request.cr, SUPERUSER_ID, request.context
        _logger.info('Beginning Paypal cancel with post data %s', pprint.pformat(post))  # debug
        return_url = self._get_return_url(**post)
        return werkzeug.utils.redirect(return_url)
