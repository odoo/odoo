# -*- coding: utf-8 -*-

import json
import logging
import pprint
import urllib
import urllib2
import werkzeug

from odoo import http
from odoo.addons.payment.models.payment_acquirer import ValidationError
from odoo.http import request

_logger = logging.getLogger(__name__)


class PaypalController(http.Controller):
    _notify_url = '/payment/paypal/ipn/'
    _return_url = '/payment/paypal/dpn/'
    _cancel_url = '/payment/paypal/cancel/'

    def _get_return_url(self, **post):
        """ Extract the return URL from the data coming from paypal. """
        return_url = post.pop('return_url', '')
        if not return_url:
            custom = json.loads(urllib.unquote_plus(post.pop('custom', False) or post.pop('cm', False) or '{}'))
            return_url = custom.get('return_url', '/')
        return return_url

    def _parse_pdt_response(self, response):
        """ Parse a text response for a PDT verification.

            :param response str: text response, structured in the following way:
                STATUS\nkey1=value1\nkey2=value2...\n
             or STATUS\nError message...\n
            :rtype tuple(str, dict)
            :return: tuple containing the STATUS str and the key/value pairs
                     parsed as a dict
        """
        lines = [line for line in response.split('\n') if line]
        status = lines.pop(0)

        pdt_post = {}
        for line in lines:
            split = line.split('=', 1)
            if len(split) == 2:
                pdt_post[split[0]] = urllib.unquote_plus(split[1]).decode('utf8')
            else:
                _logger.warning('Paypal: error processing pdt response: %s', line)

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
        reference = post.get('item_number')
        tx = None
        if reference:
            tx = request.env['payment.transaction'].search([('reference', '=', reference)])
        paypal_urls = request.env['payment.acquirer']._get_paypal_urls(tx and tx.acquirer_id.environment or 'prod')
        pdt_request = bool(new_post.get('amt'))  # check for spefific pdt param
        if pdt_request:
            # this means we are in PDT instead of DPN like before
            # fetch the PDT token
            new_post['at'] = tx and tx.acquirer_id.paypal_pdt_token or ''
            new_post['cmd'] = '_notify-synch'  # command is different in PDT than IPN/DPN
        validate_url = paypal_urls['paypal_form_url']
        urequest = urllib2.Request(validate_url, werkzeug.url_encode(new_post))
        uopen = urllib2.urlopen(urequest)
        resp = uopen.read()
        if pdt_request:
            resp, post = self._parse_pdt_response(resp)
        if resp in ['VERIFIED', 'SUCCESS']:
            _logger.info('Paypal: validated data')
            res = request.env['payment.transaction'].sudo().form_feedback(post, 'paypal')
        elif resp in ['INVALID', 'FAIL']:
            _logger.warning('Paypal: answered INVALID/FAIL on data verification')
        else:
            _logger.warning('Paypal: unrecognized paypal answer, received %s instead of VERIFIED/SUCCESS or INVALID/FAIL (validation: %s)' % (resp, 'PDT' if pdt_request else 'IPN/DPN'))
        return res

    @http.route('/payment/paypal/ipn/', type='http', auth='none', methods=['POST'], csrf=False)
    def paypal_ipn(self, **post):
        """ Paypal IPN. """
        _logger.info('Beginning Paypal IPN form_feedback with post data %s', pprint.pformat(post))  # debug
        try:
            self.paypal_validate_data(**post)
        except ValidationError:
            _logger.exception('Unable to validate the Paypal payment')
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
        _logger.info('Beginning Paypal cancel with post data %s', pprint.pformat(post))  # debug
        return_url = self._get_return_url(**post)
        return werkzeug.utils.redirect(return_url)
