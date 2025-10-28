# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class StockMove(models.Model):
    _inherit = "stock.move"

    def _get_value_from_production(self, quantity, at_date=None):
        # TODO: Maybe move _cal_price here
        self.ensure_one()
        if not self.production_id:
            return super()._get_value_from_production(quantity, at_date)
        return {
            'value': quantity * self.price_unit,
            'quantity': quantity,
            'description': self.env._('Manufactured %(production)s', production=self.production_id.display_name),
        }

    def _get_all_related_sm(self, product):
        moves = super()._get_all_related_sm(product)
        return moves | self.filtered(
            lambda m:
            m.bom_line_id.bom_id.type == 'phantom' and
            m.bom_line_id.bom_id == moves.bom_line_id.bom_id
        )
