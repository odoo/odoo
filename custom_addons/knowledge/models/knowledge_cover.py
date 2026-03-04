from odoo import fields, models


class KnowledgeCover(models.Model):
    _name = "knowledge.cover"
    _description = "Knowledge Cover"
    _order = "id desc"

    name = fields.Char(required=True)
    image_1920 = fields.Image(required=True)
