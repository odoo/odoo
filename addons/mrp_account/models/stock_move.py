# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import models
from odoo.tools import float_round


class StockMove(models.Model):
    _inherit = "stock.move"

    def _set_value(self, recompute_date=None, skip_check=False):
        """Propagate component value changes through completed productions."""
        changed_moves = super()._set_value(recompute_date=recompute_date, skip_check=skip_check)
        if skip_check:
            return changed_moves

        changed_components = changed_moves.filtered(lambda move: move.product_id.cost_method in ('fifo', 'average'))
        productions = changed_components.raw_material_production_id.filtered(lambda production: production.state == 'done')
        finished_moves = productions.move_finished_ids.filtered(lambda move: move.state == 'done' and move.product_id.cost_method in ('fifo', 'average'))
        if finished_moves:
            finished_moves._set_value(recompute_date=min(finished_moves.mapped('date')))
        return changed_moves

    def _get_value_from_production(self, quantity):
        self.ensure_one()
        if not self.production_id or self.product_id.cost_method not in ('fifo', 'average'):
            return super()._get_value_from_production(quantity)

        production = self.production_id.with_company(self.company_id)
        raw_moves = production.move_raw_ids.filtered(lambda move: move.state == 'done')
        finished_moves = production.move_finished_ids.filtered(lambda move: move.state == 'done' and not move.product_id.uom_id.is_zero(move._get_valued_qty()))
        main_moves = finished_moves.filtered(lambda move: move.product_id == production.product_id)
        main_quantity = sum(move._get_valued_qty() for move in main_moves)
        total_cost = abs(sum(raw_moves.mapped('value'))) + production.workorder_ids._cal_cost() + production.extra_cost * main_quantity

        if self.product_id == production.product_id:
            byproduct_cost_share = sum(finished_moves.filtered(lambda move: move.product_id != production.product_id).mapped('cost_share'))
            cost_share = float_round(1 - byproduct_cost_share / 100, precision_rounding=0.0001)
            output_quantity = main_quantity
        else:
            cost_share = self.cost_share / 100
            output_quantity = self._get_valued_qty()

        value = total_cost * cost_share * quantity / output_quantity if output_quantity else 0
        return {
            'value': value,
            'quantity': quantity,
            'description': self.env._('%(value)s for %(quantity)s %(unit)s from %(production)s',
                value=self.company_currency_id.format(value), quantity=quantity, unit=self.product_id.uom_id.name,
                production=self.production_id.display_name),
        }

    def _get_price_unit(self, product=None, include_consigned=False, include_consumable=False):
        """ Moves coming from a kit (phantom BoM) are valued per unit of the (root)
        kit: each storable component contributes its own unit value times the quantity
        of that component in one kit, as defined by the BoM. The delivered quantities
        do not have to add up to whole kits: the kit price only depends on the BoM
        composition, not on how the components were split across pickings.

        :param product: the kit product actually sold/moved. When set, its phantom BoM
            is used as the root kit directly. This disambiguates the case where the sold
            kit is itself a component of a larger kit: a move only stores its leaf
            ``bom_line_id``, so climbing the BoM tree from the moves would wrongly reach
            the larger kit. When not set, the moves are valued the standard way.
        :param include_consumable: also value the kit's consumable components (at their
            standard price); by default only storable components enter the kit cost.
        """
        kit_moves = self.filtered(lambda m: m.bom_line_id.bom_id.type == 'phantom')
        if not product or not kit_moves:
            return super()._get_price_unit(
                include_consigned=include_consigned, product=product, include_consumable=include_consumable,
            )

        root_bom = self.env['mrp.bom']._bom_find(product, bom_type='phantom')[product]
        if not root_bom:
            return product.standard_price

        kit_product = product
        _dummy, exploded_lines = root_bom.explode(kit_product, 1.0)
        qty_per_kit_by_line = defaultdict(float)
        for line, line_data in exploded_lines:
            qty_per_kit_by_line[line] += line.uom_id._compute_quantity(
                line_data['qty'], line.product_id.uom_id, round=False,
            ) / root_bom.uom_id._compute_quantity(root_bom.product_qty, kit_product.uom_id, round=False)

        price_unit = 0
        for bom_line, moves in kit_moves.grouped('bom_line_id').items():
            if not bom_line.product_id.is_storable and not include_consumable:
                continue
            component_price = super(StockMove, moves)._get_price_unit(
                include_consigned=include_consigned, include_consumable=include_consumable,
            )
            price_unit += component_price * qty_per_kit_by_line.get(bom_line, 0)
        return price_unit
