# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ProductCombo(models.Model):
    _inherit = 'product.combo'

    def _get_max_quantity(self, website, **kwargs):
        self.ensure_one()
        max_quantities = [
            item.product_id._get_max_quantity(website, **kwargs) for item in self.combo_item_ids
        ]
        return max(max_quantities) if (None not in max_quantities) else None
