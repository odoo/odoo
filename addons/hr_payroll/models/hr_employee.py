# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from dateutil.relativedelta import relativedelta
import pytz

from odoo import api, fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'
    _description = 'Employee'

    slip_ids = fields.One2many('hr.payslip', 'employee_id', string='Payslips', readonly=True)
    payslip_count = fields.Integer(compute='_compute_payslip_count', string='Payslip Count', groups="hr_payroll.group_hr_payroll_user")

    @api.multi
    def _compute_payslip_count(self):
        for employee in self:
            employee.payslip_count = len(employee.slip_ids)


    @api.multi
    def generate_benefit(self, date_start, date_stop):
        date_start = fields.Datetime.to_datetime(date_start) + relativedelta(hour=0, minute=0, second=0)
        date_stop = fields.Datetime.to_datetime(date_stop) + relativedelta(hour=23, minute=59, second=59)
        attendance_type = self.env.ref('hr_payroll.benefit_type_attendance')
        vals_list = []

        for employee in self:
            # Approved leaves
            emp_leaves = employee.resource_calendar_id.leave_ids.filtered(
                lambda r:
                    r.resource_id == employee.resource_id and
                    r.date_from <= date_stop and
                    r.date_to >= date_start
                )
            global_leaves = employee.resource_calendar_id.global_leave_ids

            employee_leaves = (emp_leaves | global_leaves).mapped('holiday_id')
            vals_list.extend(employee_leaves._get_benefits_values())

            for contract in employee._get_contracts(date_start, date_stop):
                date_start_benefits = max(date_start, fields.Datetime.to_datetime(contract.date_start)).replace(tzinfo=pytz.utc)
                date_stop_benefits = min(date_stop, datetime.combine(contract.date_end or datetime.max.date(), datetime.max.time())).replace(tzinfo=pytz.utc)

                calendar = contract.resource_calendar_id
                resource = employee.resource_id
                attendances = calendar._work_intervals(date_start_benefits, date_stop_benefits, resource=resource)
                # Attendances
                for interval in attendances:
                    benefit_type_id = interval[2].mapped('benefit_type_id')[:1] or attendance_type
                    # All benefits generated here are using datetimes converted from the employee's timezone
                    vals_list += [{
                        'name': "%s: %s" % (benefit_type_id.name, employee.name),
                        'date_start': interval[0].astimezone(pytz.utc).replace(tzinfo=None),
                        'date_stop': interval[1].astimezone(pytz.utc).replace(tzinfo=None),
                        'benefit_type_id': benefit_type_id.id,
                        'employee_id': employee.id,
                        'state': 'confirmed',
                    }]

        new_benefits = self.env['hr.benefit']._safe_duplicate_create(vals_list, date_start, date_stop)
        new_benefits._compute_conflicts_leaves_to_approve()
