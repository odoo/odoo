# -*- coding: utf-8 -*-

from odoo import models, fields, api


class Message(models.Model):
    _name = "im_chatbot.message"
    _description = "Message from the chatbot"

    name = fields.Char()
    answer_type = fields.Selection([("selection", "selection")])
    chatbot_id = fields.Many2one("im_chatbot.chatbot", index=True)
    answer_ids = fields.Many2many("im_chatbot.answer")
