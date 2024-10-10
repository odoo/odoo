# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class ProductProduct(models.Model):
    _inherit = 'product.product'

    gelato_reference = fields.Char(name="Gelato Reference")
