from odoo import models,fields

class GeminiModel(models.Model):
    _name = 'gemini.model'
    _description = "Gemini Model"

    name = fields.Char(string='Gemini Model', required=True)