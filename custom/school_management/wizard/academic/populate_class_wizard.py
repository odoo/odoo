from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError


class UniversityPopulateClassWizard(models.TransientModel):
    _name = "university.populate.class.wizard"
    _description = "Populate Class Wizard"

    section_id = fields.Many2one(
        "university.class.section",
        string="Class Section",
        required=True,
        domain="[('active', '=', True)]",
    )
    program_id = fields.Many2one(
        "university.program",
        string="Major",
        related="section_id.program_id",
        readonly=True,
    )
    academic_year_id = fields.Many2one(
        "university.academic.year",
        string="Academic Year",
        related="section_id.semester_id.academic_year_id",
        readonly=True,
    )
    semester_id = fields.Many2one(
        "university.semester",
        string="Semester",
        related="section_id.semester_id",
        readonly=True,
    )
    eligible_enrollment_ids = fields.Many2many(
        "university.enrollment",
        string="Eligible Enrollments",
        compute="_compute_eligible_enrollments",
    )
    enrollment_ids = fields.Many2many(
        "university.enrollment",
        "university_populate_class_enrollment_rel",
        "wizard_id",
        "enrollment_id",
        string="Enrollments to Assign",
    )
    available_seats = fields.Integer(string="Available Seats", compute="_compute_available_seats")

    @api.depends("section_id")
    def _compute_eligible_enrollments(self):
        for wizard in self:
            wizard.eligible_enrollment_ids = wizard._eligible_enrollments()

    @api.depends("section_id", "section_id.enrollment_ids.status")
    def _compute_available_seats(self):
        for wizard in self:
            section = wizard.section_id
            if not section or not section.capacity:
                wizard.available_seats = 0
                continue
            current = self.env["university.enrollment"].search_count(
                [("section_id", "=", section.id), ("status", "=", "enrolled")]
            )
            wizard.available_seats = max(section.capacity - current, 0)

    @api.onchange("section_id")
    def _onchange_section_id(self):
        self.enrollment_ids = False

    def _eligible_enrollments(self):
        self.ensure_one()
        if not self.section_id:
            return self.env["university.enrollment"]
        section = self.section_id
        program = section.program_id
        if not program and section.subject_id.program_ids:
            program = section.subject_id.program_ids[:1]
        if not program:
            return self.env["university.enrollment"]
        return self.env["university.enrollment"].search(
            [
                ("program_id", "=", program.id),
                ("academic_year_id", "=", section.semester_id.academic_year_id.id),
                ("semester_id", "=", section.semester_id.id),
                ("section_id", "=", False),
                ("status", "=", "enrolled"),
            ]
        )

    def action_select_all_eligible(self):
        if not self.env.user.has_group("school_management.group_school_admin"):
            raise AccessError(_("Only University Administrators can populate a class."))
        self.ensure_one()
        enrollments = self._eligible_enrollments()
        if not enrollments:
            raise UserError("No eligible enrollments found for this class section.")
        self.enrollment_ids = [(6, 0, enrollments.ids)]
        return {
            "type": "ir.actions.act_window",
            "name": "Populate Class",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    def action_populate_class(self):
        if not self.env.user.has_group("school_management.group_school_admin"):
            raise AccessError(_("Only University Administrators can populate a class."))
        self.ensure_one()
        if not self.enrollment_ids:
            raise UserError("Select at least one enrollment to assign.")
        section = self.section_id
        if section.capacity:
            current = self.env["university.enrollment"].search_count(
                [("section_id", "=", section.id), ("status", "=", "enrolled")]
            )
            if current + len(self.enrollment_ids) > section.capacity:
                raise UserError(
                    "Not enough seats in %s. Available: %s, requested: %s."
                    % (section.name, max(section.capacity - current, 0), len(self.enrollment_ids))
                )
        self.enrollment_ids.write({"section_id": section.id})
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Class Populated",
                "message": "%s enrollment(s) assigned to %s." % (len(self.enrollment_ids), section.name),
                "type": "success",
                "sticky": False,
                "next": {"type": "ir.actions.act_window_close"},
            },
        }
