from odoo import models, fields

class ProductProduct(models.Model):
    _inherit = 'product.product'

    default_code = fields.Char('Default Code', unique=True)
