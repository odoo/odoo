from odoo import api, fields, models
from odoo.exceptions import ValidationError


class UniversityStudentEnrollmentWizard(models.TransientModel):
    _name = "university.student.enrollment.wizard"
    _description = "Student Enrollment Registration Wizard"

    student_id = fields.Many2one(
        "university.student",
        string="Student",
        required=True,
        readonly=True,
    )
    program_id = fields.Many2one(
        "university.program",
        string="Major ",
        required=True,
        domain="[('active', '=', True)]",
    )
    academic_year_id = fields.Many2one(
        "university.academic.year",
        string="Academic Year",
        required=True,
        domain="[('active', '=', True)]",
        help="The academic year for this enrollment.",
    )
    semester_id = fields.Many2one(
        "university.semester",
        string="Semester",
        required=True,
        domain="[('active', '=', True), ('academic_year_id', '=', academic_year_id)]",
        help="The semester for this enrollment.",
    )
    section_ids = fields.Many2many(
        "university.class.section",
        relation="student_enrollment_reg_rel",
        string="Optional Class Sections",
        domain="[('active', '=', True), ('semester_id', '=', semester_id), '|', ('program_id', '=', program_id), ('subject_id.program_ids', 'in', [program_id])]",
    )
    enrollment_date = fields.Date(
        string="Enrollment Date",
        default=fields.Date.context_today,
        required=True,
    )
    status = fields.Selection(
        [
            ("enrolled", "Enrolled"),
            ("completed", "Completed"),
            ("dropped", "Dropped"),
        ],
        string="Initial Status",
        default="enrolled",
        required=True,
    )

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        student_id = values.get("student_id") or self.env.context.get("default_student_id")
        student = self.env["university.student"].browse(student_id).exists() if student_id else False

        if student:
            values.setdefault("student_id", student.id)
            if student.program_id:
                values.setdefault("program_id", student.program_id.id)
            if student.academic_year_id:
                values.setdefault("academic_year_id", student.academic_year_id.id)
            if student.current_semester_id:
                semester = student.current_semester_id
                academic_year_id = values.get("academic_year_id")
                if not academic_year_id or semester.academic_year_id.id == academic_year_id:
                    values.setdefault("semester_id", semester.id)
                    values.setdefault("academic_year_id", semester.academic_year_id.id)

        # Robust fallbacks for required academic_year_id and semester_id
        if not values.get("academic_year_id"):
            active_year = self.env["university.academic.year"].search([("active", "=", True)], limit=1, order="date_start desc")
            if not active_year:
                active_year = self.env["university.academic.year"].search([], limit=1, order="date_start desc")
            if active_year:
                values["academic_year_id"] = active_year.id

        if not values.get("semester_id"):
            year_id = values.get("academic_year_id")
            sem_domain = [("active", "=", True)]
            if year_id:
                sem_domain.append(("academic_year_id", "=", year_id))
            active_sem = self.env["university.semester"].search(sem_domain, limit=1, order="date_start desc")
            if not active_sem:
                active_sem = self.env["university.semester"].search([], limit=1, order="date_start desc")
            if active_sem:
                values["semester_id"] = active_sem.id

        return values

    @api.onchange("student_id")
    def _onchange_student_id(self):
        if not self.student_id:
            return self._section_domain_result()

        self.program_id = self.student_id.program_id
        self.academic_year_id = self.student_id.academic_year_id
        self.semester_id = self.student_id.current_semester_id
        if self.semester_id:
            self.academic_year_id = self.semester_id.academic_year_id
        if not self.academic_year_id:
            active_year = self.env["university.academic.year"].search([("active", "=", True)], limit=1, order="date_start desc")
            if active_year:
                self.academic_year_id = active_year.id
        if not self.semester_id and self.academic_year_id:
            active_sem = self.env["university.semester"].search([
                ("active", "=", True),
                ("academic_year_id", "=", self.academic_year_id.id),
            ], limit=1, order="date_start desc")
            if active_sem:
                self.semester_id = active_sem.id

        self.section_ids = False
        return self._section_domain_result()

    @api.onchange("academic_year_id")
    def _onchange_academic_year_id(self):
        if self.semester_id and self.semester_id.academic_year_id != self.academic_year_id:
            self.semester_id = False
        self.section_ids = False
        return self._section_domain_result()

    @api.onchange("semester_id", "program_id")
    def _onchange_semester_or_program(self):
        self.section_ids = False
        return self._section_domain_result()

    def _section_domain_result(self):
        domain = [("active", "=", True)]
        if self.semester_id:
            domain.append(("semester_id", "=", self.semester_id.id))
        if self.program_id:
            domain.extend([
                "|",
                ("program_id", "=", self.program_id.id),
                ("subject_id.program_ids", "in", [self.program_id.id]),
            ])
        return {"domain": {"section_ids": domain}}

    def action_register_enrollment(self):
        self.ensure_one()

        if self.semester_id.academic_year_id != self.academic_year_id:
            raise ValidationError(
                "The selected semester does not belong to the selected academic year."
            )

        continue_student = bool(self.env.context.get("continue_student"))
        if continue_student:
            if not self.env.su and not self.env.user.has_group("school_management.group_school_admin"):
                raise ValidationError("Only University Administrators can continue a student.")
            if self.student_id.status != "dropped" and self.student_id.active:
                raise ValidationError("Only dropped or inactive students can be continued.")

        if not self.section_ids:
            return self._register_major_enrollment()

        existing_enrollments = self.env["university.enrollment"].search([
            ("student_id", "=", self.student_id.id),
            ("section_id", "in", self.section_ids.ids),
        ])
        existing_section_ids = existing_enrollments.mapped("section_id.id")

        sections_to_enroll = self.section_ids.filtered(lambda s: s.id not in existing_section_ids)
        enrollments_to_reopen = existing_enrollments.filtered(
            lambda enrollment: enrollment.status == "dropped"
        ) if continue_student else self.env["university.enrollment"]

        if not sections_to_enroll and not enrollments_to_reopen:
            raise ValidationError("The student is already enrolled in all selected sections.")

        sections_to_process = sections_to_enroll | enrollments_to_reopen.mapped("section_id")
        if sections_to_process:
            self.env.cr.execute(
                "SELECT id, capacity FROM university_class_section WHERE id IN %s ORDER BY id FOR UPDATE",
                [tuple(sections_to_process.ids)]
            )
            locked_sections = {row[0]: row[1] for row in self.env.cr.fetchall()}
            
            errors = []
            requested_by_section = {
                section.id: len(sections_to_enroll.filtered(lambda item: item.id == section.id))
                + len(enrollments_to_reopen.filtered(lambda enrollment: enrollment.section_id == section))
                for section in sections_to_process
            }
            for section in sections_to_process:
                capacity = locked_sections.get(section.id)
                if capacity:
                    self.env.cr.execute(
                        "SELECT count(*) FROM university_enrollment WHERE section_id = %s AND status = 'enrolled'",
                        [section.id]
                    )
                    real_enrolled_count = self.env.cr.fetchone()[0]
                    requested_count = requested_by_section[section.id]
                    if real_enrolled_count + requested_count > capacity:
                        errors.append(
                            f"'{section.name}' (Subject: {section.subject_id.name}) "
                            f"does not have enough seats. Capacity: {capacity}, "
                            f"requested: {requested_count}."
                        )
            
            if errors:
                error_msg = "\n".join(errors)
                raise ValidationError(f"Cannot enroll due to capacity limits:\n{error_msg}")

        if enrollments_to_reopen:
            enrollments_to_reopen.write({
                "enrollment_date": self.enrollment_date,
                "status": "enrolled",
            })

        enrollments = self.env["university.enrollment"].create([
            {
                "student_id": self.student_id.id,
                "program_id": self._get_program_for_section(section).id,
                "section_id": section.id,
                "academic_year_id": section.semester_id.academic_year_id.id,
                "semester_id": section.semester_id.id,
                "enrollment_date": self.enrollment_date,
                "status": "enrolled" if continue_student else self.status,
            }
            for section in sections_to_enroll
        ])

        if continue_student:
            self.student_id.write({"status": "active", "active": True})
            message = (
                f"Student continued successfully. Reopened {len(enrollments_to_reopen)} "
                f"section enrollment(s) and created {len(enrollments)} new enrollment(s)."
            )
        else:
            message = f"Student successfully enrolled in {len(enrollments)} section(s)."

        skipped_count = len(existing_enrollments) - len(enrollments_to_reopen)
        if skipped_count:
            message += f" Skipped {skipped_count} section(s) already enrolled or completed."

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Registration Complete",
                "message": message,
                "type": "success",
                "sticky": False,
                "next": {"type": "ir.actions.act_window_close"},
            },
        }

    # Alias to match student_enrollment_wizard_views.xml
    action_register_enrollments = action_register_enrollment

    def _register_major_enrollment(self):
        enrollment_model = self.env["university.enrollment"]
        existing_major = enrollment_model.search([
            ("student_id", "=", self.student_id.id),
            ("program_id", "=", self.program_id.id),
            ("academic_year_id", "=", self.academic_year_id.id),
            ("semester_id", "=", self.semester_id.id),
            ("section_id", "=", False),
        ], order="id desc")

        active_major = existing_major.filtered(
            lambda enrollment: enrollment.status == "enrolled"
        )
        if active_major and self.status == "enrolled":
            raise ValidationError(
                "This student is already enrolled in this major/program for "
                "the selected academic year and semester."
            )

        reopened = self.env["university.enrollment"]
        if self.env.context.get("continue_student"):
            reopened = existing_major.filtered(
                lambda enrollment: enrollment.status == "dropped"
            )[:1]
            if reopened:
                reopened.write({
                    "enrollment_date": self.enrollment_date,
                    "status": "enrolled",
                })

        if not reopened:
            enrollment_model.create({
                "student_id": self.student_id.id,
                "program_id": self.program_id.id,
                "academic_year_id": self.academic_year_id.id,
                "semester_id": self.semester_id.id,
                "enrollment_date": self.enrollment_date,
                "status": (
                    "enrolled"
                    if self.env.context.get("continue_student")
                    else self.status
                ),
            })

        if self.env.context.get("continue_student"):
            self.student_id.write({"status": "active", "active": True})
            message = "Student continued successfully. Major enrollment was reopened."
        else:
            message = "Student successfully enrolled in the major/program."

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Registration Complete",
                "message": message,
                "type": "success",
                "sticky": False,
                "next": {"type": "ir.actions.act_window_close"},
            },
        }

    def _get_program_for_section(self, section):
        program = section.program_id or self.student_id.program_id
        if not program and section.subject_id.program_ids:
            program = section.subject_id.program_ids[:1]
        if not program:
            raise ValidationError(
                f"No major could be determined for section {section.display_name}."
            )
        return program
