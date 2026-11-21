from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError


class UniversityServiceHour(models.Model):
    _name = "university.service.hour"
    _description = "Service Hour"
    _order = "create_date desc"
    # _inherit = ['mail.theard','mail.activity.mixin']

    name = fields.Char(
        string="Title",
        required=True,
        default="Service Activity",
    )
    student_id = fields.Many2one(
        "university.student",
        string="Student",
        required=True,
    )
    teacher_id = fields.Many2one(
        "university.teacher",
        string="Supervisor",
        required=True,
    )
    start_time = fields.Datetime(
        string="Start Time",
    )
    end_time = fields.Datetime(
        string="End Time",
    )
    date = fields.Date(
        string="Date",
        required=True,
        default=fields.Date.context_today,
    )
    academic_year_id = fields.Many2one(
        "university.academic.year",
        string="Academic Year",
    )
    semester_id = fields.Many2one(
        "university.semester",
        string="Semester",
        domain="[('academic_year_id', '=', academic_year_id)]",
    )
    hours = fields.Float(
        string="Total Hours",
        required=True,
        default=1.0,
    )
    description = fields.Text(
        string="Description",
    )
    state = fields.Selection(
        [("pending", "Pending"), ("approved", "Approved"), ("rejected", "Rejected")],
        string="Status",
        default="pending",
    )

    approved_by = fields.Many2one(
        "res.users",
        string="Approved By",
        readonly=True,
        copy=False,
    )
    approved_date = fields.Date(
        string="Approved Date",
        readonly=True,
        copy=False,
    )

    @api.onchange("start_time", "end_time")
    def _onchange_time_range(self):
        if self.start_time and self.end_time:
            if self.end_time > self.start_time:
                diff = (self.end_time - self.start_time).total_seconds() / 3600.0
                self.hours = round(diff, 2)
            if not self.date:
                self.date = self.start_time.date()
        elif self.start_time and not self.date:
            self.date = self.start_time.date()

    @api.constrains("hours")
    def _check_hours(self):
        for service_hour in self:
            if service_hour.hours <= 0:
                raise ValidationError(_("Service hours must be greater than zero."))

    @api.constrains("start_time", "end_time")
    def _check_time_range(self):
        for service_hour in self:
            if service_hour.start_time and service_hour.end_time and service_hour.end_time < service_hour.start_time:
                raise ValidationError(_("End Time must be after Start Time."))

    @api.constrains("semester_id", "academic_year_id")
    def _check_period(self):
        for service_hour in self:
            if (
                service_hour.semester_id
                and service_hour.academic_year_id
                and service_hour.semester_id.academic_year_id != service_hour.academic_year_id
            ):
                raise ValidationError(_("The semester must belong to the selected academic year."))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name"):
                vals["name"] = _("Service Activity")
            if vals.get("start_time") and not vals.get("date"):
                st = fields.Datetime.to_datetime(vals["start_time"])
                if st:
                    vals["date"] = st.date()
            if vals.get("start_time") and vals.get("end_time") and ("hours" not in vals or not vals.get("hours")):
                st = fields.Datetime.to_datetime(vals["start_time"])
                et = fields.Datetime.to_datetime(vals["end_time"])
                if st and et and et > st:
                    vals["hours"] = round((et - st).total_seconds() / 3600.0, 2)

        if not self.env.su and self.env.user.has_group("school_management.group_school_student"):
            student = self.env.user.student_id
            for vals in vals_list:
                if not student or vals.get("student_id") != student.id:
                    raise AccessError(_("Students can only submit service hours for themselves."))
        return super().create(vals_list)

    def write(self, vals):
        if not self.env.su and self.env.user.has_group("school_management.group_school_student"):
            student = self.env.user.student_id
            if any(record.student_id != student for record in self):
                raise AccessError(_("Students can only edit their own service hours."))
            if any(record.state != "pending" for record in self):
                raise AccessError(_("Only pending service-hour requests can be edited."))
            if vals.get("student_id") and vals["student_id"] != student.id:
                raise AccessError(_("Students cannot assign service hours to another student."))
            if any(key in vals for key in ("state", "approved_by", "approved_date")):
                raise AccessError(_("Students cannot approve or reject service hours."))
        return super().write(vals)

    def _check_approval_access(self):
        if (
            self.env.su
            or self.env.user.has_group("school_management.group_school_admin")
            or self.env.user.has_group("base.group_system")
        ):
            return
        if not self.env.user.has_group("school_management.group_school_teacher"):
            raise AccessError(_("Only an administrator or supervisor can approve service hours."))
        if any(record.teacher_id.user_id != self.env.user for record in self):
            raise AccessError(_("A supervisor can approve only their assigned service hours."))

    def action_approve(self):
        self._check_approval_access()
        if any(record.state != "pending" for record in self):
            raise ValidationError(_("Only pending service hours can be approved."))
        self.write({
            "state": "approved",
            "approved_by": self.env.user.id,
            "approved_date": fields.Date.context_today(self),
        })

    def action_reject(self):
        self._check_approval_access()
        if any(record.state != "pending" for record in self):
            raise ValidationError(_("Only pending service hours can be rejected."))
        self.write({
            "state": "rejected",
            "approved_by": self.env.user.id,
            "approved_date": fields.Date.context_today(self),
        })

    def action_reset_pending(self):
        self._check_approval_access()
        self.write({
            "state": "pending",
            "approved_by": False,
            "approved_date": False,
        })
