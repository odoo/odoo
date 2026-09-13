from odoo import api, fields, models


class HrAttendanceOvertimeLine(models.Model):
    _name = "hr.attendance.overtime.line"
    _description = "Attendance Overtime Line"
    _rec_name = "employee_id"
    _order = "time_start"

    attendance_id = fields.Many2one(
        comodel_name="hr.attendance",
        index=True,
        ondelete="cascade",
    )
    employee_id = fields.Many2one(
        comodel_name="hr.employee",
        index=True,
        required=True,
        ondelete="cascade",
    )
    company_id = fields.Many2one(related="employee_id.company_id")

    date = fields.Date(
        string="Day",
        index=True,
        required=True,
    )
    status = fields.Selection(
        selection=[
            ("to_approve", "To Approve"),
            ("approved", "Approved"),
            ("refused", "Refused"),
        ],
        compute="_compute_status",
        precompute=True,
        store=True,
        readonly=False,
        required=True,
    )
    duration = fields.Float(
        string="Extra Hours",
        default=0.0,
        required=True,
    )
    manual_duration = fields.Float(
        string="Extra Hours (encoded)",
        compute="_compute_manual_duration",
        store=True,
        readonly=False,
    )

    time_start = fields.Datetime(string="Start")
    time_stop = fields.Datetime(string="Stop")
    amount_rate = fields.Float(
        string="Overtime pay rate",
        default=1.0,
        required=True,
    )

    is_manager = fields.Boolean(compute="_compute_is_manager")

    rule_ids = fields.Many2many(
        comodel_name="hr.attendance.overtime.rule",
        string="Applied Rules",
    )

    _overtime_start_before_end = models.Constraint(
        "CHECK (time_stop > time_start)",
        "Starting time should be before end time.",
    )

    @api.depends("employee_id")
    def _compute_status(self):
        for overtime in self:
            if not overtime.status:
                overtime.status = (
                    "to_approve"
                    if overtime.employee_id.company_id.attendance_overtime_validation
                    == "by_manager"
                    else "approved"
                )

    @api.depends("duration")
    def _compute_manual_duration(self):
        for overtime in self:
            overtime.manual_duration = overtime.duration

    @api.depends("employee_id")
    def _compute_is_manager(self):
        # The same verdict `hr.attendance.is_manager` gives: "manage all
        # attendances" approves anyone's, an officer approves their own
        # employees'. The two used to disagree, and the line's approve button
        # hid from a user whose attendance-level button was shown.
        has_all_right = self.env.user.has_group(
            "hr_attendance.group_hr_attendance_user"
        )
        has_officer_right = self.env.user.has_group(
            "hr_attendance.group_hr_attendance_officer"
        )
        for overtime in self:
            overtime.is_manager = has_all_right or (
                has_officer_right
                and overtime.employee_id.attendance_manager_id == self.env.user
            )

    def _regeneration_key(self):
        """Identity of an overtime line across a regeneration.

        Two lines with the same key describe the same overtime: the same
        attendance, day, set of rules and computed amount. A manager's
        decision on one carries to the other; a change to any part of the key
        makes it a different line that starts from its default status.
        """
        self.check_singleton()
        return (
            self.attendance_id.id,
            self.date,
            tuple(sorted(self.rule_ids.ids)),
            round(self.duration, 3),
        )

    @api.model
    def _regeneration_key_from_vals(self, vals):
        return (
            vals.get("attendance_id"),
            vals.get("date"),
            tuple(sorted(vals.get("rule_ids") or ())),
            round(vals.get("duration") or 0.0, 3),
        )

    def action_approve(self):
        self.write({"status": "approved"})

    def action_refuse(self):
        self.write({"status": "refused"})

    def _linked_attendances(self):
        return self.attendance_id
