from odoo import api, fields, models
from odoo.exceptions import UserError


class UniversityProgram(models.Model):
    _name = "university.program"
    _description = "University Program"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "name"

    name = fields.Char(string="Program Name", required=True, tracking=True)
    code = fields.Char(string="Program Code", required=True, tracking=True)
    department_id = fields.Many2one(
        "university.department", string="Department", required=True, tracking=True
    )
    faculty_id = fields.Many2one(
        "university.faculty",
        string="Faculty",
        related="department_id.faculty_id",
        store=True,
        readonly=True,
    )
    degree_type = fields.Selection(
        [
            ("bachelor", "Bachelor"),
            ("master", "Master"),
            ("doctorate", "Doctorate"),
            ("diploma", "Diploma"),
        ],
        string="Degree Type",
        default="bachelor",
        required=True,
        tracking=True,
    )
    duration_years = fields.Integer(string="Duration (Years)", default=4, tracking=True)
    total_credits = fields.Integer(string="Total Credits Required", default=120, tracking=True)
    min_graduation_grade_id = fields.Many2one(
        "university.grade.scale.line",
        string="Minimum Graduation Grade",
        help="Minimum passing grade required for graduation. If not set, falls back to the lowest passing scale line.",
        tracking=True,
    )
    student_ids = fields.One2many(
        "university.student", "program_id", string="Students"
    )
    subject_ids = fields.Many2many(
        "university.subject",
        "university_program_subject_rel",
        "program_id",
        "subject_id",
        string="Subjects",
    )
    curriculum_line_ids = fields.One2many(
        "university.curriculum.line",
        "program_id",
        string="Curriculum Lines",
    )
    section_ids = fields.One2many(
        "university.class.section",
        "program_id",
        string="Class Sections",
    )
    subject_count = fields.Integer(
        string="Subject Count",
        compute="_compute_counts",
        store=True,
    )
    student_count = fields.Integer(
        string="Student Count",
        compute="_compute_counts",
        store=True,
    )
    active_student_count = fields.Integer(
        string="Active Students",
        compute="_compute_counts",
        store=True,
    )
    section_count = fields.Integer(
        string="Section Count",
        compute="_compute_counts",
        store=True,
    )
    exam_score_count = fields.Integer(
        string="Exam & Quiz Results",
        compute="_compute_exam_score_count",
    )
    active = fields.Boolean(string="Active", default=True, tracking=True)
    color = fields.Integer(string="Color Index", default=0)

    @api.depends("subject_ids", "student_ids.status", "section_ids")
    def _compute_counts(self):
        for program in self:
            program.subject_count = len(program.subject_ids)
            program.student_count = len(program.student_ids)
            program.active_student_count = len(
                program.student_ids.filtered(lambda s: s.status == "active")
            )
            program.section_count = len(program.section_ids)

    def _compute_exam_score_count(self):
        for program in self:
            program.exam_score_count = self.env["university.exam.score"].search_count([
                ("exam_id.program_id", "=", program.id)
            ])

    def action_view_students(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id("school_management.action_university_student")
        action["domain"] = [("program_id", "=", self.id)]
        action["context"] = {"default_program_id": self.id}
        return action

    def action_view_subjects(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id("school_management.action_university_subject")
        action["domain"] = [("program_ids", "in", self.id)]
        action["context"] = {"default_program_ids": [(4, self.id)], "search_default_program_ids": self.id}
        return action

    def action_view_sections(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id("school_management.action_university_class_section")
        action["domain"] = [("program_id", "=", self.id)]
        action["context"] = {"default_program_id": self.id}
        return action

    def action_view_exam_scores(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id("school_management.action_university_exam_score")
        action["domain"] = [("exam_id.program_id", "=", self.id)]
        action["context"] = {"search_default_group_by_exam": 1}
        action["name"] = _("Exam & Quiz Results - %s") % self.name
        return action

    def action_link_department_subjects(self):
        self.ensure_one()
        subjects = self.env["university.subject"].search([
            ("department_id", "=", self.department_id.id),
            ("program_ids", "=", False),
        ])
        if not subjects:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "No Subjects to Link",
                    "message": "All subjects in this department are already linked to a major.",
                    "type": "warning",
                    "sticky": False,
                },
            }
        subjects.write({"program_ids": [(4, self.id)]})
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Subjects Linked",
                "message": f"{len(subjects)} subject(s) linked to {self.name}.",
                "type": "success",
                "sticky": False,
            },
        }

    def action_print_curriculum_report(self):
        """Print the Semester Curriculum PDF for the selected program(s)."""
        return self.env.ref(
            "school_management.action_report_curriculum"
        ).report_action(self)

    @api.model
    def action_print_curriculum_5plus(self):
        """
        Find all active programs with >= 5 active students and print
        their semester curriculum. Called from the Enrollment list toolbar.
        """
        programs = self.search([("active", "=", True)])
        qualified = programs.filtered(
            lambda p: len(
                p.student_ids.filtered(lambda s: s.status == "active")
            ) >= 5
        )
        if not qualified:
            raise UserError(
                "No major currently has 5 or more active students enrolled."
            )
        return self.env.ref(
            "school_management.action_report_curriculum"
        ).report_action(qualified)
