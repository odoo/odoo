# -*- coding: utf-8 -*-
# from odoo import http


# class SaleExtension(http.Controller):
#     @http.route('/sale_extension/sale_extension', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/sale_extension/sale_extension/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('sale_extension.listing', {
#             'root': '/sale_extension/sale_extension',
#             'objects': http.request.env['sale_extension.sale_extension'].search([]),
#         })

#     @http.route('/sale_extension/sale_extension/objects/<model("sale_extension.sale_extension"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('sale_extension.object', {
#             'object': obj
#         })

