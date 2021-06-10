# -*- coding: utf-8 -*-
# from odoo import http


# class Tecdoc(http.Controller):
#     @http.route('/tecdoc/tecdoc/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/tecdoc/tecdoc/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('tecdoc.listing', {
#             'root': '/tecdoc/tecdoc',
#             'objects': http.request.env['tecdoc.tecdoc'].search([]),
#         })

#     @http.route('/tecdoc/tecdoc/objects/<model("tecdoc.tecdoc"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('tecdoc.object', {
#             'object': obj
#         })
