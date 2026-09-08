from collections import defaultdict

from odoo import models
from odoo.exceptions import UserError


class L10nJpTotalAverageCostWizard(models.TransientModel):
    _inherit = 'l10n_jp_stock.total.average.cost.wizard'

    def _get_move_domain(self, products, period_start, period_end):
        # unbuilding returns components an order consumed, and reversing an issue
        # is not an acquisition (施行令28条1項1号ハ)
        return super()._get_move_domain(products, period_start, period_end) + [
            ('unbuild_id', '=', False),
        ]

    def _get_evaluation_batches(self, products, moves):
        """
        Group the products by how deep they sit in the manufacturing of the period.

        What an order's output cost is read off the value of the moves that issued
        its components, so those components must already be evaluated, and their
        moves corrected, by the time the good made out of them is valued. The
        orders themselves say what came out of what, which a BoM only approximates
        and a by-product is missing from entirely.
        """
        issued_for = defaultdict(lambda: self.env['product.product'])
        for production in moves.production_id | moves.raw_material_production_id:
            issued = production.move_raw_ids.product_id
            # a by-product leaves the same order, so it costs those same components
            for produced in production.move_finished_ids.product_id:
                issued_for[produced] |= issued

        depths = {}
        walked = []

        def depth(product):
            if product not in depths:
                if product in walked:
                    # orders that come out of each other have no level to start from,
                    # and core only forbids a loop through the components of a BoM,
                    # never one closed by a by-product
                    loop = walked[walked.index(product):] + [product]
                    raise UserError(self.env._(
                        'The orders of the period make these products out of each other, '
                        'so their costs cannot be evaluated in order: %s',
                        ' → '.join(looped.display_name for looped in loop),
                    ))
                walked.append(product)
                depths[product] = 1 + max(
                    (depth(component) for component in issued_for[product]),
                    default=-1,
                )
                walked.pop()
            return depths[product]

        batches = products.grouped(depth)
        return [batches[level] for level in sorted(batches)]

    def _get_production_move_values(self, moves):
        """
        Value an MO's output at its 製造原価.

        法人税法施行令 32条1項2号 counts the materials, the labour and the overhead,
        which is what core's own _cal_price totals, and by-products take the share
        of it their BoM assigns them.
        """
        values = super()._get_production_move_values(moves)
        period_end = self._get_period_bounds()[1]

        def allocate(order_moves, value):
            # the order is valued once and spread over all it produced, not per period
            order_qty = sum(order_moves.mapped('quantity_product_uom'))
            share = value / order_qty if order_qty else 0.0
            for move in order_moves & moves:
                values[move.id] = share * move.quantity_product_uom

        for production in moves.production_id:
            # the shares come from the order, so they do not depend on which of its
            # outputs the evaluation happens to cover
            byproducts = production.move_byproduct_ids.filtered(lambda m: m.state == 'done')
            byproducts_by_product = byproducts.grouped('product_id')
            finished_moves = production.move_finished_ids.filtered(
                lambda m: m.state == 'done' and m.product_id == production.product_id,
            )
            finished_qty = sum(finished_moves.mapped('quantity_product_uom'))
            total_cost = abs(sum(production.move_raw_ids.mapped('value')))
            # only the time the period itself paid for, like every other input
            total_cost += production.workorder_ids._cal_cost(period_end)
            total_cost += production.extra_cost * finished_qty
            byproduct_share = sum(
                product_moves[0].cost_share for product_moves in byproducts_by_product.values()
            )
            for product, product_moves in byproducts_by_product.items():
                allocate(product_moves, total_cost * product_moves[0].cost_share / 100)
            allocate(finished_moves, total_cost * (1 - byproduct_share / 100))
        return values
