# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import models


class StockMove(models.Model):
    _inherit = "stock.move"

    def _get_value_from_production(self, quantity, at_date=None):
        # TODO: Maybe move _cal_price here
        self.ensure_one()
        if not self.production_id:
            return super()._get_value_from_production(quantity, at_date)
        value = quantity * self.price_unit
        return {
            'value': value,
            'quantity': quantity,
            'description': self.env._('%(value)s for %(quantity)s %(unit)s from %(production)s',
                value=self.company_currency_id.format(value), quantity=quantity, unit=self.product_id.uom_id.name,
                production=self.production_id.display_name),
        }

    def _get_all_related_sm(self, product):
        moves = super()._get_all_related_sm(product)
        return moves | self.filtered(
            lambda m:
            m.bom_line_id.bom_id.type == 'phantom' and
            m.bom_line_id.bom_id == moves.bom_line_id.bom_id
        )

    def _get_kit_price_unit(self, product, kit_bom, valuated_quantity):
        """ Override the value for kit products """
        _dummy, exploded_lines = kit_bom.explode(product, valuated_quantity)
        total_price_unit = 0
        component_qty_per_kit = defaultdict(float)
        for line in exploded_lines:
            component_qty_per_kit[line[0].product_id] += line[1]['qty']
        for component, valuated_moves in self.grouped('product_id').items():
            price_unit = super(StockMove, valuated_moves)._get_price_unit()
            qty_per_kit = component_qty_per_kit[component] / kit_bom.product_qty
            total_price_unit += price_unit * qty_per_kit
        return total_price_unit / valuated_quantity if not product.uom_id.is_zero(valuated_quantity) else 0
