from datetime import timedelta
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class UniversityExam(models.Model):
    _name = "university.exam"
    _description = "University Examination"
    _inherit = ["mail.thread", "mail.activity.mixin", "university.document.download.mixin"]
    _order = "exam_date desc, id desc"

    _download_report_xmlid = "school_management.action_report_university_exam_marksheet"

    name = fields.Char(
        string="Exam Name",
        compute="_compute_name",
        store=True,
        default=lambda self: _("New Exam"),
        tracking=True,
    )
    exam_type = fields.Selection(
        [
            ("quiz", "Quiz"),
            ("midterm", "Midterm Exam"),
            ("final", "Final Exam"),
        ],
        string="Exam Type",
        required=True,
        default="quiz",
        tracking=True,
    )
    subject_id = fields.Many2one(
        "university.subject",
        string="Subject",
        required=True,
        tracking=True,
    )
    section_id = fields.Many2one(
        "university.class.section",
        string="Class Section",
        required=True,
        tracking=True,
    )
    department_id = fields.Many2one(
        "university.department",
        string="Department",
        related="section_id.department_id",
        store=True,
        readonly=True,
    )
    program_id = fields.Many2one(
        "university.program",
        string="Program / Major",
        related="section_id.program_id",
        store=True,
        readonly=True,
    )
    timetable_slot_id = fields.Many2one(
        "university.timetable.slot",
        string="Timetable Session",
        ondelete="set null",
        help="The timetable session that triggered this exam (if auto-created).",
    )
    auto_created = fields.Boolean(
        string="Auto Created",
        default=False,
        readonly=True,
        help="True if generated automatically when the class session started.",
    )
    academic_year_id = fields.Many2one(
        "university.academic.year",
        string="Academic Year",
        compute="_compute_academic_period",
        store=True,
        readonly=False,
        required=True,
    )
    semester_id = fields.Many2one(
        "university.semester",
        string="Semester",
        compute="_compute_academic_period",
        store=True,
        readonly=False,
        required=True,
        domain="[('academic_year_id', '=', academic_year_id)]",
    )
    teacher_id = fields.Many2one(
        "university.teacher",
        string="Teacher",
        compute="_compute_teacher_id",
        store=True,
        readonly=False,
        required=True,
        tracking=True,
    )
    exam_date = fields.Date(
        string="Exam Date",
        default=fields.Date.context_today,
        required=True,
        tracking=True,
    )
    start_time = fields.Datetime(
        string="Start Time",
        tracking=True,
        help="When the exam/quiz opens for students.",
    )
    end_time = fields.Datetime(
        string="End Time",
        tracking=True,
        help="When the exam/quiz closes (deadline).",
    )
    duration_minutes = fields.Integer(
        string="Duration (Minutes)",
        compute="_compute_duration",
        store=True,
        readonly=False,
        help="Allotted time in minutes for this exam.",
    )
    late_submission_allowed = fields.Boolean(
        string="Allow Late Submission",
        default=False,
        help="If checked, students may submit after end time with an optional penalty.",
    )
    late_penalty_percent = fields.Float(
        string="Late Penalty (%)",
        default=10.0,
        help="Percentage deducted from raw score if submitted after end time.",
    )
    auto_close = fields.Boolean(
        string="Auto-Close on Deadline",
        default=True,
        help="If enabled, this exam automatically transitions to closed when end_time passes.",
    )
    max_score = fields.Float(
        string="Max Score",
        default=100.0,
        required=True,
        tracking=True,
    )
    weight_percent = fields.Float(
        string="Weight (%)",
        compute="_compute_default_weight",
        store=True,
        readonly=False,
        help="Contribution towards the final course grade (e.g. 20% for Quiz, 30% for Midterm, 50% for Final).",
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("scheduled", "Scheduled"),
            ("open", "Open"),
            ("closed", "Closed"),
            ("grading", "Grading"),
            ("published", "Published"),
            ("cancelled", "Cancelled"),
        ],
        string="Status",
        default="draft",
        required=True,
        tracking=True,
    )
    score_ids = fields.One2many(
        "university.exam.score",
        "exam_id",
        string="Student Scores",
    )

    # Computed metrics
    student_count = fields.Integer(
        string="Eligible Students",
        compute="_compute_exam_stats",
        store=True,
        help="Total students actively enrolled in the section.",
    )
    scored_count = fields.Integer(
        string="Graded Students",
        compute="_compute_exam_stats",
        store=True,
        help="Count of students with scores entered.",
    )
    average_score = fields.Float(
        string="Class Average",
        compute="_compute_exam_stats",
        store=True,
        digits=(5, 2),
        help="Average score of all students graded so far.",
    )
    highest_score = fields.Float(
        string="Highest Score",
        compute="_compute_exam_stats",
        store=True,
        digits=(5, 2),
    )
    lowest_score = fields.Float(
        string="Lowest Score",
        compute="_compute_exam_stats",
        store=True,
        digits=(5, 2),
    )
    pass_count = fields.Integer(
        string="Passed Count",
        compute="_compute_exam_stats",
        store=True,
    )
    fail_count = fields.Integer(
        string="Failed Count",
        compute="_compute_exam_stats",
        store=True,
    )

    @api.depends("subject_id", "exam_type", "section_id", "exam_date")
    def _compute_name(self):
        type_labels = dict(self._fields["exam_type"].selection)
        for exam in self:
            subject_name = exam.subject_id.name or _("Subject")
            type_label = type_labels.get(exam.exam_type, _("Exam"))
            section_name = exam.section_id.name or _("Section")
            date_str = str(exam.exam_date) if exam.exam_date else ""
            exam.name = f"{subject_name} - {type_label} - {section_name} ({date_str})".strip()

    @api.depends("section_id")
    def _compute_academic_period(self):
        for exam in self:
            if exam.section_id and exam.section_id.semester_id:
                exam.semester_id = exam.section_id.semester_id
                exam.academic_year_id = exam.section_id.semester_id.academic_year_id

    @api.depends("section_id", "subject_id")
    def _compute_teacher_id(self):
        for exam in self:
            if exam.section_id and exam.section_id.teacher_id:
                exam.teacher_id = exam.section_id.teacher_id
            elif not exam.teacher_id:
                teacher = self.env["university.teacher"].search(
                    [("user_id", "=", self.env.user.id)], limit=1
                )
                if teacher:
                    exam.teacher_id = teacher

    @api.depends("exam_type", "subject_id")
    def _compute_default_weight(self):
        default_weights = {
            "quiz": 20.0,
            "midterm": 30.0,
            "final": 50.0,
        }
        for exam in self:
            # Check if there is an existing assessment category matching this exam type
            category = self.env["university.assessment.category"].search(
                [("name", "ilike", exam.exam_type), ("active", "=", True)], limit=1
            )
            if category and category.weight:
                exam.weight_percent = category.weight
            else:
                exam.weight_percent = default_weights.get(exam.exam_type, 20.0)

    @api.depends("start_time", "end_time")
    def _compute_duration(self):
        for exam in self:
            if exam.start_time and exam.end_time and exam.end_time > exam.start_time:
                diff = exam.end_time - exam.start_time
                exam.duration_minutes = int(diff.total_seconds() / 60)
            elif not exam.duration_minutes:
                exam.duration_minutes = 60 if exam.exam_type == "quiz" else 120

    @api.depends("score_ids", "score_ids.score", "score_ids.is_absent", "section_id", "max_score")
    def _compute_exam_stats(self):
        for exam in self:
            # Total eligible students enrolled in the section
            enrolled_count = self.env["university.enrollment"].search_count(
                [("section_id", "=", exam.section_id.id), ("status", "=", "enrolled")]
            ) if exam.section_id else 0
            exam.student_count = enrolled_count or len(exam.score_ids)

            valid_scores = exam.score_ids.filtered(lambda s: not s.is_absent)
            scored_lines = [s.final_score for s in valid_scores]

            exam.scored_count = len(exam.score_ids)
            if scored_lines:
                exam.average_score = sum(scored_lines) / len(scored_lines)
                exam.highest_score = max(scored_lines)
                exam.lowest_score = min(scored_lines)
            else:
                exam.average_score = 0.0
                exam.highest_score = 0.0
                exam.lowest_score = 0.0

            passing_threshold = (exam.max_score or 100.0) * 0.5
            exam.pass_count = sum(1 for s in valid_scores if s.final_score >= passing_threshold)
            exam.fail_count = sum(1 for s in valid_scores if s.final_score < passing_threshold)

    @api.constrains("max_score")
    def _check_max_score(self):
        for exam in self:
            if exam.max_score <= 0:
                raise ValidationError(_("Maximum score must be strictly greater than 0."))

    @api.constrains("start_time", "end_time")
    def _check_time_range(self):
        for exam in self:
            if exam.start_time and exam.end_time and exam.start_time >= exam.end_time:
                raise ValidationError(_("Exam start time must be before end time."))

    @api.constrains("late_penalty_percent")
    def _check_late_penalty(self):
        for exam in self:
            if exam.late_penalty_percent < 0 or exam.late_penalty_percent > 100:
                raise ValidationError(_("Late penalty percentage must be between 0% and 100%."))

    @api.onchange("exam_date", "exam_type", "semester_id")
    def _onchange_exam_date_semester(self):
        """Warn (non-blocking) if exam_date is out of semester or poorly placed (Exam BRD/SRS §2.1a / Rule 17)."""
        if not self.exam_date or not self.semester_id:
            return
        sem = self.semester_id
        if sem.date_start and sem.date_end:
            if self.exam_date < sem.date_start or self.exam_date > sem.date_end:
                return {
                    "warning": {
                        "title": _("Exam Date Warning"),
                        "message": _(
                            "The selected exam date (%s) falls outside the semester dates (%s to %s)."
                        ) % (self.exam_date, sem.date_start, sem.date_end),
                    }
                }
            midpoint = sem.date_start + (sem.date_end - sem.date_start) / 2
            if self.exam_type == "final" and self.exam_date < midpoint:
                return {
                    "warning": {
                        "title": _("Exam Schedule Advisory"),
                        "message": _(
                            "A Final Exam is scheduled before the semester midpoint (%s)."
                        ) % midpoint,
                    }
                }
            if self.exam_type == "midterm" and self.exam_date > midpoint:
                return {
                    "warning": {
                        "title": _("Exam Schedule Advisory"),
                        "message": _(
                            "A Midterm Exam is scheduled after the semester midpoint (%s)."
                        ) % midpoint,
                    }
                }

    def unlink(self):
        for exam in self:
            if exam.score_ids and not self.env.user.has_group("school_management.group_school_admin"):
                raise UserError(_("Cannot delete an exam that already has scores recorded unless you are an Administrator."))
        return super().unlink()

    # -------------------------------------------------------------------------
    # Actions & Workflow
    # -------------------------------------------------------------------------
    def action_populate_students(self):
        """Populate exam scores from enrolled students in the section."""
        self.ensure_one()
        if not self.section_id:
            raise UserError(_("Please select a Class Section first."))

        enrollments = self.env["university.enrollment"].search([
            ("section_id", "=", self.section_id.id),
            ("status", "=", "enrolled"),
        ])

        if not enrollments:
            raise UserError(_("No students are actively enrolled in this class section."))

        existing_students = set(self.score_ids.mapped("student_id.id"))
        scores_to_create = []

        for enroll in enrollments:
            if enroll.student_id.id not in existing_students:
                scores_to_create.append({
                    "exam_id": self.id,
                    "student_id": enroll.student_id.id,
                    "enrollment_id": enroll.id,
                    "score": 0.0,
                    "is_absent": False,
                })

        if scores_to_create:
            self.env["university.exam.score"].create(scores_to_create)

        return True

    def action_view_exam_scores(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id("school_management.action_university_exam_score")
        action["domain"] = [("exam_id", "=", self.id)]
        action["context"] = {"default_exam_id": self.id}
        action["name"] = _("Results: %s") % self.name
        return action

    def action_mark_all_present(self):
        for exam in self:
            exam.score_ids.write({"is_absent": False})

    def action_schedule(self):
        self.write({"state": "scheduled"})

    def action_open(self):
        for exam in self:
            if not exam.score_ids:
                exam.action_populate_students()
            exam.write({"state": "open"})

    def action_close(self):
        self.write({"state": "closed"})

    def action_start_grading(self):
        self.write({"state": "grading"})

    def action_publish(self):
        """Publish exam scores and synchronize into university.assessment.result."""
        for exam in self:
            if exam.state == "draft":
                raise UserError(_("Cannot publish a draft exam."))

            # Ensure an assessment category exists for this exam type
            cat_name = dict(exam._fields["exam_type"].selection).get(exam.exam_type, "Exam")
            category = self.env["university.assessment.category"].search(
                [("name", "ilike", cat_name), ("active", "=", True)], limit=1
            )
            if not category:
                category = self.env["university.assessment.category"].create({
                    "name": cat_name,
                    "code": exam.exam_type.upper(),
                    "weight": exam.weight_percent or 20.0,
                    "active": True,
                })

            # Sync each non-absent student score into assessment result
            for score_line in exam.score_ids:
                existing_result = self.env["university.assessment.result"].search([
                    ("exam_id", "=", exam.id),
                    ("student_id", "=", score_line.student_id.id),
                ], limit=1)

                result_vals = {
                    "student_id": score_line.student_id.id,
                    "section_id": exam.section_id.id,
                    "subject_id": exam.subject_id.id,
                    "teacher_id": exam.teacher_id.id,
                    "academic_year_id": exam.academic_year_id.id,
                    "semester_id": exam.semester_id.id,
                    "category_id": category.id,
                    "date": exam.exam_date,
                    "score": 0.0 if score_line.is_absent else score_line.final_score,
                    "max_score": exam.max_score,
                    "exam_id": exam.id,
                    "state": "published",
                }

                if existing_result:
                    existing_result.write(result_vals)
                else:
                    self.env["university.assessment.result"].create(result_vals)

            exam.write({"state": "published"})

    def action_reset_draft(self):
        for exam in self:
            # Revert any published assessment results to draft
            results = self.env["university.assessment.result"].search([("exam_id", "=", exam.id)])
            results.write({"state": "draft"})
            exam.write({"state": "draft"})

    def action_cancel(self):
        for exam in self:
            results = self.env["university.assessment.result"].search([("exam_id", "=", exam.id)])
            results.unlink()
            exam.write({"state": "cancelled"})

    def _generate_xlsx_bytes(self):
        self.ensure_one()
        from ...controllers.grading.exam_marksheet import build_marksheet_xlsx
        exam_type_label = dict(self._fields['exam_type'].selection).get(self.exam_type, (self.exam_type or 'Exam').capitalize())
        state_label = dict(self._fields['state'].selection).get(self.state, (self.state or '').capitalize())
        course_label = f"[{self.subject_id.code}] {self.subject_id.name}" if self.subject_id.code else (self.subject_id.name or 'Subject')
        period_label = f"{self.academic_year_id.name or ''} - {self.semester_id.name or ''}".strip(' -')
        teacher_label = f"{self.teacher_id.name} ({self.teacher_id.teacher_id})" if self.teacher_id.teacher_id else (self.teacher_id.name or 'Course Instructor')
        duration_str = f"{self.duration_minutes} minutes" if self.duration_minutes else 'Standard Duration'
        date_str = str(self.exam_date) if self.exam_date else 'TBA'
        date_duration_label = f"{date_str} ({duration_str})"

        exam_info = {
            'institution': self.env.company.name or 'HARVARD UNIVERSITY - FACULTY ACADEMIC PORTAL',
            'course': course_label,
            'section': self.section_id.name or 'N/A',
            'program': self.program_id.name or (self.section_id.program_id.name if self.section_id else 'N/A'),
            'department': self.department_id.name or (self.section_id.department_id.name if self.section_id else 'Academic Department'),
            'academic_period': period_label,
            'teacher': teacher_label,
            'teacher_name': self.teacher_id.name or 'Teacher',
            'teacher_code': self.teacher_id.teacher_id or '',
            'weight': f"{self.weight_percent:.1f}%" if self.weight_percent else 'N/A',
            'exam_type': exam_type_label,
            'exam_date_duration': date_duration_label,
            'status': state_label,
            'avg_score': self.average_score or 0.0,
            'pass_count': self.pass_count or 0,
            'fail_count': self.fail_count or 0,
            'student_count': self.student_count or len(self.score_ids),
        }

        subjects = [self.subject_id.name or 'Subject']
        students = []
        for score in self.score_ids.sorted(key=lambda s: (s.student_code or '', s.student_id.name or '')):
            students.append({
                'id': score.student_code or score.student_id.student_id or f'STU-{score.student_id.id}',
                'name': score.student_id.name or '',
                'is_absent': score.is_absent,
                'raw_score': score.score,
                'penalty': score.penalty_applied or 0.0,
                'final_score': score.final_score if not score.is_absent else 0.0,
                'percentage': score.percentage or 0.0,
                'remark': score.remark or '',
                'marks': [score.final_score if not score.is_absent else 0.0],
            })

        full_marks = self.max_score or 100.0
        pass_marks = round(full_marks * 0.5, 2)

        return build_marksheet_xlsx(
            title=self.name or 'Student Examination Marksheet',
            subtitle=f"{exam_type_label} Official Ledger",
            full_marks=full_marks,
            pass_marks=pass_marks,
            subjects=subjects,
            students=students,
            exam_info=exam_info,
        )

    def _get_xlsx_data(self):
        self.ensure_one()
        headers = ["No.", "Student ID", "Student Name", "Attendance", "Raw Score", "Final Score", "Percentage", "Result"]
        rows = []
        for idx, score in enumerate(self.score_ids.sorted(key=lambda s: (s.student_code or '', s.student_id.name or '')), 1):
            rows.append([
                idx,
                score.student_code or score.student_id.student_id or '',
                score.student_id.name or '',
                'Absent' if score.is_absent else 'Present',
                score.score if not score.is_absent else 0.0,
                score.final_score if not score.is_absent else 0.0,
                f"{score.percentage:.1f}%",
                'ABSENT' if score.is_absent else ('PASS' if score.is_passed else 'FAIL'),
            ])
        return (f"Exam_{self.id}", headers, rows)

    def action_download_marksheet(self):
        self.ensure_one()
        if hasattr(self, '_log_download'):
            self._log_download(file_type='Excel')
        return {
            'type': 'ir.actions.act_url',
            'url': f'/university/marksheet/{self.id}/xlsx',
            'target': 'self',
        }

    def action_print_marksheet_pdf(self):
        self.ensure_one()
        if hasattr(self, '_log_download'):
            self._log_download(file_type='PDF')
        return self.env.ref("school_management.action_report_university_exam_marksheet").report_action(self)

    def action_download_marksheet_pdf(self):
        self.ensure_one()
        if hasattr(self, '_log_download'):
            self._log_download(file_type='PDF')
        return {
            'type': 'ir.actions.act_url',
            'url': f'/university/marksheet/{self.id}/pdf',
            'target': 'self',
        }

    # -------------------------------------------------------------------------
    # Cron Jobs
    # -------------------------------------------------------------------------
    @api.model
    def _cron_auto_close_expired_exams(self):
        """Automatically close open exams whose end_time has passed (Quiz_Deadline_Session_Rules §6)."""
        now = fields.Datetime.now()
        expired_exams = self.search([
            ("state", "=", "open"),
            ("end_time", "!=", False),
            ("end_time", "<", now),
            ("auto_close", "=", True),
        ])
        if expired_exams:
            expired_exams.write({"state": "closed"})

    @api.model
    def _cron_auto_create_session_quiz(self):
        """
        Auto-create a plain quiz for class sessions (timetable slots) starting right now,
        if section or subject has auto_quiz_per_session enabled and semester is active (Exam BRD/SRS §2.1a / Rule 16).
        """
        now = fields.Datetime.now()
        window_start = now - timedelta(minutes=15)
        window_end = now + timedelta(minutes=15)

        slots = self.env["university.timetable.slot"].search([
            ("start_time", ">=", window_start),
            ("start_time", "<=", window_end),
            ("status", "in", ["upcoming", "ongoing"]),
        ])

        for slot in slots:
            # Check semester active date (Exam BRD/SRS §2.1a / Rule 16)
            if slot.semester_id and not slot.semester_id.is_active:
                continue

            # Check if section or subject requires a per-session quiz
            requires_quiz = (
                getattr(slot.section_id, "auto_quiz_per_session", False) or
                getattr(slot.subject_id, "auto_quiz_per_session", False)
            )
            if not requires_quiz:
                continue

            # Ensure we haven't already created an exam for this timetable slot
            existing = self.search([("timetable_slot_id", "=", slot.id)], limit=1)
            if existing:
                continue

            exam = self.create({
                "exam_type": "quiz",
                "subject_id": slot.subject_id.id,
                "section_id": slot.section_id.id,
                "timetable_slot_id": slot.id,
                "teacher_id": slot.teacher_id.id,
                "academic_year_id": slot.academic_year_id.id,
                "semester_id": slot.semester_id.id,
                "exam_date": slot.start_time.date() if slot.start_time else fields.Date.context_today(self),
                "start_time": slot.start_time,
                "end_time": slot.end_time,
                "auto_created": True,
                "state": "open",
                "max_score": 100.0,
            })
            exam.action_populate_students()


class UniversityExamScore(models.Model):
    _name = "university.exam.score"
    _description = "Student Exam Score"
    _order = "student_id, id"

    _unique_exam_student = models.Constraint(
        "unique (exam_id, student_id)",
        "A student can have only one score per exam.",
    )

    exam_id = fields.Many2one(
        "university.exam",
        string="Exam",
        required=True,
        ondelete="cascade",
        index=True,
    )
    student_id = fields.Many2one(
        "university.student",
        string="Student",
        required=True,
        ondelete="cascade",
        index=True,
    )
    student_code = fields.Char(
        string="Student ID",
        related="student_id.student_id",
        store=True,
        readonly=True,
    )
    exam_type = fields.Selection(
        related="exam_id.exam_type",
        string="Exam Type",
        store=True,
        readonly=True,
    )
    subject_id = fields.Many2one(
        "university.subject",
        related="exam_id.subject_id",
        string="Subject",
        store=True,
        readonly=True,
    )
    section_id = fields.Many2one(
        "university.class.section",
        related="exam_id.section_id",
        string="Class Section",
        store=True,
        readonly=True,
    )
    department_id = fields.Many2one(
        "university.department",
        related="exam_id.department_id",
        string="Department",
        store=True,
        readonly=True,
    )
    program_id = fields.Many2one(
        "university.program",
        related="exam_id.program_id",
        string="Program",
        store=True,
        readonly=True,
    )
    exam_date = fields.Date(
        related="exam_id.exam_date",
        string="Exam Date",
        store=True,
        readonly=True,
    )
    max_score = fields.Float(
        related="exam_id.max_score",
        string="Max Score",
        store=True,
        readonly=True,
    )
    enrollment_id = fields.Many2one(
        "university.enrollment",
        string="Enrollment",
        compute="_compute_enrollment_id",
        store=True,
        readonly=False,
    )
    score = fields.Float(
        string="Raw Score",
        default=0.0,
    )
    remark = fields.Char(string="Remark")
    is_absent = fields.Boolean(
        string="Absent",
        default=False,
        help="If checked, the student was absent from the examination.",
    )
    submitted_at = fields.Datetime(
        string="Submission Time",
        help="When the attempt/submission was recorded.",
    )
    is_late = fields.Boolean(
        string="Late",
        compute="_compute_is_late",
        store=True,
    )
    penalty_applied = fields.Float(
        string="Penalty (%)",
        compute="_compute_final_score",
        store=True,
    )
    final_score = fields.Float(
        string="Final Score",
        compute="_compute_final_score",
        store=True,
        digits=(5, 2),
    )
    percentage = fields.Float(
        string="Percentage (%)",
        compute="_compute_final_score",
        store=True,
        digits=(5, 2),
    )
    is_passed = fields.Boolean(
        string="Passed",
        compute="_compute_final_score",
        store=True,
    )
    state = fields.Selection(
        related="exam_id.state",
        string="Status",
        store=True,
        readonly=True,
    )

    @api.depends("student_id", "exam_id.section_id")
    def _compute_enrollment_id(self):
        for line in self:
            if line.student_id and line.exam_id.section_id:
                enroll = self.env["university.enrollment"].search([
                    ("student_id", "=", line.student_id.id),
                    ("section_id", "=", line.exam_id.section_id.id),
                ], limit=1)
                line.enrollment_id = enroll or False
            else:
                line.enrollment_id = False

    @api.depends("submitted_at", "exam_id.end_time")
    def _compute_is_late(self):
        for line in self:
            if line.submitted_at and line.exam_id.end_time and line.submitted_at > line.exam_id.end_time:
                line.is_late = True
            else:
                line.is_late = False

    @api.depends("score", "is_absent", "is_late", "exam_id.max_score", "exam_id.late_submission_allowed", "exam_id.late_penalty_percent")
    def _compute_final_score(self):
        for line in self:
            if line.is_absent:
                line.final_score = 0.0
                line.penalty_applied = 0.0
                line.percentage = 0.0
                line.is_passed = False
                continue

            max_score = line.exam_id.max_score or 100.0
            base_score = max(0.0, min(line.score, max_score))

            penalty = 0.0
            if line.is_late and line.exam_id.late_submission_allowed and line.exam_id.late_penalty_percent:
                penalty = line.exam_id.late_penalty_percent
                base_score = max(0.0, base_score * (1.0 - (penalty / 100.0)))

            line.penalty_applied = penalty
            line.final_score = base_score
            line.percentage = (base_score / max_score * 100.0) if max_score > 0 else 0.0
            line.is_passed = line.percentage >= 50.0

    @api.constrains("score", "exam_id")
    def _check_score_bounds(self):
        for line in self:
            if not line.is_absent:
                if line.score < 0:
                    raise ValidationError(_("Score cannot be negative."))
                if line.exam_id and line.score > line.exam_id.max_score:
                    raise ValidationError(_(
                        "Score %(score)s for student %(student)s cannot exceed max score %(max)s.",
                        score=line.score,
                        student=line.student_id.display_name,
                        max=line.exam_id.max_score,
                    ))
