from odoo import models, api, _, fields


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    limit_ch = fields.Boolean(string='Set Discount Limit', default=False)
    limit_val = fields.Float(string='Max Discount(%)')
