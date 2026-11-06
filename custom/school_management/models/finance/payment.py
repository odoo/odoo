from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class UniversityPayment(models.Model):
    _name = "university.payment"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Student Payment"
    _order = "date desc, id desc"

    name = fields.Char(
        string="Receipt Reference",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: "New",
        tracking=True,
    )
    student_id = fields.Many2one("university.student", string="Student", required=True, tracking=True)
    fee_id = fields.Many2one(
        "university.fee",
        string="Fee Invoice",
        domain="[('student_id', '=', student_id), ('state', '=', 'posted')]",
        tracking=True,
    )

    date = fields.Date(string="Payment Date", default=fields.Date.context_today, required=True, tracking=True)
    currency_id = fields.Many2one("res.currency", string="Currency", compute="_compute_currency_id")
    amount = fields.Float(string="Amount", required=True, tracking=True)
    payment_method = fields.Selection(
        [
            ("cash", "Cash"),
            ("bank_transfer", "Bank Transfer"),
            ("credit_card", "Credit Card"),
        ],
        string="Payment Method",
        default="cash",
        required=True,
        tracking=True,
    )
    reference = fields.Char(string="Transaction Reference", tracking=True)

    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("posted", "Posted"),
            ("canceled", "Canceled"),
        ],
        string="Status",
        default="draft",
        tracking=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code("university.payment") or "New"
        return super().create(vals_list)

    def _compute_currency_id(self):
        currency = self.env.company.currency_id
        for payment in self:
            payment.currency_id = currency

    @api.constrains("amount")
    def _check_amount_positive(self):
        for payment in self:
            if payment.amount <= 0:
                raise ValidationError(_("Payment amount must be strictly positive."))

    @api.constrains("student_id", "fee_id")
    def _check_student_fee_consistency(self):
        for payment in self:
            if payment.fee_id and payment.fee_id.student_id != payment.student_id:
                raise ValidationError(
                    _("The selected fee invoice must belong to the same student as the payment.")
                )

    @api.constrains("amount", "fee_id", "state")
    def _check_no_overpayment(self):
        for payment in self:
            if payment.fee_id and payment.state == "posted":
                other_posted = payment.fee_id.payment_ids.filtered(
                    lambda p: p.state == "posted" and p.id != payment.id
                )
                remaining = payment.fee_id.total_amount - sum(
                    other_posted.mapped("amount")
                )
                if payment.amount > remaining + 0.001:
                    raise ValidationError(
                        _(
                            "Payment amount (%(amount).2f) exceeds the remaining balance "
                            "(%(balance).2f) on fee invoice %(fee)s.",
                            amount=payment.amount,
                            balance=remaining,
                            fee=payment.fee_id.name,
                        )
                    )

    def write(self, vals):
        if not vals or self.env.context.get("bypass_payment_write_guard"):
            return super().write(vals)

        locked_payments = self.filtered(lambda payment: payment.state != "draft")
        if locked_payments:
            if set(vals) == {"state"}:
                raise ValidationError(
                    _("Use the payment actions to change the state of a confirmed payment.")
                )
            raise ValidationError(
                _("Confirmed or canceled payments cannot be edited. Reset the payment to draft first.")
            )

        return super().write(vals)

    def action_post(self):
        for payment in self:
            if payment.state != "draft":
                raise ValidationError(_("Only draft payments can be posted."))
            if payment.fee_id and payment.fee_id.state != "posted":
                raise ValidationError(
                    _("Payments can only be posted against posted fee invoices.")
                )
            fee = payment.fee_id
            was_paid = bool(fee and fee.state == "paid")
            payment.with_context(bypass_payment_write_guard=True).write({"state": "posted"})
            if fee:
                fee._update_state_from_balance()
                # Post chatter confirmation note
                method_name = dict(payment._fields["payment_method"].selection).get(payment.payment_method, payment.payment_method)
                msg = Markup(_(
                    "<p>✅ <strong>Payment Received:</strong> $%(amount).2f via %(method)s "
                    "(Receipt: %(receipt)s, Ref: %(ref)s). Remaining Invoice Balance: $%(balance).2f.</p>",
                )) % {
                    "amount": payment.amount,
                    "method": method_name,
                    "receipt": payment.name,
                    "ref": payment.reference or "N/A",
                    "balance": fee.balance,
                }
                fee.message_post(body=msg, message_type="comment", subtype_xmlid="mail.mt_note")
                if payment.student_id:
                    payment.student_id.message_post(body=msg, message_type="comment", subtype_xmlid="mail.mt_note")

                if not was_paid and fee.state == "paid":
                    fee._send_payment_receipt_email(payment)

    def action_cancel(self):
        for payment in self:
            if payment.state != "posted":
                raise ValidationError(_("Only posted payments can be canceled."))
            payment.with_context(bypass_payment_write_guard=True).write({"state": "canceled"})
            if payment.fee_id:
                payment.fee_id._update_state_from_balance()

    def action_draft(self):
        if not self.env.su and not self.env.user.has_group("school_management.group_school_admin"):
            raise ValidationError(
                _("Only University Administrators can reset payments to draft.")
            )
        for payment in self:
            if payment.state != "canceled":
                raise ValidationError(_("Only canceled payments can be reset to draft."))
            payment.with_context(bypass_payment_write_guard=True).write({"state": "draft"})

    def action_print_receipt(self):
        self.ensure_one()
        return self.env.ref(
            "school_management.action_report_university_payment_receipt"
        ).report_action(self)

    def action_view_fee(self):
        self.ensure_one()
        if not self.fee_id:
            raise ValidationError(_("No fee invoice linked to this payment."))
        return {
            "type": "ir.actions.act_window",
            "res_model": "university.fee",
            "view_mode": "form",
            "res_id": self.fee_id.id,
        }

    def action_view_student(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "university.student",
            "view_mode": "form",
            "res_id": self.student_id.id,
        }
