# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _compute_sale_id(self):
        super()._compute_sale_id()
        for picking in self:
            # Components picked for an MO belong to the MO, even when its group is linked to the SO
            if picking.group_id.mrp_production_ids and picking.picking_type_id == picking.picking_type_id.warehouse_id.pbm_type_id:
                picking.sale_id = False
