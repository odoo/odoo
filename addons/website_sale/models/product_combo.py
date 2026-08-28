# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ProductCombo(models.Model):
    _inherit = "product.combo"

    def _get_max_quantity(self, website, sale_order, **kwargs):
        """Return the max quantity of a combo.
        It is the max quantity of its combo item with the highest max quantity. If one of the combo
        items has no max quantity, then the combo also has no max quantity.

        Note: self.ensure_one()

        :param website website: The website for which to compute the max quantity.
        :return: The max quantity of the combo.
        :rtype: float | None
        """
        self.ensure_one()
        max_quantities = [
            item.product_id._get_max_quantity(website, sale_order, **kwargs)
            for item in self.combo_item_ids
        ]
        if None in max_quantities:
            return None
        included_qty = self.included_qty or 1
        return max(int(max_quantity // included_qty) for max_quantity in max_quantities)
