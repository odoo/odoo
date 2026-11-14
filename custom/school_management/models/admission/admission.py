from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError


class UniversityAdmissionApplication(models.Model):
    _name = "university.admission.application"
    _description = "Admission Application"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "application_date desc, id desc"

    name = fields.Char(
        string="Application Reference",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: "New",
    )
    applicant_name = fields.Char(string="Applicant Name", required=True, tracking=True)
    email = fields.Char(string="Email")
    phone = fields.Char(string="Phone")
    address = fields.Text(string="Address")
    date_of_birth = fields.Date(string="Date of Birth")
    gender = fields.Selection(
        [("male", "Male"), ("female", "Female"), ("other", "Other")],
        string="Gender",
    )
    application_date = fields.Date(
        string="Application Date",
        default=fields.Date.context_today,
        required=True,
    )
    program_id = fields.Many2one(
        "university.program",
        string="Major",
        required=True,
        domain="[('active', '=', True)]",
    )
    department_id = fields.Many2one(
        "university.department",
        related="program_id.department_id",
        string="Department",
        store=True,
        readonly=True,
    )
    faculty_id = fields.Many2one(
        "university.faculty",
        related="program_id.department_id.faculty_id",
        string="Faculty",
        store=True,
        readonly=True,
    )
    academic_year_id = fields.Many2one(
        "university.academic.year",
        string="Academic Year",
        required=True,
        domain="[('active', '=', True)]",
    )
    semester_id = fields.Many2one(
        "university.semester",
        string="Semester",
        required=True,
        domain="[('active', '=', True), ('academic_year_id', '=', academic_year_id)]",
    )
    section_id = fields.Many2one(
        "university.class.section",
        string="Requested Class Section",
        domain="[('active', '=', True), ('semester_id', '=', semester_id), '|', ('program_id', '=', program_id), ('subject_id.program_ids', 'in', [program_id])]",
    )
    fee_structure_id = fields.Many2one(
        "university.fee.structure",
        string="Fee Structure",
        domain="["
        "('active', '=', True), "
        "'|', ('program_id', '=', False), ('program_id', '=', program_id), "
        "'|', ('academic_year_id', '=', False), ('academic_year_id', '=', academic_year_id), "
        "'|', ('semester_id', '=', False), ('semester_id', '=', semester_id)"
        "]",
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        compute="_compute_currency_id",
        default=lambda self: self.env.company.currency_id,
        store=True,
    )
    fee_amount = fields.Monetary(
        string="Fee Amount",
        compute="_compute_fee_amount",
        currency_field="currency_id",
        store=True,
        readonly=True,
    )
    student_id = fields.Many2one(
        "university.student",
        string="Student",
        readonly=True,
        copy=False,
    )
    enrollment_id = fields.Many2one(
        "university.enrollment",
        string="Enrollment",
        readonly=True,
        copy=False,
    )
    fee_ids = fields.One2many(
        "university.fee",
        "admission_application_id",
        string="Generated Fees",
    )
    fee_count = fields.Integer(string="Fee Count", compute="_compute_fee_count")
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("submitted", "Submitted"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
            ("confirmed", "Confirmed"),
            ("cancelled", "Cancelled"),
        ],
        string="Status",
        default="draft",
        tracking=True,
    )
    decision_note = fields.Text(string="Decision Note")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code(
                        "university.admission.application"
                    )
                    or "New"
                )
        return super().create(vals_list)

    def _compute_currency_id(self):
        currency = self.env.company.currency_id
        for application in self:
            application.currency_id = currency

    @api.depends("fee_structure_id.total_amount", "fee_ids.total_amount", "state")
    def _compute_fee_amount(self):
        for application in self:
            if application.state == "confirmed" and application.fee_ids:
                active_fees = application.fee_ids.filtered(lambda f: f.state != "canceled")
                if active_fees:
                    application.fee_amount = sum(active_fees.mapped("total_amount"))
                elif application.fee_structure_id:
                    application.fee_amount = application.fee_structure_id.total_amount
                else:
                    application.fee_amount = 0.0
            elif application.fee_structure_id:
                application.fee_amount = application.fee_structure_id.total_amount
            else:
                application.fee_amount = 0.0

    @api.onchange("program_id", "academic_year_id", "semester_id")
    def _onchange_academic_fee_structure(self):
        self.fee_structure_id = False
        self.fee_amount = 0.0

        if not (self.program_id and self.academic_year_id and self.semester_id):
            return

        # 1. Search for exact match
        domain_exact = [
            ("active", "=", True),
            ("program_id", "=", self.program_id.id),
            ("academic_year_id", "=", self.academic_year_id.id),
            ("semester_id", "=", self.semester_id.id),
        ]
        matching = self.env["university.fee.structure"].search(domain_exact)

        # 2. Fallback to generic fee structures if no exact match found
        if not matching:
            # Fallback A: program + academic year (any semester)
            matching = self.env["university.fee.structure"].search([
                ("active", "=", True),
                ("program_id", "=", self.program_id.id),
                ("academic_year_id", "=", self.academic_year_id.id),
                ("semester_id", "=", False),
            ])
        if not matching:
            # Fallback B: program only (any academic year and semester)
            matching = self.env["university.fee.structure"].search([
                ("active", "=", True),
                ("program_id", "=", self.program_id.id),
                ("academic_year_id", "=", False),
                ("semester_id", "=", False),
            ])
        if not matching:
            # Fallback C: global generic structure
            matching = self.env["university.fee.structure"].search([
                ("active", "=", True),
                ("program_id", "=", False),
                ("academic_year_id", "=", False),
                ("semester_id", "=", False),
            ])

        if len(matching) == 1:
            self.fee_structure_id = matching
            self.fee_amount = matching.total_amount
        elif len(matching) > 1:
            self.fee_structure_id = False
            self.fee_amount = 0.0
            return {
                "warning": {
                    "title": _("Multiple Fee Structures Found"),
                    "message": _(
                        "Multiple fee structures match the selected academic criteria for %(program)s. "
                        "Please select the appropriate fee structure manually.",
                        program=self.program_id.display_name,
                    ),
                }
            }

    @api.onchange("fee_structure_id")
    def _onchange_fee_structure_id(self):
        if self.fee_structure_id:
            self.fee_amount = self.fee_structure_id.total_amount
        else:
            self.fee_amount = 0.0

    @api.depends("fee_ids")
    def _compute_fee_count(self):
        for application in self:
            application.fee_count = len(application.fee_ids)

    def _validate_fee_structure_consistency(self):
        for application in self:
            if not application.fee_structure_id:
                continue
            struct = application.fee_structure_id
            if struct.program_id and struct.program_id != application.program_id:
                raise ValidationError(
                    _(
                        "The selected fee structure '%(fee)s' belongs to program '%(fee_prog)s', "
                        "which does not match application program '%(app_prog)s'.",
                        fee=struct.name,
                        fee_prog=struct.program_id.display_name,
                        app_prog=application.program_id.display_name,
                    )
                )
            if struct.academic_year_id and struct.academic_year_id != application.academic_year_id:
                raise ValidationError(
                    _(
                        "The selected fee structure '%(fee)s' belongs to academic year '%(fee_year)s', "
                        "which does not match application academic year '%(app_year)s'.",
                        fee=struct.name,
                        fee_year=struct.academic_year_id.name,
                        app_year=application.academic_year_id.name,
                    )
                )
            if struct.semester_id and struct.semester_id != application.semester_id:
                raise ValidationError(
                    _(
                        "The selected fee structure '%(fee)s' belongs to semester '%(fee_sem)s', "
                        "which does not match application semester '%(app_sem)s'.",
                        fee=struct.name,
                        fee_sem=struct.semester_id.name,
                        app_sem=application.semester_id.name,
                    )
                )

    @api.constrains("fee_structure_id", "program_id", "academic_year_id", "semester_id")
    def _check_fee_structure_consistency(self):
        self._validate_fee_structure_consistency()

    @api.constrains("semester_id", "academic_year_id")
    def _check_period_consistency(self):
        for application in self:
            if (
                application.semester_id
                and application.academic_year_id
                and application.semester_id.academic_year_id
                != application.academic_year_id
            ):
                raise ValidationError(
                    _("The selected semester does not belong to the selected academic year.")
                )

    @api.constrains("date_of_birth", "application_date")
    def _check_dates(self):
        today = fields.Date.context_today(self)
        for application in self:
            if application.date_of_birth and application.date_of_birth > today:
                raise ValidationError(_("Date of birth cannot be in the future."))
            if application.application_date and application.application_date > today:
                raise ValidationError(_("Application date cannot be in the future."))

    @api.constrains("email", "program_id", "academic_year_id", "semester_id")
    def _check_duplicate_application(self):
        for application in self:
            email = (application.email or "").strip()
            if not email or not application.program_id or not application.academic_year_id:
                continue
            duplicate = self.search(
                [
                    ("id", "!=", application.id),
                    ("email", "=ilike", email),
                    ("program_id", "=", application.program_id.id),
                    ("academic_year_id", "=", application.academic_year_id.id),
                    ("semester_id", "=", application.semester_id.id),
                    ("state", "not in", ("rejected", "cancelled")),
                ],
                limit=1,
            )
            if duplicate:
                raise ValidationError(
                    _(
                        "An active admission application already exists for this email, "
                        "program, academic year, and semester: %(reference)s."
                    )
                    % {"reference": duplicate.display_name}
                )

    @api.constrains("section_id", "program_id", "semester_id")
    def _check_section_consistency(self):
        for application in self:
            section = application.section_id
            if not section:
                continue
            if section.semester_id != application.semester_id:
                raise ValidationError(
                    "The requested section must belong to the selected semester."
                )
            if section.program_id and section.program_id != application.program_id:
                raise ValidationError(
                    "The requested section must belong to the selected program."
                )
            if (
                not section.program_id
                and section.subject_id.program_ids
                and application.program_id not in section.subject_id.program_ids
            ):
                raise ValidationError(
                    "The requested subject section is not offered for the selected program."
                )

    @api.onchange("academic_year_id")
    def _onchange_academic_year_id(self):
        if (
            self.semester_id
            and self.academic_year_id
            and self.semester_id.academic_year_id != self.academic_year_id
        ):
            self.semester_id = False
            self.fee_structure_id = False
            self.fee_amount = 0.0
        self.section_id = False

    @api.onchange("program_id", "semester_id")
    def _onchange_program_period(self):
        self.section_id = False

    def action_submit(self):
        for application in self:
            if application.state != "draft":
                raise ValidationError(
                    _("Only draft admission applications can be submitted.")
                )
            application.state = "submitted"

    def action_approve(self):
        self._check_workflow_manager()
        for application in self:
            if application.state != "submitted":
                raise ValidationError(
                    _("Only submitted admission applications can be approved.")
                )
            application.state = "approved"

    def action_reject(self):
        self._check_workflow_manager()
        for application in self:
            if application.state != "submitted":
                raise ValidationError(
                    _("Only submitted admission applications can be rejected.")
                )
            application.state = "rejected"

    def action_cancel(self):
        self._check_workflow_manager()
        for application in self:
            if application.state not in ("draft", "submitted", "approved"):
                raise ValidationError(
                    _("Only draft, submitted, or approved applications can be cancelled.")
                )
            application.state = "cancelled"

    def action_reset_to_draft(self):
        self._check_workflow_manager()
        for application in self:
            if application.state not in ("rejected", "cancelled"):
                raise ValidationError(
                    _("Only rejected or cancelled applications can be reset to draft.")
                )
            application.state = "draft"

    def action_confirm(self):
        self._check_workflow_manager()
        for application in self:
            if application.state == "confirmed":
                continue
            if application.state != "approved":
                raise ValidationError(
                    _("Only approved admission applications can be confirmed.")
                )
            if not application.fee_structure_id:
                raise ValidationError(
                    _("A fee structure is required to confirm the admission application.")
                )
            application._validate_fee_structure_consistency()
            if not application.fee_structure_id.line_ids:
                raise ValidationError(
                    _(
                        "The selected fee structure '%(fee)s' does not have any fee lines.",
                        fee=application.fee_structure_id.name,
                    )
                )
            student = application._get_or_create_student()
            enrollment = application._get_or_create_enrollment(student)
            application._generate_required_fee(student)
            application.write(
                {
                    "student_id": student.id,
                    "enrollment_id": enrollment.id,
                    "state": "confirmed",
                }
            )
            application.message_post(
                body=_(
                    "Admission confirmed. Student %(student)s was enrolled in %(program)s.",
                    student=student.display_name,
                    program=application.program_id.display_name,
                )
            )
        return {
            "type": "ir.actions.act_window",
            "name": "Admission Applications",
            "res_model": self._name,
            "view_mode": "list,form",
        }

    def action_view_fees(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Admission Fees",
            "res_model": "university.fee",
            "view_mode": "list,form",
            "domain": [("admission_application_id", "=", self.id)],
            "context": {
                "default_admission_application_id": self.id,
                "default_student_id": self.student_id.id,
            },
        }

    def _get_or_create_student(self):
        self.ensure_one()
        if self.student_id:
            student = self.student_id
            return student

        student = False
        if self.email:
            student = self.env["university.student"].search(
                [("email", "=", self.email)], limit=1
            )
        if student:
            return student

        vals = self._student_update_vals()
        vals.update(
            {
                "name": self.applicant_name,
                "email": self.email,
                "phone": self.phone,
                "address": self.address,
                "date_of_birth": self.date_of_birth,
                "gender": self.gender,
            }
        )
        return self.env["university.student"].create(vals)

    def _check_workflow_manager(self):
        if not self.env.su and not self.env.user.has_group(
            "school_management.group_school_admin"
        ):
            raise AccessError(_("Only University Administrators can change admission status."))

    def _student_update_vals(self):
        self.ensure_one()
        return {
            "program_id": self.program_id.id,
            "academic_year_id": self.academic_year_id.id,
            "current_semester_id": self.semester_id.id,
            "status": "active",
            "active": True,
        }

    def _get_or_create_enrollment(self, student):
        self.ensure_one()
        domain = [
            ("student_id", "=", student.id),
            ("program_id", "=", self.program_id.id),
            ("academic_year_id", "=", self.academic_year_id.id),
            ("semester_id", "=", self.semester_id.id),
            ("status", "=", "enrolled"),
        ]
        if self.section_id:
            domain.append(("section_id", "=", self.section_id.id))
        else:
            domain.append(("section_id", "=", False))
        enrollment = self.env["university.enrollment"].search(domain, limit=1)
        if enrollment:
            return enrollment
        return self.env["university.enrollment"].with_context(bypass_registration_window=True).create(
            {
                "student_id": student.id,
                "program_id": self.program_id.id,
                "section_id": self.section_id.id,
                "academic_year_id": self.academic_year_id.id,
                "semester_id": self.semester_id.id,
                "enrollment_date": fields.Date.context_today(self),
                "status": "enrolled",
            }
        )

    def _generate_required_fee(self, student):
        self.ensure_one()
        if not self.fee_structure_id:
            return self.env["university.fee"]

        existing_fee = self.fee_ids.filtered(lambda f: f.state != "canceled")[:1]
        if not existing_fee:
            existing_fee = self.env["university.fee"].search(
                [
                    ("admission_application_id", "=", self.id),
                    ("state", "!=", "canceled"),
                ],
                limit=1,
            )
        if existing_fee:
            if existing_fee.state == "draft":
                existing_fee.action_post()
            return existing_fee

        fee_vals = self.fee_structure_id._prepare_fee_vals(student, admission=self)
        fee = self.env["university.fee"].create(fee_vals)
        fee.action_post()
        return fee
