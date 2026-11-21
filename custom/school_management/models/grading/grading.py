import secrets

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from ..academic.academic_lock import can_maintain_closed_year_records


class UniversityGradeScale(models.Model):
    _name = "university.grade.scale"
    _description = "Grade Scale"
    _order = "name"

    name = fields.Char(string="Grade Scale", required=True)
    active = fields.Boolean(string="Active", default=True)
    line_ids = fields.One2many(
        "university.grade.scale.line",
        "scale_id",
        string="Grade Lines",
    )

    def get_grade_line(self, score):
        self.ensure_one()
        return self.line_ids.filtered(lambda item: score >= item.min_score).sorted(
            "min_score", reverse=True
        )[:1]


class UniversityGradeScaleLine(models.Model):
    _name = "university.grade.scale.line"
    _description = "Grade Scale Line"
    _order = "scale_id, min_score desc, id"

    scale_id = fields.Many2one(
        "university.grade.scale",
        string="Grade Scale",
        required=True,
        ondelete="cascade",
    )
    name = fields.Char(string="Grade", required=True)
    min_score = fields.Float(string="Minimum Score", required=True)
    max_score = fields.Float(string="Maximum Score", required=True, default=100.0)
    grade_point = fields.Float(string="Grade Point", required=True)
    honors_grade_point = fields.Float(string="Honors Grade Point")
    is_passing = fields.Boolean(string="Passing Grade", default=True)

    @api.constrains("min_score", "max_score", "grade_point")
    def _check_grade_line_values(self):
        for line in self:
            if line.min_score > line.max_score:
                raise ValidationError("Minimum score cannot exceed maximum score.")
            if line.min_score < 0 or line.max_score > 100:
                raise ValidationError("Grade scale scores must be between 0 and 100.")
            if line.grade_point < 0:
                raise ValidationError("Grade points cannot be negative.")


