# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields
from odoo import api # TODO remove


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

    def _get_default_status(self):
        if self.employee_id.company_id.attendance_overtime_validation != 'by_manager':
            return 'approved'
        return 'to_approve'


    employee_id = fields.Many2one(
        'hr.employee', string="Employee",
        required=True, ondelete='cascade', index=True)
    company_id = fields.Many2one(related='employee_id.company_id')

    date = fields.Date(string='Day', index=True, required=True)
    status = fields.Selection([
            ('to_approve', "To Approve"),
            ('approved', "Approved"),
            ('refused', "Refused")
        ], 
        required=True,
        default=_get_default_status,
    )
    duration = fields.Float(string='Extra Hours', default=0.0, required=True)
    manual_duration = fields.Float(
        string='Extra Hours (encoded)',
        compute='_compute_manual_duration',
        store=True, readonly=False,
    )
    # duration_real = fields.Float(
    #     string='Extra Hours (Real)', default=0.0,
    #     help="Extra-hours including the threshold duration")
    # adjustment = fields.Boolean(default=False)

    time_start = fields.Datetime(string='Start', required=True)
    time_stop = fields.Datetime(string='Stop', required=True)
    amount_rate = fields.Float("Overtime pay rate", required=True, default=1.0)

    is_manager = fields.Boolean(compute="_compute_is_manager")

    # TODO overkill?
    rule_ids = fields.Many2many("hr.attendance.overtime.rule")
    # TODO remove (debug only)
    rules_display = fields.Char(compute='_compute_rules_display')

    @api.depends('rule_ids')
    def _compute_rules_display(self):
        for line in self:
            line.rules_display = '|'.join(line.rule_ids.mapped('name'))

    @api.depends('duration')
    def _compute_manual_duration(self):
        for overtime in self:
            overtime.manual_duration = overtime.duration

    @api.depends('employee_id')
    def _compute_overtime_status(self):
        for overtime in self:
            if not overtime.status:
                overtime.status = 'to_approve' if overtime.employee_id.company_id.attendance_overtime_validation == 'by_manager' else 'approved'

    @api.depends('employee_id')
    def _compute_is_manager(self):
        has_manager_right = self.env.user.has_group('hr_attendance.group_hr_attendance_manager')
        has_officer_right = self.env.user.has_group('hr_attendance.group_hr_attendance_officer')
        for overtime in self:
            overtime.is_manager = (
                has_manager_right or 
                (
                    has_officer_right 
                    and overtime.employee_id.attendance_maneger_id == self.env.user
                )
            )

    def action_approve(self):
        self.write({'status': 'approved'})

    def action_refuse(self):
        self.write({'status': 'refused'})

    # in payroll: rate, work_entry_type
    # in time_off: convertible_to_time_off

    # Check no overlapping overtimes for the same employee.
    # Technical explanation: Exclude constraints compares the given expression on rows 2 by 2 using the given operator; && on tsrange is the intersection.
    # cf: https://www.postgresql.org/docs/current/ddl-constraints.html#DDL-CONSTRAINTS-EXCLUSION
    # for employee_id we compare [employee_id -> employee_id] ranges bc raw integer is not supported (?)
    _overtime_no_overlap_same_employee = models.Constraint("""
        EXCLUDE USING GIST (
            tsrange(time_start, time_stop, '()') WITH &&,
            int4range(employee_id, employee_id, '[]') WITH = 
        )
        """,
        "Employee cannot have overlapping overtimes",
    )
    _overtime_start_before_end = models.Constraint(
        'CHECK (time_stop > time_start)',
        'Starting time should be before end time.',
    )
