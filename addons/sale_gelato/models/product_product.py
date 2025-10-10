# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.fields import Command


class ProductProduct(models.Model):
    _inherit = 'product.product'

    gelato_product_uid = fields.Char(name="Gelato Product UID", readonly=True)

    gelato_variant_image_placement = fields.One2many(
        string="Gelato Variant Print Images",
        comodel_name='product.document',
        inverse_name='res_id',
        domain=[('is_gelato', '=', True)],
        readonly=True,
        help='To ensure a good printing result, upload a PNG of the entire printing area with your '
             'graphics correctly placed on it.',
    )

    def action_enable_separate_images(self):
        existing_placements = self.gelato_variant_image_placement.mapped('name')
        missing_placements = self.product_tmpl_id.gelato_image_ids.filtered(lambda l: l.name not in existing_placements)
        for image_placement in missing_placements:
            self.gelato_variant_image_placement = [Command.create({
                    'name': image_placement.name,
                    'res_id': self.id,
                    'res_model': 'product.product',
                    'is_gelato': True,
                })]
