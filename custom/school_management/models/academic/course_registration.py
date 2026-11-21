# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class UniversityCourseRegistration(models.Model):
    _name = "university.course.registration"
    _description = "Student Course Registration (Add/Drop)"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(
        string="Registration Reference",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _("New"),
    )
    student_id = fields.Many2one(
        "university.student",
        string="Student",
        required=True,
        default=lambda self: self._default_student_id(),
        tracking=True,
    )
    program_id = fields.Many2one(
        "university.program",
        string="Major / Degree Program",
        related="student_id.program_id",
        store=True,
        readonly=True,
    )
    academic_year_id = fields.Many2one(
        "university.academic.year",
        string="Academic Year",
        required=True,
        default=lambda self: self._default_academic_year(),
    )
    semester_id = fields.Many2one(
        "university.semester",
        string="Semester",
        required=True,
        default=lambda self: self._default_semester(),
        domain="[('academic_year_id', '=', academic_year_id)]",
    )
    registration_date = fields.Date(
        string="Registration Date",
        default=fields.Date.context_today,
        readonly=True,
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("submitted", "Submitted / Validated"),
            ("approved", "Confirmed / Enrolled"),
            ("rejected", "Rejected"),
            ("cancelled", "Cancelled"),
        ],
        string="Status",
        default="draft",
        tracking=True,
    )
    line_ids = fields.One2many(
        "university.course.registration.line",
        "registration_id",
        string="Registration Items",
    )
    total_credits = fields.Integer(
        string="Total Registered Credits",
        compute="_compute_total_credits",
    )
    notes = fields.Text(string="Notes / Remarks")

    @api.model
    def _default_student_id(self):
        user = self.env.user
        student = self.env["university.student"].search([("user_id", "=", user.id)], limit=1)
        if not student and self.env.context.get("default_student_id"):
            student = self.env["university.student"].browse(self.env.context.get("default_student_id"))
        return student.id if student else False

    @api.model
    def _default_academic_year(self):
        year = self.env["university.academic.year"].search([("current", "=", True)], limit=1)
        if not year:
            year = self.env["university.academic.year"].search([], order="date_start desc", limit=1)
        return year.id if year else False

    @api.model
    def _default_semester(self):
        sem = self.env["university.semester"].search([("is_current", "=", True)], limit=1)
        if not sem:
            sem = self.env["university.semester"].search([("is_active", "=", True)], limit=1)
        return sem.id if sem else False

    @api.depends("line_ids.credits", "line_ids.action_type")
    def _compute_total_credits(self):
        for rec in self:
            add_credits = sum(line.credits for line in rec.line_ids if line.action_type == "add")
            rec.total_credits = add_credits

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = self.env["ir.sequence"].next_by_code("university.course.registration") or _("REG-%s") % fields.Date.today().strftime("%Y%m%d")
        return super().create(vals_list)

    def action_validate_eligibility(self):
        """Perform comprehensive validation: prerequisites, seats, conflicts, registration window."""
        self.ensure_one()
        today = fields.Date.context_today(self)

        # 1. Registration window check
        term = self.env["university.department.term"].search([
            ("department_id", "=", self.student_id.department_id.id),
            ("semester_id", "=", self.semester_id.id),
        ], limit=1)

        if term:
            if term.registration_start and term.registration_end:
                if not (term.registration_start <= today <= term.registration_end or
                        (term.add_drop_start and term.add_drop_end and term.add_drop_start <= today <= term.add_drop_end)):
                    self.message_post(body=_("Note: Registration submitted outside normal priority window (%s - %s).") % (
                        term.registration_start, term.registration_end
                    ))

        # 2. Check each line
        for line in self.line_ids:
            line._validate_line(self.student_id)

        self.state = "submitted"
        return True

    def action_confirm_registration(self):
        """Confirm enrollment and create/update university.enrollment records."""
        self.ensure_one()
        self.action_validate_eligibility()

        for line in self.line_ids:
            if line.validation_status != "valid":
                raise ValidationError(_("Cannot confirm registration: section '%s' has issue: %s") % (
                    line.section_id.name, line.validation_message or line.validation_status
                ))

            if line.action_type == "add":
                existing = self.env["university.enrollment"].search([
                    ("student_id", "=", self.student_id.id),
                    ("section_id", "=", line.section_id.id),
                ], limit=1)
                if not existing:
                    self.env["university.enrollment"].create({
                        "student_id": self.student_id.id,
                        "section_id": line.section_id.id,
                        "subject_id": line.section_id.subject_id.id,
                        "semester_id": line.section_id.semester_id.id,
                        "academic_year_id": line.section_id.academic_year_id.id,
                        "status": "enrolled",
                    })
                elif existing.status != "enrolled":
                    existing.write({"status": "enrolled"})
            elif line.action_type == "drop":
                existing = self.env["university.enrollment"].search([
                    ("student_id", "=", self.student_id.id),
                    ("section_id", "=", line.section_id.id),
                    ("status", "=", "enrolled"),
                ], limit=1)
                if existing:
                    existing.write({"status": "dropped"})

        self.state = "approved"
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Registration Confirmed"),
                "message": _("Successfully processed course enrollment for %s.") % self.student_id.name,
                "type": "success",
            },
        }

    def action_cancel(self):
        self.write({"state": "cancelled"})