class UniversityAssessmentCategory(models.Model):
    _name = "university.assessment.category"
    _description = "Assessment Category"
    _order = "sequence, name"

    sequence = fields.Integer(default=10)
    name = fields.Char(string="Category", required=True)
    code = fields.Char(string="Code", required=True)
    weight = fields.Float(
        string="Weight (%)",
        default=10.0,
        help="Percent contribution to the final subject score.",
    )
    evaluation_type = fields.Selection(
        [
            ("coursework", "Coursework & Homework"),
            ("exam", "Formal Examination"),
            ("quiz", "Quizzes & Short Tests"),
            ("attendance", "Attendance & Participation"),
            ("practical", "Lab & Practical"),
            ("project", "Project / Capstone"),
        ],
        string="Evaluation Type",
        default="coursework",
        required=True,
    )
    description = fields.Text(
        string="Description / Policy",
        help="Institutional grading policy, assessment criteria, and rubrics for this category.",
    )
    icon = fields.Char(string="Icon", default="fa-tasks")
    color = fields.Integer(string="Color Index", default=0)
    active = fields.Boolean(string="Active", default=True)

    assignment_ids = fields.One2many(
        "university.assignment",
        "category_id",
        string="Linked Assignments",
    )
    result_ids = fields.One2many(
        "university.assessment.result",
        "category_id",
        string="Assessment Results",
    )

    assignment_count = fields.Integer(
        string="Assignments",
        compute="_compute_category_metrics",
    )
    exam_count = fields.Integer(
        string="Exams",
        compute="_compute_category_metrics",
    )
    result_count = fields.Integer(
        string="Graded Records",
        compute="_compute_category_metrics",
    )
    avg_score = fields.Float(
        string="Avg Score (%)",
        compute="_compute_category_metrics",
        digits=(5, 2),
    )
    passing_rate = fields.Float(
        string="Pass Rate (%)",
        compute="_compute_category_metrics",
        digits=(5, 2),
    )

    @api.depends("assignment_ids", "result_ids", "result_ids.percentage", "result_ids.state")
    def _compute_category_metrics(self):
        for category in self:
            category.assignment_count = len(category.assignment_ids)
            results = category.result_ids
            category.result_count = len(results)

            exam_domain = [
                "|",
                ("exam_type", "=", category.code.lower() if category.code else ""),
                ("name", "ilike", category.name or ""),
            ]
            category.exam_count = self.env["university.exam"].search_count(exam_domain)

            if results:
                published = results.filtered(lambda r: r.state == "published") or results
                percentages = published.mapped("percentage")
                category.avg_score = round(sum(percentages) / len(percentages), 1) if percentages else 0.0
                passing = len([p for p in percentages if p >= 50.0])
                category.passing_rate = round((passing / len(percentages)) * 100.0, 1) if percentages else 0.0
            else:
                category.avg_score = 0.0
                category.passing_rate = 0.0

    @api.constrains("weight", "active")
    def _check_weight(self):
        for category in self:
            if category.weight <= 0 or category.weight > 100:
                raise ValidationError("Assessment category weight must be above 0 and no more than 100.")
        if self.env.context.get("install_mode"):
            return
        active_categories = self.search([("active", "=", True)])
        if active_categories and abs(sum(active_categories.mapped("weight")) - 100.0) > 0.01:
            raise ValidationError("Active assessment category weights must sum to 100%.")

    def action_view_assignments(self):
        self.ensure_one()
        return {
            "name": _("Assignments: %s", self.name),
            "type": "ir.actions.act_window",
            "res_model": "university.assignment",
            "view_mode": "list,form",
            "domain": [("category_id", "=", self.id)],
            "context": {"default_category_id": self.id},
        }

    def action_view_results(self):
        self.ensure_one()
        return {
            "name": _("Assessment Results: %s", self.name),
            "type": "ir.actions.act_window",
            "res_model": "university.assessment.result",
            "view_mode": "list,form",
            "domain": [("category_id", "=", self.id)],
            "context": {"default_category_id": self.id},
        }

    def action_view_exams(self):
        self.ensure_one()
        exam_domain = [
            "|",
            ("exam_type", "=", self.code.lower() if self.code else ""),
            ("name", "ilike", self.name or ""),
        ]
        return {
            "name": _("Exams: %s", self.name),
            "type": "ir.actions.act_window",
            "res_model": "university.exam",
            "view_mode": "list,form",
            "domain": exam_domain,
        }


