# from odoo import http


# class MySuperAddon(http.Controller):
#     @http.route('/my_super_addon/my_super_addon', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/my_super_addon/my_super_addon/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('my_super_addon.listing', {
#             'root': '/my_super_addon/my_super_addon',
#             'objects': http.request.env['my_super_addon.my_super_addon'].search([]),
#         })

#     @http.route('/my_super_addon/my_super_addon/objects/<model("my_super_addon.my_super_addon"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('my_super_addon.object', {
#             'object': obj
#         })

