# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ProductProduct(models.Model):
    _inherit = "product.product"

    def _get_description(self, picking_type_id):
        if picking_type_id.code == 'dropship':
            return self.description_pickingout or self.display_name
        else:
            return super()._get_description(picking_type_id)
