from datetime import timedelta
from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError

class UniversityAssignment(models.Model):
    _name = "university.assignment"
    _description = "Assignment"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc"

    name = fields.Char(string="Assignment Name", required=True, tracking=True)
    teacher_id = fields.Many2one(
        "university.teacher", 
        string="Prepared By", 
        required=True, 
        default=lambda self: self._default_teacher()
    )
    subject_id = fields.Many2one("university.subject", string="Subject", required=True)
    section_id = fields.Many2one("university.class.section", string="Grade/Section", required=True)
    assignment_type = fields.Selection(
        [("class", "Class Assignment"), ("student", "Student Assignment")],
        string="Assignment Type",
        required=True,
        default="class"
    )
    description = fields.Html(string="Description")
    due_date = fields.Date(string="Due Date", index=True)
    category_id = fields.Many2one(
        "university.assessment.category",
        string="Assessment Category",
        domain="[('active', '=', True)]",
    )
    max_score = fields.Float(string="Max Score", default=100.0)
    is_due_this_week = fields.Boolean(
        string="Due This Week",
        compute="_compute_is_due_this_week",
        search="_search_is_due_this_week",
    )
    submission_ids = fields.One2many(
        "university.assignment.submission",
        "assignment_id",
        string="Submissions",
    )
    submission_count = fields.Integer(
        string="Submission Count",
        compute="_compute_submission_count",
    )
    state = fields.Selection(
        [("draft", "Draft"), ("approved", "Approved")], 
        string="Status", 
        default="draft", 
        tracking=True
    )
    
    student_id = fields.Many2one(
        "university.student", 
        string="Student", 
        help="Specific student if this is a Student Assignment"
    )

    my_submission_id = fields.Many2one(
        "university.assignment.submission",
        string="My Submission",
        compute="_compute_my_submission",
    )
    my_submission_state = fields.Selection(
        [
            ("draft", "Draft"),
            ("submitted", "Submitted"),
            ("reviewing", "Reviewing"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
            ("evaluated", "Evaluated"),
            ("returned", "Returned"),
        ],
        string="My Submission Status",
        compute="_compute_my_submission",
    )
    my_submission_score = fields.Float(
        string="My Score",
        compute="_compute_my_submission",
    )

    def _default_teacher(self):
        teacher = self.env["university.teacher"].search([("user_id", "=", self.env.uid)], limit=1)
        return teacher.id if teacher else False

    @api.depends("due_date")
    def _compute_is_due_this_week(self):
        today = fields.Date.context_today(self)
        monday = today - timedelta(days=today.weekday())
        sunday = monday + timedelta(days=6)
        for rec in self:
            rec.is_due_this_week = bool(rec.due_date and monday <= rec.due_date <= sunday)

    def _search_is_due_this_week(self, operator, value):
        if operator not in ("=", "!="):
            return []
        today = fields.Date.context_today(self)
        monday = today - timedelta(days=today.weekday())
        sunday = monday + timedelta(days=6)
        matching_domain = [("due_date", ">=", monday), ("due_date", "<=", sunday)]
        if (operator == "=" and value) or (operator == "!=" and not value):
            return matching_domain
        return ["|", ("due_date", "<", monday), ("due_date", ">", sunday)]

    @api.depends("submission_ids")
    def _compute_submission_count(self):
        for assignment in self:
            assignment.submission_count = len(assignment.submission_ids)

    def _compute_my_submission(self):
        user = self.env.user
        student = self.env["university.student"].search([("user_id", "=", user.id)], limit=1)
        if not student:
            for assignment in self:
                assignment.my_submission_id = False
                assignment.my_submission_state = False
                assignment.my_submission_score = 0.0
            return

        submissions = self.env["university.assignment.submission"].search([
            ("assignment_id", "in", self.ids),
            ("student_id", "=", student.id),
        ])
        sub_by_assign = {s.assignment_id.id: s for s in submissions}
        for assignment in self:
            sub = sub_by_assign.get(assignment.id)
            assignment.my_submission_id = sub.id if sub else False
            assignment.my_submission_state = sub.state if sub else False
            assignment.my_submission_score = sub.score if sub else 0.0

    def action_approve(self):
        self.write({"state": "approved"})

    def action_draft(self):
        self.write({"state": "draft"})

    def action_view_submissions(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Assignment Submissions",
            "res_model": "university.assignment.submission",
            "view_mode": "kanban,list,form",
            "domain": [("assignment_id", "=", self.id)],
            "context": {
                "default_assignment_id": self.id,
                "default_section_id": self.section_id.id,
                "default_subject_id": self.subject_id.id,
                "default_teacher_id": self.teacher_id.id,
                "default_category_id": self.category_id.id,
                "default_max_score": self.max_score,
            },
        }

    def action_student_submit_work(self):
        self.ensure_one()
        user = self.env.user
        student = self.env["university.student"].search([("user_id", "=", user.id)], limit=1)
        if not student:
            raise ValidationError(_("No student record found for your user account."))

        submission = self.env["university.assignment.submission"].search([
            ("assignment_id", "=", self.id),
            ("student_id", "=", student.id),
        ], limit=1)

        if not submission:
            submission = self.env["university.assignment.submission"].create({
                "assignment_id": self.id,
                "student_id": student.id,
                "state": "draft",
            })

        return {
            "type": "ir.actions.act_window",
            "name": _("Submit Work: %s", self.name),
            "res_model": "university.assignment.submission",
            "view_mode": "form",
            "res_id": submission.id,
            "target": "current",
        }

    @api.constrains("max_score")
    def _check_max_score(self):
        for assignment in self:
            if assignment.max_score <= 0:
                raise ValidationError("Assignment maximum score must be greater than zero.")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            section = False
            if vals.get("section_id"):
                section = self.env["university.class.section"].browse(vals["section_id"])

            if section and not vals.get("teacher_id"):
                if not section.teacher_id:
                    raise ValidationError(_("Please set a Teacher on the class before adding assignments."))
                teacher = section.teacher_id
                if teacher._name == "university.teacher":
                    vals["teacher_id"] = teacher.id
                elif teacher._name == "res.users":
                    teacher_rec = self.env["university.teacher"].search([("user_id", "=", teacher.id)], limit=1)
                    if not teacher_rec:
                        raise ValidationError(_("Please set a Teacher on the class before adding assignments."))
                    vals["teacher_id"] = teacher_rec.id
                elif hasattr(teacher, "teacher_id") and teacher.teacher_id:
                    vals["teacher_id"] = teacher.teacher_id.id
                else:
                    vals["teacher_id"] = teacher.id

            if section and not vals.get("subject_id") and section.subject_id:
                vals["subject_id"] = section.subject_id.id

        return super().create(vals_list)


class UniversityAssignmentSubmission(models.Model):
    _name = "university.assignment.submission"
    _description = "Assignment Submission"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "submitted_on desc, id desc"

    name = fields.Char(string="Reference", compute="_compute_name", store=True)
    assignment_id = fields.Many2one(
        "university.assignment",
        string="Assignment",
        required=True,
        ondelete="cascade",
        domain="[('state', '=', 'approved')]",
    )
    student_id = fields.Many2one(
        "university.student",
        string="Student",
        required=True,
        default=lambda self: self._default_student(),
    )
    section_id = fields.Many2one(
        "university.class.section",
        string="Class Section",
        related="assignment_id.section_id",
        store=True,
        readonly=True,
    )
    subject_id = fields.Many2one(
        "university.subject",
        string="Subject",
        related="assignment_id.subject_id",
        store=True,
        readonly=True,
    )
    teacher_id = fields.Many2one(
        "university.teacher",
        string="Teacher",
        related="assignment_id.teacher_id",
        store=True,
        readonly=True,
    )
    academic_year_id = fields.Many2one(
        "university.academic.year",
        string="Academic Year",
        related="section_id.semester_id.academic_year_id",
        store=True,
        readonly=True,
    )
    semester_id = fields.Many2one(
        "university.semester",
        string="Semester",
        related="section_id.semester_id",
        store=True,
        readonly=True,
    )
    category_id = fields.Many2one(
        "university.assessment.category",
        string="Assessment Category",
        related="assignment_id.category_id",
        store=True,
        readonly=True,
    )
    submitted_on = fields.Datetime(string="Submitted On")
    answer_text = fields.Html(string="Submission Text")
    attachment_ids = fields.Many2many(
        "ir.attachment",
        "university_assignment_submission_attachment_rel",
        "submission_id",
        "attachment_id",
        string="Attachments",
    )
    score = fields.Float(string="Score")
    max_score = fields.Float(
        string="Max Score",
        related="assignment_id.max_score",
        store=True,
        readonly=True,
    )
    feedback = fields.Html(string="Teacher Feedback")
    assessment_result_id = fields.Many2one(
        "university.assessment.result",
        string="Assessment Result",
        readonly=True,
        copy=False,
    )
    can_edit_status = fields.Boolean(
        string="Can Edit Status",
        compute="_compute_can_edit_status",
    )
    is_evaluated = fields.Boolean(
        string="Is Evaluated",
        compute="_compute_is_evaluated",
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("submitted", "Submitted"),
            ("reviewing", "Reviewing"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
            ("evaluated", "Evaluated"),
            ("returned", "Returned"),
        ],
        string="Status",
        default="draft",
        tracking=True,
    )

    def _default_student(self):
        student = self.env["university.student"].search([("user_id", "=", self.env.uid)], limit=1)
        return student.id if student else False

    @api.depends("state")
    def _compute_is_evaluated(self):
        for sub in self:
            sub.is_evaluated = sub.state in ("approved", "evaluated")

    @api.depends_context("uid")
    def _compute_can_edit_status(self):
        is_teacher_or_admin = (
            self.env.user.has_group("school_management.group_school_teacher")
            or self.env.user.has_group("school_management.group_school_admin")
            or self.env.is_superuser()
        )
        for submission in self:
            submission.can_edit_status = is_teacher_or_admin

    @api.depends("assignment_id.name", "student_id.name")
    def _compute_name(self):
        for submission in self:
            if submission.assignment_id and submission.student_id:
                submission.name = f"{submission.assignment_id.name} - {submission.student_id.name}"
            else:
                submission.name = "Assignment Submission"

    @api.constrains("student_id", "assignment_id")
    def _check_student_enrolled(self):
        for submission in self:
            if not submission.student_id or not submission.section_id:
                continue
            enrolled = self.env["university.enrollment"].search_count(
                [
                    ("student_id", "=", submission.student_id.id),
                    ("section_id", "=", submission.section_id.id),
                    ("status", "=", "enrolled"),
                ]
            )
            if not enrolled:
                raise ValidationError("Only enrolled students can submit work for this assignment.")

    @api.constrains("score", "max_score")
    def _check_score(self):
        for submission in self.filtered(lambda item: item.state in ("approved", "evaluated")):
            if submission.score < 0 or submission.score > submission.max_score:
                raise ValidationError("Submission score must be between 0 and the assignment maximum score.")

    @api.model_create_multi
    def create(self, vals_list):
        is_teacher_or_admin = (
            self.env.user.has_group("school_management.group_school_teacher")
            or self.env.user.has_group("school_management.group_school_admin")
            or self.env.is_superuser()
        )
        for vals in vals_list:
            if "state" in vals and vals["state"] != "draft" and not is_teacher_or_admin:
                raise AccessError(_("Students cannot set submission status directly upon creation."))
        return super().create(vals_list)

    def write(self, vals):
        is_teacher_or_admin = (
            self.env.user.has_group("school_management.group_school_teacher")
            or self.env.user.has_group("school_management.group_school_admin")
            or self.env.is_superuser()
        )
        if "state" in vals and not is_teacher_or_admin:
            raise AccessError(_("Only teachers and administrators can update the submission status."))
        if any(f in vals for f in ("score", "feedback", "assessment_result_id")) and not is_teacher_or_admin:
            raise AccessError(_("Only teachers and administrators can grade or give feedback on submissions."))
        if not is_teacher_or_admin:
            for sub in self:
                if sub.state in ("submitted", "reviewing", "approved", "evaluated") and any(
                    f in vals for f in ("answer_text", "attachment_ids", "assignment_id", "student_id")
                ):
                    raise ValidationError(_("You cannot modify an assignment that has already been submitted or reviewed."))
        return super().write(vals)

    def unlink(self):
        is_admin = self.env.user.has_group("school_management.group_school_admin") or self.env.is_superuser()
        if not is_admin:
            raise AccessError(_("Only administrators are allowed to delete assignment submissions."))
        return super().unlink()

    def action_submit(self):
        for submission in self:
            if submission.state not in ("draft", "rejected", "returned"):
                raise ValidationError(_("Only draft or returned/rejected submissions can be submitted."))
            if not submission.answer_text and not submission.attachment_ids:
                raise ValidationError(_("Add submission text or at least one attachment before submitting."))
            submission.sudo().write(
                {
                    "state": "submitted",
                    "submitted_on": fields.Datetime.now(),
                }
            )

    def action_start_review(self):
        is_teacher_or_admin = (
            self.env.user.has_group("school_management.group_school_teacher")
            or self.env.user.has_group("school_management.group_school_admin")
            or self.env.is_superuser()
        )
        if not is_teacher_or_admin:
            raise AccessError(_("Only teachers and administrators can review submissions."))
        for submission in self:
            if submission.state != "submitted":
                raise ValidationError(_("Only submitted assignments can be marked as reviewing."))
            submission.write({"state": "reviewing"})

    def action_approve(self):
        is_teacher_or_admin = (
            self.env.user.has_group("school_management.group_school_teacher")
            or self.env.user.has_group("school_management.group_school_admin")
            or self.env.is_superuser()
        )
        if not is_teacher_or_admin:
            raise AccessError(_("Only teachers and administrators can approve submissions."))
        for submission in self:
            if not submission.category_id:
                raise ValidationError(_("Set an assessment category on the assignment before approval."))
            if submission.score < 0 or submission.score > submission.max_score:
                raise ValidationError(_("Submission score must be between 0 and the assignment maximum score."))
            vals = {
                "student_id": submission.student_id.id,
                "section_id": submission.section_id.id,
                "subject_id": submission.subject_id.id,
                "teacher_id": submission.teacher_id.id,
                "academic_year_id": submission.academic_year_id.id,
                "semester_id": submission.semester_id.id,
                "category_id": submission.category_id.id,
                "assignment_id": submission.assignment_id.id,
                "submission_id": submission.id,
                "score": submission.score,
                "max_score": submission.max_score,
                "state": "published",
            }
            if submission.assessment_result_id:
                submission.assessment_result_id.write(vals)
            else:
                submission.assessment_result_id = self.env["university.assessment.result"].create(vals)
            submission.write({"state": "approved"})

    def action_evaluate(self):
        return self.action_approve()

    def action_reject(self):
        is_teacher_or_admin = (
            self.env.user.has_group("school_management.group_school_teacher")
            or self.env.user.has_group("school_management.group_school_admin")
            or self.env.is_superuser()
        )
        if not is_teacher_or_admin:
            raise AccessError(_("Only teachers and administrators can reject submissions."))
        for submission in self:
            submission.write({"state": "rejected"})

    def action_return(self):
        return self.action_reject()
