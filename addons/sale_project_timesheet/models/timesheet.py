# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import ValidationError

from odoo import api, fields, models, _


class TimesheetLine(models.Model):
    _inherit = 'account.analytic.line'

    timesheet_invoice_type = fields.Selection(selection_add=[('non_billable_project', 'No task found')])

    @api.multi
    @api.depends('project_id', 'task_id')
    def _compute_timesheet_invoice_type(self):
        super(TimesheetLine, self)._compute_timesheet_invoice_type()

        for timesheet in self:
            if timesheet.is_timesheet and timesheet.project_id and not timesheet.task_id:
                timesheet.timesheet_invoice_type = 'non_billable_project'

    @api.constrains('so_line', 'project_id')
    def _check_sale_line_in_project_map(self):
        for timesheet in self:
            if timesheet.project_id and timesheet.so_line:  # billed timesheet
                if timesheet.so_line not in timesheet.project_id.mapped('sale_line_employee_ids.sale_line_id') | timesheet.task_id.sale_line_id | timesheet.project_id.sale_line_id:
                    raise ValidationError(_("This timesheet line cannot be billed: there is no Sale Order Item defined on the task, nor on the project. Please define one to save your timesheet line."))

    @api.onchange('employee_id')
    def _onchange_task_id_employee_id(self):
        if self.is_timesheet and self.project_id:  # timesheet only
            if self.task_id.billable_type == 'task_rate':
                self.so_line = self.task_id.sale_line_id
            elif self.task_id.billable_type == 'employee_rate':
                self.so_line = self._timesheet_determine_sale_line(self.task_id, self.employee_id)
            else:
                self.so_line = False

    # -----------------------------------------------------------
    # Timesheet specific-model methods
    # -----------------------------------------------------------

    @api.model
    def _timesheet_preprocess(self, values):
        values = super(TimesheetLine, self)._timesheet_preprocess(values)
        # task implies so line (at create)
        if 'task_id' in values and not values.get('so_line') and values.get('employee_id'):
            task = self.env['project.task'].sudo().browse(values['task_id'])
            employee = self.env['hr.employee'].sudo().browse(values['employee_id'])
            values['so_line'] = self._timesheet_determine_sale_line(task, employee).id
        return values

    @api.multi
    def _timesheet_postprocess_values(self, values):
        result = super(TimesheetLine, self)._timesheet_postprocess_values(values)
        # (re)compute the sale line
        if any([field_name in values for field_name in ['task_id', 'employee_id']]):
            for timesheet in self:
                if timesheet.project_id:
                    result[timesheet.id].update({
                        'so_line': timesheet._timesheet_determine_sale_line(timesheet.task_id, timesheet.employee_id).id,
                    })
        return result

    # -----------------------------------------------------------
    # Business methods
    # -----------------------------------------------------------

    @api.model
    def _timesheet_protected_fields(self):
        field_list = super(TimesheetLine, self)._timesheet_protected_fields()
        field_list += ['project_id', 'task_id']
        return field_list

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
