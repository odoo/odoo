# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _get_new_picking_values(self):
        return {
            **super()._get_new_picking_values(),
            'project_id': self.purchase_line_id.order_id.project_id.id,
        }
