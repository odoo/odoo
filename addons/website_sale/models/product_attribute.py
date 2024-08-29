# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons import product

from odoo import fields, models


class ProductAttribute(models.Model, product.ProductAttribute):

    visibility = fields.Selection(
        selection=[('visible', "Visible"), ('hidden', "Hidden")],
        default='visible',
    )
