# from odoo import http


# class TrainingModule(http.Controller):
#     @http.route('/training_module/training_module', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/training_module/training_module/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('training_module.listing', {
#             'root': '/training_module/training_module',
#             'objects': http.request.env['training_module.training_module'].search([]),
#         })

#     @http.route('/training_module/training_module/objects/<model("training_module.training_module"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('training_module.object', {
#             'object': obj
#         })

