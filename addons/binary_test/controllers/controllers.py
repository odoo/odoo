# -*- coding: utf-8 -*-
from odoo import http

# class BinaryTest(http.Controller):
#     @http.route('/binary_test/binary_test/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/binary_test/binary_test/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('binary_test.listing', {
#             'root': '/binary_test/binary_test',
#             'objects': http.request.env['binary_test.binary_test'].search([]),
#         })

#     @http.route('/binary_test/binary_test/objects/<model("binary_test.binary_test"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('binary_test.object', {
#             'object': obj
#         })