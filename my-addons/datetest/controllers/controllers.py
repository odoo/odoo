# -*- coding: utf-8 -*-
# from odoo import http


# class Datetest(http.Controller):
#     @http.route('/datetest/datetest/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/datetest/datetest/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('datetest.listing', {
#             'root': '/datetest/datetest',
#             'objects': http.request.env['datetest.datetest'].search([]),
#         })

#     @http.route('/datetest/datetest/objects/<model("datetest.datetest"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('datetest.object', {
#             'object': obj
#         })
