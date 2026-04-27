from odoo import api, models


class StockMove(models.Model):
    _inherit = 'stock.move'

    @api.model
    def _l10n_ke_oscu_process_moves(self):
        if self and self.picking_id:
            for picking in self.picking_id:
                if picking.pos_order_id and picking.pos_order_id.l10n_ke_order_send_status == 'not_sent':
                    return
        return super()._l10n_ke_oscu_process_moves()
