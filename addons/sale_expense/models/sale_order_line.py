from odoo import api, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.depends(
        'qty_delivered_method',
        'analytic_line_ids.so_line',
        'analytic_line_ids.unit_amount',
        'analytic_line_ids.product_uom_id',
        'analytic_line_ids.move_line_id.expense_id',
        'is_expense',
        'product_uom_qty',
    )
    def _compute_qty_delivered(self):
        expense_lines = self.filtered(
            lambda line: (
                line.is_expense
                and line.product_id.expense_policy == 'cost'
                and line.analytic_line_ids.move_line_id.expense_id
            )
        )
        super(SaleOrderLine, self - expense_lines)._compute_qty_delivered()

        for line in expense_lines:
            line.qty_delivered = 1.0 if line.product_uom_qty else 0.0
