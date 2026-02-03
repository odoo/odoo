# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class Website(models.Model):
    _inherit = 'website'

    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse')

    def _get_product_available_qty(self, product, **kwargs):
        """Give the available quantity of a given product.

        :param product: product.product record
        :param dict kwargs: unused parameters, available for overrides
        :return: available quantity
        :rtype: float
        """
        return product.with_context(warehouse_id=self.warehouse_id.id).free_qty
