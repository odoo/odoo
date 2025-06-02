# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    def _create_stock_moves(self, picking):
        """
            There is no bridge module between project_purchase_stock and
            mrp_subcontracting, so we have passed the context here. The project
            is used while creating the Resupply.
        """
        stock_moves = super()._create_stock_moves(picking)
        return stock_moves.with_context(project_id=picking.project_id.id)
