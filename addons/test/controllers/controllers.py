# -*- coding: utf-8 -*-
from odoo import http

# class Addons/test(http.Controller):
#     @http.route('/addons/test/addons/test/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/addons/test/addons/test/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('addons/test.listing', {
#             'root': '/addons/test/addons/test',
#             'objects': http.request.env['addons/test.addons/test'].search([]),
#         })

#     @http.route('/addons/test/addons/test/objects/<model("addons/test.addons/test"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('addons/test.object', {
#             'object': obj
#         })