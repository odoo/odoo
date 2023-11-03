# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class HolidaysType(models.Model):
    _inherit = "hr.leave.type"

    timesheet_generate = fields.Boolean(
        'Generate Timesheets', compute='_compute_timesheet_generate', store=True, readonly=False,
        help="If checked, when validating a time off, timesheet will be generated in the Vacation Project of the company.")
    timesheet_project_id = fields.Many2one('project.project', string="Project", domain="[('company_id', '=', company_id)]",
        compute="_compute_timesheet_project_id", store=True, readonly=False)
    timesheet_task_id = fields.Many2one(
        'project.task', string="Task", compute='_compute_timesheet_task_id',
        store=True, readonly=False,
        domain="[('project_id', '=', timesheet_project_id),"
                "('project_id', '!=', False),"
                "('company_id', '=', company_id)]")

    @api.depends('timesheet_task_id', 'timesheet_project_id')
    def _compute_timesheet_generate(self):
        for leave_type in self:
            leave_type.timesheet_generate = not leave_type.company_id or (leave_type.timesheet_task_id and leave_type.timesheet_project_id)

    @api.depends('company_id')
    def _compute_timesheet_project_id(self):
        for leave in self:
            leave.timesheet_project_id = leave.company_id.internal_project_id

    @api.depends('timesheet_project_id')
    def _compute_timesheet_task_id(self):
        for leave_type in self:
            default_task_id = leave_type.company_id.leave_timesheet_task_id

            if default_task_id and default_task_id.project_id == leave_type.timesheet_project_id:
                leave_type.timesheet_task_id = default_task_id
            else:
                leave_type.timesheet_task_id = False

    @api.constrains('timesheet_generate', 'timesheet_project_id', 'timesheet_task_id')
    def _check_timesheet_generate(self):
        for holiday_status in self:
            if holiday_status.timesheet_generate and holiday_status.company_id:
                if not holiday_status.timesheet_project_id or not holiday_status.timesheet_task_id:
                    raise ValidationError(_("Both the internal project and task are required to "
                    "generate a timesheet for the time off %s. If you don't want a timesheet, you should "
                    "leave the internal project and task empty.", holiday_status.name))


class Holidays(models.Model):
    _inherit = "hr.leave"

    timesheet_ids = fields.One2many('account.analytic.line', 'holiday_id', string="Analytic Lines")

    def _validate_leave_request(self):
        """ Timesheet will be generated on leave validation only if timesheet_generate is True
            If company is set, timesheet_project_id and timesheet_task_id from leave type are
            used as project_id and task_id.
            Else, internal_project_id and leave_timesheet_task_id are used.
            The generated timesheet will be attached to this project/task.
        """
        vals_list = []
        leave_ids = []
        for leave in self:
            if leave.holiday_type != 'employee' or not leave.holiday_status_id.timesheet_generate:
                continue

            if leave.holiday_status_id.company_id:
                project, task = leave.holiday_status_id.timesheet_project_id, leave.holiday_status_id.timesheet_task_id
            else:
                project, task = leave.employee_id.company_id.internal_project_id, leave.employee_id.company_id.leave_timesheet_task_id

            if not project or not task:
                continue

            leave_ids.append(leave.id)
            if not leave.employee_id:
                continue

            work_hours_data = leave.employee_id.list_work_time_per_day(
                leave.date_from,
                leave.date_to)

            for index, (day_date, work_hours_count) in enumerate(work_hours_data):
                vals_list.append(leave._timesheet_prepare_line_values(index, work_hours_data, day_date, work_hours_count, project, task))

        # Unlink previous timesheets to avoid doublon (shouldn't happen on the interface but meh)
        old_timesheets = self.env["account.analytic.line"].sudo().search([('project_id', '!=', False), ('holiday_id', 'in', leave_ids)])
        if old_timesheets:
            old_timesheets.holiday_id = False
            old_timesheets.unlink()

        self.env['account.analytic.line'].sudo().create(vals_list)

        return super()._validate_leave_request()

    def _timesheet_prepare_line_values(self, index, work_hours_data, day_date, work_hours_count, project, task):
        self.ensure_one()
        return {
            'name': _("Time Off (%s/%s)", index + 1, len(work_hours_data)),
            'project_id': project.id,
            'task_id': task.id,
            'account_id': project.sudo().analytic_account_id.id,
            'unit_amount': work_hours_count,
            'user_id': self.employee_id.user_id.id,
            'date': day_date,
            'holiday_id': self.id,
            'employee_id': self.employee_id.id,
            'company_id': task.sudo().company_id.id or project.sudo().company_id.id,
        }

    def action_refuse(self):
        """ Remove the timesheets linked to the refused holidays """
        result = super(Holidays, self).action_refuse()
        timesheets = self.sudo().mapped('timesheet_ids')
        timesheets.write({'holiday_id': False})
        timesheets.unlink()
        return result

    def _action_user_cancel(self, reason):
        res = super()._action_user_cancel(reason)
        timesheets = self.sudo().timesheet_ids
        timesheets.write({'holiday_id': False})
        timesheets.unlink()
        return res
