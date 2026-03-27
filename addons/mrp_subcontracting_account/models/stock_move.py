# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _get_aml_value(self):
        value = super()._get_aml_value()
        if (
            self.production_id
            and self.move_dest_ids.filtered(lambda m: m.state == "done")[-1:].is_subcontract
            and self.product_id.cost_method != "standard"
        ):
            value -= self.production_id.extra_cost * self.product_uom._compute_quantity(self.quantity, self.product_id.uom_id)
        return value
