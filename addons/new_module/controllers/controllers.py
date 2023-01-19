# -*- coding: utf-8 -*-
# from odoo import http


# class NewModule(http.Controller):
#     @http.route('/new_module/new_module', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/new_module/new_module/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('new_module.listing', {
#             'root': '/new_module/new_module',
#             'objects': http.request.env['new_module.new_module'].search([]),
#         })

#     @http.route('/new_module/new_module/objects/<model("new_module.new_module"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('new_module.object', {
#             'object': obj
#         })
