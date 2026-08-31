from odoo import models


class L10nJpTotalAverageCostWizard(models.TransientModel):
    _inherit = 'l10n_jp_stock.total.average.cost.wizard'

    def _get_production_move_values(self, moves):
        """Value a manufacturing order's output at its 製造原価.

        法人税法施行令 32条1項2号 counts the materials, the labour and the overhead,
        which is what core's own _cal_price totals, and by-products take the share
        of it their bill of materials assigns them.
        """
        values = super()._get_production_move_values(moves)

        def allocate(output_moves, value):
            # the order is valued once, so a second output move re-counts nothing
            for index, move in enumerate(output_moves):
                values[move.id] = value if index == 0 else 0.0

        for production, outputs in moves.grouped('production_id').items():
            if not production:
                continue
            finished = outputs.filtered(lambda m: m.product_id == production.product_id)
            total_cost = abs(sum(production.move_raw_ids.mapped('value')))
            total_cost += sum(order._cal_cost() for order in production.workorder_ids)
            total_cost += production.extra_cost * sum(finished.mapped('quantity_product_uom'))
            byproduct_share = 0.0
            for byproduct_moves in (outputs - finished).grouped('product_id').values():
                share = byproduct_moves[0].cost_share
                byproduct_share += share
                allocate(byproduct_moves, total_cost * share / 100)
            allocate(finished, total_cost * (1 - byproduct_share / 100))
        return values
