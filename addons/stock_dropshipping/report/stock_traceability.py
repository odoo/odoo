# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api
from odoo.fields import Domain


class StockTraceabilityReport(models.TransientModel):
    _inherit = 'stock.traceability.report'

    @api.model
    def _get_location_domain(self, main_loc_ids=None):
        return Domain.OR([
            super()._get_location_domain(main_loc_ids=main_loc_ids),
            Domain('picking_code', '=', 'dropship'),
        ])

    @api.model
    def _get_lot_lines(self, move_lines=None, level=0, main_loc_ids=None):
        """ We need to process dropship lines separately since they never pass through the stock.
        The dropship line itself is considered as a child line and we see if there's a parent line. """
        dropship_lines = move_lines.filtered(lambda ml: ml.picking_code == 'dropship')
        final_vals = super()._get_lot_lines(move_lines=move_lines - dropship_lines, level=level, main_loc_ids=main_loc_ids)
        for line in dropship_lines:
            unfoldable = self._is_unfoldable(line, 'child')
            final_vals.append(self._make_dict_move(move_line=line, line_type='child', level=level, unfoldable=unfoldable))
            parent_line = self._get_related_move_lines(line, 'parent')
            if parent_line:
                unfoldable = self._is_unfoldable(parent_line, 'parent')
                final_vals.append(self._make_dict_move(move_line=parent_line, line_type='parent', level=level, unfoldable=unfoldable))
        return sorted(final_vals, key=lambda l: (l['date'], l['id']), reverse=True)
