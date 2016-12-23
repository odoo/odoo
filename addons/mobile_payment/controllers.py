# -*- coding: utf-8 -*-
from openerp import http

# class MobilePayment(http.Controller):
#     @http.route('/mobile_payment/mobile_payment/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/mobile_payment/mobile_payment/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('mobile_payment.listing', {
#             'root': '/mobile_payment/mobile_payment',
#             'objects': http.request.env['mobile_payment.mobile_payment'].search([]),
#         })

#     @http.route('/mobile_payment/mobile_payment/objects/<model("mobile_payment.mobile_payment"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('mobile_payment.object', {
#             'object': obj
#         })