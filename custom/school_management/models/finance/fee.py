from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class UniversityFee(models.Model):
    _name = "university.fee"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Student Fee Invoice"
    _order = "date desc, id desc"

    name = fields.Char(
        string="Invoice Reference",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: "New",
        tracking=True,
    )
    student_id = fields.Many2one("university.student", string="Student", required=True, tracking=True)
    academic_year_id = fields.Many2one("university.academic.year", string="Academic Year", tracking=True)
    semester_id = fields.Many2one("university.semester", string="Semester", tracking=True)
    fee_structure_id = fields.Many2one(
        "university.fee.structure",
        string="Fee Structure",
    )
    admission_application_id = fields.Many2one(
        "university.admission.application",
        string="Admission Application",
        ondelete="set null",
    )
    
    date = fields.Date(string="Invoice Date", default=fields.Date.context_today, required=True, tracking=True)
    due_date = fields.Date(string="Due Date", tracking=True)
    
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        compute="_compute_currency_id",
        default=lambda self: self.env.company.currency_id,
    )
    line_ids = fields.One2many("university.fee.line", "fee_id", string="Fee Lines")
    payment_ids = fields.One2many("university.payment", "fee_id", string="Payments")
    signature_ids = fields.One2many(
        "university.document.signature",
        "fee_id",
        string="Document Signatures",
        groups="base.group_system,school_management.group_school_admin",
    )
    signature_count = fields.Integer(
        string="Signature Count",
        compute="_compute_signature_count",
        groups="base.group_system,school_management.group_school_admin",
    )
    payment_count = fields.Integer(
        string="Payments Count",
        compute="_compute_payment_count",
    )
    
    total_amount = fields.Float(string="Total Amount", compute="_compute_totals", store=True, tracking=True)
    paid_amount = fields.Float(string="Paid Amount", compute="_compute_totals", store=True, tracking=True)
    balance = fields.Float(string="Balance", compute="_compute_totals", store=True, tracking=True)

    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("posted", "Posted"),
            ("paid", "Paid"),
            ("canceled", "Canceled"),
        ],
        string="Status",
        default="draft",
        tracking=True,
    )

    payment_state = fields.Selection(
        [
            ("not_paid", "Unpaid / Pending"),
            ("partial", "Partially Paid"),
            ("paid", "Fully Paid"),
            ("overdue", "Overdue / Alert"),
        ],
        string="Payment Status",
        compute="_compute_payment_state",
        store=True,
        index=True,
    )
    is_overdue = fields.Boolean(
        string="Is Overdue",
        compute="_compute_payment_state",
        store=True,
        index=True,
    )
    days_overdue = fields.Integer(
        string="Days Overdue",
        compute="_compute_days_overdue",
    )
    reminder_count = fields.Integer(
        string="Reminders Sent",
        default=0,
    )
    last_reminder_date = fields.Datetime(
        string="Last Reminder Date",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code("university.fee") or "New"
        return super().create(vals_list)

    def _compute_currency_id(self):
        currency = self.env.company.currency_id
        for fee in self:
            fee.currency_id = currency

    @api.depends("payment_ids")
    def _compute_payment_count(self):
        for fee in self:
            fee.payment_count = len(fee.payment_ids)

    def _compute_days_overdue(self):
        today = fields.Date.context_today(self)
        for fee in self:
            if fee.due_date and fee.due_date < today and fee.balance > 0 and fee.state == "posted":
                fee.days_overdue = (today - fee.due_date).days
            else:
                fee.days_overdue = 0

    @api.depends(
        "line_ids.amount",
        "payment_ids.amount",
        "payment_ids.state",
    )
    def _compute_totals(self):
        for fee in self:
            total = sum(fee.line_ids.mapped("amount"))
            paid = sum(fee.payment_ids.filtered(lambda p: p.state == "posted").mapped("amount"))
            fee.total_amount = total
            fee.paid_amount = paid
            fee.balance = total - paid

    @api.depends("state", "balance", "due_date", "total_amount", "paid_amount")
    def _compute_payment_state(self):
        today = fields.Date.context_today(self)
        for fee in self:
            if fee.state == "paid" or (fee.state == "posted" and fee.balance <= 0 and fee.total_amount > 0):
                fee.payment_state = "paid"
                fee.is_overdue = False
            elif fee.state == "posted":
                is_past_due = bool(fee.due_date and fee.due_date < today and fee.balance > 0)
                fee.is_overdue = is_past_due
                if is_past_due:
                    fee.payment_state = "overdue"
                elif fee.paid_amount > 0 and fee.balance > 0:
                    fee.payment_state = "partial"
                else:
                    fee.payment_state = "not_paid"
            else:
                fee.payment_state = "not_paid"
                fee.is_overdue = False

    def _update_state_from_balance(self):
        """Transition fee state based on payment balance.

        Called after payments are posted/canceled so that the state
        always reflects the actual balance without creating a
        compute-dependency cycle on the ``state`` field.
        """
        for fee in self:
            if fee.state == "posted" and fee.balance <= 0 and fee.total_amount > 0:
                fee.state = "paid"
            elif fee.state == "paid" and fee.balance > 0:
                fee.state = "posted"

    def _send_payment_receipt_email(self, payment):
        """Send a payment receipt email for a fee that has just become paid.

        Skips sending (and logs a note in the chatter) when the student has no
        email address configured.
        """
        email = self.student_id.email
        if not email:
            self.message_post(
                body=_(
                    "Payment receipt generated for %(ref)s but NOT emailed: "
                    "the student has no email address configured.",
                    ref=self.name,
                )
            )
            return

        template = self.env.ref(
            "school_management.mail_template_payment_receipt"
        )
        template.send_mail(
            payment.id,
            force_send=False,
            email_layout_xmlid="mail.mail_notification_light",
            email_values={
                "email_to": email,
            },
        )

    @api.depends("signature_ids")
    def _compute_signature_count(self):
        for fee in self:
            fee.signature_count = len(fee.signature_ids)

    def action_register_payment(self):
        self.ensure_one()
        if self.state != "posted":
            raise ValidationError(_("You can only register payments for posted fee invoices."))
        if self.balance <= 0:
            raise ValidationError(_("This invoice is already fully settled."))
        return {
            "name": _("Register Payment - %s") % self.name,
            "type": "ir.actions.act_window",
            "res_model": "university.payment",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_student_id": self.student_id.id,
                "default_fee_id": self.id,
                "default_amount": self.balance,
                "default_date": fields.Date.context_today(self),
            },
        }

    def action_send_payment_reminder(self):
        self.ensure_one()
        if self.balance <= 0 or self.state != "posted":
            raise ValidationError(_("No outstanding balance requires payment for this invoice."))

        self.reminder_count += 1
        self.last_reminder_date = fields.Datetime.now()
        due_str = self.due_date.strftime("%B %d, %Y") if self.due_date else "Immediate Settlement"

        body = Markup(_(
            "<div style='border: 1px solid #f5c2c7; background-color: #f8d7da; padding: 12px; border-radius: 6px;'>"
            "<h5 style='color: #842029; margin-top: 0;'><i class='fa fa-exclamation-triangle'></i> URGENT TUITION PAYMENT NOTICE</h5>"
            "<p style='color: #842029; margin-bottom: 8px;'>This official notice alerts <strong>%(student)s</strong> regarding an outstanding balance on invoice <strong>%(invoice)s</strong>.</p>"
            "<ul style='color: #842029; margin-bottom: 8px;'>"
            "<li><strong>Outstanding Balance:</strong> $%(balance).2f</li>"
            "<li><strong>Invoice Due Date:</strong> %(due)s</li>"
            "<li><strong>Reminder Sequence:</strong> Notice #%(count)d</li>"
            "</ul>"
            "<p style='color: #842029; font-weight: bold; margin-bottom: 0;'>Please arrange payment as soon as possible via the University Finance Cashier or Bank Wire to maintain enrollment in good standing.</p>"
            "</div>"
        )) % {
            "student": self.student_id.name,
            "invoice": self.name,
            "balance": self.balance,
            "due": due_str,
            "count": self.reminder_count,
        }
        self.message_post(body=body, message_type="comment", subtype_xmlid="mail.mt_note")
        if self.student_id:
            self.student_id.message_post(body=body, message_type="comment", subtype_xmlid="mail.mt_note")

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Urgent Payment Notice Sent"),
                "message": _("Payment alert #%d recorded for %s ($%.2f outstanding).") % (self.reminder_count, self.student_id.name, self.balance),
                "type": "warning",
                "sticky": False,
            }
        }

    def action_view_payments(self):
        self.ensure_one()
        return {
            "name": _("Payments - %s") % self.name,
            "type": "ir.actions.act_window",
            "res_model": "university.payment",
            "view_mode": "list,kanban,form",
            "domain": [("fee_id", "=", self.id)],
            "context": {"default_fee_id": self.id, "default_student_id": self.student_id.id},
        }

    def action_view_student(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "university.student",
            "view_mode": "form",
            "res_id": self.student_id.id,
        }

    def action_request_signature(self):
        self.ensure_one()
        if self.state != "posted":
            raise ValidationError("A signature can only be requested for a posted fee invoice.")

        signature = self.signature_ids.filtered(
            lambda record: record.state == "pending"
        )[:1]
        if not signature:
            signature = self.env["university.document.signature"].create(
                {
                    "student_id": self.student_id.id,
                    "fee_id": self.id,
                }
            )

        return {
            "type": "ir.actions.act_window",
            "name": "Document Signature",
            "res_model": "university.document.signature",
            "view_mode": "form",
            "res_id": signature.id,
            "target": "current",
        }

    def action_view_signatures(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Document Signatures",
            "res_model": "university.document.signature",
            "view_mode": "list,form",
            "domain": [("fee_id", "=", self.id)],
            "context": {
                "default_fee_id": self.id,
                "default_student_id": self.student_id.id,
            },
        }

    def action_post(self):
        for fee in self:
            if fee.state != "draft":
                raise ValidationError(
                    _("Only draft fee invoices can be posted.")
                )
            if not fee.line_ids:
                raise ValidationError(_("You cannot post a fee invoice without lines."))
            fee.state = "posted"

    def action_cancel(self):
        for fee in self:
            if fee.state not in ("draft", "posted"):
                raise ValidationError(
                    _("Only draft or posted fee invoices can be canceled.")
                )
            if fee.payment_ids.filtered(lambda p: p.state == "posted"):
                raise ValidationError(
                    _(
                        "You cannot cancel a fee invoice that has posted payments. "
                        "Cancel the payments first."
                    )
                )
            fee.state = "canceled"
            
    def action_draft(self):
        if not self.env.su and not self.env.user.has_group("school_management.group_school_admin"):
            raise ValidationError(
                _("Only University Administrators can reset fee invoices to draft.")
            )
        for fee in self:
            if fee.state not in ("posted", "canceled"):
                raise ValidationError(
                    _("Only posted or canceled fee invoices can be reset to draft.")
                )
            if fee.payment_ids.filtered(lambda p: p.state == "posted"):
                raise ValidationError(
                    _("You cannot reset a fee invoice with posted payments to draft.")
                )
            fee.state = "draft"

    def action_print_invoice(self):
        self.ensure_one()
        return self.env.ref(
            "school_management.action_report_university_fee_invoice"
        ).report_action(self)

    def action_print_receipt(self):
        self.ensure_one()
        payment = self.payment_ids.filtered(
            lambda p: p.state == "posted"
        ).sorted("date desc, id desc")[:1]
        if not payment:
            raise ValidationError("No confirmed payment found for this invoice.")
        return self.env.ref(
            "school_management.action_report_university_payment_receipt"
        ).report_action(payment)


