from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class Od19SalesContract(models.Model):
    _name = "od19.sales.contract"
    _description = "Sales Master Contract"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(required=True, tracking=True)
    partner_id = fields.Many2one("res.partner", required=True, tracking=True)
    od19_project_id = fields.Many2one(
        "project.project",
        string="Project",
        required=True,
        tracking=True,
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("approved", "Approved"),
            ("active", "Active"),
            ("closed", "Closed"),
        ],
        default="draft",
        required=True,
        tracking=True,
        copy=False,
    )
    start_date = fields.Date(tracking=True)
    end_date = fields.Date(tracking=True)
    limit_amount = fields.Float(required=True, tracking=True)
    consumed_amount = fields.Float(
        compute="_compute_consumed_amount", store=True, tracking=True
    )
    consumed_from_orders = fields.Float(
        compute="_compute_consumed_from_orders",
        store=True,
        help="Sum of confirmed sale order amounts linked to this contract.",
    )
    over_limit_policy = fields.Selection(
        [("warn", "Warn"), ("approval", "Approval"), ("block", "Block")],
        default="warn",
        required=True,
    )
    contract_activity_ids = fields.One2many(
        "od19.sales.contract.activity", "contract_id"
    )
    amendment_ids = fields.One2many(
        "od19.sales.contract.amendment", "contract_id"
    )
    sale_order_ids = fields.One2many(
        "sale.order",
        "od19_contract_id",
        string="Sale Orders",
        help="Sale orders linked to this contract (used to compute consumption).",
    )
    billing_line_ids = fields.One2many(
        "od19.contract.billing.line",
        "contract_id",
        string="Billing Schedule",
    )
    billing_scheduled_amount = fields.Float(
        compute="_compute_billing_totals",
        store=True,
        help="Sum of all planned installment amounts.",
    )
    billing_invoiced_amount = fields.Float(
        compute="_compute_billing_totals",
        store=True,
        help="Sum of installment amounts already invoiced.",
    )
    billing_remaining_amount = fields.Float(
        compute="_compute_billing_totals",
        store=True,
        help="Remaining amount still to be billed from the schedule.",
    )
    revenue_line_ids = fields.One2many(
        "od19.contract.revenue.line",
        "contract_id",
        string="Revenue Schedule",
    )
    revenue_journal_id = fields.Many2one(
        "account.journal",
        string="Revenue Journal",
        help="Journal used to post TFRS 15 revenue recognition entries.",
    )
    deferred_revenue_account_id = fields.Many2one(
        "account.account",
        string="Deferred Revenue Account",
        domain="[('account_type', 'in', ['liability_current', 'liability_non_current'])]",
        help="Liability account debited when revenue is recognized.",
    )
    revenue_account_id = fields.Many2one(
        "account.account",
        string="Revenue Account",
        domain="[('account_type', 'in', ['income', 'income_other'])]",
        help="Income account credited when revenue is recognized.",
    )
    revenue_total_amount = fields.Float(
        compute="_compute_revenue_totals",
        store=True,
        help="Transaction price allocated to the performance obligations.",
    )
    revenue_recognized_amount = fields.Float(
        compute="_compute_revenue_totals",
        store=True,
        help="Revenue already recognized (reconciles with the general ledger).",
    )
    revenue_deferred_amount = fields.Float(
        compute="_compute_revenue_totals",
        store=True,
        help="Revenue allocated but not yet recognized.",
    )

    @api.depends(
        "contract_activity_ids.amount_to_consume",
        "consumed_from_orders",
    )
    def _compute_consumed_amount(self):
        for contract in self:
            activity_amount = sum(
                contract.contract_activity_ids.mapped("amount_to_consume")
            )
            contract.consumed_amount = activity_amount + contract.consumed_from_orders

    @api.depends("sale_order_ids.amount_untaxed", "sale_order_ids.state")
    def _compute_consumed_from_orders(self):
        for contract in self:
            orders = contract.sale_order_ids.filtered(
                lambda order: order.state == "sale"
            )
            contract.consumed_from_orders = sum(orders.mapped("amount_untaxed"))

    @api.depends(
        "billing_line_ids.amount",
        "billing_line_ids.state",
        "limit_amount",
    )
    def _compute_billing_totals(self):
        for contract in self:
            scheduled = sum(contract.billing_line_ids.mapped("amount"))
            invoiced = sum(
                contract.billing_line_ids.filtered(
                    lambda line: line.state == "invoiced"
                ).mapped("amount")
            )
            contract.billing_scheduled_amount = scheduled
            contract.billing_invoiced_amount = invoiced
            contract.billing_remaining_amount = scheduled - invoiced

    @api.depends(
        "revenue_line_ids.total_amount",
        "revenue_line_ids.recognized_amount",
    )
    def _compute_revenue_totals(self):
        for contract in self:
            contract.revenue_total_amount = sum(
                contract.revenue_line_ids.mapped("total_amount")
            )
            contract.revenue_recognized_amount = sum(
                contract.revenue_line_ids.mapped("recognized_amount")
            )
            contract.revenue_deferred_amount = (
                contract.revenue_total_amount - contract.revenue_recognized_amount
            )

    def action_recognize_revenue(self):
        """Recognize the revenue of every obligation that still has a balance."""
        self.ensure_one()
        pending = self.revenue_line_ids.filtered(
            lambda line: line._od19_target_recognized_amount()
            - line.recognized_amount
            > 1e-6
        ).sorted("sequence")
        if not pending:
            raise UserError(
                _("There is no revenue left to recognize for this contract.")
            )
        action = True
        for line in pending:
            action = line.action_recognize()
        return action

    def action_create_next_billing_invoice(self):
        """Create the invoice for the next un-invoiced installment."""
        self.ensure_one()
        next_line = self.billing_line_ids.filtered(
            lambda line: line.state != "invoiced"
        ).sorted("sequence")[:1]
        if not next_line:
            raise UserError(
                _("All installments of this contract have already been invoiced.")
            )
        return next_line.action_create_invoice()

    @api.constrains("start_date", "end_date")
    def _check_dates(self):
        for contract in self:
            if (
                contract.start_date
                and contract.end_date
                and contract.end_date < contract.start_date
            ):
                raise ValidationError(
                    _("Contract end date cannot be earlier than start date.")
                )

    def action_approve(self):
        for contract in self:
            if contract.state != "draft":
                raise UserError(
                    _("Only draft contracts can be approved.")
                )
            contract.state = "approved"
        return True

    def action_activate(self):
        for contract in self:
            if contract.state not in ("approved", "active"):
                raise UserError(
                    _("Only approved contracts can be activated.")
                )
            contract.state = "active"
        return True

    def action_close(self):
        for contract in self:
            if contract.state not in ("approved", "active"):
                raise UserError(
                    _("Only approved or active contracts can be closed.")
                )
            contract.state = "closed"
        return True

    def action_draft(self):
        for contract in self:
            if contract.state != "closed":
                raise UserError(
                    _("Only closed contracts can be reset to draft.")
                )
            contract.state = "draft"
        return True

    def _od19_check_contract_limit(self, order_amount):
        """Check whether adding order_amount would exceed the contract limit.

        Returns a tuple (exceeded, message).
        """
        self.ensure_one()
        projected = self.consumed_amount + order_amount
        exceeded = projected > self.limit_amount
        message = False
        if exceeded:
            message = _(
                "Contract %s would exceed its limit (projected %.2f > limit %.2f)."
            ) % (self.name, projected, self.limit_amount)
        return exceeded, message


