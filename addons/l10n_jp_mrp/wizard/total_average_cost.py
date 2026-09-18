from collections import defaultdict

from odoo import fields, models
from odoo.exceptions import UserError


class L10nJpTotalAverageCostWizard(models.TransientModel):
    _inherit = 'l10n_jp_stock.total.average.cost.wizard'

    include_components = fields.Boolean(
        string='Include Consumed Components',
        help="Also evaluate the components the manufacturing orders of the period consumed, and the "
             "components those were made out of in turn. A good is valued off what its components "
             "cost, so one left at the price of an earlier period values the good on a stale figure.",
    )

    def _get_consumed_components(self, moves):
        """
        Return what the orders behind these moves consumed, when asked for it.

        The orders say what actually went into the goods, which a BoM only
        approximates; the same source the evaluation order is read off.
        """
        components = super()._get_consumed_components(moves)
        if not self.include_components:
            return components
        productions = moves.production_id | moves.raw_material_production_id
        return components | productions.move_raw_ids.product_id

    def _get_move_domain(self, products, period_start, period_end):
        # an unbuild reverses an issue, it does not acquire (施行令28条1項1号ハ)
        return super()._get_move_domain(products, period_start, period_end) + [
            ('unbuild_id', '=', False),
        ]

    def _get_evaluation_batches(self, products, moves, pulled_in):
        """
        Group the products by how deep they sit in the manufacturing of the period.

        What an order's output cost is read off the value of the moves that issued
        its components, so those components must already be evaluated, and their
        moves corrected, by the time the good made out of them is valued. The
        orders themselves say what came out of what, which a BoM only approximates
        and a by-product is missing from entirely.

        Products the period makes out of each other have no level to start from.
        Naming one asks for that product, so it is refused; one the evaluation
        pulled in on its own is left out instead, and so is everything made out of
        it, whose own cost would otherwise be read off a component that never moved.
        """
        issued_for = defaultdict(lambda: self.env['product.product'])
        for production in moves.production_id | moves.raw_material_production_id:
            issued = production.move_raw_ids.product_id
            # a by-product leaves the same order, so it costs those same components
            for produced in production.move_finished_ids.product_id:
                issued_for[produced] |= issued

        depths = {}
        walked = []
        looping = set()
        reasons = {}

        def depth(product):
            """Return how deep the product sits, or nothing when a loop lies at or under it."""
            if product in depths:
                return depths[product]
            if product in walked:
                # core only forbids a loop through a BoM's components, never one a by-product closes
                loop = walked[walked.index(product):] + [product]
                for looped in loop:
                    looping.add(looped)
                    reasons[looped] = self.env._(
                        'The orders of the period make these products out of each other, '
                        'so their costs cannot be evaluated in order: %s',
                        ' → '.join(other.display_name for other in loop),
                    )
                return None
            walked.append(product)
            components = issued_for[product]
            levels = [depth(component) for component in components]
            walked.pop()
            if stale := [c for c, level in zip(components, levels) if level is None]:
                depths[product] = None
                # the good would be valued off a component the period never corrected
                reasons.setdefault(product, self.env._(
                    'Its cost is read off %s, which the evaluation could not cost either.',
                    ', '.join(component.display_name for component in stale),
                ))
            else:
                depths[product] = 1 + max(levels, default=-1)
            return depths[product]

        batches = defaultdict(lambda: self.env['product.product'])
        excluded = {}
        for product in products:
            if (level := depth(product)) is None:
                excluded[product] = reasons[product]
            else:
                batches[level] |= product
        if refused := next((product for product in products - pulled_in if product in looping), None):
            raise UserError(reasons[refused])
        return [batches[level] for level in sorted(batches)], excluded

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
            unit_cost = value / order_qty if order_qty else 0.0
            for move in order_moves & moves:
                qty = move.quantity_product_uom
                valued_qty = move._get_valued_qty()
                stated_share = qty / valued_qty if valued_qty else 0.0
                if (manual := move._get_manual_value(qty))['quantity']:
                    values[move.id] = manual['value'] * stated_share
                else:
                    values[move.id] = (
                        unit_cost * qty
                        + move._get_value_from_extra(qty)['value'] * stated_share
                    )

        for production in moves.production_id:
            # the shares come from the order, not from which outputs are evaluated
            byproducts = production.move_byproduct_ids.filtered(lambda m: m.state == 'done')
            byproducts_by_product = byproducts.grouped('product_id')
            finished_moves = production.move_finished_ids.filtered(
                lambda m: m.state == 'done' and m.product_id == production.product_id,
            )
            total_cost = abs(sum(production.move_raw_ids.mapped('value')))
            # only the time the period itself paid for, like every other input
            total_cost += production.workorder_ids._cal_cost(period_end)
            total_cost += self._get_extra_cost(production, finished_moves)
            byproduct_share = sum(
                product_moves[0].cost_share for product_moves in byproducts_by_product.values()
            )
            for product, product_moves in byproducts_by_product.items():
                allocate(product_moves, total_cost * product_moves[0].cost_share / 100)
            allocate(finished_moves, total_cost * (1 - byproduct_share / 100))
        return values

    def _get_extra_cost(self, production, finished_moves):
        """
        Return what an order charged on top of its components and its labour.

        A subcontractor's fee is frozen into ``extra_cost`` when the order is marked
        done, so the bill that follows the goods never reaches it. The receipt that
        fee was estimated off does carry the bill, so price it there instead.
        """
        move_fields = self.env['stock.move']._fields
        # a fee is only ever billed where the receipt is bought on an order
        billable = 'is_subcontract' in move_fields and 'purchase_line_id' in move_fields
        total = 0.0
        for move in finished_moves:
            qty = move.quantity_product_uom
            receipt = billable and move.move_dest_ids.filtered(
                lambda m: m.state == 'done' and m.is_subcontract and m.purchase_line_id,
            ).sorted('create_date', reverse=True)[:1]
            # nobody bills an order made in house, its extra cost is the one stated on it
            total += self._get_acquisition_value(receipt, qty) if receipt else production.extra_cost * qty
        return total
