from odoo import models


class StockMove(models.Model):
    _inherit = "stock.move"

    def _get_landed_cost(self, at_date=None):
        domain = [('move_id', 'in', self.ids), ('cost_id.state', '=', 'done')]
        if at_date:
            domain.append(('cost_id.date', '<=', at_date))
        landed_cost_group = self.env['stock.valuation.adjustment.lines']._read_group(domain, ['move_id'], ['id:recordset'])
        return dict(landed_cost_group)

    def _get_value_from_account_move(self, quantity, at_date=None):
        self.ensure_one()
        value, quantity = super()._get_value_from_account_move(quantity, at_date=at_date)
        # Add landed costs value
        lc = self._get_landed_cost(at_date=at_date)
        extra_value = 0
        if lc.get(self):
            extra_value = sum(lc[self].mapped('additional_landed_cost'))
        return value + extra_value, quantity
