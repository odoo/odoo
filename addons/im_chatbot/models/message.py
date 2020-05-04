# -*- coding: utf-8 -*-

from odoo import models, fields, api


class Message(models.Model):
    _name = "im_chatbot.message"
    _description = "Message from the chatbot"
    _order = "sequence, id"

    name = fields.Char(string="Message")
    sequence = fields.Integer(string="Sequence", default=10)
    answer_type = fields.Selection(
        [("selection", "Selection"), ("input", "User input")], required=True
    )
    chatbot_id = fields.Many2one("im_chatbot.chatbot", index=True)
    answer_ids = fields.Many2many("im_chatbot.answer")
