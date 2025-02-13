# -*- coding: utf-8 -*-
# from odoo import http


# class OdooStockSaleCommission(http.Controller):
#     @http.route('/odoo_stock_sale_commission/odoo_stock_sale_commission', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/odoo_stock_sale_commission/odoo_stock_sale_commission/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('odoo_stock_sale_commission.listing', {
#             'root': '/odoo_stock_sale_commission/odoo_stock_sale_commission',
#             'objects': http.request.env['odoo_stock_sale_commission.odoo_stock_sale_commission'].search([]),
#         })

#     @http.route('/odoo_stock_sale_commission/odoo_stock_sale_commission/objects/<model("odoo_stock_sale_commission.odoo_stock_sale_commission"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('odoo_stock_sale_commission.object', {
#             'object': obj
#         })

