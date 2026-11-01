from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class Od19ContractBillingLine(models.Model):
    _name = "od19.contract.billing.line"
    _description = "Contract Billing Schedule Line"
    _order = "contract_id, sequence, id"

    name = fields.Char(required=True)
    contract_id = fields.Many2one(
        "od19.sales.contract", required=True, ondelete="cascade", index=True
    )
    sequence = fields.Integer(
        default=10, help="Installment number (งวดที่) used to enforce order."
    )
    line_type = fields.Selection(
        [
            ("milestone", "Milestone"),
            ("periodic", "Periodic"),
            ("percent", "Percent of Contract"),
        ],
        default="percent",
        required=True,
    )
    percent = fields.Float(string="Percent (%)")
    amount = fields.Float(
        compute="_compute_amount",
        store=True,
        readonly=False,
        help="Installment amount. Derived from percent x contract limit when "
        "line_type is 'percent', otherwise entered manually.",
    )
    due_date = fields.Date()
    progress_percent = fields.Float(
        string="Progress (%)",
        help="Recorded work progress, supporting TFRS 15 revenue recognition.",
    )
    state = fields.Selection(
        [("draft", "Draft"), ("invoiced", "Invoiced")],
        default="draft",
        required=True,
        copy=False,
    )
    sale_order_id = fields.Many2one(
        "sale.order",
        string="Sale Order",
        help="Sale order used to issue the invoice for this installment.",
    )
    invoice_id = fields.Many2one(
        "account.move", string="Invoice", readonly=True, copy=False
    )
    invoice_date = fields.Date(readonly=True, copy=False)

    @api.depends("percent", "line_type", "contract_id.limit_amount")
    def _compute_amount(self):
        for line in self:
            if line.line_type == "percent":
                line.amount = (
                    (line.percent or 0.0)
                    / 100.0
                    * (line.contract_id.limit_amount or 0.0)
                )

    @api.constrains("percent", "progress_percent")
    def _check_percent_range(self):
        for line in self:
            if line.percent < 0 or line.percent > 100:
                raise ValidationError(
                    _("Billing percent must be between 0 and 100.")
                )
            if line.progress_percent < 0 or line.progress_percent > 100:
                raise ValidationError(
                    _("Progress percent must be between 0 and 100.")
                )

    @api.constrains("amount", "contract_id")
    def _check_total_within_limit(self):
        for line in self:
            if not line.contract_id:
                continue
            total = sum(line.contract_id.billing_line_ids.mapped("amount"))
            limit = line.contract_id.limit_amount
            if limit and total > limit:
                raise ValidationError(
                    _(
                        "Total billing schedule amount (%.2f) exceeds the "
                        "contract limit (%.2f)."
                    )
                    % (total, limit)
                )

    def action_create_invoice(self):
        """Create the invoice for this installment.

        The invoice is issued from the linked sale order so that the billing
        evidence gate (enforced on ``sale.order._create_invoices``) is applied.
        Earlier installments must be invoiced first.
        """
        self.ensure_one()
        if self.state == "invoiced":
            raise UserError(
                _("Installment '%s' has already been invoiced.") % self.name
            )
        earlier = self.contract_id.billing_line_ids.filtered(
            lambda line: line.sequence < self.sequence and line.state != "invoiced"
        )
        if earlier:
            raise UserError(
                _("Please invoice earlier installments first: %s")
                % ", ".join(earlier.mapped("name"))
            )
        if not self.sale_order_id:
            raise UserError(
                _(
                    "Please link a sale order to installment '%s' before "
                    "creating its invoice."
                )
                % self.name
            )
        invoices = self.sale_order_id._create_invoices()
        invoice = invoices[:1] if invoices else False
        self.write(
            {
                "state": "invoiced",
                "invoice_id": invoice.id if invoice else False,
                "invoice_date": fields.Date.context_today(self),
            }
        )
        if invoice:
            return {
                "type": "ir.actions.act_window",
                "res_model": "account.move",
                "res_id": invoice.id,
                "view_mode": "form",
                "target": "current",
            }
        return True
