# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class UniversityCourseEvaluation(models.Model):
    _name = "university.course.evaluation"
    _description = "Student Course & Lecturer Evaluation Survey"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "evaluation_date desc, id desc"

    student_id = fields.Many2one(
        "university.student",
        string="Student",
        required=True,
        default=lambda self: self._default_student_id(),
        tracking=True,
    )
    section_id = fields.Many2one(
        "university.class.section",
        string="Class Section",
        required=True,
        domain="[('enrollment_ids.student_id', '=', student_id), ('enrollment_ids.status', '=', 'enrolled')]",
    )
    subject_id = fields.Many2one(
        "university.subject",
        string="Course / Subject",
        related="section_id.subject_id",
        store=True,
        readonly=True,
    )
    teacher_id = fields.Many2one(
        "university.teacher",
        string="Lecturer / Instructor",
        related="section_id.teacher_id",
        store=True,
        readonly=True,
    )
    academic_year_id = fields.Many2one(
        "university.academic.year",
        string="Academic Year",
        related="section_id.academic_year_id",
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
    evaluation_date = fields.Date(
        string="Evaluation Date",
        default=fields.Date.context_today,
        readonly=True,
    )
    state = fields.Selection(
        [("draft", "Draft"), ("submitted", "Submitted")],
        string="Status",
        default="draft",
        tracking=True,
    )

    # Evaluation Criteria (1 to 5 scale)
    rating_content = fields.Selection(
        [
            ("1", "1 - Poor"),
            ("2", "2 - Fair"),
            ("3", "3 - Satisfactory"),
            ("4", "4 - Very Good"),
            ("5", "5 - Excellent"),
        ],
        string="Course Content & Organization",
        required=True,
        default="5",
    )
    rating_teaching = fields.Selection(
        [
            ("1", "1 - Poor"),
            ("2", "2 - Fair"),
            ("3", "3 - Satisfactory"),
            ("4", "4 - Very Good"),
            ("5", "5 - Excellent"),
        ],
        string="Teaching Quality & Interaction",
        required=True,
        default="5",
    )
    rating_punctuality = fields.Selection(
        [
            ("1", "1 - Poor"),
            ("2", "2 - Fair"),
            ("3", "3 - Satisfactory"),
            ("4", "4 - Very Good"),
            ("5", "5 - Excellent"),
        ],
        string="Punctuality & Availability",
        required=True,
        default="5",
    )
    rating_grading = fields.Selection(
        [
            ("1", "1 - Poor"),
            ("2", "2 - Fair"),
            ("3", "3 - Satisfactory"),
            ("4", "4 - Very Good"),
            ("5", "5 - Excellent"),
        ],
        string="Fairness of Grading & Feedback",
        required=True,
        default="5",
    )
    rating_facilities = fields.Selection(
        [
            ("1", "1 - Poor"),
            ("2", "2 - Fair"),
            ("3", "3 - Satisfactory"),
            ("4", "4 - Very Good"),
            ("5", "5 - Excellent"),
        ],
        string="Learning Environment & Facilities",
        required=True,
        default="5",
    )
    comments = fields.Text(
        string="Constructive Feedback / Suggestions",
        help="Confidential feedback shared anonymously with faculty to improve instructional quality.",
    )
    strengths = fields.Text(
        string="Key Strengths",
        help="What were the most effective strengths of this course and lecturer?",
    )
    improvements = fields.Text(
        string="Areas for Improvement",
        help="What areas or topics could be improved for future cohorts?",
    )
    additional_comments = fields.Text(
        string="Additional Comments / Suggestions",
        help="Any additional recommendations or feedback...",
    )
    average_score = fields.Float(
        string="Average Rating",
        compute="_compute_average_score",
        store=True,
        digits=(3, 2),
    )

    _student_section_unique = models.Constraint(
        "UNIQUE(student_id, section_id)",
        "You have already submitted an evaluation for this class section.",
    )

    @api.model
    def _default_student_id(self):
        user = self.env.user
        student = self.env["university.student"].search([("user_id", "=", user.id)], limit=1)
        if not student and self.env.context.get("default_student_id"):
            student = self.env["university.student"].browse(self.env.context.get("default_student_id"))
        return student.id if student else False

    @api.depends("rating_content", "rating_teaching", "rating_punctuality", "rating_grading", "rating_facilities")
    def _compute_average_score(self):
        for rec in self:
            scores = [
                int(rec.rating_content or 5),
                int(rec.rating_teaching or 5),
                int(rec.rating_punctuality or 5),
                int(rec.rating_grading or 5),
                int(rec.rating_facilities or 5),
            ]
            rec.average_score = round(sum(scores) / len(scores), 2)

    @api.model
    def action_open_student_evaluations(self):
        """Prepare one draft evaluation per enrolled section for the current student."""
        student_id = self._default_student_id()
        if not student_id:
            raise UserError(_("No student profile is linked to your user account."))
        student = self.env["university.student"].browse(student_id).exists()
        if not student:
            raise UserError(_("No student profile is linked to your user account."))

        sections = self.env["university.class.section"].search([
            ("enrollment_ids.student_id", "=", student.id),
            ("enrollment_ids.status", "=", "enrolled"),
        ])
        existing = self.search([
            ("student_id", "=", student.id),
            ("section_id", "in", sections.ids),
        ])
        existing_sections = set(existing.mapped("section_id").ids)
        missing = sections.filtered(lambda section: section.id not in existing_sections)
        if missing:
            self.create([
                {"student_id": student.id, "section_id": section.id}
                for section in missing
            ])

        action = self.env["ir.actions.act_window"]._for_xml_id(
            "school_management.action_university_course_evaluation_student"
        )
        action["domain"] = [("student_id", "=", student.id)]
        action["context"] = {
            **dict(self.env.context),
            "default_student_id": student.id,
        }
        return action

    def action_submit_evaluation(self):
        self.ensure_one()
        self.write({"state": "submitted"})
        self.message_post(body=_("Course & Lecturer evaluation submitted successfully."))
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Evaluation Completed"),
                "message": _("Thank you! Your feedback has been recorded and course grades are unmasked."),
                "type": "success",
            },
        }

    def action_submit(self):
        return self.action_submit_evaluation()
