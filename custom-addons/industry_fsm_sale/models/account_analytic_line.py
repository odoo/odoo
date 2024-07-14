# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    def _timesheet_determine_sale_line(self):
        if self.project_id.is_fsm and self.project_id.pricing_type == 'employee_rate':
            # Then we want to keep the SOL define for this timesheet
            if not self.task_id.sale_line_id:
                return False
            mapping = self.env['project.sale.line.employee.map'].search([('project_id', '=', self.project_id.id), ('employee_id', '=', self.employee_id.id)], limit=1)
            sol = mapping and self.env['sale.order.line'].search([
                ('product_id', '=', mapping.timesheet_product_id.id),
                ('price_unit', '=', mapping.price_unit),
                ('order_id', '=', self.task_id.sale_order_id.id)],
                limit=1)
            return sol or self.task_id.sale_line_id
        return super()._timesheet_determine_sale_line()
