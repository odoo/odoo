# from odoo import http


# class SalePhones(http.Controller):
#     @http.route('/sale_phones/sale_phones', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/sale_phones/sale_phones/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('sale_phones.listing', {
#             'root': '/sale_phones/sale_phones',
#             'objects': http.request.env['sale_phones.sale_phones'].search([]),
#         })

#     @http.route('/sale_phones/sale_phones/objects/<model("sale_phones.sale_phones"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('sale_phones.object', {
#             'object': obj
#         })

