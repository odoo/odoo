from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class UniversityLessonPlan(models.Model):
    _name = "university.lesson.plan"
    _description = "Lesson Plan"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc"

    name = fields.Char(string="Title", required=True, tracking=True)
    teacher_id = fields.Many2one(
        "university.teacher",
        string="Prepared By",
        required=True,
        default=lambda self: self._default_teacher(),
    )
    subject_id = fields.Many2one("university.subject", string="Subject", required=True)
    section_id = fields.Many2one(
        "university.class.section", string="Grade/Section", required=True
    )
    description = fields.Html(string="Lesson Plan")
    share_to = fields.Selection(
        [("all", "All"), ("only_me", "Only Me")],
        string="Shared To",
        default="all",
    )
    state = fields.Selection(
        [("draft", "Draft"), ("approved", "Approved")],
        string="Status",
        default="draft",
        tracking=True,
    )
    assignment_count = fields.Integer(
        string="Assignment Count",
        compute="_compute_assignment_count",
    )

    # Helper field: the subjects that belong to the selected section.
    # The form view uses it in the Subject field domain.
    plan_allowed_subject_ids = fields.Many2many(
        "university.subject",
        string="Allowed Subjects",
        compute="_compute_plan_allowed_subject_ids",
    )

    # ------------------------------------------------------------------
    # Compute / onchange / constraints
    # ------------------------------------------------------------------
    @api.depends(
        "section_id",
        "section_id.subject_id",
        "section_id.program_id",
        "section_id.program_id.subject_ids",
    )
    def _compute_plan_allowed_subject_ids(self):
        for plan in self:
            section = plan.section_id
            plan.plan_allowed_subject_ids = (
                section.subject_id or section.program_id.subject_ids
            )

    @api.onchange("section_id")
    def _onchange_section_id_set_subject(self):
        allowed = self.section_id.subject_id or self.section_id.program_id.subject_ids
        if self.subject_id not in allowed:
            self.subject_id = False
        if len(allowed) == 1:
            self.subject_id = allowed

    @api.constrains("subject_id", "section_id")
    def _check_subject_is_taught(self):
        for rec in self:
            allowed = rec.section_id.subject_id or rec.section_id.program_id.subject_ids
            if rec.subject_id and rec.subject_id not in allowed:
                raise ValidationError(
                    _("This subject is not in the selected section.")
                )

    @api.depends("section_id", "subject_id")
    def _compute_assignment_count(self):
        for plan in self:
            plan.assignment_count = self.env["university.assignment"].search_count([
                ("section_id", "=", plan.section_id.id),
                ("subject_id", "=", plan.subject_id.id),
            ])

    # ------------------------------------------------------------------
    # Defaults
    # ------------------------------------------------------------------
    def _default_teacher(self):
        teacher = self.env["university.teacher"].search(
            [("user_id", "=", self.env.uid)], limit=1
        )
        return teacher.id if teacher else False

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def action_approve(self):
        self.write({"state": "approved"})

    def action_draft(self):
        self.write({"state": "draft"})

    def action_view_assignments(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Assignments - %s", self.name),
            "res_model": "university.assignment",
            "view_mode": "kanban,list,form",
            "domain": [
                ("section_id", "=", self.section_id.id),
                ("subject_id", "=", self.subject_id.id),
            ],
            "context": {
                "default_section_id": self.section_id.id,
                "default_subject_id": self.subject_id.id,
                "default_teacher_id": self.teacher_id.id,
            },
        }
