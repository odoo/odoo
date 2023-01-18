# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class Department(models.Model):

    _inherit = 'hr.department'

    absence_of_today = fields.Integer(
        compute='_compute_leave_count', string='Absence by Today')
    leave_to_approve_count = fields.Integer(
        compute='_compute_leave_count', string='Time Off to Approve')
    allocation_to_approve_count = fields.Integer(
        compute='_compute_leave_count', string='Allocation to Approve')

    def _compute_leave_count(self):
        Requests = self.env['hr.leave']
        Allocations = self.env['hr.leave.allocation']
        today_date = datetime.datetime.utcnow().date()
        today_start = fields.Datetime.to_string(today_date)  # get the midnight of the current utc day
        today_end = fields.Datetime.to_string(today_date + relativedelta(hours=23, minutes=59, seconds=59))

        leave_data = Requests._aggregate(
            [('department_id', 'in', self.ids),
             ('state', '=', 'confirm')],
            ['*:count'], ['department_id'])
        allocation_data = Allocations._aggregate(
            [('department_id', 'in', self.ids),
             ('state', '=', 'confirm')],
            ['*:count'], ['department_id'])
        absence_data = Requests._aggregate(
            [('department_id', 'in', self.ids), ('state', 'not in', ['cancel', 'refuse']),
             ('date_from', '<=', today_end), ('date_to', '>=', today_start)],
            ['*:count'], ['department_id'])

        for department in self:
            department.leave_to_approve_count = leave_data.get_agg(department.id, '*:count', 0)
            department.allocation_to_approve_count = allocation_data.get_agg(department.id, '*:count', 0)
            department.absence_of_today = absence_data.get_agg(department.id, '*:count', 0)

    def _get_action_context(self):
        return {
            'search_default_approve': 1,
            'search_default_active_employee': 2,
            'search_default_department_id': self.id,
            'default_department_id': self.id,
        }

    def action_open_leave_department(self):
        action = self.env["ir.actions.actions"]._for_xml_id("hr_holidays.hr_leave_action_action_approve_department")
        action['context'] = {
            **self._get_action_context(),
            'search_default_active_time_off': 3,
            'hide_employee_name': 1,
            'holiday_status_name_get': False
        }
        return action

    def action_open_allocation_department(self):
        action = self.env["ir.actions.actions"]._for_xml_id("hr_holidays.hr_leave_allocation_action_approve_department")
        action['context'] = self._get_action_context()
        action['context']['search_default_second_approval'] = 3
        return action
