# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class HolidaysType(models.Model):
    _inherit = "hr.leave.type"

    def _default_project_id(self):
        company = self.company_id if self.company_id else self.env.company
        return company.leave_timesheet_project_id.id

    def _default_task_id(self):
        company = self.company_id if self.company_id else self.env.company
        return company.leave_timesheet_task_id.id

    timesheet_generate = fields.Boolean('Generate Timesheet', default=True, help="If checked, when validating a time off, timesheet will be generated in the Vacation Project of the company.")
    timesheet_project_id = fields.Many2one('project.project', string="Project", default=_default_project_id, domain="[('company_id', '=', company_id)]", help="The project will contain the timesheet generated when a time off is validated.")
    timesheet_task_id = fields.Many2one('project.task', string="Task for timesheet", default=_default_task_id, domain="[('project_id', '=', timesheet_project_id), ('company_id', '=', company_id)]")

    @api.onchange('timesheet_task_id')
    def _onchange_timesheet_generate(self):
        if self.timesheet_task_id or self.timesheet_project_id:
            self.timesheet_generate = True
        else:
            self.timesheet_generate = False

    @api.onchange('timesheet_project_id')
    def _onchange_timesheet_project(self):
        company = self.company_id if self.company_id else self.env.company
        default_task_id = company.leave_timesheet_task_id
        if default_task_id and default_task_id.project_id == self.timesheet_project_id:
            self.timesheet_task_id = default_task_id
        else:
            self.timesheet_task_id = False
        if self.timesheet_project_id:
            self.timesheet_generate = True
        else:
            self.timesheet_generate = False

    @api.constrains('timesheet_generate', 'timesheet_project_id', 'timesheet_task_id')
    def _check_timesheet_generate(self):
        for holiday_status in self:
            if holiday_status.timesheet_generate:
                if not holiday_status.timesheet_project_id or not holiday_status.timesheet_task_id:
                    raise ValidationError(_("Both the internal project and task are required to "
                    "generate a timesheet for the time off. If you don't want a timesheet, you should "
                    "leave the internal project and task empty."))


class Holidays(models.Model):
    _inherit = "hr.leave"

    timesheet_ids = fields.One2many('account.analytic.line', 'holiday_id', string="Analytic Lines")

    def _validate_leave_request(self):
        """ Timesheet will be generated on leave validation only if a timesheet_project_id and a
            timesheet_task_id are set on the corresponding leave type. The generated timesheet will
            be attached to this project/task.
        """
        # create the timesheet on the vacation project
        for holiday in self.filtered(
                lambda request: request.holiday_type == 'employee' and
                                request.holiday_status_id.timesheet_project_id and
                                request.holiday_status_id.timesheet_task_id):
            holiday._timesheet_create_lines()

        return super(Holidays, self)._validate_leave_request()

    def _timesheet_create_lines(self):
        self.ensure_one()
        work_hours_data = self.employee_id.list_work_time_per_day(
            self.date_from,
            self.date_to,
        )
        timesheets = self.env['account.analytic.line']
        for index, (day_date, work_hours_count) in enumerate(work_hours_data):
            timesheets |= self.env['account.analytic.line'].sudo().create(self._timesheet_prepare_line_values(index, work_hours_data, day_date, work_hours_count))
        return timesheets

    def _timesheet_prepare_line_values(self, index, work_hours_data, day_date, work_hours_count):
        self.ensure_one()
        return {
            'name': "%s (%s/%s)" % (self.holiday_status_id.name or '', index + 1, len(work_hours_data)),
            'project_id': self.holiday_status_id.timesheet_project_id.id,
            'task_id': self.holiday_status_id.timesheet_task_id.id,
            'account_id': self.holiday_status_id.timesheet_project_id.analytic_account_id.id,
            'unit_amount': work_hours_count,
            'user_id': self.employee_id.user_id.id,
            'date': day_date,
            'holiday_id': self.id,
            'employee_id': self.employee_id.id,
            'company_id': self.holiday_status_id.timesheet_task_id.company_id.id or self.holiday_status_id.timesheet_project_id.company_id.id,
        }

    def action_refuse(self):
        """ Remove the timesheets linked to the refused holidays """
        result = super(Holidays, self).action_refuse()
        timesheets = self.sudo().mapped('timesheet_ids')
        timesheets.write({'holiday_id': False})
        timesheets.unlink()
        return result
