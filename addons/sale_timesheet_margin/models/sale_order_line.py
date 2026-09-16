from odoo import api, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    @api.depends("analytic_line_ids.amount", "qty_transferred_method")
    def _compute_purchase_price(self):
        service_non_timesheet_sols = self.filtered(
            lambda sol: (
                not sol.is_expense
                and sol.is_service
                and sol.product_id.service_policy == "ordered_prepaid"
                and sol.state == "done"
                and sol.purchase_price != 0
            )
        )
        timesheet_sols = self.filtered(
            lambda sol: (
                sol.qty_transferred_method == "timesheet"
                and not sol.product_id.standard_price
            )
        )
        super(
            SaleOrderLine, self - timesheet_sols - service_non_timesheet_sols
        )._compute_purchase_price()
        if timesheet_sols:
            group_amount = self.env["account.analytic.line"]._read_group(
                [("so_line", "in", timesheet_sols.ids), ("project_id", "!=", False)],
                ["so_line"],
                ["amount:sum", "unit_amount:sum"],
            )
            mapped_sol_timesheet_amount = {
                so_line.id: -amount_sum / unit_amount_sum if unit_amount_sum else 0.0
                for so_line, amount_sum, unit_amount_sum in group_amount
            }
            _debug.perf.count(
                "timesheet_cost_read_group",
                lines=len(timesheet_sols),
                rows=len(mapped_sol_timesheet_amount),
            )
            for line in timesheet_sols:
                line = line.with_company(line.company_id)
                product_cost = mapped_sol_timesheet_amount.get(
                    line.id, line.product_id.standard_price
                )
                product_uom_id = line.product_uom_id or line.product_id.uom_id
                if product_uom_id != line.company_id.project_time_mode_id:
                    product_cost = product_uom_id._get_quantity_in_unit(
                        product_cost, line.company_id.project_time_mode_id
                    )

                _debug.logic(
                    "line_cost", line=line, by="timesheet_amount", cost=product_cost
                )
                line.purchase_price = line._convert_to_sol_currency(
                    product_cost, line.product_id.cost_currency_id
                )
