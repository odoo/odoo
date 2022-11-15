# -*- coding: utf-8 -*-
# from odoo import http


# class ViinProduct(http.Controller):
#     @http.route('/viin_product/viin_product', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/viin_product/viin_product/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('viin_product.listing', {
#             'root': '/viin_product/viin_product',
#             'objects': http.request.env['viin_product.viin_product'].search([]),
#         })

#     @http.route('/viin_product/viin_product/objects/<model("viin_product.viin_product"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('viin_product.object', {
#             'object': obj
#         })
