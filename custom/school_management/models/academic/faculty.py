from odoo import api, fields, models


class UniversityFaculty(models.Model):
    _name = "university.faculty"
    _description = "University Faculty"

    name = fields.Char(string="Faculty Name", required=True)
    code = fields.Char(string="Faculty Code", required=True)
    dean_id = fields.Many2one(
        "university.teacher",
        string="Head of Faculty",
        compute="_compute_dean_id",
        store=True,
        compute_sudo=True,
        readonly=True,
        help="Automatically derived from the most recent active Head of Faculty assignment.",
    )
    department_ids = fields.One2many(
        "university.department", "faculty_id", string="Departments"
    )
    description = fields.Text(string="Description")
    color = fields.Integer(string="Color Index", default=1)
    active = fields.Boolean(string="Active", default=True)
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("active", "Active"),
            ("closed", "Closed"),
        ],
        string="Stage",
        default="draft",
    )

    assignment_ids = fields.One2many(
        "university.academic.assignment",
        "faculty_id",
        string="Dean Appointments",
    )

    # Derby set of children used by the "derby_reports" tab is derived from
    # the departments; counts are separate stored/non-stored computes so that
    # each compute method groups fields with a consistent 'store' flag.

    department_count = fields.Integer(
        compute="_compute_department_count", string="Department Count", store=True
    )
    teacher_count = fields.Integer(
        compute="_compute_counts", string="Teacher Count"
    )
    student_count = fields.Integer(
        compute="_compute_counts", string="Student Count"
    )
    program_count = fields.Integer(
        compute="_compute_counts", string="Program Count"
    )

    teacher_ids = fields.Many2many(
        "university.teacher",
        compute="_compute_scoped_records",
        string="Teachers",
    )
    program_ids = fields.Many2many(
        "university.program",
        compute="_compute_scoped_records",
        string="Programs",
    )
    student_ids = fields.Many2many(
        "university.student",
        compute="_compute_scoped_records",
        string="Students",
    )

    @api.depends("department_ids", "department_ids.active")
    def _compute_department_count(self):
        for rec in self:
            rec.department_count = len(rec.department_ids)

    @api.depends(
        "assignment_ids.role",
        "assignment_ids.active",
        "assignment_ids.staff_id",
    )
    def _compute_dean_id(self):
        for rec in self:
            appointee = rec.assignment_ids.filtered(
                lambda a: a.active and a.role in ("dean", "vice_dean")
            )[:1].staff_id
            rec.dean_id = appointee

    @api.depends(
        "department_ids.teacher_ids",
        "department_ids.program_ids",
        "department_ids.student_ids",
    )
    def _compute_counts(self):
        for rec in self:
            depts = rec.department_ids
            rec.teacher_count = len(depts.mapped("teacher_ids"))
            rec.student_count = len(depts.mapped("student_ids"))
            rec.program_count = len(depts.mapped("program_ids"))

    @api.depends(
        "department_ids.teacher_ids",
        "department_ids.program_ids",
        "department_ids.student_ids",
    )
    def _compute_scoped_records(self):
        for rec in self:
            depts = rec.department_ids
            rec.teacher_ids = depts.mapped("teacher_ids")
            rec.program_ids = depts.mapped("program_ids")
            rec.student_ids = depts.mapped("student_ids")

    def action_set_draft(self):
        self.write({"state": "draft"})

    def action_set_active(self):
        self.write({"state": "active"})

    def action_set_closed(self):
        self.write({"state": "closed"})

    def action_view_departments(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "school_management.action_university_department"
        )
        action["domain"] = [("faculty_id", "=", self.id)]
        context = dict(self.env.context)
        context.update({
            "default_faculty_id": self.id,
            "search_default_faculty_id": self.id,
        })
        action["context"] = context
        return action
