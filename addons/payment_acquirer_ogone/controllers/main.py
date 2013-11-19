# -*- coding: utf-8 -*-
from openerp.addons.web import http
from openerp.addons.web.http import request
from openerp.addons.website.models import website


class OgoneController(http.Controller):
    _accept_url = '/payment/ogone/test/accept'
    _decline_url = '/payment/ogone/test/decline'
    _exception_url = '/payment/ogone/test/exception'
    _cancel_url = '/payment/ogone/test/cancel'

    @website.route([
        '/payment/ogone/accept', '/payment/ogone/test/accept',
        '/payment/ogone/decline', '/payment/ogone/test/decline',
        '/payment/ogone/exception', '/payment/ogone/test/exception',
        '/payment/ogone/cancel', '/payment/ogone/test/cancel',
    ], type='http', auth='admin')
    def ogone_form_feedback(self, **post):
        cr, uid, context = request.cr, request.uid, request.context
        Payment = request.registry['payment.transaction']
        print 'Entering ogone feedback with', post
        return_url = post.pop('return_url', '/')
        print 'return_url', return_url

        res = Payment.ogone_form_feedback(cr, uid, post, context)
        print 'result after feedback', res
        return request.redirect(return_url)
