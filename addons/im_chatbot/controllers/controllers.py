# -*- coding: utf-8 -*-
# from odoo import http


# class ImChatbot(http.Controller):
#     @http.route('/im_chatbot/im_chatbot/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/im_chatbot/im_chatbot/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('im_chatbot.listing', {
#             'root': '/im_chatbot/im_chatbot',
#             'objects': http.request.env['im_chatbot.im_chatbot'].search([]),
#         })

#     @http.route('/im_chatbot/im_chatbot/objects/<model("im_chatbot.im_chatbot"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('im_chatbot.object', {
#             'object': obj
#         })
