# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class Website(models.Model):
    _inherit = "website"

    warehouse_id = fields.Many2one("stock.warehouse", string="Warehouse")

    def _get_product_available_qty(self, product, **kwargs):
        """Override of _get_product_available_qty in website_sale module
        Give the available quantity of a given product.

        :param product: product.product record
        :param dict kwargs: additional values given for inherited models.
        :return: available quantity
        :rtype: float
        """
        kwargs["warehouse_id"] = self.warehouse_id.id
        return super()._get_product_available_qty(product, **kwargs)
