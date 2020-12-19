# -*- coding: utf-8 -*-
# from odoo import http


# class Dayintest(http.Controller):
#     @http.route('/dayintest/dayintest/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/dayintest/dayintest/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('dayintest.listing', {
#             'root': '/dayintest/dayintest',
#             'objects': http.request.env['dayintest.dayintest'].search([]),
#         })

#     @http.route('/dayintest/dayintest/objects/<model("dayintest.dayintest"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('dayintest.object', {
#             'object': obj
#         })
