# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    @api.depends("product_variant_ids.free_qty")
    def _compute_is_published(self):
        """Override of `website_sale` to add `free_qty` in depends."""
        super()._compute_is_published()
