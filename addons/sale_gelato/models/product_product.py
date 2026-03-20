# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, fields, models
from odoo.fields import Command


class ProductProduct(models.Model):
    _inherit = 'product.product'

    gelato_product_uid = fields.Char(name="Gelato Product UID", readonly=True)
    gelato_variant_image_ids = fields.One2many(
        string="Gelato Variant Print Images",
        help="To ensure a good printing result, upload a PNG of the entire printing area with your"
        " graphics correctly placed on it.",
        comodel_name='product.document',
        inverse_name='res_id',
        domain=[('is_gelato', '=', True)],
        readonly=True,
    )

    def action_generate_variant_gelato_images(self):
        """Create separate Gelato image placements for selected product variant.

        :return: The action to display a toast notification to the user.
        :rtype: dict
        """
        existing_placements = self.gelato_variant_image_ids.mapped('name')
        missing_placements = self.product_tmpl_id.gelato_image_ids.filtered(
            lambda image: image.name not in existing_placements
        )
        self.gelato_variant_image_ids = [Command.create({
            'name': image_placement.name,
            'res_id': self.id,
            'res_model': 'product.product',
            'is_gelato': True,
        }) for image_placement in missing_placements]

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'title': _("Successfully updated print images."),
                'message': _("Missing images have been successfully created."),
                'sticky': False,
                'next': {'type': 'ir.actions.client', 'tag': 'soft_reload'},
            },
        }
