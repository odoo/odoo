# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, models
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def button_validate(self):
        res = super().button_validate()
        if res is not True:
            return res

        for picking in self:
            project = picking.project_id
            sale_order = project.reinvoiced_sale_order_id
            if not (sale_order and picking.picking_type_id.analytic_costs):
                continue
            reinvoicable_stock_moves = picking.move_ids.filtered(lambda m: m.product_id.expense_policy in {'sales_price', 'cost'})
            if not reinvoicable_stock_moves:
                continue
            # raise if the sale order is not currently open
            if sale_order.state in ('draft', 'sent'):
                raise UserError(_(
                    "The Sales Order %(order)s linked to the Project %(project)s must be"
                    " validated before validating the stock picking.",
                    order=sale_order.name,
                    project=project.name,
                ))
            elif sale_order.state == 'cancel':
                raise UserError(_(
                    "The Sales Order %(order)s linked to the Project %(project)s is cancelled."
                    " You cannot validate a stock picking on a cancelled Sales Order.",
                    order=sale_order.name,
                    project=project.name,
                ))
            elif sale_order.locked:
                raise UserError(_(
                    "The Sales Order %(order)s linked to the Project %(project)s is currently locked."
                    " You cannot validate a stock picking on a locked Sales Order."
                    " Please create a new SO linked to this Project.",
                    order=sale_order.name,
                    project=project.name,
                ))
            # Create SOLs in reinvoiced_sale_order_id with reinvoicable stock moves
            sale_line_values_to_create = []
            # Get last sequence SOL
            last_so_line = self.env['sale.order.line'].search_read(
                [('order_id', '=', sale_order.id)],
                ['sequence'], order='sequence desc', limit=1,
            )
            last_sequence = next((sol['sequence'] for sol in last_so_line), 100)

            for stock_move in reinvoicable_stock_moves:
                # Get price
                price = stock_move._sale_get_invoice_price(sale_order)
                # Create the sale lines in batch
                sale_line_values_to_create.append(stock_move._sale_prepare_sale_line_values(sale_order, price, last_sequence))
                last_sequence += 1
            self.env['sale.order.line'].with_context(skip_procurement=True).create(sale_line_values_to_create)
        return res
