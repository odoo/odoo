# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ChatBot(models.Model):
    _name = "im_chatbot.chatbot"
    _description = "Chatbots available"
    _inherit = ["image.mixin"]

    name = fields.Char(String="Bot name")
    subject = fields.Char(String="Subject")
    message_ids = fields.One2many("im_chatbot.message", "chatbot_id")
