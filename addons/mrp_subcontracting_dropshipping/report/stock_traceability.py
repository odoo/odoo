# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api


class StockTraceabilityReport(models.TransientModel):
    _inherit = 'stock.traceability.report'

    @api.model
    def _is_unfoldable(self, move_line, line_type=None):
        """ If the product was dropshipped, we don't check if the source location
        is the same as the destination location in case it is between subcontractors """
        if move_line.picking_code == 'dropship':
            return bool(
                move_line.lot_id and (
                    (line_type == 'parent' and (
                            move_line.consume_line_ids
                            or self._get_related_move_lines(move_line, line_type)
                    ))
                    or (line_type == 'child' and (
                        move_line.produce_line_ids
                        or self._get_related_move_lines(move_line, line_type)
                    ))
                )
            )
        return super()._is_unfoldable(move_line, line_type)
