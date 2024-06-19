# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _get_analytic_distribution(self):
        if not self.picking_id:
            return super()._get_analytic_distribution()
        account_ids = self.picking_id.project_id._get_analytic_account_ids()
        if not account_ids:
            return super()._get_analytic_distribution()
        return {",".join((str(account_id) for account_id in account_ids.ids)): 100}

    def _prepare_analytic_line_values(self, account_field_values, amount, unit_amount):
        res = super()._prepare_analytic_line_values(account_field_values, amount, unit_amount)
        if self.picking_id:
            res['name'] = self.picking_id.name
        return res

    def _account_analytic_entry_move(self):
        unvalid_moves = self.filtered(lambda m: m.picking_id and not (m.picking_id.project_id and m.picking_type_id.analytic_costs))
        super(StockMove, self - unvalid_moves)._account_analytic_entry_move()
