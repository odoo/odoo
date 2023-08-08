from odoo import models , fields
class product (models.model):
    _name = "product.product"
    _description = "product.product"
    
    name = fields.Char()
    tags = fields.Many2many()  