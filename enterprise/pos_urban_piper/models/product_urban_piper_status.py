from odoo import fields, models


class ProductUrbanPiperStatus(models.Model):
    _name = 'product.urban.piper.status'
    _description = 'Urban piper product status'

    config_id = fields.Many2one('pos.config', string='Urban Piper Config')
    is_product_linked = fields.Boolean(string='Is Product Linked?', help='Product Status on Urban piper.')
    product_tmpl_id = fields.Many2one('product.template', string='Product')
