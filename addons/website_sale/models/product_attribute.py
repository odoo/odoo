# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ProductAttribute(models.Model):
    _inherit = 'product.attribute'

    visibility = fields.Selection(
        selection=[('visible', "Visible"), ('hidden', "Hidden")],
        default='visible',
    )
    show_variants = fields.Selection(
        selection=[
            ('visible', "Visible"),
            ('hidden', "Hidden"),
            ('hover', "Hover"),
            ('image', "Variant Images"),
        ],
        default='hidden',
        help="Variants are available for selection from your /shop page",
    )
