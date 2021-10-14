# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models

class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    @api.depends('analytic_line_ids.amount', 'qty_delivered_method')
    def _compute_purchase_price(self):
        timesheet_sols = self.filtered(
            lambda sol: sol.qty_delivered_method == 'timesheet' and not sol.product_id.standard_price
        )
        super(SaleOrderLine, self - timesheet_sols)._compute_purchase_price()
        if timesheet_sols:
            group_amount = self.env['account.analytic.line'].read_group(
                [('so_line', 'in', timesheet_sols.ids), ('project_id', '!=', False)],
                ['so_line', 'amount:sum', 'unit_amount:sum'],
                ['so_line'])
            mapped_sol_timesheet_amount = {
                amount['so_line'][0]: -amount['amount'] / amount['unit_amount'] if amount['unit_amount'] else 0.0
                for amount in group_amount
            }
            for line in timesheet_sols:
                line = line.with_company(line.company_id)
                product_cost = mapped_sol_timesheet_amount.get(line.id, line.product_id.standard_price)
                if line.product_id.uom_id != line.company_id.project_time_mode_id and\
                   line.product_id.uom_id.category_id.id == line.company_id.project_time_mode_id.category_id.id:
                    product_cost = line.company_id.project_time_mode_id._compute_quantity(
                        product_cost,
                        line.product_id.uom_id
                    )
                line.purchase_price = line._convert_price(product_cost, line.product_id.uom_id)
