# from odoo import http


# class ViaSuiteBase(http.Controller):
#     @http.route('/via_suite_base/via_suite_base', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/via_suite_base/via_suite_base/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('via_suite_base.listing', {
#             'root': '/via_suite_base/via_suite_base',
#             'objects': http.request.env['via_suite_base.via_suite_base'].search([]),
#         })

#     @http.route('/via_suite_base/via_suite_base/objects/<model("via_suite_base.via_suite_base"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('via_suite_base.object', {
#             'object': obj
#         })

