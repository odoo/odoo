from odoo import api, fields, models


class Od19ContractBillingLine(models.Model):
    _inherit = "od19.contract.billing.line"

    od19_retention_rate = fields.Float(
        string="Retention Rate (%)",
        digits=(5, 2),
        compute="_compute_od19_retention_rate",
        store=True,
        readonly=False,
        help="Percentage withheld from this installment. Defaults to the "
        "contract retention rate.",
    )
    od19_retention_amount = fields.Float(
        string="Retention Amount",
        compute="_compute_od19_retention_amount",
        store=True,
        readonly=False,
        help="VAT-inclusive amount withheld from this installment. Derived "
        "from the tax invoice total once the installment is invoiced, "
        "otherwise estimated on the net installment amount.",
    )
    od19_retention_id = fields.Many2one(
        "od19.sales.retention",
        string="Retention",
        readonly=True,
        copy=False,
        help="Retention record created when the installment invoice is posted.",
    )

    @api.depends("contract_id.od19_default_retention_rate")
    def _compute_od19_retention_rate(self):
        for line in self:
            if not line.od19_retention_rate:
                line.od19_retention_rate = (
                    line.contract_id.od19_default_retention_rate
                )

    @api.depends("od19_retention_rate", "amount", "invoice_id.amount_total")
    def _compute_od19_retention_amount(self):
        for line in self:
            if line.invoice_id:
                base = line.invoice_id.amount_total
            else:
                base = line.amount
            line.od19_retention_amount = (
                (line.od19_retention_rate or 0.0) / 100.0 * (base or 0.0)
            )

    def _od19_create_retention(self):
        """Create and hold the retention for this invoiced installment."""
        self.ensure_one()
        if self.od19_retention_id:
            return self.od19_retention_id
        if not self.od19_retention_rate or not self.invoice_id:
            return self.env["od19.sales.retention"]
        retention = self.env["od19.sales.retention"].create(
            {
                "contract_id": self.contract_id.id,
                "billing_line_id": self.id,
                "partner_id": self.invoice_id.partner_id.id
                or self.contract_id.partner_id.id,
                "invoice_id": self.invoice_id.id,
                "base_amount": self.invoice_id.amount_untaxed,
                "retention_rate": self.od19_retention_rate,
                "retention_amount": self.od19_retention_amount,
            }
        )
        retention.action_hold()
        self.od19_retention_id = retention.id
        return retention
