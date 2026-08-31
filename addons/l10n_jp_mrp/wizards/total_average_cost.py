from odoo import models


class L10nJpTotalAverageCostWizard(models.TransientModel):
    _inherit = 'l10n_jp_stock.total.average.cost.wizard'

    def _get_production_move_values(self, moves):
        values = super()._get_production_move_values(moves)
        productions_seen = set()
        for move in moves:
            if not (production := move.production_id):
                continue
            if production.id in productions_seen:
                values[move.id] = 0.0
            else:
                productions_seen.add(production.id)
                values[move.id] = -sum(production.move_raw_ids.mapped('value'))
        return values
