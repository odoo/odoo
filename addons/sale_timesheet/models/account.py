# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import UserError
from odoo import api, fields, models, _
from odoo.osv import expression


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    def _default_sale_line_domain(self):
        domain = super(AccountAnalyticLine, self)._default_sale_line_domain()
        return expression.OR([domain, [('qty_delivered_method', '=', 'timesheet')]])

    timesheet_invoice_type = fields.Selection([
        ('billable_time', 'Billable Time'),
        ('billable_fixed', 'Billable Fixed'),
        ('non_billable', 'Non Billable'),
        ('non_billable_project', 'No task found')], string="Billable Type", compute='_compute_timesheet_invoice_type', store=True, readonly=True)
    timesheet_invoice_id = fields.Many2one('account.invoice', string="Invoice", readonly=True, copy=False, help="Invoice created from the timesheet")

    @api.multi
    @api.depends('so_line.product_id', 'project_id', 'task_id')
    def _compute_timesheet_invoice_type(self):
        for timesheet in self:
            if timesheet.project_id:  # AAL will be set to False
                invoice_type = 'non_billable_project' if not timesheet.task_id else 'non_billable'
                if timesheet.task_id and timesheet.so_line.product_id.type == 'service':
                    if timesheet.so_line.product_id.invoice_policy == 'delivery':
                        if timesheet.so_line.product_id.service_type == 'timesheet':
                            invoice_type = 'billable_time'
                        else:
                            invoice_type = 'billable_fixed'
                    elif timesheet.so_line.product_id.invoice_policy == 'order':
                        invoice_type = 'billable_fixed'
                timesheet.timesheet_invoice_type = invoice_type

    @api.multi
    def write(self, values):
        # prevent to update invoiced timesheets if one line is of type delivery
        if self.sudo().filtered(lambda aal: aal.so_line.product_id.invoice_policy == "delivery") and self.filtered(lambda timesheet: timesheet.timesheet_invoice_id):
            if any([field_name in values for field_name in ['unit_amount', 'employee_id', 'task_id', 'so_line', 'amount', 'date']]):
                raise UserError(_('You can not modify already invoiced timesheets (linked to a Sales order items invoiced on Time and material).'))
        result = super(AccountAnalyticLine, self).write(values)
        return result

    @api.model
    def _timesheet_preprocess(self, values):
        values = super(AccountAnalyticLine, self)._timesheet_preprocess(values)
        # task implies so line
        if 'task_id' in values:
            task = self.env['project.task'].sudo().browse(values['task_id'])
            values['so_line'] = task.sale_line_id.id or values.get('so_line', False)

        # Set product_uom_id now so delivered qty is computed in SO line
        if not 'product_uom_id' in values and all([v in values for v in ['employee_id', 'project_id']]):
            employee = self.env['hr.employee'].sudo().browse(values['employee_id'])
            values['product_uom_id'] = employee.company_id.project_time_mode_id.id
        return values

    @api.multi
    def _timesheet_postprocess_values(self, values):
        result = super(AccountAnalyticLine, self)._timesheet_postprocess_values(values)
        # (re)compute the UoM from the employee company
        if any([field_name in values for field_name in ['employee_id']]):
            for timesheet in self:
                uom = timesheet.employee_id.company_id.project_time_mode_id
                result[timesheet.id].update({
                    'product_uom_id': uom.id,
                })
        return result
