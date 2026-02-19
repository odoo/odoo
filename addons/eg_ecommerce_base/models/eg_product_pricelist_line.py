from odoo import models, fields


class EgProductPricelistLine(models.Model):
    _name = 'eg.product.pricelist.line'

    eg_product_pricelist_id = fields.Many2one(comodel_name='eg.product.pricelist')
    eg_product_template_id = fields.Many2one(comodel_name='eg.product.template', string='Products')
    eg_product_id = fields.Many2one(comodel_name='eg.product.product', string='Variants')
    price_unit = fields.Float(string='Price')
