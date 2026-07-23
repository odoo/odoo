# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ProductProduct(models.Model):
    _inherit = "product.product"

    def _get_free_qty(self, *, warehouse_id=None, **_kwargs):
        """Override of `website_sale` to take a given warehouse into account.

        :param int warehouse_id: ID of the warehouse to check the product availability
        :param dict _kwargs: Optional data. This parameter is not used here
        :return: available quantity
        :rtype: float
        """
        return self.with_context(warehouse_id=warehouse_id).sudo().free_qty
