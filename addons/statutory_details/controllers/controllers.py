# -*- coding: utf-8 -*-
from openerp import http

# class StatutoryDetails(http.Controller):
#     @http.route('/statutory_details/statutory_details/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/statutory_details/statutory_details/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('statutory_details.listing', {
#             'root': '/statutory_details/statutory_details',
#             'objects': http.request.env['statutory_details.statutory_details'].search([]),
#         })

#     @http.route('/statutory_details/statutory_details/objects/<model("statutory_details.statutory_details"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('statutory_details.object', {
#             'object': obj
#         })