# -*- coding: utf-8 -*-
# from odoo import http


# class Prova(http.Controller):
#     @http.route('/prova/prova/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/prova/prova/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('prova.listing', {
#             'root': '/prova/prova',
#             'objects': http.request.env['prova.prova'].search([]),
#         })

#     @http.route('/prova/prova/objects/<model("prova.prova"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('prova.object', {
#             'object': obj
#         })
