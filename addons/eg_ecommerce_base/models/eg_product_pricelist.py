from odoo import fields, models


class EgProductPricelist(models.Model):
    _name = 'eg.product.pricelist'

    eg_product_pricelist_line_ids = fields.One2many(comodel_name='eg.product.pricelist.line',
                                                     inverse_name='eg_product_pricelist_id')
    name = fields.Char(string='Name')
    instance_id = fields.Many2one(comodel_name='eg.ecom.instance')
    provider = fields.Selection(related="instance_id.provider", store=True)
