# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class ChatbotController(http.Controller):

    @http.route("/im_chatbot/answer", type="json", auth="public")
    def ChatbotAnswer(self, operator, channel_id):
        partner = request.env["res.partner"].sudo().browse(operator[0])
        if partner.is_bot:
            channel = request.env["mail.channel"].sudo().browse(channel_id)
            channel._bot_answer()
        return {
            "ok": True
        }

    @http.route("/im_chatbot/action", type="json", auth="public")
    def ChatbotAction(self, action, channel_id):
        channel = request.env["mail.channel"].sudo().browse(channel_id)
        chatbot = channel.livechat_operator_id.chatbot_ids[0]
        chatbot._action_engine(channel, action)

        return {
            "ok": True
        }
