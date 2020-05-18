# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class ChatbotController(http.Controller):

    @http.route("/im_chatbot/answer", type="json", auth="public")
    def ChatbotAnswer(self, operator, channel_id):
        partner = request.env["res.partner"].sudo().browse(operator[0])
        if partner.is_bot:
            chatbot = partner.chatbot_ids
            channel = request.env["mail.channel"].sudo().browse(channel_id)
            channel._bot_answer()

        return {
            "ok": True
        }

    @http.route("/im_chatbot/action", type="json", auth="public")
    def ChatbotAction(self):
        return {
            "ok": True
        }

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
