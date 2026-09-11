from odoo import fields, models


class ChatGPTModel(models.Model):
    _name = 'chatgpt.model'
    _description = "ChatGPT Model"

    name = fields.Char(string='ChatGPT Model', required=True)



class ChatGPTemp(models.Model):
    _name = 'chatgpt.tempreture'
    _description = "ChatGPT Tempreture"

    name = fields.Float(string="Tempreture", required=True)