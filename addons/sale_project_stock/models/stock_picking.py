from odoo import _, models
from odoo.exceptions import UserError
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def button_validate(self):
        res = super().button_validate()
        if res is not True:
            return res

        for picking in self:
            project = picking.project_id
            sale_order = project.sudo().reinvoiced_sale_order_id
            if not (sale_order and picking.picking_type_id.analytic_costs):
                continue
            reinvoicable_stock_moves = picking.move_ids.filtered(
                lambda m: m.product_id.expense_policy in {"sales_price", "cost"}
            )
            if not reinvoicable_stock_moves:
                continue
            if sale_order.state in ("draft", "sent"):
                _debug.logic(
                    "picking_validate_refused",
                    picking=picking,
                    order=sale_order,
                    reason="order_not_confirmed",
                )
                raise UserError(
                    _(
                        "The Sales Order %(order)s linked to the Project %(project)s must be"
                        " validated before validating the stock picking.",
                        order=sale_order.name,
                        project=project.name,
                    )
                )
            if sale_order.state == "cancel":
                _debug.logic(
                    "picking_validate_refused",
                    picking=picking,
                    order=sale_order,
                    reason="order_cancelled",
                )
                raise UserError(
                    _(
                        "The Sales Order %(order)s linked to the Project %(project)s is cancelled."
                        " You cannot validate a stock picking on a cancelled Sales Order.",
                        order=sale_order.name,
                        project=project.name,
                    )
                )
            if sale_order.locked:
                _debug.logic(
                    "picking_validate_refused",
                    picking=picking,
                    order=sale_order,
                    reason="order_locked",
                )
                raise UserError(
                    _(
                        "The Sales Order %(order)s linked to the Project %(project)s is currently locked."
                        " You cannot validate a stock picking on a locked Sales Order."
                        " Please create a new SO linked to this Project.",
                        order=sale_order.name,
                        project=project.name,
                    )
                )
            sale_line_values_to_create = []
            last_so_line = self.env["sale.order.line"].search_read(  # noqa: E8507 - one lookup per sale order of the picking
                [("order_id", "=", sale_order.id)],
                ["sequence"],
                order="sequence desc",
                limit=1,
            )
            last_sequence = next((sol["sequence"] for sol in last_so_line), 100)

            for stock_move in reinvoicable_stock_moves:
                price = stock_move._sale_get_invoice_price(sale_order)
                sale_line_values_to_create.append(
                    stock_move._sale_prepare_sale_line_values(
                        sale_order, price, last_sequence
                    )
                )
                last_sequence += 1
            _debug.lifecycle(
                "reinvoiced_lines_from_picking",
                picking=picking,
                order=sale_order,
                lines=len(sale_line_values_to_create),
            )
            self.env["sale.order.line"].with_context(
                skip_procurement=True
            ).sudo().create(sale_line_values_to_create)
        return res
