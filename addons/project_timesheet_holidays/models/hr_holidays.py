# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

import pytz


class HolidaysType(models.Model):
    _inherit = "hr.leave.type"

    timesheet_generate = fields.Boolean(
        'Generate Timesheets', compute='_compute_timesheet_generate', store=True, readonly=False,
        help="If checked, when validating a time off, timesheet will be generated in the Vacation Project of the company.")
    timesheet_project_id = fields.Many2one('project.project', string="Project", domain="[('company_id', 'in', [False, company_id])]",
        compute="_compute_timesheet_project_id", store=True, readonly=False)
    timesheet_task_id = fields.Many2one(
        'project.task', string="Task", compute='_compute_timesheet_task_id',
        store=True, readonly=False,
        domain="[('project_id', '=', timesheet_project_id),"
                "('project_id', '!=', False),"
                "('company_id', 'in', [False, company_id])]")

    @api.depends('timesheet_task_id', 'timesheet_project_id', 'time_type')
    def _compute_timesheet_generate(self):
        for leave_type in self:
            leave_type.timesheet_generate = leave_type.time_type != 'other' and (not leave_type.company_id or (leave_type.timesheet_task_id and leave_type.timesheet_project_id))

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
        self._generate_timesheets()
        return super()._validate_leave_request()

    def _generate_timesheets(self, ignored_resource_calendar_leaves=None):
        """ Timesheet will be generated only if timesheet_generate is True
            If company is set, timesheet_project_id and timesheet_task_id from leave type are
            used as project_id and task_id.
            Else, internal_project_id and leave_timesheet_task_id are used.
            The generated timesheet will be attached to this project/task.
        """
        vals_list = []
        leave_ids = []
        calendar_leaves_data = self.env['resource.calendar.leaves']._read_group([('holiday_id', 'in', self.ids)], ['holiday_id'], ['id:array_agg'])
        mapped_calendar_leaves = {leave: calendar_leave_ids[0] for leave, calendar_leave_ids in calendar_leaves_data}
        for leave in self:
            if not leave.holiday_status_id.timesheet_generate:
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

            calendar = leave.employee_id.resource_calendar_id
            calendar_timezone = pytz.timezone((calendar or leave.employee_id).tz)

            if calendar.flexible_hours and (leave.request_unit_hours or leave.request_unit_half or leave.date_from.date() == leave.date_to.date()):
                leave_date = leave.date_from.astimezone(calendar_timezone).date()
                if leave.request_unit_hours:
                    hours = leave.request_hour_to - leave.request_hour_from
                elif leave.request_unit_half:
                    hours = calendar.hours_per_day / 2
                else:  # Single-day leave
                    hours = calendar.hours_per_day
                work_hours_data = [(leave_date, hours)]
            else:
                ignored_resource_calendar_leaves = ignored_resource_calendar_leaves or []
                if leave in mapped_calendar_leaves:
                    ignored_resource_calendar_leaves.append(mapped_calendar_leaves[leave])
                work_hours_data = leave.employee_id._list_work_time_per_day(
                    leave.date_from,
                    leave.date_to,
                    domain=[('id', 'not in', ignored_resource_calendar_leaves)] if ignored_resource_calendar_leaves else None)[leave.employee_id.id]

            for index, (day_date, work_hours_count) in enumerate(work_hours_data):
                vals_list.append(leave._timesheet_prepare_line_values(index, work_hours_data, day_date, work_hours_count, project, task))

        # Unlink previous timesheets to avoid doublon (shouldn't happen on the interface but meh). Necessary when the function is called to regenerate timesheets.
        old_timesheets = self.env["account.analytic.line"].sudo().search([('project_id', '!=', False), ('holiday_id', 'in', leave_ids)])
        if old_timesheets:
            old_timesheets.holiday_id = False
            old_timesheets.unlink()

        self.env['account.analytic.line'].sudo().create(vals_list)

    def _timesheet_prepare_line_values(self, index, work_hours_data, day_date, work_hours_count, project, task):
        self.ensure_one()
        return {
            'name': _("Time Off (%(index)s/%(total)s)", index=index + 1, total=len(work_hours_data)),
            'project_id': project.id,
            'task_id': task.id,
            'account_id': project.sudo().account_id.id,
            'unit_amount': work_hours_count,
            'user_id': self.employee_id.user_id.id,
            'date': day_date,
            'holiday_id': self.id,
            'employee_id': self.employee_id.id,
            'company_id': task.sudo().company_id.id or project.sudo().company_id.id,
        }

    def _check_missing_global_leave_timesheets(self):
        if not self:
            return
        min_date = min([leave.date_from for leave in self])
        max_date = max([leave.date_to for leave in self])

        global_leaves = self.env['resource.calendar.leaves'].search([
            ("resource_id", "=", False),
            ("date_to", ">=", min_date),
            ("date_from", "<=", max_date),
            ("company_id.internal_project_id", "!=", False),
            ("company_id.leave_timesheet_task_id", "!=", False),
        ])
        if global_leaves:
            global_leaves._generate_public_time_off_timesheets(self.employee_id)

    def action_refuse(self):
        """ Remove the timesheets linked to the refused holidays """
        result = super(Holidays, self).action_refuse()
        timesheets = self.sudo().mapped('timesheet_ids')
        timesheets.write({'holiday_id': False})
        timesheets.unlink()
        self._check_missing_global_leave_timesheets()
        return result

    def _action_user_cancel(self, reason):
        res = super()._action_user_cancel(reason)
        timesheets = self.sudo().timesheet_ids
        timesheets.write({'holiday_id': False})
        timesheets.unlink()
        self._check_missing_global_leave_timesheets()
        return res

    def _force_cancel(self, *args, **kwargs):
        super()._force_cancel(*args, **kwargs)
        # override this method to reevaluate timesheets after the leaves are updated via force cancel
        timesheets = self.sudo().timesheet_ids
        timesheets.holiday_id = False
        timesheets.unlink()

    def write(self, vals):
        res = super().write(vals)
        # reevaluate timesheets after the leaves are wrote in order to remove empty timesheets
        timesheet_ids_to_remove = []
        for leave in self:
            if leave.number_of_days == 0 and leave.sudo().timesheet_ids:
                leave.sudo().timesheet_ids.holiday_id = False
                timesheet_ids_to_remove.extend(leave.timesheet_ids)
        self.env['account.analytic.line'].browse(set(timesheet_ids_to_remove)).sudo().unlink()
        return res
