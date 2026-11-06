from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from ..academic.academic_lock import can_maintain_closed_year_records


class UniversityEnrollment(models.Model):
    _name = "university.enrollment"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "University Enrollment"
    _order = "enrollment_date desc, id desc"

    _student_class_section_unique = models.Constraint(
        "UNIQUE (student_id, class_section_id)",
        "This student is already enrolled in this class section.",
    )

    student_id = fields.Many2one(
        "university.student",
        string="Student",
        required=True,
        index=True,
        domain="[('active', '=', True), ('status', '=', 'active')]",
        tracking=True,
    )
    class_section_id = fields.Many2one(
        "university.class.section",
        string="Class Section",
        index=True,
        domain="[('active', '=', True)]",
        tracking=True,
    )
    section_id = fields.Many2one(
        "university.class.section",
        string="Class Section (Legacy)",
        compute="_compute_section_id",
        inverse="_inverse_section_id",
        store=True,
        index=True,
    )

    program_id = fields.Many2one(
        "university.program",
        string="Major / Program",
        compute="_compute_derived_fields",
        store=True,
        readonly=True,
        index=True,
    )
    department_id = fields.Many2one(
        "university.department",
        string="Department",
        compute="_compute_derived_fields",
        store=True,
        readonly=True,
        index=True,
    )
    faculty_id = fields.Many2one(
        "university.faculty",
        string="Faculty",
        compute="_compute_derived_fields",
        store=True,
        readonly=True,
        index=True,
    )
    subject_id = fields.Many2one(
        "university.subject",
        string="Subject",
        compute="_compute_derived_fields",
        store=True,
        readonly=True,
        index=True,
    )
    instructor_id = fields.Many2one(
        "university.teacher",
        string="Instructor",
        compute="_compute_derived_fields",
        store=True,
        readonly=True,
        index=True,
    )
    teacher_id = fields.Many2one(
        "university.teacher",
        string="Instructor (Legacy)",
        compute="_compute_derived_fields",
        store=True,
        readonly=True,
    )
    semester_id = fields.Many2one(
        "university.semester",
        string="Semester",
        compute="_compute_derived_fields",
        store=True,
        readonly=True,
        index=True,
    )
    academic_year_id = fields.Many2one(
        "university.academic.year",
        string="Academic Year",
        compute="_compute_derived_fields",
        store=True,
        readonly=True,
        index=True,
    )

    enrollment_date = fields.Date(
        string="Enrollment Date",
        default=fields.Date.context_today,
        required=True,
        tracking=True,
    )
    status = fields.Selection(
        [
            ("draft", "Draft"),
            ("enrolled", "Enrolled"),
            ("completed", "Completed"),
            ("dropped", "Dropped"),
            ("to_approve", "To Approve"),
            ("withdrawn", "Withdrawn"),
        ],
        string="Status",
        default="draft",
        required=True,
        tracking=True,
    )
    pending_change = fields.Json(
        string="Pending Change",
        copy=False,
        readonly=True,
    )
    possible_duplicate = fields.Boolean(
        string="Possible Duplicate",
        compute="_compute_possible_duplicate",
        search="_search_possible_duplicate",
    )

    @api.depends("class_section_id")
    def _compute_section_id(self):
        for rec in self:
            rec.section_id = rec.class_section_id

    def _inverse_section_id(self):
        for rec in self:
            if rec.section_id and not rec.class_section_id:
                rec.class_section_id = rec.section_id

    @api.depends(
        "class_section_id",
        "class_section_id.subject_id",
        "class_section_id.subject_id.department_id",
        "class_section_id.subject_id.program_ids",
        "class_section_id.teacher_id",
        "class_section_id.semester_id",
        "class_section_id.semester_id.academic_year_id",
        "class_section_id.program_id",
        "class_section_id.program_id.department_id",
        "student_id",
        "student_id.program_id",
        "student_id.department_id",
    )
    def _compute_derived_fields(self):
        for rec in self:
            section = rec.class_section_id
            student = rec.student_id

            if section:
                subject = section.subject_id
                instructor = section.teacher_id
                semester = section.semester_id
                year = semester.academic_year_id if semester else False

                program = False
                if section.program_id:
                    program = section.program_id
                elif student and student.program_id:
                    program = student.program_id
                elif subject and subject.program_ids:
                    program = subject.program_ids[0]

                dept = False
                if subject and subject.department_id:
                    dept = subject.department_id
                elif program and program.department_id:
                    dept = program.department_id
                elif student and student.department_id:
                    dept = student.department_id

                faculty = dept.faculty_id if dept else False

                rec.subject_id = subject
                rec.instructor_id = instructor
                rec.teacher_id = instructor
                rec.semester_id = semester
                rec.academic_year_id = year
                rec.program_id = program
                rec.department_id = dept
                rec.faculty_id = faculty
            else:
                # Sectionless enrollment (e.g. major registration wizard)
                if not rec.program_id and student and student.program_id:
                    rec.program_id = student.program_id
                dept = rec.program_id.department_id if rec.program_id else (student.department_id if student else False)
                rec.department_id = dept
                rec.faculty_id = dept.faculty_id if dept else False
                if rec.semester_id and not rec.academic_year_id:
                    rec.academic_year_id = rec.semester_id.academic_year_id

    @api.onchange("class_section_id", "student_id")
    def _onchange_class_section_or_student(self):
        self._compute_derived_fields()
        if self.student_id and self.class_section_id and self.class_section_id.semester_id:
            semester = self.class_section_id.semester_id
            other_enrollments = self.env["university.enrollment"].search([
                ("id", "!=", self.id or 0),
                ("student_id", "=", self.student_id.id),
                ("class_section_id", "!=", self.class_section_id.id),
                ("class_section_id", "!=", False),
                ("status", "in", ("draft", "enrolled")),
            ])
            other_sections = other_enrollments.mapped("class_section_id").filtered(
                lambda s: s.semester_id == semester
            )
            my_lines = self.class_section_id.schedule_line_ids.filtered("active")
            for other_sec in other_sections:
                other_lines = other_sec.schedule_line_ids.filtered("active")
                for l1 in my_lines:
                    for l2 in other_lines:
                        if l1.weekday == l2.weekday:
                            if (
                                l1.timeslot_id
                                and l2.timeslot_id
                                and l1.timeslot_id.start_hour < l2.timeslot_id.end_hour
                                and l1.timeslot_id.end_hour > l2.timeslot_id.start_hour
                            ):
                                return {
                                    "warning": {
                                        "title": _("Schedule Overlap Warning"),
                                        "message": _(
                                            "Warning: Student '%(student)s' is already enrolled in class section '%(other)s' "
                                            "which has an overlapping schedule (%(slot1)s vs %(slot2)s)."
                                        ) % {
                                            "student": self.student_id.name,
                                            "other": other_sec.display_name,
                                            "slot1": l1.timeslot_id.name,
                                            "slot2": l2.timeslot_id.name,
                                        },
                                    }
                                }

    @api.depends("student_id", "subject_id", "semester_id", "class_section_id", "status")
    def _compute_possible_duplicate(self):
        for rec in self:
            if not (rec.student_id and rec.subject_id and rec.semester_id) or rec.status in ("dropped", "withdrawn"):
                rec.possible_duplicate = False
                continue
            duplicate = self.search([
                ("id", "!=", rec.id or 0),
                ("student_id", "=", rec.student_id.id),
                ("subject_id", "=", rec.subject_id.id),
                ("semester_id", "=", rec.semester_id.id),
                ("class_section_id", "!=", rec.class_section_id.id if rec.class_section_id else 0),
                ("status", "not in", ["dropped", "withdrawn"]),
            ], limit=1)
            rec.possible_duplicate = bool(duplicate)

    def _search_possible_duplicate(self, operator, value):
        self.env.cr.execute(
            """
            SELECT e1.id
              FROM university_enrollment e1
              JOIN university_enrollment e2 ON e1.student_id = e2.student_id
                                          AND e1.subject_id = e2.subject_id
                                          AND e1.semester_id = e2.semester_id
                                          AND e1.id != e2.id
                                          AND COALESCE(e1.class_section_id, 0) != COALESCE(e2.class_section_id, 0)
             WHERE e1.status NOT IN ('dropped', 'withdrawn')
               AND e2.status NOT IN ('dropped', 'withdrawn')
            """
        )
        duplicate_ids = [row[0] for row in self.env.cr.fetchall()]
        is_positive = (operator in ("=", "==") and value) or (operator in ("!=", "<>") and not value)
        if is_positive:
            return [("id", "in", duplicate_ids or [0])]
        return [("id", "not in", duplicate_ids or [0])]

    @api.constrains("student_id", "class_section_id", "status", "enrollment_date")
    def _check_enrollment_rules(self):
        for rec in self:
            # 1. Active student
            if not rec.student_id.active or (hasattr(rec.student_id, "status") and rec.student_id.status != "active"):
                raise ValidationError("The student must be active to enroll in a class.")

            if rec.class_section_id:
                # 2. Open / active class section
                if not rec.class_section_id.active:
                    raise ValidationError("The selected class section is closed or inactive.")

                if not rec.class_section_id.semester_id:
                    raise ValidationError("The class section must belong to a semester.")

                # 4. Department term registration window
                if not self.env.context.get("bypass_registration_window"):
                    semester = rec.semester_id or rec.class_section_id.semester_id
                    dept = (
                        rec.department_id
                        or (rec.class_section_id.subject_id.department_id if rec.class_section_id.subject_id else False)
                        or (rec.program_id.department_id if rec.program_id else False)
                    )
                    term = False
                    if "university.department.term" in self.env:
                        term = self.env["university.department.term"].search([
                            ("semester_id", "=", semester.id if semester else 0),
                            ("department_id", "=", dept.id if dept else 0),
                        ], limit=1)
                    if term and term.registration_start and term.registration_end:
                        today = rec.enrollment_date or fields.Date.context_today(rec)
                        is_reg_open = term.is_registration_open(today) if hasattr(term, "is_registration_open") else (term.registration_start <= today <= term.registration_end)
                        is_add_drop = term.is_add_drop_open(today) if hasattr(term, "is_add_drop_open") else False
                        if not (is_reg_open or is_add_drop):
                            raise ValidationError(
                                f"Registration for department '{dept.name}' is closed. "
                                f"The registration window is {term.registration_start} to {term.registration_end}."
                            )

                # 5. Section capacity check
                if rec.status == "enrolled" and rec.class_section_id.capacity:
                    enrolled_count = self.search_count([
                        ("class_section_id", "=", rec.class_section_id.id),
                        ("status", "=", "enrolled"),
                        ("id", "!=", rec.id or 0),
                    ])
                    if enrolled_count + 1 > rec.class_section_id.capacity:
                        raise ValidationError(
                            f"Class section '{rec.class_section_id.name}' has reached its maximum capacity of {rec.class_section_id.capacity} seats."
                        )

                # 6. Student must not already be enrolled in the same subject in the same semester
                if rec.student_id and rec.subject_id and rec.semester_id and rec.status in ("draft", "enrolled"):
                    dup = self.search([
                        ("id", "!=", rec.id or 0),
                        ("student_id", "=", rec.student_id.id),
                        ("subject_id", "=", rec.subject_id.id),
                        ("semester_id", "=", rec.semester_id.id),
                        ("status", "in", ["draft", "enrolled"]),
                    ], limit=1)
                    if dup:
                        raise ValidationError(
                            f"Student '{rec.student_id.name}' is already enrolled in subject '{rec.subject_id.name}' for semester '{rec.semester_id.name}'."
                        )

            # 3. Closed / archived academic year lock
            year = rec.academic_year_id or (rec.class_section_id.semester_id.academic_year_id if rec.class_section_id and rec.class_section_id.semester_id else False)
            if year and year.state in ("closed", "archived") and not can_maintain_closed_year_records(self.env):
                raise UserError("Enrollments cannot be created or modified for a closed or archived academic year.")

    def action_confirm(self):
        for rec in self:
            if rec.status != "draft":
                raise UserError("Only draft enrollments can be confirmed.")
            rec.status = "enrolled"
            rec.message_post(body="Enrollment confirmed: status changed to Enrolled.")
        return True

    def action_complete(self):
        for rec in self:
            if rec.status != "enrolled":
                raise UserError("Only active enrollments can be completed.")
            rec.status = "completed"
            rec.message_post(body="Enrollment completed: status changed to Completed.")
        return True

    def action_drop(self):
        for rec in self:
            if rec.status not in ("draft", "enrolled"):
                raise UserError("Only draft or enrolled records can be dropped.")
            rec.status = "dropped"
            rec.message_post(body="Enrollment dropped: status changed to Dropped.")
        return True

    def action_reset_draft(self):
        for rec in self:
            if rec.status != "dropped":
                raise UserError("Only dropped enrollments can be reset to draft.")
            rec.status = "draft"
            rec.message_post(body="Enrollment reset to draft: status changed to Draft.")
        return True

    # Legacy method compatibility
    def action_withdraw(self):
        return self.action_drop()

    def action_approve(self):
        return self.action_confirm()

    def action_reject(self):
        return self.action_drop()

    @api.model_create_multi
    def create(self, vals_list):
        vals_list = [dict(vals) for vals in vals_list]
        for vals in vals_list:
            if not vals.get("class_section_id") and vals.get("section_id"):
                vals["class_section_id"] = vals["section_id"]
            if not vals.get("section_id") and vals.get("class_section_id"):
                vals["section_id"] = vals["class_section_id"]
            if not vals.get("status"):
                vals["status"] = "draft"

            if not can_maintain_closed_year_records(self.env):
                year_id = vals.get("academic_year_id")
                if not year_id and vals.get("class_section_id"):
                    section = self.env["university.class.section"].browse(vals["class_section_id"]).exists()
                    if section and section.semester_id and section.semester_id.academic_year_id:
                        year_id = section.semester_id.academic_year_id.id
                if year_id:
                    year = self.env["university.academic.year"].browse(year_id).exists()
                    if year and year.state in ("closed", "archived"):
                        raise UserError("Enrollments cannot be created for a closed or archived academic year.")

        return super().create(vals_list)

    def write(self, vals):
        if not can_maintain_closed_year_records(self.env):
            if any(rec.academic_year_id.state in ("closed", "archived") for rec in self):
                raise UserError("Enrollments in a closed or archived academic year cannot be modified.")
        if "section_id" in vals and "class_section_id" not in vals:
            vals["class_section_id"] = vals["section_id"]
        elif "class_section_id" in vals and "section_id" not in vals:
            vals["section_id"] = vals["class_section_id"]
        return super().write(vals)

    def unlink(self):
        if not can_maintain_closed_year_records(self.env):
            if any(rec.academic_year_id.state in ("closed", "archived") for rec in self):
                raise UserError("Enrollments of a closed or archived academic year cannot be deleted.")
        return super().unlink()
