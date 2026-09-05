from odoo import models, fields


class ModelA(models.Model):
    _name = 'model_a'
    _description = "A model may not be loaded for manual fields"

    name = fields.Char('Name')
    category_id = fields.Many2one('test_orm.category', 'Category')