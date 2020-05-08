# -*- coding: utf-8 -*-

from odoo import models, fields, api


class Answer(models.Model):
    _name = "im_chatbot.answer"
    _description = "Possible answer to a chatbot message"

    name = fields.Char(String="Bot name")
    message_ids = fields.Many2many("im_chatbot.script")
