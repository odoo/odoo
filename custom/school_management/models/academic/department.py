from odoo import api, fields, models


class UniversityDepartment(models.Model):
    _name = "university.department"
    _description = "University Department"

    name = fields.Char(string="Department Name", required=True)
    code = fields.Char(string="Department Code", required=True)
    faculty_id = fields.Many2one(
        "university.faculty", string="Faculty", required=True
    )
    image_1920 = fields.Image(string="Department Cover / Logo", max_width=1024, max_height=1024)
    color = fields.Integer(string="Color Index", default=0)
    head_id = fields.Many2one(
        "university.teacher",
        string="Head of Department",
        compute="_compute_head_id",
        store=True,
        compute_sudo=True,
        readonly=True,
        help="Automatically derived from the most recent active HOD assignment.",
    )
    program_ids = fields.One2many(
        "university.program", "department_id", string="Programs"
    )
    teacher_ids = fields.One2many(
        "university.teacher", "department_id", string="Teachers"
    )
    subject_ids = fields.One2many(
        "university.subject", "department_id", string="Subjects"
    )
    student_ids = fields.One2many(
        "university.student", "department_id", string="Students"
    )
    class_section_ids = fields.Many2many(
        "university.class.section",
        compute="_compute_class_sections",
        string="Class Sections",
    )
    active = fields.Boolean(string="Active", default=True)

    assignment_ids = fields.One2many(
        "university.academic.assignment",
        "department_id",
        string="Head Appointments",
    )

    program_count = fields.Integer(compute="_compute_counts", string="Program Count")
    teacher_count = fields.Integer(compute="_compute_counts", string="Teacher Count")
    subject_count = fields.Integer(compute="_compute_counts", string="Subject Count")
    student_count = fields.Integer(compute="_compute_counts", string="Student Count")
    class_section_count = fields.Integer(
        compute="_compute_counts", string="Class Section Count"
    )

    _unique_code = models.UniqueIndex(
        "(code, active)",
        "The department code must be unique!",
    )

    @api.depends("subject_ids.section_ids")
    def _compute_class_sections(self):
        for rec in self:
            rec.class_section_ids = rec.subject_ids.mapped("section_ids")

    @api.depends(
        "assignment_ids.role",
        "assignment_ids.active",
        "assignment_ids.staff_id",
    )
    def _compute_head_id(self):
        for rec in self:
            appointee = rec.assignment_ids.filtered(
                lambda a: a.active and a.role == "department_head"
            )[:1].staff_id
            rec.head_id = appointee

    @api.depends(
        "program_ids",
        "teacher_ids",
        "subject_ids",
        "student_ids",
        "class_section_ids",
    )
    def _compute_counts(self):
        for rec in self:
            rec.program_count = len(rec.with_context(active_test=False).program_ids)
            rec.teacher_count = len(rec.with_context(active_test=False).teacher_ids)
            rec.subject_count = len(rec.with_context(active_test=False).subject_ids)
            rec.student_count = len(rec.with_context(active_test=False).student_ids)
            rec.class_section_count = len(
                rec.with_context(active_test=False).class_section_ids
            )

    def action_view_subjects(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id("school_management.action_university_subject")
        action["domain"] = [("department_id", "=", self.id)]
        action["context"] = {"default_department_id": self.id}
        return action
