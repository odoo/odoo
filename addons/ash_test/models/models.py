from odoo import models, fields, api

class ProductTemplate(models.Model):
    _inherit = 'product.template'  # Inherit from `product.template`

    custom_field_1 = fields.Char('Custom Field 1')
    custom_field_2 = fields.Integer('Custom Field 2')