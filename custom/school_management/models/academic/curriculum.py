from odoo import api, fields, models


class UniversityCurriculum(models.Model):
    _name = "university.curriculum"
    _description = "University Curriculum"
    _order = "name"

    name = fields.Char(
        string="Curriculum Name",
        compute="_compute_name",
        store=True,
        readonly=False,
        precompute=True,
    )
    program_id = fields.Many2one(
        "university.program",
        string="Program",
        required=True,
        ondelete="cascade",
        index=False,
    )
    session_id = fields.Many2one(
        "university.academic.year",
        string="Session",
        required=True,
        ondelete="restrict",
        index=True,
    )
    active = fields.Boolean(string="Active", default=True)
    line_ids = fields.One2many(
        "university.curriculum.line",
        "curriculum_id",
        string="Curriculum Lines",
    )
    credit_load_warning = fields.Text(
        string="Credit Load Review",
        compute="_compute_credit_load_warning",
    )

    _curriculum_program_session_uniq = models.Constraint(
        "UNIQUE(program_id, session_id)",
        "A curriculum already exists for this program and session.",
    )

    @api.depends("program_id.name", "session_id.name")
    def _compute_name(self):
        for rec in self:
            if rec.program_id and rec.session_id:
                rec.name = f"{rec.program_id.name} - {rec.session_id.name}"
            elif rec.program_id:
                rec.name = rec.program_id.name
            elif not rec.name:
                rec.name = "Curriculum"

    @api.depends("line_ids.credits", "line_ids.year_level", "line_ids.semester_number")
    def _compute_credit_load_warning(self):
        for rec in self:
            warnings = []
            loads = {}
            for line in rec.line_ids:
                key = (line.year_level, line.semester_number)
                loads[key] = loads.get(key, 0) + (line.credits or 0)
            for (yl, sn), total in sorted(loads.items()):
                if total != 15:
                    warnings.append(
                        f"Year {yl} Semester {sn}: total load is {total} credits "
                        f"(standard target is 15 credits / weekly hours per semester)."
                    )
            rec.credit_load_warning = "\n".join(warnings) if warnings else False


class UniversityCurriculumLine(models.Model):
    _name = "university.curriculum.line"
    _description = "Curriculum Line"
    _order = "program_id, year_level, semester_number, sequence, id"

    curriculum_id = fields.Many2one(
        "university.curriculum",
        string="Curriculum",
        ondelete="cascade",
        index=True,
    )
    program_id = fields.Many2one(
        "university.program",
        string="Program",
        compute="_compute_program_id",
        store=True,
        readonly=False,
        required=True,
        ondelete="cascade",
        index=True,
    )
    subject_id = fields.Many2one(
        "university.subject",
        string="Subject",
        required=True,
        index=True,
    )
    year_level = fields.Selection([
        ("1", "Year 1"),
        ("2", "Year 2"),
        ("3", "Year 3"),
        ("4", "Year 4"),
    ], string="Year Level", required=True, default="1")

    semester_number = fields.Selection([
        ("1", "Semester 1"),
        ("2", "Semester 2"),
    ], string="Semester", required=True, default="1")

    sequence = fields.Integer(string="Sequence", default=10)
    credits = fields.Integer(string="Credits", related="subject_id.credits", store=True, readonly=False)

    # Legacy compatibility fields
    semester = fields.Selection([
        ("1", "Semester 1"),
        ("2", "Semester 2"),
    ], string="Semester (Legacy)", compute="_compute_legacy_semester", inverse="_inverse_legacy_semester", store=True)
    required = fields.Boolean(string="Required", default=True)

    # Student-facing view helpers
    is_current_student_year = fields.Boolean(
        string="Current Student Year",
        compute="_compute_student_view_flags",
    )
    is_student_enrolled = fields.Boolean(
        string="Enrolled",
        compute="_compute_student_view_flags",
    )
    enrollment_status = fields.Char(
        string="Enrollment Status",
        compute="_compute_student_view_flags",
    )

    _curriculum_line_uniq = models.Constraint(
        "UNIQUE(curriculum_id, subject_id, year_level, semester_number)",
        "This subject already exists in this curriculum for this year level and semester.",
    )

    @api.depends("curriculum_id.program_id")
    def _compute_program_id(self):
        for rec in self:
            if rec.curriculum_id and rec.curriculum_id.program_id:
                rec.program_id = rec.curriculum_id.program_id

    @api.depends("semester_number")
    def _compute_legacy_semester(self):
        for rec in self:
            rec.semester = rec.semester_number

    def _inverse_legacy_semester(self):
        for rec in self:
            if rec.semester:
                rec.semester_number = rec.semester

    @api.depends("subject_id.name", "year_level", "semester_number")
    def _compute_display_name(self):
        for rec in self:
            if rec.subject_id:
                rec.display_name = f"{rec.subject_id.name} (Year {rec.year_level or '1'} - Sem {rec.semester_number or '1'})"
            else:
                rec.display_name = f"Curriculum Line #{rec.id}"

    def _compute_student_view_flags(self):
        user = self.env.user
        student = self.env["university.student"].search([("user_id", "=", user.id)], limit=1)
        active_student_id = (
            self.env.context.get("active_student_id")
            or self.env.context.get("default_student_id")
            or (self.env.context.get("active_model") == "university.student" and self.env.context.get("active_id"))
        )
        if not student and active_student_id:
            student = self.env["university.student"].browse(active_student_id).exists()

        for line in self:
            if not student:
                line.is_current_student_year = False
                line.is_student_enrolled = False
                line.enrollment_status = "Planned"
                continue

            line.is_current_student_year = (line.year_level == student.year_level)

            # Check if student completed results for this subject (via report card line or completed enrollment)
            completed_rc_line = self.env["university.report.card.line"].search([
                ("student_id", "=", student.id),
                ("subject_id", "=", line.subject_id.id),
                ("is_passing", "=", True),
            ], limit=1)
            if completed_rc_line:
                line.is_student_enrolled = True
                line.enrollment_status = "Completed"
                continue

            # Check active enrollment
            enrollment = self.env["university.enrollment"].search([
                ("student_id", "=", student.id),
                ("subject_id", "=", line.subject_id.id),
                ("status", "in", ["enrolled", "completed"]),
            ], limit=1)
            if enrollment:
                line.is_student_enrolled = True
                line.enrollment_status = "Completed" if enrollment.status == "completed" else "Enrolled"
            else:
                line.is_student_enrolled = False
                line.enrollment_status = "Planned"
