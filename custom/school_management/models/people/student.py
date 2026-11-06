from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

DEFAULT_STUDENT_PASSWORD = "student123"


class Student(models.Model):
    _name = "university.student"
    _inherit = ["mail.thread", "mail.activity.mixin", "avatar.mixin"]
    _description = "University Student"

    # Identity
    name = fields.Char(string="Student Name", required=True)
    student_id = fields.Char(string="Student ID", copy=False, index=True)
    color = fields.Integer(
        string="Color Index",
        related="faculty_id.color",
        store=True,
        readonly=True,
    )
    user_id = fields.Many2one(
        "res.users",
        string="Related User",
        ondelete="set null",
        index=True,
        help="The Odoo login for this student.",
    )
    image_1920 = fields.Image(
        string="Photo",
        max_width=1920,
        max_height=1920,
    )
    image_128 = fields.Image(
        string="Photo Thumbnail",
        related="image_1920",
        max_width=128,
        max_height=128,
        store=True,
    )
    date_of_birth = fields.Date(string="Date of Birth")
    gender = fields.Selection(
        [
            ("male", "Male"),
            ("female", "Female"),
            ("other", "Other"),
        ],
        string="Gender",
        default="male",
    )

    # Contact Information
    email = fields.Char(string="Email")
    phone = fields.Char(string="Phone")
    address = fields.Text(string="Address")
    emergency_contact_name = fields.Char(string="Emergency Contact Name")
    emergency_contact_phone = fields.Char(string="Emergency Contact Phone")

    # Academic Information
    program_id = fields.Many2one(
        "university.program",
        string="Program",
        index=True,
    )
    department_id = fields.Many2one(
        "university.department",
        string="Department",
        compute="_compute_department_id",
        store=True,
        readonly=False,
        precompute=True,
        help="Derived from the selected program or assigned directly.",
    )
    faculty_id = fields.Many2one(
        "university.faculty",
        string="Faculty",
        related="department_id.faculty_id",
        store=True,
        readonly=True,
        help="Derived from the selected department.",
    )
    academic_year_id = fields.Many2one(
        "university.academic.year",
        string="Academic Year",
    )
    current_semester_id = fields.Many2one(
        "university.semester",
        string="Current Semester",
        domain="[('academic_year_id', '=?', academic_year_id)]",
    )
    curriculum_id = fields.Many2one(
        "university.curriculum",
        string="Curriculum",
        domain="[('program_id', '=', program_id)]",
    )
    year_level = fields.Selection([
        ('1', 'Year 1'),
        ('2', 'Year 2'),
        ('3', 'Year 3'),
        ('4', 'Year 4'),
    ], string="Year Level")
    curriculum_line_ids = fields.Many2many(
        "university.curriculum.line",
        string="Curriculum Lines",
        compute="_compute_curriculum_line_ids",
    )

    @api.depends("program_id", "program_id.curriculum_line_ids", "curriculum_id", "curriculum_id.line_ids", "academic_year_id")
    def _compute_curriculum_line_ids(self):
        for student in self:
            curriculum = student.sudo().curriculum_id
            if curriculum and curriculum.line_ids:
                student.curriculum_line_ids = curriculum.line_ids
            elif student.program_id:
                if student.academic_year_id:
                    session_curriculum = self.env["university.curriculum"].sudo().search([
                        ("program_id", "=", student.program_id.id),
                        ("session_id", "=", student.academic_year_id.id),
                    ], limit=1)
                    if session_curriculum and session_curriculum.line_ids:
                        student.curriculum_line_ids = session_curriculum.line_ids
                        continue
                if student.program_id.sudo().curriculum_line_ids:
                    student.curriculum_line_ids = student.program_id.sudo().curriculum_line_ids
                else:
                    student.curriculum_line_ids = False
            else:
                student.curriculum_line_ids = False
    advisor_id = fields.Many2one(
        "university.teacher",
        string="Academic Advisor",
        index=True,
        tracking=True,
        help="Teacher acting as academic advisor for this student.",
    )
    advising_note_ids = fields.One2many(
        "university.student.advising.note",
        "student_id",
        string="Advising Notes",
        groups="school_management.group_school_hod,school_management.group_school_admin",
    )
    followup_ids = fields.One2many(
        "university.student.followup",
        "student_id",
        string="Follow-up Actions",
    )
    advising_note_count = fields.Integer(
        string="Advising Notes Count",
        compute="_compute_advising_counts",
        groups="school_management.group_school_teacher,school_management.group_school_hod,school_management.group_school_admin",
    )
    followup_count = fields.Integer(
        string="Follow-up Count",
        compute="_compute_advising_counts",
    )
    pending_followup_count = fields.Integer(
        string="Pending Follow-ups",
        compute="_compute_advising_counts",
    )
    exam_score_ids = fields.One2many(
        "university.exam.score",
        "student_id",
        string="Exam & Quiz Scores",
    )
    exam_score_count = fields.Integer(
        string="Exams & Quizzes",
        compute="_compute_exam_score_count",
    )

    @api.depends("exam_score_ids")
    def _compute_exam_score_count(self):
        for student in self:
            student.exam_score_count = len(student.exam_score_ids)

    # Academic Performance & Risk Metrics
    gpa = fields.Float(
        string="Cumulative GPA",
        compute="_compute_academic_metrics",
        store=True,
        digits=(3, 2),
    )
    attendance_rate = fields.Float(
        string="Attendance Rate (%)",
        compute="_compute_academic_metrics",
        store=True,
        digits=(5, 1),
    )
    completed_credits = fields.Integer(
        string="Completed Credits",
        compute="_compute_academic_metrics",
        store=True,
    )
    failed_subject_count = fields.Integer(
        string="Failed Subjects",
        compute="_compute_academic_metrics",
        store=True,
    )
    risk_level = fields.Selection(
        [
            ("low", "On Track"),
            ("medium", "Watch"),
            ("high", "High Risk"),
        ],
        string="Risk Level",
        compute="_compute_academic_metrics",
        store=True,
        index=True,
        default="low",
    )
    risk_reason = fields.Char(
        string="Risk Reason",
        compute="_compute_academic_metrics",
        store=True,
    )

    # Status
    status = fields.Selection(
        [
            ("active", "Active"),
            ("suspended", "Suspended"),
            ("graduated", "Graduated"),
            ("dropped", "Dropped"),
        ],
        string="Status",
        default="active",
    )
    active = fields.Boolean(string="Active", default=True)

    notes = fields.Text(string="Notes")

    enrollment_ids = fields.One2many(
        "university.enrollment",
        "student_id",
        string="Enrollments",
    )
    admission_application_ids = fields.One2many(
        "university.admission.application",
        "student_id",
        string="Admission Applications",
    )
    submission_ids = fields.One2many(
        "university.assignment.submission",
        "student_id",
        string="Assignment Submissions",
    )
    report_card_ids = fields.One2many(
        "university.report.card",
        "student_id",
        string="Report Cards",
    )
    transcript_ids = fields.One2many(
        "university.transcript",
        "student_id",
        string="Transcripts",
    )
    transcript_request_ids = fields.One2many(
        "university.transcript.request",
        "student_id",
        string="Transcript Requests",
    )
    fee_ids = fields.One2many(
        "university.fee",
        "student_id",
        string="Fee Invoices",
        groups="school_management.group_school_admin,base.group_system",
    )
    payment_ids = fields.One2many(
        "university.payment",
        "student_id",
        string="Payments",
        groups="school_management.group_school_admin,base.group_system",
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        compute="_compute_currency_id",
    )
    fee_total = fields.Monetary(
        string="Fee Total",
        compute="_compute_fee_totals",
        currency_field="currency_id",
        groups="school_management.group_school_admin,base.group_system",
    )
    fee_paid = fields.Monetary(
        string="Fees Paid",
        compute="_compute_fee_totals",
        currency_field="currency_id",
        groups="school_management.group_school_admin,base.group_system",
    )
    fee_balance = fields.Monetary(
        string="Fee Balance",
        compute="_compute_fee_totals",
        currency_field="currency_id",
        groups="school_management.group_school_admin,base.group_system",
    )
    financial_status = fields.Selection(
        [
            ("good_standing", "Paid / Good Standing"),
            ("pending", "Tuition Pending"),
            ("overdue", "Payment Overdue / Urgent Alert"),
            ("no_invoices", "No Invoices"),
        ],
        string="Financial Status",
        compute="_compute_financial_status",
        store=True,
        groups="school_management.group_school_admin,base.group_system",
    )
    overdue_fee_count = fields.Integer(
        string="Overdue Invoices Count",
        compute="_compute_financial_status",
        store=True,
        groups="school_management.group_school_admin,base.group_system",
    )
    unpaid_fee_count = fields.Integer(
        string="Unpaid Invoices Count",
        compute="_compute_financial_status",
        store=True,
        groups="school_management.group_school_admin,base.group_system",
    )
    enrollment_count = fields.Integer(
        string="Enrollment Count",
        compute="_compute_counts",
    )
    session_count = fields.Integer(
        string="Total Sessions",
        compute="_compute_counts",
    )
    submission_count = fields.Integer(
        string="Submission Count",
        compute="_compute_counts",
    )
    report_card_count = fields.Integer(
        string="Report Card Count",
        compute="_compute_counts",
    )

    _unique_student_id = models.UniqueIndex(
        "(lower(student_id)) WHERE student_id IS NOT NULL",
        "The Student ID must be unique.",
    )
    _unique_user_id = models.UniqueIndex(
        "(user_id) WHERE user_id IS NOT NULL",
        "A student login can only be linked to one student record.",
    )
    _check_status = models.Constraint(
        "CHECK(status IN ('active', 'suspended', 'graduated', 'dropped'))",
        "Student status must be active, suspended, graduated, or dropped.",
    )

    def _compute_currency_id(self):
        currency = self.env.company.currency_id
        for rec in self:
            rec.currency_id = currency

    def action_view_payments(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Payments",
            "res_model": "university.payment",
            "view_mode": "list,form",
            "domain": [("student_id", "=", self.id)],
            "context": {"default_fee_id": False},
        }

    def action_view_enrollments(self):
        self.ensure_one()
        user = self.env.user
        is_admin = user.has_group("school_management.group_school_admin") or self.env.su
        teacher_rec = False
        if not is_admin and (
            user.has_group("school_management.group_school_teacher")
            or user.has_group("school_management.group_university_teacher")
        ):
            teacher_rec = self.env["university.teacher"].search([("user_id", "=", user.id)], limit=1)

        domain = [("student_id", "=", self.id)]
        if teacher_rec:
            domain.append(("section_id.teacher_id", "=", teacher_rec.id))

        return {
            "type": "ir.actions.act_window",
            "name": _("Enrollments - %s", self.name),
            "res_model": "university.enrollment",
            "view_mode": "list,form",
            "domain": domain,
            "context": {"default_student_id": self.id},
        }

    def action_view_sessions(self):
        self.ensure_one()
        user = self.env.user
        is_admin = user.has_group("school_management.group_school_admin") or self.env.su
        teacher_rec = False
        if not is_admin and (
            user.has_group("school_management.group_school_teacher")
            or user.has_group("school_management.group_university_teacher")
        ):
            teacher_rec = self.env["university.teacher"].search([("user_id", "=", user.id)], limit=1)

        if teacher_rec:
            teacher_enrs = self.sudo().enrollment_ids.filtered(lambda e: e.section_id.teacher_id == teacher_rec)
            sec_ids = teacher_enrs.mapped("section_id").ids
            domain = [("section_id", "in", sec_ids), "|", ("teacher_id", "=", teacher_rec.id), ("instructor_id", "=", teacher_rec.id)]
        else:
            sec_ids = self.sudo().enrollment_ids.mapped("section_id").ids
            domain = [("section_id", "in", sec_ids)]

        return {
            "type": "ir.actions.act_window",
            "name": _("Sessions - %s", self.name),
            "res_model": "university.timetable.slot",
            "view_mode": "calendar,list,form",
            "domain": domain,
            "context": {"default_student_id": self.id},
        }

    def action_view_fees(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Fee Invoices - %s", self.name),
            "res_model": "university.fee",
            "view_mode": "list,form",
            "domain": [("student_id", "=", self.id)],
            "context": {"default_student_id": self.id},
        }

    def action_view_submissions(self):
        self.ensure_one()
        user = self.env.user
        is_admin = user.has_group("school_management.group_school_admin") or self.env.su
        teacher_rec = False
        if not is_admin and (
            user.has_group("school_management.group_school_teacher")
            or user.has_group("school_management.group_university_teacher")
        ):
            teacher_rec = self.env["university.teacher"].search([("user_id", "=", user.id)], limit=1)

        domain = [("student_id", "=", self.id)]
        if teacher_rec:
            domain.append(("assignment_id.teacher_id", "=", teacher_rec.id))

        return {
            "type": "ir.actions.act_window",
            "name": _("Submissions - %s", self.name),
            "res_model": "university.assignment.submission",
            "view_mode": "list,form",
            "domain": domain,
            "context": {"default_student_id": self.id},
        }

    def action_view_report_cards(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Report Cards - %s", self.name),
            "res_model": "university.report.card",
            "view_mode": "list,form",
            "domain": [("student_id", "=", self.id)],
            "context": {"default_student_id": self.id},
        }

    def action_view_exam_scores(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id("school_management.action_university_exam_score")
        action["domain"] = [("student_id", "=", self.id)]
        action["context"] = {"default_student_id": self.id}
        action["name"] = _("Exam & Quiz Results - %s") % self.name
        return action

    def action_register_student_payment(self):
        self.ensure_one()
        fee = self.sudo().fee_ids.filtered(lambda f: f.state == "posted" and f.balance > 0).sorted("date asc, id asc")[:1]
        if not fee:
            raise UserError(_("No unpaid posted fee invoices found for this student."))
        return fee.action_register_payment()

    def action_send_urgent_payment_reminder(self):
        self.ensure_one()
        fees = self.sudo().fee_ids.filtered(lambda f: f.state == "posted" and f.balance > 0)
        if not fees:
            raise UserError(_("No unpaid posted fee invoices found for this student."))
        for f in fees:
            f.action_send_payment_reminder()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Urgent Payment Notices Sent"),
                "message": _("Payment alert notifications sent for %s's outstanding fees totaling $%.2f.") % (self.name, self.fee_balance),
                "type": "warning",
                "sticky": False,
            }
        }

    def action_open_enrollment_registration(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Register Enrollments",
            "res_model": "university.student.enrollment.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_student_id": self.id,
            },
        }

    def action_continue_student(self):
        self.ensure_one()
        if not self.env.su and not self.env.user.has_group("school_management.group_school_admin"):
            raise AccessError("Only University Administrators can continue a dropped student.")
        if self.status != "dropped" and self.active:
            raise UserError("Only dropped or inactive students can be continued.")

        return {
            "type": "ir.actions.act_window",
            "name": "Continue Student",
            "res_model": "university.student.enrollment.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_student_id": self.id,
                "continue_student": True,
            },
        }

    def _check_user_is_student_only(self, user):
        """Never touch staff/admin accounts from the student form."""
        user = user.sudo()
        if (
            user.has_group("base.group_system")
            or user.has_group("school_management.group_school_admin")
            or user.has_group("school_management.group_school_teacher")
            or user.has_group("school_management.group_school_hod")
            or user.has_group("school_management.group_school_dean")
        ):
            raise UserError(
                _("User %s is a staff or admin account and cannot be managed from the student form.")
                % user.login
            )

    def action_create_user(self):
        self.ensure_one()
        if not self.env.su and not self.env.user.has_group("school_management.group_school_admin"):
            raise AccessError(_("Only University Administrators can create student login accounts."))

        email = (self.email or "").strip().lower()
        if not email:
            raise UserError(_("Cannot create account: student %s has no email address.") % self.name)

        if self.user_id:
            raise UserError(_("Student %s is already linked to user account %s.") % (self.name, self.user_id.login))

        Users = self.env["res.users"].sudo()
        student_group = self.env.ref("school_management.group_school_student")
        internal_group = self.env.ref("base.group_user")

        existing_user = Users.search([("login", "=", email)], limit=1)
        if existing_user:
            other_student = self.sudo().search(
                [("user_id", "=", existing_user.id), ("id", "!=", self.id)], limit=1
            )
            if other_student:
                raise UserError(
                    _("Email %(email)s is already linked to another student: %(student)s.")
                    % {"email": email, "student": other_student.name}
                )
            self._check_user_is_student_only(existing_user)
            existing_user.write({"group_ids": [(4, internal_group.id), (4, student_group.id)]})
            self.sudo().write({"user_id": existing_user.id})
            message = _("Existing account %s linked to %s. Its password was not changed.") % (email, self.name)
        else:
            user = Users.with_context(no_reset_password=True).create({
                "name": self.name,
                "login": email,
                "email": email,
                "password": DEFAULT_STUDENT_PASSWORD,
                "group_ids": [(6, 0, [internal_group.id, student_group.id])],
            })
            self.sudo().write({"user_id": user.id})
            message = _("Login created for %(name)s. Login: %(login)s / Password: %(pwd)s") % {
                "name": self.name, "login": email, "pwd": DEFAULT_STUDENT_PASSWORD,
            }

        self.message_post(body=_("Login account set up by %s.") % self.env.user.name)
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Account Ready"),
                "message": message,
                "type": "success",
                "sticky": False,
            },
        }

    def action_reset_password(self):
        self.ensure_one()
        if not self.env.su and not self.env.user.has_group("school_management.group_school_admin"):
            raise AccessError(_("Only University Administrators can reset student passwords."))

        if not self.user_id:
            raise UserError(_("Student %s does not have a linked login account.") % self.name)

        self._check_user_is_student_only(self.user_id)
        self.user_id.sudo().write({"password": DEFAULT_STUDENT_PASSWORD})
        self.message_post(body=_("Password reset to the default by %s.") % self.env.user.name)
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Password Reset"),
                "message": _("The password for %(login)s is now %(pwd)s.") % {
                    "login": self.user_id.login, "pwd": DEFAULT_STUDENT_PASSWORD,
                },
                "type": "success",
                "sticky": False,
            },
        }

    @api.depends("enrollment_ids", "submission_ids", "report_card_ids")
    @api.depends_context("uid")
    def _compute_counts(self):
        user = self.env.user
        is_admin = user.has_group("school_management.group_school_admin") or self.env.su
        is_teacher = not is_admin and (
            user.has_group("school_management.group_school_teacher")
            or user.has_group("school_management.group_university_teacher")
        )
        teacher_rec = False
        if is_teacher:
            teacher_rec = self.env["university.teacher"].search([("user_id", "=", user.id)], limit=1)

        if teacher_rec:
            enrollment_data = dict(
                self.env["university.enrollment"].sudo()._read_group(
                    [("student_id", "in", self.ids), ("section_id.teacher_id", "=", teacher_rec.id)],
                    groupby=["student_id"],
                    aggregates=["__count"],
                )
            )
            submission_data = dict(
                self.env["university.assignment.submission"].sudo()._read_group(
                    [("student_id", "in", self.ids), ("assignment_id.teacher_id", "=", teacher_rec.id)],
                    groupby=["student_id"],
                    aggregates=["__count"],
                )
            )
            report_card_data = dict(
                self.env["university.report.card"].sudo()._read_group(
                    [("student_id", "in", self.ids)],
                    groupby=["student_id"],
                    aggregates=["__count"],
                )
            )
            teacher_slots = self.env["university.timetable.slot"].sudo().search([
                "|",
                ("teacher_id", "=", teacher_rec.id),
                ("instructor_id", "=", teacher_rec.id),
            ])
            sec_slot_map = {}
            for slot in teacher_slots:
                if slot.section_id:
                    sec_slot_map[slot.section_id.id] = sec_slot_map.get(slot.section_id.id, 0) + 1

            teacher_enrollments = self.env["university.enrollment"].sudo().search([
                ("student_id", "in", self.ids),
                ("section_id.teacher_id", "=", teacher_rec.id),
            ])
            student_sec_map = {}
            for enr in teacher_enrollments:
                if enr.section_id:
                    student_sec_map.setdefault(enr.student_id.id, []).append(enr.section_id.id)

            for student in self:
                student.enrollment_count = enrollment_data.get(student, 0)
                student.submission_count = submission_data.get(student, 0)
                student.report_card_count = report_card_data.get(student, 0)
                sec_ids = student_sec_map.get(student.id, [])
                student.session_count = sum(sec_slot_map.get(s, 0) for s in sec_ids)
        else:
            enrollment_data = dict(
                self.env["university.enrollment"]._read_group(
                    [("student_id", "in", self.ids)],
                    groupby=["student_id"],
                    aggregates=["__count"],
                )
            )
            submission_data = dict(
                self.env["university.assignment.submission"]._read_group(
                    [("student_id", "in", self.ids)],
                    groupby=["student_id"],
                    aggregates=["__count"],
                )
            )
            report_card_data = dict(
                self.env["university.report.card"].sudo()._read_group(
                    [("student_id", "in", self.ids)],
                    groupby=["student_id"],
                    aggregates=["__count"],
                )
            )
            all_slots = self.env["university.timetable.slot"].search([
                ("section_id", "!=", False)
            ])
            sec_slot_map = {}
            for slot in all_slots:
                sec_slot_map[slot.section_id.id] = sec_slot_map.get(slot.section_id.id, 0) + 1

            all_enrollments = self.env["university.enrollment"].sudo().search([
                ("student_id", "in", self.ids),
            ])
            student_sec_map = {}
            for enr in all_enrollments:
                if enr.section_id:
                    student_sec_map.setdefault(enr.student_id.id, []).append(enr.section_id.id)

            for student in self:
                student.enrollment_count = enrollment_data.get(student, 0)
                student.submission_count = submission_data.get(student, 0)
                student.report_card_count = report_card_data.get(student, 0)
                sec_ids = student_sec_map.get(student.id, [])
                student.session_count = sum(sec_slot_map.get(s, 0) for s in sec_ids)

    @api.depends(
        "fee_ids.total_amount",
        "fee_ids.paid_amount",
        "fee_ids.balance",
        "fee_ids.state",
    )
    def _compute_fee_totals(self):
        for rec in self:
            confirmed = rec.sudo().fee_ids.filtered(lambda fee: fee.state in ("posted", "paid"))
            rec.fee_total = sum(confirmed.mapped("total_amount"))
            rec.fee_paid = sum(confirmed.mapped("paid_amount"))
            rec.fee_balance = sum(confirmed.mapped("balance"))

    @api.depends("fee_ids.balance", "fee_ids.state", "fee_ids.due_date")
    def _compute_financial_status(self):
        today = fields.Date.context_today(self)
        for student in self:
            active_fees = student.sudo().fee_ids.filtered(lambda f: f.state in ("posted", "paid"))
            if not active_fees:
                student.financial_status = "no_invoices"
                student.overdue_fee_count = 0
                student.unpaid_fee_count = 0
                continue

            overdue_fees = active_fees.filtered(lambda f: f.state == "posted" and f.balance > 0 and f.due_date and f.due_date < today)
            unpaid_fees = active_fees.filtered(lambda f: f.state == "posted" and f.balance > 0)
            student.overdue_fee_count = len(overdue_fees)
            student.unpaid_fee_count = len(unpaid_fees)

            if overdue_fees:
                student.financial_status = "overdue"
            elif unpaid_fees:
                student.financial_status = "pending"
            else:
                student.financial_status = "good_standing"

    @api.depends("program_id.department_id")
    def _compute_department_id(self):
        for rec in self:
            if rec.program_id:
                rec.department_id = rec.program_id.department_id
            elif not rec.department_id:
                rec.department_id = False

    @api.onchange("program_id")
    def _onchange_program_id(self):
        if self.program_id:
            self.department_id = self.program_id.department_id

    @api.constrains("date_of_birth")
    def _check_date_of_birth(self):
        today = fields.Date.context_today(self)
        for rec in self:
            if rec.date_of_birth:
                if rec.date_of_birth > today:
                    raise ValidationError(_("Date of birth cannot be in the future."))
                try:
                    min_birth_date = today.replace(year=today.year - 15)
                except ValueError:
                    min_birth_date = today.replace(year=today.year - 15, day=28)
                if rec.date_of_birth > min_birth_date:
                    raise ValidationError(_("Student must be at least 15 years old for admission."))

    @api.constrains("program_id", "department_id")
    def _check_program_department(self):
        for rec in self:
            if rec.program_id and rec.department_id and rec.program_id.department_id != rec.department_id:
                raise ValidationError(
                    _("The program '%(program)s' does not belong to department '%(department)s'.")
                    % {
                        "program": rec.program_id.display_name,
                        "department": rec.department_id.display_name,
                    }
                )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            raw_id = vals.get("student_id")
            if not raw_id or not str(raw_id).strip():
                vals["student_id"] = (
                    self.env["ir.sequence"].next_by_code("university.student")
                    or _("New")
                )
            elif isinstance(raw_id, str):
                vals["student_id"] = raw_id.strip()
        return super().create(vals_list)

    def _compute_advising_counts(self):
        NoteModel = self.env["university.student.advising.note"].sudo()
        FollowupModel = self.env["university.student.followup"].sudo()
        for student in self:
            student.advising_note_count = NoteModel.search_count([("student_id", "=", student.id)])
            followups = FollowupModel.search([("student_id", "=", student.id)])
            student.followup_count = len(followups)
            student.pending_followup_count = len(followups.filtered(lambda f: f.state in ("pending", "in_progress")))

    @api.depends(
        "report_card_ids.state",
        "report_card_ids.line_ids.is_passing",
        "report_card_ids.line_ids.credits",
        "report_card_ids.line_ids.grade_point",
        "transcript_ids.cumulative_gpa",
        "transcript_ids.total_credits",
    )
    def _compute_academic_metrics(self):
        ICP = self.env["ir.config_parameter"].sudo()
        try:
            gpa_thresh = float(ICP.get_param("school_management.risk_gpa_threshold", 2.0))
        except (ValueError, TypeError):
            gpa_thresh = 2.0
        try:
            att_thresh = float(ICP.get_param("school_management.risk_attendance_threshold", 75.0))
        except (ValueError, TypeError):
            att_thresh = 75.0

        for student in self:
            # 1. GPA and Credits
            transcripts = student.transcript_ids.filtered(lambda t: t.state in ("generated", "approved"))
            if transcripts:
                gpa = transcripts[0].cumulative_gpa
                credits = transcripts[0].total_credits
            else:
                cards = student.report_card_ids.filtered(lambda c: c.state in ("generated", "approved"))
                if cards:
                    total_pts = sum(line.credits * line.grade_point for c in cards for line in c.line_ids)
                    total_creds = sum(line.credits for c in cards for line in c.line_ids)
                    gpa = round(total_pts / total_creds, 2) if total_creds else 0.0
                    credits = sum(line.credits for c in cards for line in c.line_ids if line.is_passing)
                else:
                    gpa = 0.0
                    credits = 0

            # 2. Failed Subjects & Graduation Standard
            cards = student.report_card_ids.filtered(lambda c: c.state in ("generated", "approved"))
            min_grad = student.program_id.min_graduation_grade_id
            if min_grad:
                failed_count = sum(1 for c in cards for line in c.line_ids if not line.is_passing or line.grade_point < min_grad.grade_point)
            else:
                failed_count = sum(1 for c in cards for line in c.line_ids if not line.is_passing)

            # 3. Attendance Rate
            attendances = self.env["university.attendance"].search([("student_id", "=", student.id)])
            if attendances:
                present_cnt = sum(1 for a in attendances if a.status in ("present", "late", "excused"))
                attendance_rate = round(present_cnt * 100.0 / len(attendances), 1)
            else:
                attendance_rate = 100.0

            # 4. Risk Level & Reason
            reasons = []
            risk = "low"
            if gpa > 0 and gpa < gpa_thresh:
                reasons.append(_("GPA is %.2f (below threshold %.2f)") % (gpa, gpa_thresh))
                risk = "high"
            if len(attendances) >= 3 and attendance_rate < att_thresh:
                reasons.append(_("Attendance is %.1f%% (below threshold %.1f%%)") % (attendance_rate, att_thresh))
                if risk != "high":
                    risk = "medium"
            if failed_count > 0:
                reasons.append(_("%d failed subject(s)") % failed_count)
                if risk == "low":
                    risk = "medium"

            student.gpa = gpa
            student.completed_credits = credits
            student.failed_subject_count = failed_count
            student.attendance_rate = attendance_rate
            student.risk_level = risk
            student.risk_reason = " | ".join(reasons) if reasons else _("Academic progress on track")

    def action_view_advising_notes(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Advising Notes - %s", self.name),
            "res_model": "university.student.advising.note",
            "view_mode": "list,form",
            "domain": [("student_id", "=", self.id)],
            "context": {"default_student_id": self.id},
        }

    @api.model
    def action_open_own_profile(self):
        """Open the student profile linked to the current login."""
        student = self.search([("user_id", "=", self.env.user.id)], limit=1)
        if not student:
            raise UserError(
                _("No student profile is linked to your login. Please contact an administrator.")
            )

        return {
            "type": "ir.actions.act_window",
            "name": _("My Profile"),
            "res_model": "university.student",
            "res_id": student.id,
            "views": [
                (self.env.ref("school_management.view_university_student_form").id, "form")
            ],
            "view_mode": "form",
            "target": "current",
            "context": {
                "create": False,
                "edit": False,
                "delete": False,
                "form_view_initial_mode": "readonly",
            },
        }

    def action_view_followups(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Follow-up Actions - %s", self.name),
            "res_model": "university.student.followup",
            "view_mode": "list,form",
            "domain": [("student_id", "=", self.id)],
            "context": {"default_student_id": self.id},
        }

    def write(self, vals):
        if "student_id" in vals and isinstance(vals["student_id"], str):
            vals["student_id"] = vals["student_id"].strip()

        if "advisor_id" in vals:
            is_admin = self.env.su or self.env.user.has_group("school_management.group_school_admin")
            is_hod = self.env.user.has_group("school_management.group_school_hod")
            if not is_admin and not is_hod:
                raise AccessError(_("Only University Administrators and Heads of Department can assign academic advisors."))
            if is_hod and not is_admin:
                hod_teacher = self.env.user.teacher_id or self.env["university.teacher"].sudo().search([("user_id", "=", self.env.user.id)], limit=1)
                managed_dept = (hod_teacher.managed_department_id if hod_teacher else False) or (self.env["university.department"].search([("head_id", "=", hod_teacher.id)], limit=1) if hod_teacher else False)
                new_advisor_id = vals.get("advisor_id")
                if new_advisor_id:
                    advisor = self.env["university.teacher"].browse(new_advisor_id)
                    if not managed_dept or advisor.department_id != managed_dept:
                        raise AccessError(_("Heads of Department can only assign advisors within their managed department."))
                for student in self:
                    if not managed_dept or student.department_id != managed_dept:
                        raise AccessError(_("Heads of Department can only assign advisors for students in their managed department."))

        return super().write(vals)

    def unlink(self):
        for rec in self:
            blocking = []
            if rec.enrollment_ids:
                blocking.append(_("%(count)d enrollment(s)", count=len(rec.enrollment_ids)))
            if rec.report_card_ids:
                blocking.append(_("%(count)d report card(s)", count=len(rec.report_card_ids)))
            if rec.transcript_ids:
                blocking.append(_("%(count)d transcript(s)", count=len(rec.transcript_ids)))
            if blocking:
                raise UserError(
                    _("Cannot delete student '%(student)s' because they have existing records: %(details)s. Archive the student instead.")
                    % {
                        "student": rec.display_name,
                        "details": ", ".join(blocking),
                    }
                )
        return super().unlink()
