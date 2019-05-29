# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import UserError, ValidationError

from odoo import api, fields, models, _
from odoo.osv import expression


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    def _default_sale_line_domain(self):
        domain = super(AccountAnalyticLine, self)._default_sale_line_domain()
        return expression.OR([domain, [('qty_delivered_method', '=', 'timesheet')]])

    timesheet_invoice_type = fields.Selection([
        ('billable_time', 'Billed on Timesheets'),
        ('billable_fixed', 'Billed at a Fixed price'),
        ('non_billable', 'Non Billable Tasks'),
        ('non_billable_project', 'No task found')], string="Billable Type", compute='_compute_timesheet_invoice_type', compute_sudo=True, store=True, readonly=True)
    timesheet_invoice_id = fields.Many2one('account.move', string="Invoice", readonly=True, copy=False, help="Invoice created from the timesheet")

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

    @api.onchange('employee_id')
    def _onchange_task_id_employee_id(self):
        if self.project_id:  # timesheet only
            if self.task_id.billable_type == 'task_rate':
                self.so_line = self.task_id.sale_line_id
            elif self.task_id.billable_type == 'employee_rate':
                self.so_line = self._timesheet_determine_sale_line(self.task_id, self.employee_id)
            else:
                self.so_line = False

    @api.constrains('so_line', 'project_id')
    def _check_sale_line_in_project_map(self):
        for timesheet in self:
            if timesheet.project_id and timesheet.so_line:  # billed timesheet
                if timesheet.so_line not in timesheet.project_id.mapped('sale_line_employee_ids.sale_line_id') | timesheet.task_id.sale_line_id | timesheet.project_id.sale_line_id:
                    raise ValidationError(_("This timesheet line cannot be billed: there is no Sale Order Item defined on the task, nor on the project. Please define one to save your timesheet line."))

    @api.multi
    def write(self, values):
        # prevent to update invoiced timesheets if one line is of type delivery
        self._check_can_write(values)
        result = super(AccountAnalyticLine, self).write(values)
        return result

    @api.multi
    def _check_can_write(self, values):
        if self.sudo().filtered(lambda aal: aal.so_line.product_id.invoice_policy == "delivery") and self.filtered(lambda timesheet: timesheet.timesheet_invoice_id):
            if any([field_name in values for field_name in ['unit_amount', 'employee_id', 'project_id', 'task_id', 'so_line', 'amount', 'date']]):
                raise UserError(_('You can not modify already invoiced timesheets (linked to a Sales order items invoiced on Time and material).'))

    @api.model
    def _timesheet_preprocess(self, values):
        values = super(AccountAnalyticLine, self)._timesheet_preprocess(values)
        # task implies so line (at create)
        if 'task_id' in values and not values.get('so_line') and values.get('employee_id'):
            task = self.env['project.task'].sudo().browse(values['task_id'])
            employee = self.env['hr.employee'].sudo().browse(values['employee_id'])
            values['so_line'] = self._timesheet_determine_sale_line(task, employee).id
        return values

    @api.multi
    def _timesheet_postprocess_values(self, values):
        result = super(AccountAnalyticLine, self)._timesheet_postprocess_values(values)
        # (re)compute the sale line
        if any([field_name in values for field_name in ['task_id', 'employee_id']]):
            for timesheet in self:
                result[timesheet.id].update({
                    'so_line': timesheet._timesheet_determine_sale_line(timesheet.task_id, timesheet.employee_id).id,
                })
        return result

    @api.model
    def _timesheet_determine_sale_line(self, task, employee):
        """ Deduce the SO line associated to the timesheet line:
            1/ timesheet on task rate: the so line will be the one from the task
            2/ timesheet on employee rate task: find the SO line in the map of the project (even for subtask), or fallback on the SO line of the task, or fallback
                on the one on the project
            NOTE: this have to be consistent with `_compute_billable_type` on project.task.
        """
        if task.billable_type != 'no':
            if task.billable_type == 'employee_rate':
                map_entry = self.env['project.sale.line.employee.map'].search([('project_id', '=', task.project_id.id), ('employee_id', '=', employee.id)])
                if map_entry:
                    return map_entry.sale_line_id
                if task.sale_line_id:
                    return task.sale_line_id
                return task.project_id.sale_line_id
            elif task.billable_type == 'task_rate':
                return task.sale_line_id
        return self.env['sale.order.line']
