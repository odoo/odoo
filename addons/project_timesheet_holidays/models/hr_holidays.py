# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class HrLeave(models.Model):
    _inherit = "hr.leave"

    timesheet_ids = fields.One2many('account.analytic.line', 'holiday_id', string="Analytic Lines")

    def _validate_leave_request(self):
        """ Timesheet will be generated on leave validation
            internal_project_id and leave_timesheet_task_id are used.
            The generated timesheet will be attached to this project/task.
        """
        vals_list = []
        leave_ids = []
        for leave in self:
            project, task = leave.employee_id.company_id.internal_project_id, leave.employee_id.company_id.leave_timesheet_task_id

            if not project or not task:
                continue

            leave_ids.append(leave.id)
            if not leave.employee_id:
                continue

            work_hours_data = leave.employee_id._list_work_time_per_day(
                leave.date_from,
                leave.date_to)[leave.employee_id.id]

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
        result = super().action_refuse()
        timesheets = self.sudo().timesheet_ids
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
