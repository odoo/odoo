# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class Website(models.Model):
    _inherit = "website"

    warehouse_id = fields.Many2one("stock.warehouse", string="Warehouse")

    def _get_product_available_qty(self, product, *, warehouse_id=None, **kwargs):
        """Override of `website_sale` to pass the default warehouse_id.

        :param product: product.product record
        :param int warehouse_id: ID of the warehouse to check the product availability
        :param dict kwargs: unused parameters, available for overrides
        :return: available quantity
        :rtype: float
        """
        if warehouse_id is None:
            warehouse_id = self.warehouse_id.id
        return super()._get_product_available_qty(product, warehouse_id=warehouse_id, **kwargs)
