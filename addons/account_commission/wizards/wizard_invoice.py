from odoo import _, exceptions, fields, models


class CommissionMakeInvoice(models.TransientModel):
    _name = "commission.make.invoice"
    _description = "Wizard for making an invoice from a settlement"

    def _default_journal_id(self):
        return self.env["account.journal"].search(
            [("type", "=", "purchase"), ("company_id", "=", self.env.company.id)],
            limit=1,
        )

    def _default_settlement_ids(self):
        context = self.env.context
        if context.get("active_model") == "commission.settlement":
            settlements = self.env[context["active_model"]].browse(
                context.get("active_ids")
            )
            settlements = settlements.filtered_domain(
                [
                    ("state", "=", "settled"),
                    ("agent_type", "=", "agent"),
                    ("company_id", "=", self.env.company.id),
                ]
            )
            if not settlements:
                raise exceptions.UserError(_("No valid settlements to invoice."))
            return settlements.ids
        return self.env.context.get("settlement_ids", [])

    def _default_from_settlement(self):
        return bool(self._default_settlement_ids())

    journal_id = fields.Many2one(
        comodel_name="account.journal",
        required=True,
        domain="[('type', '=', 'purchase')]",
        default=lambda self: self._default_journal_id(),
    )
    company_id = fields.Many2one(
        comodel_name="res.company", related="journal_id.company_id", readonly=True
    )
    product_id = fields.Many2one(
        string="Product for invoicing", comodel_name="product.product", required=True
    )
    settlement_ids = fields.Many2many(
        comodel_name="commission.settlement",
        relation="commission_make_invoice_settlement_rel",
        column1="wizard_id",
        column2="settlement_id",
        domain="[('state', '=', 'settled'),('agent_type', '=', 'agent'),"
        "('company_id', '=', company_id)]",
        default=lambda self: self._default_settlement_ids(),
    )
    from_settlement = fields.Boolean(
        default=lambda self: self._default_from_settlement()
    )
    date = fields.Date(default=fields.Date.context_today)
    grouped = fields.Boolean(string="Group invoices")

    def button_create(self):
        self.ensure_one()
        settlements = self.settlement_ids or self.env["commission.settlement"].search(
            [
                ("state", "=", "settled"),
                ("agent_type", "=", "agent"),
                ("company_id", "=", self.journal_id.company_id.id),
            ]
        )
        invoices = settlements.make_invoices(
            self.journal_id,
            self.product_id,
            date=self.date,
            grouped=self.grouped,
        )
        # go to results
        if len(settlements):
            return {
                "name": _("Created Invoices"),
                "type": "ir.actions.act_window",
                "views": [[False, "list"], [False, "form"]],
                "res_model": "account.move",
                "domain": [["id", "in", invoices.ids]],
            }
