# from odoo import http


# class CustomNotes(http.Controller):
#     @http.route('/custom_notes/custom_notes', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/custom_notes/custom_notes/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('custom_notes.listing', {
#             'root': '/custom_notes/custom_notes',
#             'objects': http.request.env['custom_notes.custom_notes'].search([]),
#         })

#     @http.route('/custom_notes/custom_notes/objects/<model("custom_notes.custom_notes"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('custom_notes.object', {
#             'object': obj
#         })

