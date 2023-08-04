# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class HolidaysType(models.Model):
    _inherit = "hr.leave.type"

    timesheet_generate = fields.Boolean(
        'Generate Timesheet', compute='_compute_timesheet_generate', store=True, readonly=False,
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
            leave_type.timesheet_generate = leave_type.timesheet_task_id and leave_type.timesheet_project_id

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
                    "leave the internal project and task empty.") % (holiday_status.name))


class Holidays(models.Model):
    _inherit = "hr.leave"

    timesheet_ids = fields.One2many('account.analytic.line', 'holiday_id', string="Analytic Lines")

    def _validate_leave_request(self):
        """ Timesheet will be generated on leave validation only if a timesheet_project_id and a
            timesheet_task_id are set on the corresponding leave type. The generated timesheet will
            be attached to this project/task.
        """
        holidays = self.filtered(
            lambda l: l.holiday_type == 'employee' and
            l.holiday_status_id.timesheet_project_id and
            l.holiday_status_id.timesheet_task_id and
            l.holiday_status_id.timesheet_project_id.sudo().company_id == (l.holiday_status_id.company_id or self.env.company))

        # Unlink previous timesheets do avoid doublon (shouldn't happen on the interface but meh)
        old_timesheets = holidays.sudo().timesheet_ids
        if old_timesheets:
            old_timesheets.holiday_id = False
            old_timesheets.unlink()

        # create the timesheet on the vacation project
        holidays._timesheet_create_lines()

        return super()._validate_leave_request()

    def _timesheet_create_lines(self):
        vals_list = []
        for leave in self:
            if not leave.employee_id:
                continue
            work_hours_data = leave.employee_id.list_work_time_per_day(
                leave.date_from,
                leave.date_to)
            for index, (day_date, work_hours_count) in enumerate(work_hours_data):
                vals_list.append(leave._timesheet_prepare_line_values(index, work_hours_data, day_date, work_hours_count))
        return self.env['account.analytic.line'].sudo().create(vals_list)

    def _timesheet_prepare_line_values(self, index, work_hours_data, day_date, work_hours_count):
        self.ensure_one()
        return {
            'name': _("Time Off (%s/%s)", index + 1, len(work_hours_data)),
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

    def _action_user_cancel(self, reason):
        res = super()._action_user_cancel(reason)
        timesheets = self.sudo().timesheet_ids
        timesheets.write({'holiday_id': False})
        timesheets.unlink()
        return res
