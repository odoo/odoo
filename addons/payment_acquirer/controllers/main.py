# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2013-Today OpenERP SA (<http://www.openerp.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.addons.web import http
from openerp.addons.web.http import request
# from openerp.addons.payment_acquirer.models.payment_acquirer import ValidationError
from openerp.addons.website.models import website

import logging
import requests
from urllib import urlencode

_logger = logging.getLogger(__name__)


class PaypalController(http.Controller):
    _notify_url = '/payment/paypal/ipn/'
    _return_url = '/payment/paypal/dpn/'
    _cancel_url = '/payment/paypal/cancel/'
    # _ipn_url2 = '/payment/paypal/<int:acquirer_id>/ipn/'

    @website.route('/payment/paypal/<int:acquirer_id>/ipn/', type='http', auth='admin')
    def paypal_ipn(self, **post):
        print 'Entering paypal_ipn with post', post
        # step 1: return an empty HTTP 200 response -> will be done at the end by returning ''

        # step 2: POST the complete, unaltered message back to Paypal (preceded by cmd=_notify-validate), with same encoding
        paypal_url = "https://www.sandbox.paypal.com/cgi-bin/webscr"
        post_url = '%s?cmd=_notify-validate&%s' % (paypal_url, urlencode(post))
        resp = requests.post(post_url)
        print '\tReceived response', resp, resp.text

        # step 3: paypal send either VERIFIED or INVALID (single word)
        if resp.text == 'VERIFIED':
            # _logger.warning('')
            cr, uid, context = request.cr, request.uid, request.context
            # payment_transaction = request.registry['payment.transaction']
            # payment_transaction.validate()
        elif resp.text == 'INVALID':
            # _logger.warning('')
            pass
        else:
            # _logger.warning('') -> something went wrong
            pass

        return ''

    @website.route([
        '/payment/paypal/test/dpn',
    ], type='http', auth="public")
    def paypal_test_success(self, **post):
        """ TODO
        """
        cr, uid, context = request.cr, request.uid, request.context
        print post
        return ''


class OgoneController(http.Controller):
    _accept_url = '/payment/ogone/test/accept'
    _decline_url = '/payment/ogone/test/decline'
    _exception_url = '/payment/ogone/test/exception'
    _cancel_url = '/payment/ogone/test/cancel'

    @website.route([
        '/payment/ogone/feedback', '/payment/ogone/test/accept',
        '/payment/ogone/decline', '/payment/ogone/test/decline',
        '/payment/ogone/exception', '/payment/ogone/test/exception',
        '/payment/ogone/cancel', '/payment/ogone/test/cancel',
    ], type='http', auth='admin')
    def feedback(self, **post):
        cr, uid, context = request.cr, request.uid, request.context
        Payment = request.registry['payment.transaction']
        print 'Entering ogone feedback with', post

        res = Payment.tx_ogone_feedback(cr, uid, post, context)
        print res
        return ''
