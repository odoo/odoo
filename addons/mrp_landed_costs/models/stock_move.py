from odoo import models


class StockMove(models.Model):
    _inherit = "stock.move"

    def _get_value_from_production(self, quantity, at_date=None):
        value = super()._get_value_from_production(quantity, at_date)
        # Add landed costs value
        lc = self._get_landed_cost(at_date=at_date)
        extra_value = 0
        if lc.get(self):
            extra_value = sum(lc[self].mapped('additional_landed_cost'))
        value += extra_value
        return value
