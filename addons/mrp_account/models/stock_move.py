# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, models


class StockMove(models.Model):
    _inherit = "stock.move"

    def _get_value_data(self,
        forced_std_price=False,
        at_date=False,
        ignore_manual_update=False,
        add_computed_value_to_description=False):
        self.ensure_one()
        if self.production_id:
            valued_qty = self._get_valued_qty()
            return {
                'value': self._get_value_from_production(valued_qty),
                'quantity': valued_qty,
                'description': _('From Production Order %(reference)s', reference=self.production_id.name),
            }
        return super()._get_value_data(forced_std_price, at_date, ignore_manual_update, add_computed_value_to_description)

    def _get_value_from_production(self, quantity):
        # TODO: Maybe move _cal_price here
        self.ensure_one()
        return quantity * self.price_unit

    def _get_all_related_sm(self, product):
        moves = super()._get_all_related_sm(product)
        return moves | self.filtered(
            lambda m:
            m.bom_line_id.bom_id.type == 'phantom' and
            m.bom_line_id.bom_id == moves.bom_line_id.bom_id
        )
