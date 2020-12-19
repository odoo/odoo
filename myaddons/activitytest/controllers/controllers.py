# -*- coding: utf-8 -*-
# from odoo import http


# class Activitytest(http.Controller):
#     @http.route('/activitytest/activitytest/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/activitytest/activitytest/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('activitytest.listing', {
#             'root': '/activitytest/activitytest',
#             'objects': http.request.env['activitytest.activitytest'].search([]),
#         })

#     @http.route('/activitytest/activitytest/objects/<model("activitytest.activitytest"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('activitytest.object', {
#             'object': obj
#         })
