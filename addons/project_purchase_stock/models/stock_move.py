# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _get_new_picking_values(self):
        vals = super()._get_new_picking_values()
        if self.env.context.get('po_to_notify'):
            purchase_order = self.env.context.get('po_to_notify')
            if purchase_order.project_id:
                vals['project_id'] = purchase_order.project_id.id
        return vals
