from odoo import models, fields

class ProductTemplate(models.Model):
    _inherit = 'product.template'  # Inherit from product.template

    # Define new fields
    tenant_id = fields.Char('Tenant ID')
    sku_code = fields.Char('SKU Code')
    description = fields.Char('Description')
    ean = fields.Char('EAN')
    brand = fields.Char('Brand')
    season_code = fields.Char('Season Code')
    color = fields.Char('Color')
    size = fields.Integer('Size')
    merchandise_category_code = fields.Char('Merchandise Category Code')
    style = fields.Char('Style')
    style_code = fields.Char('Style Code')
    weight = fields.Float('Weight')
    returnable = fields.Boolean('Returnable')