class Od19SalesContractActivity(models.Model):
    _name = "od19.sales.contract.activity"
    _description = "Sales Contract Activity"

    name = fields.Char(required=True)
    contract_id = fields.Many2one(
        "od19.sales.contract", required=True, ondelete="cascade"
    )
    amount_to_consume = fields.Float(required=True)

    @api.constrains("amount_to_consume", "contract_id")
    def _check_contract_limit(self):
        for activity in self:
            existing_amount = sum(
                (activity.contract_id.contract_activity_ids - activity).mapped(
                    "amount_to_consume"
                )
            )
            projected = (
                existing_amount
                + activity.amount_to_consume
                + activity.contract_id.consumed_from_orders
            )
            if (
                activity.contract_id.over_limit_policy == "block"
                and projected > activity.contract_id.limit_amount
            ):
                raise ValidationError(
                    _("Contract activity exceeds blocked contract limit.")
                )


class Od19SalesContractAmendment(models.Model):
    _name = "od19.sales.contract.amendment"
    _description = "Sales Contract Amendment"

    name = fields.Char(required=True)
    contract_id = fields.Many2one(
        "od19.sales.contract", required=True, ondelete="cascade"
    )
    added_limit_amount = fields.Float(
        string="Added Limit Amount",
        help="Amount to add to the contract limit.",
    )
    note = fields.Text()

    @api.model_create_multi
    def create(self, vals_list):
        amendments = super().create(vals_list)
        for amendment in amendments:
            if amendment.added_limit_amount:
                amendment.contract_id.limit_amount = (
                    amendment.contract_id.limit_amount
                    + amendment.added_limit_amount
                )
        return amendments

    def write(self, vals):
        if "added_limit_amount" in vals:
            for amendment in self:
                old = amendment.added_limit_amount or 0.0
                new = vals["added_limit_amount"] or 0.0
                delta = new - old
                if delta:
                    amendment.contract_id.limit_amount = (
                        amendment.contract_id.limit_amount + delta
                    )
        return super().write(vals)
