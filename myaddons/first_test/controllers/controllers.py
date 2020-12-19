# -*- coding: utf-8 -*-
# from odoo import http


# class FirstTest(http.Controller):
#     @http.route('/first_test/first_test/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/first_test/first_test/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('first_test.listing', {
#             'root': '/first_test/first_test',
#             'objects': http.request.env['first_test.first_test'].search([]),
#         })

#     @http.route('/first_test/first_test/objects/<model("first_test.first_test"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('first_test.object', {
#             'object': obj
#         })
