# -*- coding: utf-8 -*-
# from odoo import http


# class Secondtest(http.Controller):
#     @http.route('/secondtest/secondtest/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/secondtest/secondtest/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('secondtest.listing', {
#             'root': '/secondtest/secondtest',
#             'objects': http.request.env['secondtest.secondtest'].search([]),
#         })

#     @http.route('/secondtest/secondtest/objects/<model("secondtest.secondtest"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('secondtest.object', {
#             'object': obj
#         })
