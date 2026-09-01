from odoo import models


class L10nJpTotalAverageCostWizard(models.TransientModel):
    _inherit = 'l10n_jp_stock.total.average.cost.wizard'

    def _get_move_domain(self, products, period_start, period_end):
        # unbuilding returns components an order consumed, and reversing an issue
        # is not an acquisition (施行令28条1項1号ハ)
        return super()._get_move_domain(products, period_start, period_end) + [
            ('unbuild_id', '=', False),
        ]

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
            # the shares come from the order, so they do not depend on which of its
            # outputs the evaluation happens to cover
            byproducts = production.move_byproduct_ids.filtered(lambda m: m.state == 'done')
            byproducts_by_product = byproducts.grouped('product_id')
            finished_qty = sum(
                production.move_finished_ids
                .filtered(lambda m: m.state == 'done' and m.product_id == production.product_id)
                .mapped('quantity_product_uom')
            )
            total_cost = abs(sum(production.move_raw_ids.mapped('value')))
            total_cost += sum(order._cal_cost() for order in production.workorder_ids)
            total_cost += production.extra_cost * finished_qty
            byproduct_share = sum(
                product_moves[0].cost_share for product_moves in byproducts_by_product.values()
            )
            for product, product_moves in byproducts_by_product.items():
                allocate(outputs & product_moves, total_cost * product_moves[0].cost_share / 100)
            allocate(
                outputs.filtered(lambda m: m.product_id == production.product_id),
                total_cost * (1 - byproduct_share / 100),
            )
        return values
