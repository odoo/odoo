# from odoo import http


# class HtTools(http.Controller):
#     @http.route('/ht_tools/ht_tools', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/ht_tools/ht_tools/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('ht_tools.listing', {
#             'root': '/ht_tools/ht_tools',
#             'objects': http.request.env['ht_tools.ht_tools'].search([]),
#         })

#     @http.route('/ht_tools/ht_tools/objects/<model("ht_tools.ht_tools"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('ht_tools.object', {
#             'object': obj
#         })

