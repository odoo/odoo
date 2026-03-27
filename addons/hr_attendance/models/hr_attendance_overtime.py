# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields


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
    status = fields.Selection([
            ('to_approve', "To Approve"),
            ('approved', "Approved"),
            ('refused', "Refused")
        ],
        compute='_compute_status',
        required=True, store=True, readonly=False, precompute=True,
    )
    duration = fields.Float(string='Extra Hours', default=0.0, required=True)
    manual_duration = fields.Float(  # TODO -> real_duration for easier upgrade
        string='Extra Hours (encoded)',
        compute='_compute_manual_duration',
        store=True, readonly=False,
    )

    time_start = fields.Datetime(string='Start')  # time_start will be equal to attendance.check_in
    time_stop = fields.Datetime(string='Stop')  # time_stop will be equal to attendance.check_out
    amount_rate = fields.Float("Overtime pay rate", required=True, default=1.0)

    is_manager = fields.Boolean(compute="_compute_is_manager")

    rule_ids = fields.Many2many("hr.attendance.overtime.rule", string="Applied Rules")

    # in payroll: rate, work_entry_type
    # in time_off: convertible_to_time_off

    # Check no overlapping overtimes for the same employee.
    # Technical explanation: Exclude constraints compares the given expression on rows 2 by 2 using the given operator; && on tsrange is the intersection.
    # cf: https://www.postgresql.org/docs/current/ddl-constraints.html#DDL-CONSTRAINTS-EXCLUSION
    # for employee_id we compare [employee_id -> employee_id] ranges bc raw integer is not supported (?)
    # _overtime_no_overlap_same_employee = models.Constraint("""
    #     EXCLUDE USING GIST (
    #         tsrange(time_start, time_stop, '()') WITH &&,
    #         int4range(employee_id, employee_id, '[]') WITH =
    #     )
    #     """,
    #     "Employee cannot have overlapping overtimes",
    # )
    _overtime_start_before_end = models.Constraint(
        'CHECK (time_stop > time_start)',
        'Starting time should be before end time.',
    )

    @api.depends('employee_id')
    def _compute_status(self):
        for overtime in self:
            if not overtime.status:
                overtime.status = 'to_approve' if overtime.employee_id.company_id.attendance_overtime_validation == 'by_manager' else 'approved'

    @api.depends('duration')
    def _compute_manual_duration(self):
        for overtime in self:
            overtime.manual_duration = overtime.duration

    @api.depends('employee_id')
    def _compute_is_manager(self):
        has_manager_right = self.env.user.has_group('hr_attendance.group_hr_attendance_manager')
        has_officer_right = self.env.user.has_group('hr_attendance.group_hr_attendance_officer')
        for overtime in self:
            overtime.is_manager = (
                has_manager_right or
                (
                    has_officer_right
                    and overtime.employee_id.attendance_manager_id == self.env.user
                )
            )

    def action_approve(self):
        self.write({'status': 'approved'})

    def action_refuse(self):
        self.write({'status': 'refused'})

    def _linked_attendances(self):
        return self.env['hr.attendance'].search([
            ('check_in', 'in', self.mapped('time_start')),
            ('employee_id', 'in', self.employee_id.ids),
        ])

    def write(self, vals):
        if any(key in vals for key in ['status', 'manual_duration']):
            attendances = self._linked_attendances()
            self.env.add_to_compute(
                 attendances._fields['overtime_status'],
                 attendances
            )
            self.env.add_to_compute(
                 attendances._fields['validated_overtime_hours'],
                 attendances
            )
        return super().write(vals)
