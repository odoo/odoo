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
# import requests
# from urllib import urlencode

_logger = logging.getLogger(__name__)


class OgoneController(http.Controller):
    _accept_url = '/payment/ogone/test/accept'
    _decline_url = '/payment/ogone/test/decline'
    _exception_url = '/payment/ogone/test/exception'
    _cancel_url = '/payment/ogone/test/cancel'

    @website.route([
        '/payment/ogone/accept', '/payment/ogone/test/accept',
    ], type='http', auth='admin')
    def ogone_form_feedback(self, **post):
        cr, uid, context = request.cr, request.uid, request.context
        Payment = request.registry['payment.transaction']
        print 'Entering ogone feedback with', post
        return_url = post.pop('return_url', '/')
        print 'return_url', return_url

        res = Payment.ogone_form_feedback(cr, uid, post, context)
        print 'result after feedback', res
        # return ''
        return request.redirect(return_url)

    @website.route([
        '/payment/ogone/decline', '/payment/ogone/test/decline',
        '/payment/ogone/exception', '/payment/ogone/test/exception',
        '/payment/ogone/cancel', '/payment/ogone/test/cancel',
    ], type='http', auth='admin')
    def ogone_form_feedback_other(self, **post):
        cr, uid, context = request.cr, request.uid, request.context
        print 'Entering ogone_form_feedback_other', post
        return ''
