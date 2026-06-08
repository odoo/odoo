# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.tools import format_date


class StockTraceabilityReport(models.TransientModel):
    _inherit = 'stock.traceability.report'

    def _make_dict_move(self, level, parent_id, move_line, unfoldable=False):
        data = super()._make_dict_move(level, parent_id, move_line, unfoldable=unfoldable)
        data[0]['expiration_date'] = move_line.lot_id.expiration_date
        return data

    @api.model
    def _final_vals_to_lines(self, final_vals, level):
        lines = super()._final_vals_to_lines(final_vals, level)
        for line, data in zip(lines, final_vals):
            expiration_date = data.get('expiration_date') and format_date(self.env, data['expiration_date']) or ''
            expiration_date_column = self._make_column('expiration_date', expiration_date)
            for index, column in enumerate(line['columns']):
                if column['name'] == 'lot_name':
                    line['columns'].insert(index + 1, expiration_date_column)
                    break
            else:
                line['columns'].append(expiration_date_column)
        return lines
