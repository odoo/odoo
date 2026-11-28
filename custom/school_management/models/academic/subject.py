from odoo import api, fields, models
from odoo.exceptions import UserError
from .academic_lock import can_maintain_closed_year_records


class UniversitySubject(models.Model):
    _name = "university.subject"
    _description = "University Subject"

    name = fields.Char(string="Subject Name", required=True)
    code = fields.Char(string="Subject Code", copy=False, index=True)
    department_id = fields.Many2one(
        "university.department",
        string="Department",
    )
    program_ids = fields.Many2many(
        "university.program",
        "university_program_subject_rel",
        "subject_id",
        "program_id",
        string="Majors /Programs",
    )
    credits = fields.Integer(string="Credits", default=3)
    description = fields.Text(string="Description")
    syllabus_html = fields.Html(
        string="Course Syllabus & Objectives",
        sanitize=True,
    )
    teacher_ids = fields.Many2many(
        "university.teacher",
        "university_teacher_subject_rel",
        "subject_id",
        "teacher_id",
        string="Teachers",
    )

    section_ids = fields.One2many(
        "university.class.section",
        "subject_id",
        string="Class Sections",
    )
    semester_subject_ids = fields.One2many(
        "university.semester.subject",
        "subject_id",
        string="Semester Offerings",
    )
    enrollment_ids = fields.One2many(
        "university.enrollment",
        "subject_id",
        string="Enrollments",
    )
    book_link_ids = fields.One2many(
        "university.subject.book",
        "subject_id",
        string="Books",
    )
    active = fields.Boolean(string="Active", default=True)
    auto_quiz_per_session = fields.Boolean(
        string="Auto-Quiz per Session",
        default=False,
        help="If enabled, timetable sessions for this subject automatically generate a quiz when class begins.",
    )

    teacher_count = fields.Integer(
        string="Teachers Count",
        compute="_compute_counts",
        store=True,
    )
    section_count = fields.Integer(
        string="Sections Count",
        compute="_compute_counts",
        store=True,
    )
    book_count = fields.Integer(
        string="Books Count",
        compute="_compute_book_count",
    )
    student_count = fields.Integer(
        string="Enrolled Students Count",
        compute="_compute_student_count",
    )

    @api.depends("teacher_ids", "section_ids")
    def _compute_counts(self):
        for rec in self:
            rec.teacher_count = len(rec.teacher_ids)
            rec.section_count = len(rec.section_ids)

    @api.depends("book_link_ids")
    def _compute_book_count(self):
        for rec in self:
            rec.book_count = len(rec.book_link_ids)

    def _compute_student_count(self):
        for rec in self:
            rec.student_count = sum(sec.enrolled_student_count for sec in rec.section_ids)

    def action_view_sections(self):
        self.ensure_one()
        return {
            "name": f"Class Sections - {self.name}",
            "type": "ir.actions.act_window",
            "res_model": "university.class.section",
            "view_mode": "list,kanban,form",
            "domain": [("subject_id", "=", self.id)],
            "context": {"default_subject_id": self.id, "default_section_type": "course"},
        }

    def action_view_books(self):
        self.ensure_one()
        book_tmpl_ids = self.book_link_ids.mapped("product_tmpl_id").ids
        return {
            "name": f"Books - {self.name}",
            "type": "ir.actions.act_window",
            "res_model": "product.template",
            "view_mode": "kanban,list,form",
            "domain": [("id", "in", book_tmpl_ids)],
            "context": {"default_is_textbook": True},
        }

    def action_view_teachers(self):
        self.ensure_one()
        return {
            "name": f"Instructors - {self.name}",
            "type": "ir.actions.act_window",
            "res_model": "university.teacher",
            "view_mode": "kanban,list,form",
            "domain": [("id", "in", self.teacher_ids.ids)],
            "context": {"default_department_id": self.department_id.id if self.department_id else False},
        }

    def action_view_students(self):
        self.ensure_one()
        return {
            "name": f"Enrolled Students - {self.name}",
            "type": "ir.actions.act_window",
            "res_model": "university.enrollment",
            "view_mode": "list,kanban,form",
            "domain": [("subject_id", "=", self.id)],
            "context": {
                "default_subject_id": self.id,
                "default_class_section_id": self.section_ids[:1].id if self.section_ids else False,
            },
        }

    def action_enroll_students(self):
        self.ensure_one()
        default_section = self.section_ids[:1].id if self.section_ids else False
        return {
            "name": f"Enroll Student - {self.name}",
            "type": "ir.actions.act_window",
            "res_model": "university.enrollment",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_class_section_id": default_section,
                "default_status": "enrolled",
                "default_enrollment_date": fields.Date.context_today(self),
            },
        }

    @api.model
    def _ensure_subject_xml_ids(self):
        """Ensure XML IDs exist for demo subjects so data files can reference them safely."""
        mapping = {
            "CS101": "subject_cs101",
            "CS102": "subject_cs102",
            "CS103": "subject_cs103",
            "CS201": "subject_cs201",
            "CS202": "subject_cs202",
            "CS204": "subject_cs204",
            "MATH101": "subject_math101",
            "ENG101": "subject_eng101",
        }
        IrModelData = self.env["ir.model.data"].sudo()
        for code, xml_id in mapping.items():
            data = IrModelData.search([("module", "=", "school_management"), ("name", "=", xml_id)], limit=1)
            if not data:
                subject = self.search([("code", "=", code)], limit=1)
                if not subject:
                    subject = self.create({"code": code, "name": code})
                IrModelData.create({
                    "module": "school_management",
                    "name": xml_id,
                    "model": "university.subject",
                    "res_id": subject.id,
                    "noupdate": True,
                })
        return True

    @api.onchange("department_id")
    def _onchange_department_id(self):
        if self.department_id and self.program_ids:
            matching_programs = self.program_ids.filtered(lambda p: p.department_id == self.department_id)
            if matching_programs != self.program_ids:
                self.program_ids = matching_programs

    @api.onchange("program_ids")
    def _onchange_program_ids(self):
        if self.program_ids and not self.department_id:
            self.department_id = self.program_ids[0].department_id

    @api.constrains("department_id", "program_ids")
    def _check_department_program_consistency(self):
        for record in self:
            if not record.department_id and record.program_ids:
                record.department_id = record.program_ids[0].department_id

    def unlink(self):
        if not can_maintain_closed_year_records(self.env):
            locked_offering = self.with_context(active_test=False).mapped(
                "semester_subject_ids"
            ).filtered(
                lambda offering: offering.academic_year_id.state in ("closed", "archived")
            )[:1]
            if locked_offering:
                raise UserError(
                    "Cannot delete a subject with semester offerings in a closed or archived academic year."
                )
        return super().unlink()
