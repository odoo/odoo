from odoo import Command, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _sale_can_be_reinvoiced(self):
        self.check_singleton()
        if self.expense_id:
            _debug.logic("reinvoice_check", line=self, by="expense")
            return (
                self.expense_id.product_id.expense_policy in {"sales_price", "cost"}
                and self.expense_id.sale_order_id
                and self.display_type == "product"
            )
        return super()._sale_can_be_reinvoiced()

    def _get_so_mapping_from_expense(self):
        mapping_from_expense = {}
        for move_line in self.filtered(lambda move_line: move_line.expense_id):
            mapping_from_expense[move_line.id] = (
                move_line.expense_id.sale_order_id or None
            )
        return mapping_from_expense

    def _sale_get_order_map(self):
        mapping_from_invoice = super()._sale_get_order_map()
        mapping_from_invoice.update(self._get_so_mapping_from_expense())
        return mapping_from_invoice

    def _sale_prepare_sale_line_values(self, order, price, sequence=None):
        res = super()._sale_prepare_sale_line_values(order, price, sequence)
        if self.expense_id:
            res.update(
                {
                    "name": self.name,
                    "expense_ids": [Command.set(self.expense_id.ids)],
                    "product_qty": self.expense_id.quantity,
                    "analytic_distribution": self.analytic_distribution,
                }
            )
        return res

    def _sale_create_reinvoice_sale_line(self):
        expensed_lines = self.filtered("expense_id")
        res = super(
            AccountMoveLine, self - expensed_lines
        )._sale_create_reinvoice_sale_line()
        _debug.pipeline("expense_lines_reinvoiced_unmerged", lines=expensed_lines)
        res.update(
            super(
                AccountMoveLine,
                expensed_lines.with_context({"force_split_lines": True}),
            )._sale_create_reinvoice_sale_line()
        )
        return res
