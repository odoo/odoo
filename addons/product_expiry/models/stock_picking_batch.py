from odoo import models


class StockPickingBatch(models.Model):
    _inherit = 'stock.picking.batch'

    def action_batch_detailed_operations(self):
        action = super().action_batch_detailed_operations()
        if any(self.move_ids.mapped('use_expiration_date')):
            action['context'].update(
                {
                    'show_lot_removal_date': True,
                    'show_lot_expiration_date': self.picking_type_id.use_create_lots,
                }
            )
        return action
