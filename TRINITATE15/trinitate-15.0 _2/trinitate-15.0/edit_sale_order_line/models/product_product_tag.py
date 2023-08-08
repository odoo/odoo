from odoo import models, fields


class ProductProductTag(models.Model):
    _name = 'product.product.tag'
    _description = 'Product Tags'
    
    name = fields.Char(  string='Name',required=True,)
