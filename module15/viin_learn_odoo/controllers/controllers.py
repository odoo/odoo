# -*- coding: utf-8 -*-
# from odoo import http


# class ViinLearnOdoo(http.Controller):
#     @http.route('/viin_learn_odoo/viin_learn_odoo/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/viin_learn_odoo/viin_learn_odoo/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('viin_learn_odoo.listing', {
#             'root': '/viin_learn_odoo/viin_learn_odoo',
#             'objects': http.request.env['viin_learn_odoo.viin_learn_odoo'].search([]),
#         })

#     @http.route('/viin_learn_odoo/viin_learn_odoo/objects/<model("viin_learn_odoo.viin_learn_odoo"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('viin_learn_odoo.object', {
#             'object': obj
#         })
