from odoo import api, fields, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    expense_id = fields.Many2one(comodel_name="hr.expense")

    @api.depends("is_expense")
    def _compute_purchase_price(self):
        expense_lines = self.filtered("expense_id")
        for line in expense_lines:
            expense = line.expense_id
            product_cost = expense.untaxed_amount_currency / (expense.quantity or 1.0)
            _debug.logic(
                "line_cost", line=line, by="expense", expense=expense, cost=product_cost
            )
            line.purchase_price = line._convert_to_sol_currency(
                product_cost, expense.currency_id
            )

        return super(SaleOrderLine, self - expense_lines)._compute_purchase_price()