class UniversityFeeLine(models.Model):
    _name = "university.fee.line"
    _description = "Fee Line"

    fee_id = fields.Many2one("university.fee", string="Fee Invoice", required=True, ondelete="cascade")
    name = fields.Char(string="Description", required=True)
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        "res.currency",
        related="fee_id.currency_id",
        string="Currency",
        readonly=True,
    )
    amount = fields.Float(string="Amount", required=True)

    @api.constrains("amount")
    def _check_amount(self):
        for line in self:
            if line.amount < 0:
                raise ValidationError(_("Fee invoice line amounts cannot be negative."))


class UniversityFeeStructure(models.Model):
    _name = "university.fee.structure"
    _description = "Fee Structure"
    _order = "name"

    name = fields.Char(string="Fee Structure", required=True)
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        compute="_compute_currency_id",
        default=lambda self: self.env.company.currency_id,
    )
    program_id = fields.Many2one(
        "university.program",
        string="Major / Program",
        domain="[('active', '=', True)]",
    )
    academic_year_id = fields.Many2one(
        "university.academic.year",
        string="Academic Year",
        domain="[('active', '=', True)]",
    )
    semester_id = fields.Many2one(
        "university.semester",
        string="Semester",
        domain="[('active', '=', True), ('academic_year_id', '=', academic_year_id)]",
    )
    line_ids = fields.One2many(
        "university.fee.structure.line",
        "structure_id",
        string="Fee Lines",
    )
    total_amount = fields.Float(
        string="Total Amount",
        compute="_compute_total_amount",
        store=True,
    )
    active = fields.Boolean(string="Active", default=True)

    def _compute_currency_id(self):
        currency = self.env.company.currency_id
        for structure in self:
            structure.currency_id = currency

    @api.depends("line_ids.amount")
    def _compute_total_amount(self):
        for structure in self:
            structure.total_amount = sum(structure.line_ids.mapped("amount"))

    def _prepare_fee_vals(self, student, admission=None):
        self.ensure_one()
        return {
            "student_id": student.id,
            "academic_year_id": self.academic_year_id.id
            or (admission.academic_year_id.id if admission else False),
            "semester_id": self.semester_id.id
            or (admission.semester_id.id if admission else False),
            "fee_structure_id": self.id,
            "admission_application_id": admission.id if admission else False,
            "line_ids": [
                (
                    0,
                    0,
                    {
                        "name": line.name,
                        "amount": line.amount,
                    },
                )
                for line in self.line_ids
            ],
        }


class UniversityFeeStructureLine(models.Model):
    _name = "university.fee.structure.line"
    _description = "Fee Structure Line"
    _order = "sequence, id"

    sequence = fields.Integer(default=10)
    structure_id = fields.Many2one(
        "university.fee.structure",
        string="Fee Structure",
        required=True,
        ondelete="cascade",
    )
    name = fields.Char(string="Description", required=True)
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        "res.currency",
        related="structure_id.currency_id",
        string="Currency",
        readonly=True,
    )
    amount = fields.Float(string="Amount", required=True)

    @api.constrains("amount")
    def _check_amount(self):
        for line in self:
            if line.amount < 0:
                raise ValidationError(_("Fee structure line amounts cannot be negative."))
