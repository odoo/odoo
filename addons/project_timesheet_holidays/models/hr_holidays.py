# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class HolidaysType(models.Model):
    _inherit = "hr.leave.type"

    def _default_project_id(self):
        company = self.company_id if self.company_id else self.env.user.company_id
        return company.leave_timesheet_project_id.id

    def _default_task_id(self):
        company = self.company_id if self.company_id else self.env.user.company_id
        return company.leave_timesheet_task_id.id

    timesheet_generate = fields.Boolean('Generate Timesheet', default=True, help="If checked, when validating a time off, timesheet will be generated in the Vacation Project of the company.")
    timesheet_project_id = fields.Many2one('project.project', string="Project", default=_default_project_id, help="The project will contain the timesheet generated when a time off is validated.")
    timesheet_task_id = fields.Many2one('project.task', string="Task for timesheet", default=_default_task_id, domain="[('project_id', '=', timesheet_project_id)]")

    @api.onchange('timesheet_task_id')
    def _onchange_timesheet_generate(self):
        if self.timesheet_task_id or self.timesheet_project_id:
            self.timesheet_generate = True
        else:
            self.timesheet_generate = False

    @api.onchange('timesheet_project_id')
    def _onchange_timesheet_project(self):
        company = self.company_id if self.company_id else self.env.user.company_id
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
                    raise ValidationError(_('Both the internal project and task are required to\
                    generate timesheet for the time of. If you don\'t want timesheet, you must let\
                    empty internal project and task.'))


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
            holiday_project = holiday.holiday_status_id.timesheet_project_id
            holiday_task = holiday.holiday_status_id.timesheet_task_id

            work_hours_data = holiday.employee_id.list_work_time_per_day(
                fields.Datetime.from_string(holiday.date_from),
                fields.Datetime.from_string(holiday.date_to),
            )
            for index, (day_date, work_hours_count) in enumerate(work_hours_data):
                self.env['account.analytic.line'].sudo().create({
                    'name': "%s (%s/%s)" % (holiday.name or '', index + 1, len(work_hours_data)),
                    'project_id': holiday_project.id,
                    'task_id': holiday_task.id,
                    'account_id': holiday_project.analytic_account_id.id,
                    'unit_amount': work_hours_count,
                    'user_id': holiday.employee_id.user_id.id,
                    'date': fields.Date.to_string(day_date),
                    'holiday_id': holiday.id,
                    'employee_id': holiday.employee_id.id,
                })

        return super(Holidays, self)._validate_leave_request()

    @api.multi
    def action_refuse(self):
        """ Remove the timesheets linked to the refused holidays """
        result = super(Holidays, self).action_refuse()
        timesheets = self.sudo().mapped('timesheet_ids')
        timesheets.write({'holiday_id': False})
        timesheets.unlink()
        return result
