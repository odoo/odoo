from odoo import models


class StockAllocationReport(models.AbstractModel):
    _inherit = 'stock.allocation.report'

    def _get_record_source(self, record):
        moves = self._get_moves(record)
        if purchase_order := moves.purchase_line_id.order_id[:1]:
            return {
                'id': purchase_order.id,
                'name': purchase_order.display_name,
                'res_model': 'purchase.order',
                'partner': {
                    'id': purchase_order.partner_id.id,
                    'res_model': 'res.partner',
                    'display_name': purchase_order.partner_id.display_name,
                },
            }
        return super()._get_record_source(record)
