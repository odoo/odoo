from odoo import _, api, fields, models
from odoo.exceptions import AccessError


class UniversityStudentAdvisingNote(models.Model):
    _name = "university.student.advising.note"
    _description = "Student Advising Note"
    _order = "date desc, id desc"

    student_id = fields.Many2one(
        "university.student",
        string="Student",
        required=True,
        ondelete="cascade",
        index=True,
    )
    advisor_id = fields.Many2one(
        "university.teacher",
        string="Advisor / Author",
        required=True,
        index=True,
        default=lambda self: self.env.user.teacher_id,
    )
    user_id = fields.Many2one(
        "res.users",
        string="Created By",
        default=lambda self: self.env.user,
        readonly=True,
        index=True,
    )
    date = fields.Date(
        string="Date",
        default=fields.Date.context_today,
        required=True,
    )
    category = fields.Selection(
        [
            ("academic", "Academic Performance"),
            ("attendance", "Attendance & Discipline"),
            ("career", "Career & Guidance"),
            ("personal", "General / Wellbeing"),
        ],
        string="Category",
        default="academic",
        required=True,
    )
    note = fields.Text(string="Note Content", required=True)
    is_private = fields.Boolean(
        string="Private Note",
        default=False,
        help="Private notes are confidential and only visible to the authoring advisor and university administrator.",
    )
    department_id = fields.Many2one(
        "university.department",
        string="Department",
        related="student_id.department_id",
        store=True,
        index=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        is_admin = self.env.su or self.env.user.has_group("school_management.group_school_admin")
        is_teacher = self.env.user.has_group("school_management.group_school_teacher")
        for vals in vals_list:
            teacher = self.env.user.teacher_id or self.env["university.teacher"].sudo().search([("user_id", "=", self.env.user.id)], limit=1)
            if not vals.get("advisor_id") and teacher:
                vals["advisor_id"] = teacher.id
            if not vals.get("user_id"):
                vals["user_id"] = self.env.user.id
            if is_teacher and not is_admin:
                student_id = vals.get("student_id")
                if student_id:
                    student = self.env["university.student"].browse(student_id)
                    is_advisee = bool(teacher and student.advisor_id == teacher)
                    is_in_class = bool(teacher and student.enrollment_ids.filtered(lambda e: e.section_id.teacher_id == teacher))
                    if not is_advisee and not is_in_class:
                        raise AccessError(_("You may only record advising notes for your assigned advisees or students in your classes."))
        return super().create(vals_list)

    def write(self, vals):
        is_admin = self.env.su or self.env.user.has_group("school_management.group_school_admin")
        for rec in self:
            if not is_admin and rec.user_id != self.env.user:
                raise AccessError(_("You are not authorized to modify another advisor's notes."))
        return super().write(vals)

    def unlink(self):
        is_admin = self.env.su or self.env.user.has_group("school_management.group_school_admin")
        for rec in self:
            if not is_admin and rec.user_id != self.env.user:
                raise AccessError(_("You can only delete your own advising notes."))
        return super().unlink()


class UniversityStudentFollowup(models.Model):
    _name = "university.student.followup"
    _description = "Student Advising Follow-up"
    _order = "date_deadline asc, id desc"

    student_id = fields.Many2one(
        "university.student",
        string="Student",
        required=True,
        ondelete="cascade",
        index=True,
    )
    advisor_id = fields.Many2one(
        "university.teacher",
        string="Advisor",
        required=True,
        index=True,
        default=lambda self: self.env.user.teacher_id,
    )
    title = fields.Char(string="Action Title", required=True)
    description = fields.Text(string="Description")
    action_type = fields.Selection(
        [
            ("meeting", "Advising Meeting"),
            ("tutoring", "Academic Tutoring"),
            ("attendance_check", "Attendance Review"),
            ("assignment_catchup", "Assignment Catch-up"),
            ("warning", "Academic Warning"),
            ("other", "Other Action"),
        ],
        string="Action Type",
        default="meeting",
        required=True,
    )
    date_deadline = fields.Date(string="Due Date", index=True)
    state = fields.Selection(
        [
            ("pending", "Pending"),
            ("in_progress", "In Progress"),
            ("completed", "Completed"),
            ("cancelled", "Cancelled"),
        ],
        string="Status",
        default="pending",
        required=True,
        index=True,
    )
    visible_to_student = fields.Boolean(
        string="Visible to Student",
        default=True,
        help="If checked, this follow-up action is visible on the student's personal dashboard.",
    )
    department_id = fields.Many2one(
        "university.department",
        string="Department",
        related="student_id.department_id",
        store=True,
        index=True,
    )

    def action_start(self):
        self.write({"state": "in_progress"})

    def action_complete(self):
        self.write({"state": "completed"})

    def action_cancel(self):
        self.write({"state": "cancelled"})

    def action_reset(self):
        self.write({"state": "pending"})

    def unlink(self):
        user = self.env.user
        is_admin = (
            user.has_group("school_management.group_school_admin")
            or user.has_group("base.group_system")
            or self.env.su
        )
        is_hod = user.has_group("school_management.group_school_hod")
        for rec in self:
            if not is_admin and not is_hod:
                raise AccessError(_("You are not allowed to delete follow-up actions. Only Administrators and Department Heads can delete follow-up actions."))
            if is_hod and not is_admin:
                hod_user_id = rec.department_id.head_id.user_id.id if rec.department_id.head_id else False
                hod_teacher_id = rec.department_id.head_id.id if rec.department_id.head_id else False
                if hod_user_id != user.id and (not user.teacher_id or hod_teacher_id != user.teacher_id.id):
                    raise AccessError(_("Department Heads can only delete follow-up actions for students in their own department."))
        return super().unlink()
