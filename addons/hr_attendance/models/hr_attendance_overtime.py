# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class HrAttendanceOvertime(models.Model):
    _name = 'hr.attendance.overtime'
    _description = "Attendance Overtime"
    _rec_name = 'employee_id'
    _order = 'date desc'

    def _default_employee(self):
        return self.env.user.employee_id

    employee_id = fields.Many2one(
        'hr.employee', string="Employee", default=_default_employee,
        required=True, ondelete='cascade', index=True)
    company_id = fields.Many2one(related='employee_id.company_id')

    date = fields.Date(string='Day', index=True, required=True)
    duration = fields.Float(string='Extra Hours', default=0.0, required=True)
    duration_real = fields.Float(
        string='Extra Hours (Real)', default=0.0,
        help="Extra-hours including the threshold duration")
    adjustment = fields.Boolean(default=False)

    # Allows only 1 overtime record per employee per day unless it's an adjustment
    _unique_employee_per_day = models.UniqueIndex("(employee_id, date) WHERE adjustment IS NOT TRUE")

class HrAttendanceOvertimeLine(models.Model):
    _name = 'hr.attendance.overtime.line'
    _description = "Attendance Overtime Line"
    _rec_name = 'employee_id'
    _order = 'time_start'

    employee_id = fields.Many2one(
        'hr.employee', string="Employee",
        required=True, ondelete='cascade', index=True)
    company_id = fields.Many2one(related='employee_id.company_id')

    date = fields.Date(string='Day', index=True, required=True)
    duration = fields.Float(string='Extra Hours', default=0.0, required=True)
    duration_real = fields.Float(
        string='Extra Hours (Real)', default=0.0,
        help="Extra-hours including the threshold duration")
    adjustment = fields.Boolean(default=False)

    time_start = fields.Datetime(string='Start', required=True)
    time_stop = fields.Datetime(string='Stop', required=True)
    # in payroll: rate, work_entry_type
    # in time_off: convertible_to_time_off

    # Allows only 1 overtime record per employee per day unless it's an adjustment
    #_unique_employee_per_day = models.UniqueIndex("(employee_id, date) WHERE adjustment IS NOT TRUE")

    # Check no overlapping overtimes for the same employee.
    # Technical explanation: Exclude constraints compares the given expression on rows 2 by 2 using the given operator; && on tsrange is the intersection.
    # cf: https://www.postgresql.org/docs/current/ddl-constraints.html#DDL-CONSTRAINTS-EXCLUSION
    # for employee_id we compare [employee_id -> employee_id] ranges bc raw integer is not supported (?)
    _overtime_no_overlap_same_employee = models.Constraint("""
        EXCLUDE USING GIST (
            tsrange(time_start, time_stop) WITH &&,
            int4range(employee_id, employee_id, '[]') WITH = 
        )
        """,
        "Employee cannot have overlapping overtimes",
    )
    _overtime_start_before_end = models.Constraint(
        'CHECK (time_stop > time_start)',
        'Starting time should be before end time.',
    )