class UniversityAssessmentResult(models.Model):
    _name = "university.assessment.result"
    _description = "Assessment Result"
    _order = "date desc, id desc"

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )
    student_id = fields.Many2one("university.student", string="Student", required=True)
    program_id = fields.Many2one(
        "university.program",
        string="Major / Program",
        related="student_id.program_id",
        store=True,
        readonly=True,
    )
    section_id = fields.Many2one("university.class.section", string="Class Section")
    subject_id = fields.Many2one("university.subject", string="Subject", required=True)
    teacher_id = fields.Many2one("university.teacher", string="Teacher")
    academic_year_id = fields.Many2one("university.academic.year", string="Academic Year", required=True)
    semester_id = fields.Many2one(
        "university.semester",
        string="Semester",
        required=True,
        domain="[('academic_year_id', '=', academic_year_id)]",
    )
    category_id = fields.Many2one(
        "university.assessment.category",
        string="Assessment Category",
        required=True,
        domain="[('active', '=', True)]",
    )
    assignment_id = fields.Many2one("university.assignment", string="Assignment")
    submission_id = fields.Many2one("university.assignment.submission", string="Submission")
    exam_id = fields.Many2one("university.exam", string="Examination", ondelete="set null")
    date = fields.Date(string="Assessment Date", default=fields.Date.context_today)
    score = fields.Float(string="Score", required=True)
    max_score = fields.Float(string="Max Score", default=100.0, required=True)
    percentage = fields.Float(string="Percentage", compute="_compute_scores", store=True)
    weighted_score = fields.Float(string="Weighted Score", compute="_compute_scores", store=True)
    state = fields.Selection(
        [("draft", "Draft"), ("published", "Published")],
        string="Status",
        default="draft",
    )

    @api.depends("score", "max_score", "category_id.weight")
    def _compute_scores(self):
        for result in self:
            if result.max_score:
                result.percentage = result.score / result.max_score * 100.0
                result.weighted_score = result.percentage * result.category_id.weight / 100.0
            else:
                result.percentage = 0.0
                result.weighted_score = 0.0

    @api.constrains("score", "max_score")
    def _check_score(self):
        for result in self:
            if result.max_score <= 0:
                raise ValidationError("Maximum score must be greater than zero.")
            if result.score < 0 or result.score > result.max_score:
                raise ValidationError("Score must be between 0 and the maximum score.")

    @api.constrains("semester_id", "academic_year_id")
    def _check_period(self):
        for result in self:
            if result.semester_id.academic_year_id != result.academic_year_id:
                raise ValidationError("The semester must belong to the selected academic year.")

    @api.model_create_multi
    def create(self, vals_list):
        if not can_maintain_closed_year_records(self.env):
            for vals in vals_list:
                year_id = vals.get("academic_year_id")
                if not year_id and vals.get("semester_id"):
                    semester = self.env["university.semester"].browse(vals.get("semester_id")).exists()
                    year_id = semester.academic_year_id.id if semester else False
                if year_id:
                    year = self.env["university.academic.year"].browse(year_id).exists()
                    if year and year.state in ("closed", "archived"):
                        raise UserError("Grades cannot be created for a closed or archived academic year.")
        return super().create(vals_list)

    def write(self, vals):
        if not can_maintain_closed_year_records(self.env):
            if any(res.academic_year_id.state in ("closed", "archived") for res in self):
                raise UserError("Grades of a closed or archived academic year cannot be modified.")
        return super().write(vals)

    def unlink(self):
        if not can_maintain_closed_year_records(self.env):
            if any(res.academic_year_id.state in ("closed", "archived") for res in self):
                raise UserError("Grades of a closed or archived academic year cannot be deleted.")
        return super().unlink()

    def action_publish(self):
        self.write({"state": "published"})

    def action_reset_to_draft(self):
        self.write({"state": "draft"})


