from odoo import models, fields


class Area(models.Model):
    _name = "area"
    _description = "Description of the Border model"

    name = fields.Char()
