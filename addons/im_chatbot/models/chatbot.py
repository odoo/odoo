# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ChatBot(models.Model):
    _name = "im_chatbot.chatbot"
    _description = "Chatbots available"
    _inherit = ["image.mixin"]

    name = fields.Char(String="Bot name")
    subject = fields.Char(String="Subject")
    message_ids = fields.One2many("im_chatbot.message", "chatbot_id")

    channel_ids = fields.Many2many("im_livechat.channel")
class ImLivechatChannel(models.Model):
    _name = "im_livechat.channel"
    _inherit = "im_livechat.channel"

    chatbot_ids = fields.Many2many("im_chatbot.chatbot")

    nb_chatbot = fields.Integer(compute="_compute_nb_chatbot")

    @api.depends("chatbot_ids")
    def _compute_nb_chatbot(self):
        for channel in self:
            channel.nb_chatbot = len(channel.chatbot_ids)
