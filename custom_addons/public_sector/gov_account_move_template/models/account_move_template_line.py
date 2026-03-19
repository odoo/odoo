from odoo import api, fields, models
from odoo.exceptions import ValidationError


class AccountMoveTemplateLine(models.Model):
    _name = "account.move.template.line"
    _description = "Journal Entry Template Line"
    _order = "sequence asc, id asc"

    template_id = fields.Many2one(
        "account.move.template",
        required=True,
        ondelete="cascade",
    )
    company_id = fields.Many2one(
        related="template_id.company_id",
        store=True,
        readonly=True,
    )
    sequence = fields.Integer(default=10)
    name = fields.Char(required=True)
    account_id = fields.Many2one("account.account", required=True, check_company=True)
    partner_id = fields.Many2one("res.partner")
    analytic_distribution = fields.Json()
    move_type = fields.Selection([("dr", "Debit"), ("cr", "Credit")], required=True)
    amount_type = fields.Selection(
        [("fixed", "Fixed"), ("percent", "Percent"), ("computed", "Computed")],
        required=True,
        default="fixed",
    )
    currency_id = fields.Many2one(related="template_id.company_id.currency_id", readonly=True)
    amount_fixed = fields.Monetary(currency_field="currency_id")
    amount_percent = fields.Float()
    amount_expr = fields.Char()

    @api.constrains("amount_percent")
    def _check_percent(self):
        for line in self:
            if line.amount_type == "percent" and not (0.0 <= line.amount_percent <= 100.0):
                raise ValidationError("Percent lines must be between 0 and 100.")

    @api.constrains("amount_expr", "amount_type")
    def _check_expr(self):
        for line in self:
            if line.amount_type == "computed" and not line.amount_expr:
                raise ValidationError("Computed lines require an expression.")