class UniversityReportCard(models.Model):
    _name = "university.report.card"
    _description = "Report Card"
    _inherit = ["university.document.download.mixin"]
    _order = "academic_year_id desc, semester_id desc, id desc"

    _download_report_xmlid = "school_management.action_report_university_report_card"
    _download_states = ("approved",)

    name = fields.Char(
        string="Report Reference",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: "New",
    )
    student_id = fields.Many2one("university.student", string="Student", required=True)
    program_id = fields.Many2one("university.program", string="Major / Program", related="student_id.program_id", store=True)
    academic_year_id = fields.Many2one("university.academic.year", string="Academic Year", required=True)
    semester_id = fields.Many2one("university.semester", string="Semester", required=True)
    grade_scale_id = fields.Many2one("university.grade.scale", string="Grade Scale", required=True)
    line_ids = fields.One2many("university.report.card.line", "report_card_id", string="Subjects")
    gpa = fields.Float(string="GPA", compute="_compute_gpa", store=True)
    total_credits = fields.Integer(string="Total Credits", compute="_compute_gpa", store=True)
    passed_credits = fields.Integer(string="Passed Credits", compute="_compute_gpa", store=True)
    academic_standing = fields.Selection(
        [
            ("dean_list", "Dean's List"),
            ("good", "Good Standing"),
            ("probation", "Academic Probation"),
        ],
        string="Academic Standing",
        compute="_compute_gpa",
        store=True,
    )
    evaluation_status = fields.Selection(
        [
            ("in_progress", "In Progress"),
            ("completed", "Completed"),
        ],
        string="Status Overview",
        compute="_compute_evaluation_status",
        store=True,
    )
    state = fields.Selection(
        [("draft", "Draft"), ("generated", "Generated"), ("approved", "Approved")],
        string="Status",
        default="draft",
    )
    verification_code = fields.Char(string="Verification Code", copy=False, readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        if not can_maintain_closed_year_records(self.env):
            for vals in vals_list:
                year_id = vals.get("academic_year_id")
                if not year_id and vals.get("semester_id"):
                    semester = self.env["university.semester"].browse(vals.get("semester_id")).exists()
                    year_id = semester.academic_year_id.id if semester else False
                if year_id:
                    year = self.env["university.academic.year"].browse(year_id).exists()
                    if year and year.state in ("closed", "archived"):
                        raise UserError("Report cards cannot be created for a closed or archived academic year.")
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code("university.report.card") or "New"
        return super().create(vals_list)

    def write(self, vals):
        if not can_maintain_closed_year_records(self.env):
            if any(card.academic_year_id.state in ("closed", "archived") for card in self):
                raise UserError("Report cards of a closed or archived academic year cannot be modified.")
        return super().write(vals)

    def unlink(self):
        if not can_maintain_closed_year_records(self.env):
            if any(card.academic_year_id.state in ("closed", "archived") for card in self):
                raise UserError("Report cards of a closed or archived academic year cannot be deleted.")
        return super().unlink()

    @api.depends("line_ids.credits", "line_ids.grade_point", "line_ids.is_passing", "program_id.min_graduation_grade_id")
    def _compute_gpa(self):
        ICP = self.env["ir.config_parameter"].sudo()
        try:
            min_gpa = float(ICP.get_param("school_management.deans_list_min_gpa", 3.5))
        except (ValueError, TypeError):
            min_gpa = 3.5
        try:
            min_credits = float(ICP.get_param("school_management.deans_list_min_credits", 12))
        except (ValueError, TypeError):
            min_credits = 12.0

        for card in self:
            credits = sum(card.line_ids.mapped("credits"))
            min_grad = card.program_id.min_graduation_grade_id
            if min_grad:
                passed = sum(line.credits for line in card.line_ids if line.is_passing and line.grade_point >= min_grad.grade_point)
            else:
                passed = sum(line.credits for line in card.line_ids if line.is_passing)
            quality = sum(line.credits * line.grade_point for line in card.line_ids)
            card.total_credits = credits
            card.passed_credits = passed
            card.gpa = round(quality / credits, 2) if credits else 0.0

            if not card.line_ids:
                card.academic_standing = "good"
            elif card.gpa >= min_gpa and card.passed_credits >= min_credits:
                card.academic_standing = "dean_list"
            elif card.gpa >= 2.0:
                card.academic_standing = "good"
            else:
                card.academic_standing = "probation"

    @api.depends("line_ids.evaluation_status")
    def _compute_evaluation_status(self):
        for card in self:
            if not card.line_ids or any(line.evaluation_status == "in_progress" for line in card.line_ids):
                card.evaluation_status = "in_progress"
            else:
                card.evaluation_status = "completed"

    def action_generate_lines(self):
        for card in self:
            # 1. Identify enrolled subjects for this student in the target semester
            enrollments = self.env["university.enrollment"].search([
                ("student_id", "=", card.student_id.id),
                ("semester_id", "=", card.semester_id.id),
                ("status", "in", ["enrolled", "completed"]),
            ])

            subjects = self.env["university.subject"]
            for enroll in enrollments:
                if enroll.section_id:
                    if enroll.section_id.subject_id:
                        subjects |= enroll.section_id.subject_id
                    slots = self.env["university.timetable.slot"].search([
                        ("section_id", "=", enroll.section_id.id),
                    ])
                    subjects |= slots.mapped("subject_id")
                if enroll.subject_id:
                    subjects |= enroll.subject_id

            published_results = self.env["university.assessment.result"].search([
                ("student_id", "=", card.student_id.id),
                ("academic_year_id", "=", card.academic_year_id.id),
                ("semester_id", "=", card.semester_id.id),
                ("state", "=", "published"),
            ])
            subjects |= published_results.mapped("subject_id")

            lines = [(5, 0, 0)]
            for subject in subjects:
                weights = {
                    (category.code or "").upper(): category.weight
                    for category in self.env["university.assessment.category"].search(
                        [("active", "=", True)]
                    )
                }

                def component_weight(*codes):
                    for code in codes:
                        if code in weights:
                            return weights[code]
                    return 0.0

                attendance_weight = component_weight("ATTENDANCE")
                quiz_weight = component_weight("QUIZ")
                midterm_weight = component_weight("MIDTERM")
                assignment_weight = component_weight("ASSIGNMENT")
                final_weight = component_weight("EXAM", "FINAL")

                # A. Attendance Calculation (Grading_GPA_Policy.md §3.3)
                subject_sections = enrollments.mapped("section_id").filtered(
                    lambda s: s.subject_id == subject or subject in self.env["university.timetable.slot"].search([("section_id", "=", s.id)]).mapped("subject_id")
                )
                att_domain = [("student_id", "=", card.student_id.id)]
                if subject_sections:
                    att_domain.append(("section_id", "in", subject_sections.ids))

                att_records = self.env["university.attendance"].search(att_domain)
                actual_absents = len(att_records.filtered(lambda a: a.status == "absent"))
                attendance_percentage = (
                    100.0
                    if not att_records
                    else max(0.0, (len(att_records) - actual_absents) * 100.0 / len(att_records))
                )
                attendance_score = round(attendance_percentage * attendance_weight / 100.0, 2)

                # B. Component Results from published assessment results
                sub_results = published_results.filtered(lambda r: r.subject_id == subject)

                # Quiz - multi-quiz averaging
                quiz_res = sub_results.filtered(
                    lambda r: (r.category_id.code and "QUIZ" in r.category_id.code.upper())
                    or (r.category_id.name and "QUIZ" in r.category_id.name.upper())
                    or (r.exam_id and r.exam_id.exam_type == "quiz")
                )
                if quiz_res:
                    avg_quiz_pct = sum(r.percentage for r in quiz_res) / len(quiz_res)
                    quiz_score = round(avg_quiz_pct * quiz_weight / 100.0, 2)
                else:
                    quiz_score = 0.0

                # Midterm Exam
                midterm_res = sub_results.filtered(
                    lambda r: (r.category_id.code and "MID" in r.category_id.code.upper())
                    or (r.category_id.name and "MID" in r.category_id.name.upper())
                    or (r.exam_id and r.exam_id.exam_type == "midterm")
                )
                if midterm_res:
                    avg_midterm_pct = sum(r.percentage for r in midterm_res) / len(midterm_res)
                    midterm_score = round(avg_midterm_pct * midterm_weight / 100.0, 2)
                else:
                    midterm_score = 0.0

                # Assignments - multi-assignment averaging
                assign_res = sub_results.filtered(
                    lambda r: (r.category_id.code and "ASSIGN" in r.category_id.code.upper())
                    or (r.category_id.name and "ASSIGN" in r.category_id.name.upper())
                )
                if assign_res:
                    avg_assign_pct = sum(r.percentage for r in assign_res) / len(assign_res)
                    assignment_score = round(avg_assign_pct * assignment_weight / 100.0, 2)
                else:
                    assignment_score = 0.0

                # Final Exam
                final_res = sub_results.filtered(
                    lambda r: (r.category_id.code and "FINAL" in r.category_id.code.upper())
                    or (r.category_id.name and "FINAL" in r.category_id.name.upper())
                    or (r.exam_id and r.exam_id.exam_type == "final")
                )
                if final_res:
                    avg_final_pct = sum(r.percentage for r in final_res) / len(final_res)
                    final_exam_score = round(avg_final_pct * final_weight / 100.0, 2)
                else:
                    final_exam_score = 0.0

                # Other custom categories (if any)
                classified = quiz_res | midterm_res | assign_res | final_res
                other_res = sub_results - classified
                other_score = sum(r.weighted_score for r in other_res)

                # Total final score
                total_final_score = round(
                    attendance_score + quiz_score + midterm_score + assignment_score + final_exam_score + other_score,
                    2
                )
                total_final_score = min(100.0, max(0.0, total_final_score))

                grade_line = card.grade_scale_id.get_grade_line(total_final_score)
                is_completed = bool(final_res and midterm_res)

                lines.append(
                    (
                        0,
                        0,
                        {
                            "subject_id": subject.id,
                            "credits": subject.credits,
                            "attendance_score": attendance_score,
                            "quiz_score": quiz_score,
                            "midterm_score": midterm_score,
                            "assignment_score": assignment_score,
                            "final_exam_score": final_exam_score,
                            "final_score": total_final_score,
                            "grade": grade_line.name if grade_line else False,
                            "grade_point": grade_line.grade_point if grade_line else 0.0,
                            "is_passing": grade_line.is_passing if grade_line else False,
                            "evaluation_status": "completed" if is_completed else "in_progress",
                        },
                    )
                )

            card.write({"line_ids": lines, "state": "generated"})

    def action_approve(self):
        for card in self:
            vals = {"state": "approved"}
            if not card.verification_code:
                vals["verification_code"] = secrets.token_hex(8).upper()
            card.write(vals)

    def action_print_report_card(self):
        return self.env.ref("school_management.action_report_university_report_card").report_action(self)

    def _get_xlsx_data(self):
        self.ensure_one()
        headers = ["Subject", "Credits", "Grade", "Grade Point", "Passing"]
        rows = []
        for line in self.line_ids:
            rows.append([
                line.subject_id.name or '',
                line.credits or 0,
                line.grade or '',
                line.grade_point or 0.0,
                "Yes" if line.is_passing else "No",
            ])
        return (f"ReportCard_{self.student_id.student_id or self.id}", headers, rows)


class UniversityReportCardLine(models.Model):
    _name = "university.report.card.line"
    _description = "Report Card Line"
    _order = "subject_id"

    report_card_id = fields.Many2one(
        "university.report.card",
        string="Report Card",
        required=True,
        ondelete="cascade",
    )
    student_id = fields.Many2one("university.student", related="report_card_id.student_id", store=True)
    academic_year_id = fields.Many2one("university.academic.year", related="report_card_id.academic_year_id", store=True)
    semester_id = fields.Many2one("university.semester", related="report_card_id.semester_id", store=True)
    subject_id = fields.Many2one("university.subject", string="Subject", required=True)
    credits = fields.Integer(string="Credits")
    attendance_score = fields.Float(string="Attendance", digits=(5, 2))
    quiz_score = fields.Float(string="Quiz", digits=(5, 2))
    midterm_score = fields.Float(string="Midterm", digits=(5, 2))
    assignment_score = fields.Float(string="Assignment", digits=(5, 2))
    final_exam_score = fields.Float(string="Final Exam", digits=(5, 2))
    final_score = fields.Float(string="Total", digits=(5, 2))
    grade = fields.Char(string="Grade")
    grade_point = fields.Float(string="Grade Point", digits=(3, 2))
    is_passing = fields.Boolean(string="Passing")
    is_repeated = fields.Boolean(string="Repeated Course", default=False)
    counts_for_credits = fields.Boolean(string="Counts For Credits", default=True)
    evaluation_status = fields.Selection(
        [
            ("in_progress", "In Progress"),
            ("completed", "Completed"),
        ],
        string="Status",
        default="completed",
    )

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        result = super().fields_get(allfields=allfields, attributes=attributes)
        categories = self.env["university.assessment.category"].search([])
        labels = {
            "attendance_score": ("ATTENDANCE", "Att"),
            "quiz_score": ("QUIZ", "Quiz"),
            "midterm_score": ("MIDTERM", "Mid"),
            "assignment_score": ("ASSIGNMENT", "Assign"),
            "final_exam_score": ("EXAM", "Final"),
        }
        for field_name, (code, label) in labels.items():
            category = categories.filtered(lambda item: (item.code or "").upper() == code)[:1]
            if category and field_name in result:
                result[field_name]["string"] = f"{label} ({category.weight:g}%)"
        if "final_score" in result:
            total_weight = sum(categories.filtered(lambda item: item.active).mapped("weight"))
            result["final_score"]["string"] = f"Total ({total_weight:g}%)"
        return result


class UniversityTranscript(models.Model):
    _name = "university.transcript"
    _description = "Academic Transcript"
    _inherit = ["university.document.download.mixin"]
    _order = "id desc"

    _download_report_xmlid = "school_management.action_report_university_transcript"
    _download_states = ("approved",)

    name = fields.Char(
        string="Transcript Reference",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: "New",
    )
    student_id = fields.Many2one("university.student", string="Student", required=True)
    program_id = fields.Many2one("university.program", string="Major / Program", related="student_id.program_id", store=True)
    line_ids = fields.One2many("university.transcript.line", "transcript_id", string="Transcript Lines")
    grade_scale_id = fields.Many2one("university.grade.scale", string="Grade Scale")
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )
    academic_standing = fields.Selection(
        [
            ("dean_list", "Dean's List"),
            ("good", "Good Standing"),
            ("probation", "Academic Probation"),
        ],
        string="Academic Standing",
        compute="_compute_academic_standing",
        store=True,
    )
    cumulative_gpa = fields.Float(string="Cumulative GPA", compute="_compute_cumulative_gpa", store=True)
    total_credits = fields.Integer(string="Total Credits", compute="_compute_cumulative_gpa", store=True)
    state = fields.Selection(
        [("draft", "Draft"), ("generated", "Generated"), ("approved", "Approved")],
        string="Status",
        default="draft",
    )
    verification_code = fields.Char(string="Verification Code", copy=False, readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code("university.transcript") or "New"
        return super().create(vals_list)

    @api.depends("line_ids.credits", "line_ids.grade_point", "line_ids.subject_id")
    def _compute_cumulative_gpa(self):
        for transcript in self:
            subject_lines = {}
            for line in transcript.line_ids:
                subject_lines.setdefault(line.subject_id.id, []).append(line)

            best_lines = []
            for sub_id, l_list in subject_lines.items():
                if len(l_list) == 1:
                    best_lines.append(l_list[0])
                else:
                    sorted_attempts = sorted(
                        l_list,
                        key=lambda l: (
                            l.grade_point or 0.0,
                            l.academic_year_id.date_start or fields.Date.min,
                            l.semester_id.date_start or fields.Date.min,
                            l.id or 0,
                        ),
                        reverse=True,
                    )
                    best_lines.append(sorted_attempts[0])

            effective_credits = sum(l.credits for l in best_lines if l.is_passing or (l.grade_point or 0.0) > 0)
            quality = sum(l.credits * (l.grade_point or 0.0) for l in best_lines)
            gpa_credits = sum(l.credits for l in best_lines)

            transcript.total_credits = effective_credits
            transcript.cumulative_gpa = quality / gpa_credits if gpa_credits else 0.0

    @api.depends(
        "student_id.report_card_ids.academic_standing",
        "student_id.report_card_ids.state",
        "cumulative_gpa",
        "total_credits",
    )
    def _compute_academic_standing(self):
        ICP = self.env["ir.config_parameter"].sudo()
        try:
            min_gpa = float(ICP.get_param("school_management.deans_list_min_gpa", 3.5))
        except (ValueError, TypeError):
            min_gpa = 3.5
        try:
            min_credits = float(ICP.get_param("school_management.deans_list_min_credits", 12))
        except (ValueError, TypeError):
            min_credits = 12.0

        for transcript in self:
            cards = self.env["university.report.card"].search(
                [
                    ("student_id", "=", transcript.student_id.id),
                    ("state", "in", ["generated", "approved"]),
                ]
            )
            # Find chronologically latest card
            cards_sorted = cards.sorted(
                key=lambda c: (
                    c.academic_year_id.date_start or fields.Date.min,
                    c.semester_id.date_start or fields.Date.min,
                    c.id,
                ),
                reverse=True,
            )
            latest_card = cards_sorted[:1]
            if transcript.cumulative_gpa >= min_gpa and transcript.total_credits >= min_credits:
                transcript.academic_standing = "dean_list"
            elif latest_card and latest_card.academic_standing == "dean_list":
                transcript.academic_standing = "dean_list"
            elif transcript.cumulative_gpa >= 2.0:
                transcript.academic_standing = "good"
            else:
                transcript.academic_standing = "probation"

    def action_generate_lines(self):
        for transcript in self:
            cards = self.env["university.report.card"].search(
                [
                    ("student_id", "=", transcript.student_id.id),
                    ("state", "in", ["generated", "approved"]),
                ]
            )
            cards = cards.sorted(
                key=lambda c: (
                    c.academic_year_id.date_start or fields.Date.min,
                    c.semester_id.date_start or fields.Date.min,
                    c.id,
                )
            )
            raw_lines = []
            for card in cards:
                for card_line in card.line_ids:
                    raw_lines.append({
                        "academic_year_id": card.academic_year_id.id,
                        "semester_id": card.semester_id.id,
                        "subject_id": card_line.subject_id.id,
                        "credits": card_line.credits,
                        "final_score": card_line.final_score,
                        "grade": card_line.grade,
                        "grade_point": card_line.grade_point,
                        "is_passing": card_line.is_passing,
                        "date_sort": (
                            card.academic_year_id.date_start or fields.Date.min,
                            card.semester_id.date_start or fields.Date.min,
                        ),
                    })

            subject_groups = {}
            for item in raw_lines:
                subject_groups.setdefault(item["subject_id"], []).append(item)

            for sub_id, items in subject_groups.items():
                if len(items) == 1:
                    items[0]["is_repeated"] = False
                    items[0]["counts_for_credits"] = True
                else:
                    sorted_items = sorted(
                        items,
                        key=lambda x: (x["grade_point"] or 0.0, x["date_sort"]),
                        reverse=True,
                    )
                    sorted_items[0]["is_repeated"] = False
                    sorted_items[0]["counts_for_credits"] = True
                    for rep in sorted_items[1:]:
                        rep["is_repeated"] = True
                        rep["counts_for_credits"] = False

            lines = [(5, 0, 0)]
            for item in raw_lines:
                vals_line = dict(item)
                vals_line.pop("date_sort", None)
                lines.append((0, 0, vals_line))

            vals = {"line_ids": lines, "state": "generated"}
            scale = cards.mapped("grade_scale_id")[:1]
            if scale:
                vals["grade_scale_id"] = scale.id
            transcript.write(vals)

    def action_approve(self):
        for transcript in self:
            vals = {"state": "approved"}
            if not transcript.verification_code:
                vals["verification_code"] = secrets.token_hex(8).upper()
            transcript.write(vals)

    def action_print_transcript(self):
        return self.env.ref("school_management.action_report_university_transcript").report_action(self)

    def _get_xlsx_data(self):
        self.ensure_one()
        headers = ["Academic Year", "Semester", "Subject", "Credits", "Grade", "Grade Point"]
        rows = []
        for line in self.line_ids:
            rows.append([
                line.academic_year_id.name or '',
                line.semester_id.name or '',
                line.subject_id.name or '',
                line.credits or 0,
                line.grade or '',
                line.grade_point or 0.0,
            ])
        return (f"Transcript_{self.student_id.student_id or self.id}", headers, rows)


class UniversityTranscriptLine(models.Model):
    _name = "university.transcript.line"
    _description = "Transcript Line"
    _order = "academic_year_id, semester_id, subject_id"

    transcript_id = fields.Many2one(
        "university.transcript",
        string="Transcript",
        required=True,
        ondelete="cascade",
    )
    academic_year_id = fields.Many2one("university.academic.year", string="Academic Year")
    semester_id = fields.Many2one("university.semester", string="Semester")
    subject_id = fields.Many2one("university.subject", string="Subject", required=True)
    credits = fields.Integer(string="Credits")
    final_score = fields.Float(string="Final Score")
    grade = fields.Char(string="Grade")
    grade_point = fields.Float(string="Grade Point")
    is_passing = fields.Boolean(string="Passing")
