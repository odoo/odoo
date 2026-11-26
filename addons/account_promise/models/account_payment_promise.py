from odoo import api, fields, models
from odoo.exceptions import ValidationError


class AccountPaymentPromise(models.Model):
    _name = "account.payment.promise"
    _description = "Promise to Pay"

    partner_id = fields.Many2one("res.partner", required=True)
    collector_id = fields.Many2one("res.users", required=True)
    invoice_ids = fields.Many2many("account.move")
    amount = fields.Monetary(currency_field="currency_id", required=True)
    date_promised = fields.Date(required=True)
    state = fields.Selection(
        [
            ("open", "Open"),
            ("kept", "Kept"),
            ("partially_kept", "Partially Kept"),
            ("broken", "Broken"),
            ("cancelled", "Cancelled"),
        ],
        default="open",
        required=True,
    )
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
    company_id = fields.Many2one(
        "res.company",
        default=lambda self: self.env.company,
        required=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        related="company_id.currency_id",
        store=True,
    )
    note = fields.Text()

    @api.model
    def create(self, vals_list):
        for val in vals_list:
            commands = val.get("invoice_ids", [])
            invoice_ids = []

            for command in commands:
                if command[0] == 6:
                    invoice_ids.extend(command[2])
                if command[0] == 4:
                    invoice_ids.append(command[1])

            invoices = self.env["account.move"].browse(invoice_ids)

            if any(invoice.state == "cancel" for invoice in invoices):
                raise ValidationError(
                    self.env._("You cannot make a promise for the cancelled invoice"),
                )
        return super().create(vals_list)
