from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.float_utils import float_compare


class AccountPaymentPromiseWizard(models.TransientModel):
    _name = "account.payment.promise.wizard"
    _description = "Record Promise Wizard"

    invoice_ids = fields.Many2many("account.move", required=True)
    currency_id = fields.Many2one(
        "res.currency",
        default=lambda self: self.env.company.currency_id,
        required=True,
    )
    amount = fields.Monetary(
        currency_field="currency_id",
        required=True,
    )
    date_promised = fields.Date(required=True)
    promise_method = fields.Selection(
        [
            ("call", "Call"),
            ("email", "Email"),
            ("visit", "Visit"),
            ("portal", "Portal"),
        ],
        default="call",
        required=True,
    )
    note = fields.Text()

    @api.constrains("date_promised")
    def _check_date_promised(self):
        if self.date_promised < fields.Date.today():
            raise ValidationError(self.env._("Promise date cannot be in the past."))

    @api.constrains("amount")
    def _check_amount(self):
        for record in self:
            total_unpaid = sum(record.invoice_ids.mapped("amount_residual_signed"))

            if (
                float_compare(
                    record.amount,
                    0,
                    precision_rounding=record.currency_id.rounding,
                )
                <= 0
                or float_compare(
                    record.amount,
                    total_unpaid,
                    precision_rounding=record.currency_id.rounding,
                )
                > 0
            ):
                raise ValidationError(
                    self.env._(
                        f"The promised amount must be greater than zero and cannot exceed the total unpaid amount: {total_unpaid}.",
                    ),
                )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)

        invoice_id = self.env.context.get("default_invoice_id")
        partner_id = self.env.context.get("default_partner_id")

        if invoice_id:
            res["invoice_ids"] = [fields.Command.set([invoice_id])]

        elif partner_id:
            invoices = self.env["account.move"].search(
                [
                    ("partner_id", "=", partner_id),
                    ("move_type", "=", "out_invoice"),
                    ("state", "=", "posted"),
                    ("payment_state", "in", ["not_paid", "partial"]),
                ],
            )
            res["invoice_ids"] = [fields.Command.set(invoices.ids)]

        return res

    def action_confirm(self):

        # one promise at a time for one invoice for one particular customer
        existing_promise = self.env["account.payment.promise"].search_count(
            [
                ("invoice_ids", "in", self.invoice_ids.ids),
                ("state", "not in", ("broken", "cancelled", "partially_kept")),
            ],
        )
        if existing_promise:
            raise ValidationError(
                self.env._("This invoice already has an active promise!"),
            )

        # if no promise exists, then create one
        self.env["account.payment.promise"].create(
            [
                {
                    "partner_id": self.invoice_ids[:1].partner_id.id,
                    "collector_id": self.env.user.id,
                    "invoice_ids": [fields.Command.set(self.invoice_ids.ids)],
                    "amount": self.amount,
                    "date_promised": self.date_promised,
                    "promise_method": self.promise_method,
                    "note": self.note,
                },
            ],
        )
