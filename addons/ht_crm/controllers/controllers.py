# from odoo import http


# class HtCrm(http.Controller):
#     @http.route('/ht_crm/ht_crm', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/ht_crm/ht_crm/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('ht_crm.listing', {
#             'root': '/ht_crm/ht_crm',
#             'objects': http.request.env['ht_crm.ht_crm'].search([]),
#         })

#     @http.route('/ht_crm/ht_crm/objects/<model("ht_crm.ht_crm"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('ht_crm.object', {
#             'object': obj
#         })

