from odoo import api, fields, models
from odoo.exceptions import UserError
from .academic_lock import can_maintain_closed_year_records


class UniversitySemesterSubject(models.Model):
    _name = "university.semester.subject"
    _description = "Semester Subject Offering"
    _rec_name = "display_name"
    _order = "academic_year_id desc, semester_id, subject_id"

    semester_id = fields.Many2one(
        "university.semester",
        string="Semester",
        required=True,
        ondelete="cascade",
    )
    subject_id = fields.Many2one(
        "university.subject",
        string="Subject",
        required=True,
        ondelete="cascade",
    )
    subject_code = fields.Char(
        string="Subject Code",
        related="subject_id.code",
        store=True,
        readonly=True,
    )
    academic_year_id = fields.Many2one(
        "university.academic.year",
        related="semester_id.academic_year_id",
        string="Academic Year",
        store=True,
        readonly=True,
    )
    department_id = fields.Many2one(
        "university.department",
        related="subject_id.department_id",
        string="Department",
        store=True,
        readonly=True,
    )
    faculty_id = fields.Many2one(
        "university.faculty",
        related="department_id.faculty_id",
        string="Faculty",
        store=True,
        readonly=True,
    )
    teacher_ids = fields.Many2many(
        "university.teacher",
        string="Instructors",
        related="subject_id.teacher_ids",
        readonly=True,
    )
    credits = fields.Integer(
        related="subject_id.credits",
        string="Credits",
        readonly=True,
    )
    display_name = fields.Char(
        string="Display Name",
        compute="_compute_display_name",
        store=True,
    )
    book_ids = fields.Many2many(
        "product.template",
        string="Textbooks",
        compute="_compute_book_ids",
        readonly=True,
    )
    active = fields.Boolean(string="Active", default=True)

    section_count = fields.Integer(
        string="Active Sections",
        compute="_compute_section_metrics",
    )
    enrollment_count = fields.Integer(
        string="Enrolled Students",
        compute="_compute_section_metrics",
    )

    _unique_semester_subject = models.Constraint(
        "UNIQUE (semester_id, subject_id)",
        "This subject is already offered in the selected semester. An archived offering may already exist.",
    )

    @api.depends("subject_id.book_link_ids.product_tmpl_id")
    def _compute_book_ids(self):
        for rec in self:
            rec.book_ids = rec.subject_id.book_link_ids.mapped("product_tmpl_id")

    @api.depends("semester_id", "subject_id")
    def _compute_section_metrics(self):
        for rec in self:
            if not rec.semester_id or not rec.subject_id:
                rec.section_count = 0
                rec.enrollment_count = 0
                continue
            sections = self.env["university.class.section"].search([
                ("semester_id", "=", rec.semester_id.id),
                ("subject_id", "=", rec.subject_id.id),
            ])
            rec.section_count = len(sections)
            rec.enrollment_count = self.env["university.enrollment"].search_count([
                ("class_section_id", "in", sections.ids),
                ("status", "=", "enrolled"),
            ]) if sections else 0

    def action_view_sections(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": f"Sections for {self.subject_id.name}",
            "res_model": "university.class.section",
            "view_mode": "list,form",
            "domain": [
                ("semester_id", "=", self.semester_id.id),
                ("subject_id", "=", self.subject_id.id),
            ],
            "context": {
                "default_semester_id": self.semester_id.id,
                "default_subject_id": self.subject_id.id,
                "default_academic_year_id": self.academic_year_id.id,
            },
        }

    def _effective_semesters_for_create(self, vals_list):
        default_semester_id = self.default_get(["semester_id"]).get("semester_id")
        semester_ids = {
            vals["semester_id"]
            if "semester_id" in vals
            else default_semester_id
            for vals in vals_list
        }
        return self.env["university.semester"].browse(
            [semester_id for semester_id in semester_ids if semester_id]
        ).exists()

    @staticmethod
    def _has_locked_year(records):
        return any(
            record.academic_year_id.state in ("closed", "archived")
            for record in records
        )

    @api.model_create_multi
    def create(self, vals_list):
        if not can_maintain_closed_year_records(self.env):
            semesters = self._effective_semesters_for_create(vals_list)
            if any(
                semester.academic_year_id.state in ("closed", "archived")
                for semester in semesters
            ):
                raise UserError(
                    "Cannot create semester subjects in a closed or archived academic year."
                )
        return super().create(vals_list)

    def write(self, vals):
        if not can_maintain_closed_year_records(self.env):
            if self._has_locked_year(self):
                raise UserError("Semester subjects of a closed or archived academic year are read-only and cannot be modified.")
            if "semester_id" in vals:
                destination = self.env["university.semester"].browse(
                    vals["semester_id"]
                ).exists()
                if destination.academic_year_id.state in ("closed", "archived"):
                    raise UserError(
                        "Cannot move a semester subject into a closed or archived academic year."
                    )
        return super().write(vals)

    def unlink(self):
        if not can_maintain_closed_year_records(self.env):
            if self._has_locked_year(self):
                raise UserError("Cannot delete semester subjects of a closed or archived academic year.")
        return super().unlink()

    @api.depends("semester_id.name", "subject_id.name")
    def _compute_display_name(self):
        for rec in self:
            if rec.semester_id and rec.subject_id:
                rec.display_name = f"{rec.semester_id.name} - {rec.subject_id.name}"
            elif rec.subject_id:
                rec.display_name = rec.subject_id.name
            else:
                rec.display_name = "Semester Subject"
