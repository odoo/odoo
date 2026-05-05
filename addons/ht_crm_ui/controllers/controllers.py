# from odoo import http


# class HtCrmUi(http.Controller):
#     @http.route('/ht_crm_ui/ht_crm_ui', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/ht_crm_ui/ht_crm_ui/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('ht_crm_ui.listing', {
#             'root': '/ht_crm_ui/ht_crm_ui',
#             'objects': http.request.env['ht_crm_ui.ht_crm_ui'].search([]),
#         })

#     @http.route('/ht_crm_ui/ht_crm_ui/objects/<model("ht_crm_ui.ht_crm_ui"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('ht_crm_ui.object', {
#             'object': obj
#         })

