# -*- coding: utf-8 -*-
# from odoo import http


# class ItemsExtension(http.Controller):
#     @http.route('/items_extension/items_extension', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/items_extension/items_extension/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('items_extension.listing', {
#             'root': '/items_extension/items_extension',
#             'objects': http.request.env['items_extension.items_extension'].search([]),
#         })

#     @http.route('/items_extension/items_extension/objects/<model("items_extension.items_extension"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('items_extension.object', {
#             'object': obj
#         })