class UniversityCourseRegistrationLine(models.Model):
    _name = "university.course.registration.line"
    _description = "Course Registration Item"
    _order = "id asc"

    registration_id = fields.Many2one(
        "university.course.registration",
        string="Registration",
        required=True,
        ondelete="cascade",
    )
    action_type = fields.Selection(
        [("add", "Add Section"), ("drop", "Drop Section")],
        string="Action",
        default="add",
        required=True,
    )
    section_id = fields.Many2one(
        "university.class.section",
        string="Class Section",
        required=True,
        domain="[('active', '=', True)]",
    )
    subject_id = fields.Many2one(
        "university.subject",
        string="Subject",
        related="section_id.subject_id",
        store=True,
        readonly=True,
    )
    teacher_id = fields.Many2one(
        "university.teacher",
        string="Instructor",
        related="section_id.teacher_id",
        store=True,
        readonly=True,
    )
    classroom_id = fields.Many2one(
        "university.classroom",
        string="Classroom",
        related="section_id.classroom_id",
        store=True,
        readonly=True,
    )
    capacity = fields.Integer(related="section_id.capacity", string="Max Capacity", readonly=True)
    available_seats = fields.Integer(related="section_id.available_seats", string="Seats Available", readonly=True)
    credits = fields.Integer(related="subject_id.credits", string="Credits", readonly=True)
    schedule_summary = fields.Char(
        string="Schedule Slot",
        compute="_compute_schedule_summary",
    )
    validation_status = fields.Selection(
        [
            ("valid", "Eligible / Clear"),
            ("full", "Section Full"),
            ("conflict", "Schedule Conflict"),
            ("prereq_missing", "Prerequisite Missing"),
            ("already_enrolled", "Already Enrolled"),
        ],
        string="Eligibility",
        default="valid",
    )
    validation_message = fields.Char(string="Validation Details")

    @api.depends("section_id.day_summary", "section_id.time_summary")
    def _compute_schedule_summary(self):
        for line in self:
            if line.section_id:
                days = line.section_id.day_summary or ""
                times = line.section_id.time_summary or ""
                line.schedule_summary = f"{days} {times}".strip() or _("TBA")
            else:
                line.schedule_summary = ""

    def _validate_line(self, student):
        self.ensure_one()
        section = self.section_id

        if self.action_type == "add":
            # 1. Capacity check
            if section.available_seats <= 0:
                self.validation_status = "full"
                self.validation_message = _("Class section is full (0 of %d seats available).") % section.capacity
                return

            # 2. Duplicate enrollment check
            enrolled = self.env["university.enrollment"].search([
                ("student_id", "=", student.id),
                ("section_id", "=", section.id),
                ("status", "=", "enrolled"),
            ], limit=1)
            if enrolled:
                self.validation_status = "already_enrolled"
                self.validation_message = _("You are already enrolled in this section.")
                return

            # 3. Prerequisite check against curriculum line
            prereq_lines = self.env["university.curriculum.line"].search([
                ("program_id", "=", student.program_id.id),
                ("subject_id", "=", section.subject_id.id),
            ], limit=1)
            if hasattr(section.subject_id, "prerequisite_ids") and section.subject_id.prerequisite_ids:
                missing_prereqs = []
                for prereq in section.subject_id.prerequisite_ids:
                    passed = self.env["university.report.card.line"].search([
                        ("student_id", "=", student.id),
                        ("subject_id", "=", prereq.id),
                        ("is_passing", "=", True),
                    ], limit=1)
                    if not passed:
                        missing_prereqs.append(prereq.name)
                if missing_prereqs:
                    self.validation_status = "prereq_missing"
                    self.validation_message = _("Missing prerequisites: %s") % ", ".join(missing_prereqs)
                    return

            # 4. Schedule conflict check against student's existing enrolled sections
            other_sections = self.env["university.enrollment"].search([
                ("student_id", "=", student.id),
                ("status", "=", "enrolled"),
                ("section_id", "!=", section.id),
                ("semester_id", "=", section.semester_id.id),
            ]).mapped("section_id")

            my_lines = section.schedule_line_ids.filtered(lambda l: l.active)
            has_conflict = False
            conflict_info = ""
            for other_sec in other_sections:
                other_lines = other_sec.schedule_line_ids.filtered(lambda l: l.active)
                for ml in my_lines:
                    for ol in other_lines:
                        if ml.weekday == ol.weekday:
                            if ml.timeslot_id and ol.timeslot_id:
                                if ml.timeslot_id == ol.timeslot_id or (
                                    ml.timeslot_id.start_hour < ol.timeslot_id.end_hour and
                                    ml.timeslot_id.end_hour > ol.timeslot_id.start_hour
                                ):
                                    has_conflict = True
                                    conflict_info = _("Conflicts with %s on %s (%s)") % (
                                        other_sec.name, ml.weekday, ml.timeslot_id.name or ""
                                    )
                                    break
                    if has_conflict:
                        break
                if has_conflict:
                    break

            if has_conflict:
                self.validation_status = "conflict"
                self.validation_message = conflict_info
                return

        self.validation_status = "valid"
        self.validation_message = _("Section eligible for registration.")
