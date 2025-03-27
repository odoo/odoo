# -*- coding: utf-8 -*-
# Copyright (c) 2020-Present InTechual Solutions. (<https://intechualsolutions.com/>)

from odoo import fields, models


class ChatGPTModel(models.Model):
    _name = 'chatgpt.model'
    _description = "ChatGPT Model"

    name = fields.Char(string='ChatGPT Model', required=True)
