import secrets

from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


class UniversityTranscriptRequest(models.Model):
    _name = "university.transcript.request"
    _description = "Transcript Request"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    _name_unique = models.Constraint(
        "UNIQUE (name)",
        "The transcript request reference must be unique.",
    )

    def _default_student(self):
        student = self.env["university.student"].search([("user_id", "=", self.env.uid)], limit=1)
        return student.id if student else False

    name = fields.Char(
        string="Request Reference",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: "New",
    )
    student_id = fields.Many2one(
        "university.student",
        string="Student",
        required=True,
        tracking=True,
        index=True,
        default=lambda self: self._default_student(),
    )
    program_id = fields.Many2one(
        "university.program",
        string="Major / Program",
        related="student_id.program_id",
        store=True,
        readonly=True,
        index=True,
    )
    request_type = fields.Selection(
        [
            ("official", "Official Transcript"),
            ("unofficial", "Unofficial Transcript"),
        ],
        string="Request Type",
        default="official",
        required=True,
        tracking=True,
    )
    copies = fields.Integer(
        string="Number of Copies",
        default=1,
        required=True,
    )
    purpose = fields.Selection(
        [
            ("employment", "Employment"),
            ("scholarship", "Scholarship Application"),
            ("transfer", "University Transfer"),
            ("visa", "Visa / Immigration"),
            ("other", "Other"),
        ],
        string="Purpose",
        default="employment",
        required=True,
    )
    purpose_other = fields.Char(string="Purpose Details")
    delivery_method = fields.Selection(
        [
            ("download", "Electronic PDF Download"),
            ("pickup", "In-Person Campus Pickup"),
            ("mail", "Postal Mail"),
        ],
        string="Delivery Method",
        default="download",
        required=True,
    )
    recipient = fields.Char(string="Recipient / Organization")
    delivery_address = fields.Text(string="Delivery Address")

    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("submitted", "Submitted"),
            ("approved", "Approved"),
            ("issued", "Issued"),
            ("delivered", "Delivered"),
            ("rejected", "Rejected"),
            ("cancelled", "Cancelled"),
        ],
        string="Status",
        default="draft",
        required=True,
        tracking=True,
        index=True,
    )
    reject_reason = fields.Text(
        string="Rejection Reason",
        tracking=True,
    )
    approved_by = fields.Many2one(
        "res.users",
        string="Approved By",
        readonly=True,
        tracking=True,
    )
    approved_date = fields.Datetime(
        string="Approval Date",
        readonly=True,
        tracking=True,
    )
    transcript_id = fields.Many2one(
        "university.transcript",
        string="Generated Transcript",
        readonly=True,
        tracking=True,
    )
    verification_code = fields.Char(
        string="Verification Code",
        readonly=True,
        copy=False,
    )

    # Optional Fee & Payment Fields
    fee_amount = fields.Monetary(
        string="Processing Fee",
        currency_field="currency_id",
        default=0.0,
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        default=lambda self: self.env.company.currency_id,
    )
    payment_state = fields.Selection(
        [
            ("not_required", "Not Required"),
            ("pending", "Pending Payment"),
            ("paid", "Paid"),
        ],
        string="Payment Status",
        default="not_required",
        tracking=True,
    )

    # Computed helper for holds
    show_holds_alert = fields.Boolean(
        string="Show Holds Alert",
        compute="_compute_show_holds_alert",
        store=False,
    )
    can_download_transcript = fields.Boolean(
        string="Can Download Transcript",
        compute="_compute_can_download_transcript",
        store=False,
    )
    has_holds = fields.Boolean(
        string="Has Academic/Financial Holds",
        compute="_compute_holds",
        store=False,
    )
    has_block_holds = fields.Boolean(
        string="Has Blocking Holds",
        compute="_compute_holds",
        store=False,
    )
    grades_status = fields.Char(
        string="Grades Status",
        compute="_compute_holds",
        store=False,
    )
    finance_status = fields.Char(
        string="Finance Status",
        compute="_compute_holds",
        store=False,
    )
    override_user_id = fields.Many2one(
        "res.users",
        string="Override Approved By",
        readonly=True,
        tracking=True,
    )
    override_date = fields.Datetime(
        string="Override Date",
        readonly=True,
        tracking=True,
    )
    override_reason = fields.Text(
        string="Override Reason",
        readonly=True,
        tracking=True,
    )
    holds_summary = fields.Text(
        string="Active Holds",
        compute="_compute_holds",
        store=False,
    )

    # -------------------------------------------------------------------------
    # Constraints
    # -------------------------------------------------------------------------
    @api.constrains("copies")
    def _check_copies(self):
        for record in self:
            if record.copies < 1:
                raise ValidationError("The number of copies must be at least 1.")

    @api.constrains("student_id", "request_type", "state")
    def _check_open_requests(self):
        for record in self:
            if record.state in ("draft", "submitted", "approved"):
                duplicate_count = self.search_count([
                    ("id", "!=", record.id),
                    ("student_id", "=", record.student_id.id),
                    ("request_type", "=", record.request_type),
                    ("state", "in", ("draft", "submitted", "approved")),
                ])
                if duplicate_count:
                    raise ValidationError(
                        f"Student '{record.student_id.name}' already has an active {record.request_type} "
                        "transcript request in progress. Please wait until it is processed or cancelled."
                    )

    # -------------------------------------------------------------------------
    # CRUD
    # -------------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code("university.transcript.request")
                    or "New"
                )
        return super().create(vals_list)

    # -------------------------------------------------------------------------
    # Hold Detection
    # -------------------------------------------------------------------------
    def _get_transcript_holds(self):
        """Returns a list of hold dicts: [{'code': ..., 'severity': 'block'|'warning', 'message': ...}]."""
        self.ensure_one()
        holds = []
        if not self.student_id:
            return holds

        # 1. Student Status Hold: Must be active or graduated
        if self.student_id.status not in ("active", "graduated"):
            holds.append({
                "code": "student_status",
                "severity": "block",
                "message": _(
                    "Student status is '%(status)s'. Only Active or Graduated students may receive transcripts."
                ) % {"status": self.student_id.status or "Unspecified"},
            })

        # 2. Report Cards / Grades holds
        published_cards = self.env["university.report.card"].search_count([
            ("student_id", "=", self.student_id.id),
            ("state", "in", ("generated", "approved")),
        ])
        existing_transcripts = self.env["university.transcript"].search_count([
            ("student_id", "=", self.student_id.id),
            ("state", "in", ("generated", "approved")),
        ])
        if not published_cards and not existing_transcripts:
            draft_cards = self.env["university.report.card"].search_count([
                ("student_id", "=", self.student_id.id),
                ("state", "=", "draft"),
            ])
            if draft_cards:
                holds.append({
                    "code": "no_grades",
                    "severity": "block",
                    "message": _("There are %(count)d unfinalized/draft semester report card(s) pending approval.") % {"count": draft_cards},
                })
            else:
                holds.append({
                    "code": "no_grades",
                    "severity": "block",
                    "message": _("No finalized report cards found for %(name)s.") % {"name": self.student_id.name},
                })

        # 3. Financial holds (Overdue posted fees > threshold)
        ICP = self.env["ir.config_parameter"].sudo()
        try:
            min_balance = float(ICP.get_param("school_management.transcript_hold_min_balance", 0.0))
        except (ValueError, TypeError):
            min_balance = 0.0

        today = fields.Date.today()
        overdue_fees = self.env["university.fee"].search([
            ("student_id", "=", self.student_id.id),
            ("state", "=", "posted"),
            ("due_date", "<=", today),
        ])
        total_overdue = sum(fee.balance for fee in overdue_fees if fee.balance > 0.0)

        if total_overdue > min_balance:
            sev = "block" if self.request_type == "official" else "warning"
            holds.append({
                "code": "financial",
                "severity": sev,
                "message": _("Outstanding tuition/fee balance of %(balance).2f.") % {"balance": total_overdue},
            })

        # 4. Request Fee Hold (when fee_amount is charged)
        if self.fee_amount > 0.0 and self.payment_state != "paid":
            holds.append({
                "code": "request_fee",
                "severity": "block",
                "message": _("Processing fee of %(amount).2f %(curr)s has not been paid.") % {
                    "amount": self.fee_amount,
                    "curr": self.currency_id.symbol or "",
                },
            })

        return holds

    def _get_holds(self):
        """Backwards compatibility returning hold message strings."""
        return [h["message"] for h in self._get_transcript_holds()]

    @api.depends("has_holds", "state")
    def _compute_show_holds_alert(self):
        for req in self:
            req.show_holds_alert = bool(req.has_holds and req.state in ("draft", "submitted"))

    @api.depends("state", "transcript_id")
    def _compute_can_download_transcript(self):
        for req in self:
            req.can_download_transcript = bool(req.state in ("issued", "delivered") and req.transcript_id)

    @api.depends("student_id", "student_id.status", "student_id.fee_balance", "fee_amount", "payment_state", "request_type")
    def _compute_holds(self):
        for req in self:
            holds = req._get_transcript_holds() if req.student_id else []
            req.has_holds = bool(holds)
            req.has_block_holds = any(h["severity"] == "block" for h in holds)
            req.holds_summary = "\n".join(f"• {h['message']}" for h in holds) if holds else ""

            no_grades = any(h["code"] == "no_grades" for h in holds)
            req.grades_status = "Grades: Missing" if no_grades else "Grades: OK"

            today = fields.Date.today()
            overdue = sum(f.balance for f in self.env["university.fee"].search([
                ("student_id", "=", req.student_id.id),
                ("state", "=", "posted"),
                ("due_date", "<=", today),
            ]) if f.balance > 0.0) if req.student_id else 0.0

            if any(h["code"] == "financial" for h in holds):
                req.finance_status = f"Finance: Overdue {overdue:.2f}"
            else:
                req.finance_status = "Finance: Clear"

    def _check_registrar_permission(self):
        """Verifies current user belongs to Registrar or Admin role."""
        if not (
            self.env.user.has_group("school_management.group_school_registrar")
            or self.env.user.has_group("school_management.group_school_admin")
            or self.env.is_superuser()
        ):
            raise UserError(
                _("Permission Denied: Only a Registrar or University Administrator can perform this action.")
            )

    # -------------------------------------------------------------------------
    # Actions & Workflow
    # -------------------------------------------------------------------------
    def action_submit(self):
        for req in self:
            if req.state != "draft":
                raise UserError(_("Only draft requests can be submitted."))
            req.with_context(workflow_transition=True).write({"state": "submitted"})
            req.message_post(body=_("Transcript request submitted for administrative review."))

            # Schedule activity for registrar group users
            registrar_group = self.env.ref("school_management.group_school_registrar", raise_if_not_found=False)
            admin_group = self.env.ref("school_management.group_school_admin", raise_if_not_found=False)
            users = registrar_group.user_ids if registrar_group and registrar_group.user_ids else (
                admin_group.user_ids if admin_group and admin_group.user_ids else self.env["res.users"]
            )
            activity_type = self.env.ref("mail.mail_activity_data_todo", raise_if_not_found=False)
            for u in users[:5]:
                try:
                    req.sudo().activity_schedule(
                        activity_type_id=activity_type.id if activity_type else False,
                        summary=f"Review Transcript Request: {req.name}",
                        note=f"Student {req.student_id.name} submitted a request for an {req.request_type} transcript ({req.purpose}).",
                        user_id=u.id,
                    )
                except Exception:
                    pass
            req._send_transcript_mail("school_management.mail_template_transcript_request_submitted")

    def _send_transcript_mail(self, template_xmlid):
        self.ensure_one()
        template = self.env.ref(template_xmlid, raise_if_not_found=False)
        if template and self.student_id.email:
            try:
                template.sudo().send_mail(self.id, force_send=False)
            except Exception:
                pass

    def action_approve(self):
        self._check_registrar_permission()
        for req in self:
            if req.state != "submitted":
                raise UserError(_("Only submitted requests can be approved."))

            holds = req._get_transcript_holds()
            block_holds = [h for h in holds if h["severity"] == "block"]
            if block_holds:
                hold_lines = "\n".join(f"• {h['message']}" for h in block_holds)
                raise UserError(
                    _("Cannot approve transcript request due to the following active hold(s):\n\n%s") % hold_lines
                )

            req.write({
                "state": "approved",
                "approved_by": self.env.user.id,
                "approved_date": fields.Datetime.now(),
            })
            req.action_feedback(feedback=_("Transcript request approved by registrar."))
            req.message_post(body=_("Transcript request approved by %s.") % self.env.user.name)
            req._send_transcript_mail("school_management.mail_template_transcript_request_approved")

    def action_open_override_wizard(self):
        self.ensure_one()
        self._check_registrar_permission()
        return {
            "name": _("Approve Transcript Request (Override Holds)"),
            "type": "ir.actions.act_window",
            "res_model": "university.transcript.request.override.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_request_id": self.id},
        }

    def action_confirm_override(self, reason):
        self.ensure_one()
        if not (
            self.env.user.has_group("school_management.group_school_registrar")
            or self.env.user.has_group("school_management.group_school_admin")
            or self.env.is_superuser()
        ):
            raise UserError(_("Only University Administrators or Registrars can override holds."))

        if not reason or len(reason.strip()) < 10:
            raise ValidationError(_("The override reason must be at least 10 characters long."))

        holds = self._get_transcript_holds()
        hold_codes = [h["code"] for h in holds]

        self.write({
            "state": "approved",
            "approved_by": self.env.user.id,
            "approved_date": fields.Datetime.now(),
            "override_user_id": self.env.user.id,
            "override_date": fields.Datetime.now(),
            "override_reason": reason.strip(),
        })

        body = Markup(_(
            "Administrative Override executed by %(user)s.<br/>"
            "<b>Overridden hold codes:</b> %(codes)s<br/>"
            "<b>Reason:</b> %(reason)s"
        )) % {
            "user": self.env.user.name,
            "codes": ", ".join(hold_codes),
            "reason": reason.strip(),
        }
        self.message_post(body=body)
        self.action_feedback(feedback=_("Transcript request approved via administrative override."))
        self._send_transcript_mail("school_management.mail_template_transcript_request_approved")
        return True

    def action_reject(self, reason=None):
        self._check_registrar_permission()
        for req in self:
            if req.state not in ("submitted", "approved"):
                raise UserError(_("Only submitted or approved requests can be rejected."))

            if reason:
                req.reject_reason = reason

            if not req.reject_reason:
                raise UserError(_("A rejection reason is required to reject this request."))

            req.write({
                "state": "rejected",
                "approved_by": self.env.user.id,
                "approved_date": fields.Datetime.now(),
            })
            req.action_feedback(feedback=_(f"Transcript request rejected: {req.reject_reason}"))
            req.message_post(
                body=Markup(_("Transcript request rejected by %s.<br/><b>Reason:</b> %s"))
                % (self.env.user.name, req.reject_reason)
            )
            req._send_transcript_mail("school_management.mail_template_transcript_request_rejected")

    def action_open_reject_wizard(self):
        self.ensure_one()
        self._check_registrar_permission()
        return {
            "name": _("Reject Transcript Request"),
            "type": "ir.actions.act_window",
            "res_model": "university.transcript.request.reject.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_request_id": self.id},
        }

    def action_issue(self):
        self._check_registrar_permission()
        for req in self:
            if req.state != "approved":
                raise UserError(_("A transcript request must be approved before it can be issued."))

            # Ensure holds still do not exist when issuing official transcripts
            if req.request_type == "official":
                holds = req._get_holds()
                if holds:
                    hold_lines = "\n".join(f"• {h}" for h in holds)
                    raise UserError(
                        _("Cannot issue official transcript due to active hold(s):\n\n%s", hold_lines)
                    )

            # Generate or link transcript
            transcript = req.transcript_id
            if not transcript:
                # Search if student already has an approved transcript
                existing_transcript = self.env["university.transcript"].search(
                    [("student_id", "=", req.student_id.id), ("state", "=", "approved")],
                    limit=1,
                    order="id desc",
                )
                if existing_transcript:
                    transcript = existing_transcript
                else:
                    # Create transcript and generate lines from report cards
                    transcript = self.env["university.transcript"].create({
                        "student_id": req.student_id.id,
                    })
                    transcript.action_generate_lines()
                    transcript.action_approve()

            # Generate verification security code
            code = secrets.token_hex(8).upper()
            transcript.verification_code = code

            req.write({
                "state": "issued",
                "transcript_id": transcript.id,
                "verification_code": code,
            })
            req.message_post(
                body=Markup(_(
                    "Transcript successfully issued.<br/>"
                    "<b>Transcript Reference:</b> %s<br/>"
                    "<b>Verification Code:</b> <code>%s</code>"
                )) % (transcript.name, code)
            )
            req._send_transcript_mail("school_management.mail_template_transcript_request_issued")

    def action_deliver(self):
        self._check_registrar_permission()
        for req in self:
            if req.state != "issued":
                raise UserError(_("Only issued transcripts can be marked as delivered."))
            req.with_context(workflow_transition=True).write({"state": "delivered"})
            req.message_post(body=_("Transcript marked as delivered to student via %s.", req.delivery_method))

    def action_cancel(self):
        for req in self:
            if req.state not in ("draft", "submitted"):
                raise UserError(_("You can only cancel a request in Draft or Submitted status."))
            req.with_context(workflow_transition=True).write({"state": "cancelled"})
            req.action_feedback(feedback=_("Request cancelled."))
            req.message_post(body=_("Transcript request cancelled."))

    def action_reset_draft(self):
        for req in self:
            if req.state not in ("cancelled", "rejected"):
                raise UserError(_("Only cancelled or rejected requests can be reset to Draft."))
            req.with_context(workflow_transition=True).write({
                "state": "draft",
                "reject_reason": False,
            })
            req.message_post(body=_("Transcript request reset to Draft."))

    def action_feedback(self, feedback):
        """Completes all pending activities on this record."""
        activities = self.activity_ids.filtered(lambda a: a.res_model == self._name)
        if activities:
            activities.action_feedback(feedback=feedback)

    def action_download_transcript(self):
        self.ensure_one()
        if not self.transcript_id:
            raise UserError(_("No transcript has been generated for this request yet."))
        return self.env.ref("school_management.action_report_university_transcript").report_action(self.transcript_id)

    def write(self, vals):
        is_student = self.env.user.has_group("school_management.group_school_student")
        is_registrar = (
            self.env.user.has_group("school_management.group_school_registrar")
            or self.env.user.has_group("school_management.group_school_admin")
            or self.env.is_superuser()
        )
        if is_student and not is_registrar:
            if not self.env.context.get("workflow_transition"):
                restricted_fields = {
                    "state",
                    "approved_by",
                    "approved_date",
                    "reject_reason",
                    "transcript_id",
                    "verification_code",
                    "override_user_id",
                    "override_date",
                    "override_reason",
                }
                if restricted_fields.intersection(vals.keys()):
                    raise AccessError(
                        _("Students are not permitted to modify administrative or workflow fields.")
                    )
            for req in self:
                if req.state not in ("draft",) and not self.env.context.get("workflow_transition"):
                    raise UserError(
                        _("You cannot edit a transcript request once it has been submitted.")
                    )
        return super().write(vals)

    def unlink(self):
        is_registrar = (
            self.env.user.has_group("school_management.group_school_registrar")
            or self.env.user.has_group("school_management.group_school_admin")
            or self.env.is_superuser()
        )
        for req in self:
            if not is_registrar and req.state not in ("draft", "cancelled"):
                raise UserError(
                    _("Only draft or cancelled transcript requests can be deleted.")
                )
        return super().unlink()
