# -*- coding: utf-8 -*-
# from odoo import http


# class InheritanceStockPicking(http.Controller):
#     @http.route('/inheritance_stock_picking/inheritance_stock_picking/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/inheritance_stock_picking/inheritance_stock_picking/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('inheritance_stock_picking.listing', {
#             'root': '/inheritance_stock_picking/inheritance_stock_picking',
#             'objects': http.request.env['inheritance_stock_picking.inheritance_stock_picking'].search([]),
#         })

#     @http.route('/inheritance_stock_picking/inheritance_stock_picking/objects/<model("inheritance_stock_picking.inheritance_stock_picking"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('inheritance_stock_picking.object', {
#             'object': obj
#         })
