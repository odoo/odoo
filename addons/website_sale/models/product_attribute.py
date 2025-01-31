# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ProductAttribute(models.Model):
    _inherit = 'product.attribute'

    visibility = fields.Selection(
        selection=[('visible', "Visible"), ('hidden', "Hidden")],
        default='visible',
    )
    preview_variants = fields.Selection(
        string="On Product Cards",
        selection=[
            ('visible', "Visible"),
            ('hidden', "Hidden"),
            ('hover', "Hover"),
        ],
        default='hidden',
        help="Variants are available for selection from your /shop page",
    )
    is_thumbnail_visible = fields.Boolean(string="Show Thumbnails")
