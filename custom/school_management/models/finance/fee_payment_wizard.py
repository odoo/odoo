
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class UniversityFeePaymentWizard(models.TransientModel):
    _name = "university.fee.payment.wizard"
    _description = "Student Online Tuition Payment Wizard"

    student_id = fields.Many2one(
        "university.student",
        string="Student",
        required=True,
        default=lambda self: self._default_student_id(),
    )
    fee_id = fields.Many2one(
        "university.fee",
        string="Target Fee Invoice",
        domain="[('student_id', '=', student_id), ('state', '=', 'posted'), ('balance', '>', 0)]",
        required=True,
        default=lambda self: self._default_fee_id(),
    )
    currency_id = fields.Many2one(
        "res.currency",
        related="fee_id.currency_id",
        readonly=True,
    )
    total_fee = fields.Float(
        string="Total Invoice Amount",
        related="fee_id.total_amount",
        readonly=True,
    )
    already_paid = fields.Float(
        string="Amount Paid to Date",
        related="fee_id.paid_amount",
        readonly=True,
    )
    outstanding_balance = fields.Float(
        string="Outstanding Balance",
        related="fee_id.balance",
        readonly=True,
    )
    scholarship_discount = fields.Float(
        string="Scholarship / Grant Applied",
        compute="_compute_scholarship_discount",
        readonly=True,
    )

    installment_plan = fields.Selection(
        [
            ("full", "Full Outstanding Balance"),
            ("half", "50% Term Installment"),
            ("custom", "Custom Amount"),
        ],
        string="Payment Option",
        default="full",
        required=True,
    )
    amount_to_pay = fields.Float(
        string="Payment Amount ($)",
        required=True,
    )
    balance_after_payment = fields.Float(
        string="Remaining Balance After Payment",
        compute="_compute_balance_after",
    )

    payment_method = fields.Selection(
        [
            ("qr_code", "KHQR / National Mobile Banking QR"),
            ("bank_transfer", "Bank Wire Transfer (ABA / Canadia)"),
            ("credit_card", "Credit / Debit Card (Visa / Mastercard)"),
        ],
        string="Payment Method",
        default="qr_code",
        required=True,
    )

    # Bank Transfer & Card Details
    card_number = fields.Char(string="Card Number (Last 4 digits)")
    card_holder = fields.Char(string="Cardholder Name")
    transaction_ref = fields.Char(string="Bank Transaction ID / Ref", default=lambda self: _("TXN-%s") % fields.Datetime.now().strftime("%y%m%d%H%M"))
    bank_details = fields.Text(
        string="University Receiving Account",
        default="Bank: ABA Bank Ltd\nAccount Name: ROYAL UNIVERSITY OF PHNOM PENH\nAccount Number: 001 892 410 (USD)\nSWIFT / BIC: ABACLKHPP",
        readonly=True,
    )

    @api.model
    def _default_student_id(self):
        user = self.env.user
        student = self.env["university.student"].search([("user_id", "=", user.id)], limit=1)
        if not student and self.env.context.get("default_student_id"):
            student = self.env["university.student"].browse(self.env.context.get("default_student_id"))
        return student.id if student else False

    @api.model
    def _default_fee_id(self):
        fee_id = self.env.context.get("default_fee_id")
        if fee_id:
            return fee_id
        student_id = self._default_student_id()
        if student_id:
            unpaid = self.env["university.fee"].search([
                ("student_id", "=", student_id),
                ("state", "=", "posted"),
                ("balance", ">", 0),
            ], order="due_date asc, id asc", limit=1)
            return unpaid.id if unpaid else False
        return False

    @api.onchange("fee_id", "installment_plan")
    def _onchange_installment_plan(self):
        if self.fee_id:
            bal = self.fee_id.balance or 0.0
            if self.installment_plan == "full":
                self.amount_to_pay = bal
            elif self.installment_plan == "half":
                self.amount_to_pay = round(bal / 2.0, 2)

    @api.depends("fee_id")
    def _compute_scholarship_discount(self):
        for rec in self:
            discount = 0.0
            if rec.fee_id:
                for line in rec.fee_id.line_ids:
                    if line.amount < 0 or (line.name and "scholarship" in line.name.lower()):
                        discount += abs(line.amount)
            rec.scholarship_discount = discount

    @api.depends("outstanding_balance", "amount_to_pay")
    def _compute_balance_after(self):
        for rec in self:
            rec.balance_after_payment = max(0.0, rec.outstanding_balance - (rec.amount_to_pay or 0.0))

    def action_confirm_payment(self):
        self.ensure_one()
        if self.amount_to_pay <= 0:
            raise ValidationError(_("Payment amount must be greater than zero."))
        if self.amount_to_pay > self.outstanding_balance:
            raise ValidationError(_("Payment amount cannot exceed the outstanding balance of $%.2f.") % self.outstanding_balance)

        # Create university.payment
        payment_method_map = {
            "qr_code": "bank_transfer",
            "bank_transfer": "bank_transfer",
            "credit_card": "credit_card",
        }
        payment = self.env["university.payment"].create({
            "student_id": self.student_id.id,
            "fee_id": self.fee_id.id,
            "amount": self.amount_to_pay,
            "payment_method": payment_method_map.get(self.payment_method, "cash"),
            "reference": self.transaction_ref or _("Online Payment"),
            "date": fields.Date.context_today(self),
            "state": "posted",
        })

        # Recompute fee totals
        self.fee_id._compute_totals()
        self.fee_id._compute_payment_state()

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Payment Successful!"),
                "message": _("Receipt %s issued for $%.2f. Outstanding balance is now $%.2f.") % (
                    payment.name, payment.amount, self.fee_id.balance
                ),
                "type": "success",
                "sticky": False,
            },
        }

    def action_process_payment(self):
        return self.action_confirm_payment()
