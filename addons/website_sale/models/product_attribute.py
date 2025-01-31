# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


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
        help="Instantly created variants are available for selection from your /shop page.",
    )
    is_thumbnail_visible = fields.Boolean(
        string="Show Thumbnails",
        help="Use product variant images instead of the attribute values displays."
    )

    @api.onchange('create_variant', 'display_type')
    def _onchange_disable_preview_variants(self):
        """ The option to preview variants is only available for instantly created single variants.
        """
        if self.create_variant != 'always' or self.display_type == 'multi':
            self.preview_variants = 'hidden'
            self.is_thumbnail_visible = False
