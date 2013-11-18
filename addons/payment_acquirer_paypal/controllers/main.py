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

    @website.route([
        '/payment/paypal/ipn/',
    ], type='http', auth='public')
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
            _logger.info('Paypal: received verified IPN')
            cr, uid, context = request.cr, request.uid, request.context
            payment_transaction = request.registry['payment.transaction']
            res = payment_transaction.paypal_form_feedback(cr, uid, post, context=context)
            print '\tValidation result', res
        elif resp.text == 'INVALID':
            _logger.warning('Paypal: received invalid IPN with post %s' % post)
        else:
            _logger.warning('Paypal: received unrecognized IPN with post %s' % post)

        return ''

    @website.route([
        '/payment/paypal/dpn',
    ], type='http', auth="public")
    def paypal_dpn(self, **post):
        """ TODO
        """
        cr, uid, context = request.cr, request.uid, request.context
        print 'Entering paypal_dpn with post', post
        return request.redirect('/')

    @website.route([
        '/payment/paypal/cancel',
    ], type='http', auth="public")
    def paypal_cancel(self, **post):
        """ TODO
        """
        cr, uid, context = request.cr, request.uid, request.context
        print 'Entering paypal_cancel with post', post
        return ''
