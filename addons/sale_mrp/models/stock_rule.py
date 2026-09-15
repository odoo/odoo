from odoo import models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class StockRule(models.Model):
    _inherit = "stock.rule"

    def _prepare_mo_vals(self, procurement, bom):
        res = super()._prepare_mo_vals(procurement, bom)
        if procurement.values.get("sale_line_id"):
            res["sale_line_id"] = procurement.values["sale_line_id"]
        return res

    def _prepare_stock_move_vals(self, procurement):
        move_values = super()._prepare_stock_move_vals(procurement)
        sol_id = procurement.values.get("sale_line_id")
        if not sol_id or "product_id" not in move_values:
            return move_values
        sol = self.env["sale.order.line"].browse(sol_id)
        if move_values["product_id"] == sol.product_id.id:
            return move_values
        active_moves = sol.move_ids.filtered(lambda move: move.state != "cancel")
        bom_line = active_moves.bom_line_id.filtered(
            lambda line: line.product_id.id == move_values["product_id"]
        )[:1]
        if bom_line:
            _debug.logic("move_bom_line_resolved", rule=self, bom_line=bom_line)
            move_values["bom_line_id"] = bom_line.id
        return move_values
