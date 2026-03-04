import logging

from dateutil.relativedelta import relativedelta

from odoo import Command, api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    subscription_id = fields.Many2one(
        comodel_name="sale.subscription",
        string="Subscription",
        index=True,
        copy=False,
        ondelete="set null",
    )


class ProductTemplate(models.Model):
    _inherit = "product.template"

    subscribable = fields.Boolean(string="Subscribable")
    subscription_template_id = fields.Many2one(
        comodel_name="sale.subscription.template",
        string="Subscription Template",
    )


class SaleSubscription(models.Model):
    _name = "sale.subscription"
    _description = "Subscription"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(required=True, tracking=True, default="/")
    code = fields.Char(string="Reference", readonly=True, copy=False, index=True)
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Customer",
        required=True,
        index=True,
        tracking=True,
    )
    stage_id = fields.Many2one(
        comodel_name="sale.subscription.stage",
        string="Stage",
        required=True,
        index=True,
        tracking=True,
        default=lambda self: self._default_stage_id(),
        ondelete="restrict",
    )
    date_start = fields.Date(
        string="Start Date",
        default=lambda self: fields.Date.context_today(self),
    )
    date = fields.Date(string="Expiration Date")
    recurring_next_date = fields.Date(string="Next Invoice Date", tracking=True)
    recurring_rule_type = fields.Selection(
        [
            ("daily", "Day(s)"),
            ("weekly", "Week(s)"),
            ("monthly", "Month(s)"),
            ("yearly", "Year(s)"),
        ],
        string="Recurrence",
        required=True,
        default="monthly",
    )
    recurring_interval = fields.Integer(string="Invoice Every", required=True, default=1)
    pricelist_id = fields.Many2one(
        comodel_name="product.pricelist",
        string="Pricelist",
        required=True,
        default=lambda self: self._default_pricelist_id(),
        ondelete="restrict",
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Salesperson",
        required=True,
        default=lambda self: self.env.user,
        ondelete="restrict",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
        ondelete="restrict",
    )
    analytic_account_id = fields.Many2one(
        comodel_name="account.analytic.account",
        string="Analytic Account",
        ondelete="set null",
    )
    payment_token_id = fields.Many2one(
        comodel_name="payment.token",
        string="Payment Token",
        ondelete="set null",
    )
    line_ids = fields.One2many(
        comodel_name="sale.subscription.line",
        inverse_name="subscription_id",
        string="Subscription Lines",
        copy=True,
    )
    mrr = fields.Monetary(
        string="MRR",
        currency_field="currency_id",
        compute="_compute_mrr",
        store=True,
    )
    recurring_total = fields.Monetary(
        string="Recurring Subtotal",
        currency_field="currency_id",
        compute="_compute_recurring_total",
        store=True,
    )
    amount_tax = fields.Monetary(
        string="Taxes",
        currency_field="currency_id",
        compute="_compute_recurring_total",
        store=True,
    )
    amount_total = fields.Monetary(
        string="Recurring Total",
        currency_field="currency_id",
        compute="_compute_recurring_total",
        store=True,
    )
    health = fields.Selection(
        [
            ("normal", "Normal"),
            ("done", "Done"),
            ("bad", "Bad"),
        ],
        string="Health",
        compute="_compute_health",
        store=True,
    )
    to_renew = fields.Boolean(default=False, tracking=True)
    close_reason_id = fields.Many2one(
        comodel_name="sale.subscription.close.reason",
        string="Close Reason",
        ondelete="set null",
    )
    active = fields.Boolean(default=True)
    tag_ids = fields.Many2many(
        comodel_name="sale.subscription.tag",
        relation="sale_subscription_tag_rel",
        column1="subscription_id",
        column2="tag_id",
        string="Tags",
    )
    journal_id = fields.Many2one(
        comodel_name="account.journal",
        string="Journal",
        domain="[('type', '=', 'sale'), ('company_id', '=', company_id)]",
        default=lambda self: self._default_journal_id(),
        ondelete="restrict",
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        string="Currency",
        compute="_compute_currency_id",
        store=True,
    )
    invoice_ids = fields.One2many(
        comodel_name="account.move",
        inverse_name="subscription_id",
        string="Invoices",
    )
    invoice_count = fields.Integer(compute="_compute_invoice_count")
    description = fields.Text()
    template_id = fields.Many2one(
        comodel_name="sale.subscription.template",
        string="Template",
        ondelete="set null",
    )

    _recurring_interval_positive = models.Constraint(
        "CHECK(recurring_interval > 0)",
        "Recurring interval must be greater than zero.",
    )

    @api.model
    def _default_stage_id(self):
        stage = self.env["sale.subscription.stage"].search(
            [
                ("category", "=", "draft"),
                "|",
                ("company_id", "=", False),
                ("company_id", "=", self.env.company.id),
            ],
            order="sequence, id",
            limit=1,
        )
        return stage.id

    @api.model
    def _default_pricelist_id(self):
        pricelist = self.env.company.partner_id.property_product_pricelist
        if pricelist:
            return pricelist.id
        return self.env["product.pricelist"].search(
            [
                "|",
                ("company_id", "=", False),
                ("company_id", "=", self.env.company.id),
            ],
            limit=1,
        ).id

    @api.model
    def _default_journal_id(self):
        return self.env["account.journal"].search(
            [("type", "=", "sale"), ("company_id", "=", self.env.company.id)],
            limit=1,
        ).id

    @api.depends("pricelist_id", "company_id")
    def _compute_currency_id(self):
        for subscription in self:
            subscription.currency_id = (
                subscription.pricelist_id.currency_id or subscription.company_id.currency_id
            )

    @api.depends("line_ids.price_subtotal", "line_ids.price_tax", "line_ids.price_total")
    def _compute_recurring_total(self):
        for subscription in self:
            subscription.recurring_total = sum(subscription.line_ids.mapped("price_subtotal"))
            subscription.amount_tax = sum(subscription.line_ids.mapped("price_tax"))
            subscription.amount_total = sum(subscription.line_ids.mapped("price_total"))

    @api.depends("amount_total", "recurring_rule_type", "recurring_interval")
    def _compute_mrr(self):
        for subscription in self:
            interval = max(subscription.recurring_interval or 1, 1)
            amount = subscription.amount_total or 0.0
            if subscription.recurring_rule_type == "daily":
                subscription.mrr = amount * (30.0 / interval)
            elif subscription.recurring_rule_type == "weekly":
                subscription.mrr = amount * (4.0 / interval)
            elif subscription.recurring_rule_type == "yearly":
                subscription.mrr = amount / (12.0 * interval)
            else:
                subscription.mrr = amount / interval

    @api.depends("stage_id.category", "recurring_next_date")
    def _compute_health(self):
        today = fields.Date.context_today(self)
        for subscription in self:
            if subscription.stage_id.category == "closed":
                subscription.health = "done"
            elif subscription.recurring_next_date and subscription.recurring_next_date < today:
                subscription.health = "bad"
            else:
                subscription.health = "normal"

    @api.depends("invoice_ids")
    def _compute_invoice_count(self):
        for subscription in self:
            subscription.invoice_count = len(subscription.invoice_ids)

    @api.onchange("partner_id")
    def _onchange_partner_id(self):
        if self.partner_id and self.partner_id.property_product_pricelist:
            partner_pricelist = self.partner_id.property_product_pricelist
            self.pricelist_id = partner_pricelist

    @api.onchange("template_id")
    def _onchange_template_id(self):
        if not self.template_id:
            return
        self.recurring_rule_type = self.template_id.recurring_rule_type
        self.recurring_interval = self.template_id.recurring_interval
        if self.template_id.journal_id:
            self.journal_id = self.template_id.journal_id
        if self.template_id.description and not self.description:
            self.description = self.template_id.description

    @api.constrains("date_start", "date", "recurring_interval")
    def _check_dates(self):
        for subscription in self:
            if subscription.date and subscription.date_start and subscription.date < subscription.date_start:
                raise ValidationError("Expiration Date cannot be earlier than Start Date.")
            if subscription.recurring_interval <= 0:
                raise ValidationError("Recurring interval must be greater than zero.")

    @api.model_create_multi
    def create(self, vals_list):
        sequence = self.env["ir.sequence"]
        default_stage = self._default_stage_id()
        for vals in vals_list:
            if not vals.get("code"):
                vals["code"] = sequence.next_by_code("sale.subscription") or "/"
            if not vals.get("name") or vals["name"] == "/":
                vals["name"] = vals["code"]
            if not vals.get("stage_id") and default_stage:
                vals["stage_id"] = default_stage
        return super().create(vals_list)

    def _get_stage_by_category(self, category):
        self.ensure_one()
        return self.env["sale.subscription.stage"].search(
            [
                ("category", "=", category),
                "|",
                ("company_id", "=", False),
                ("company_id", "=", self.company_id.id),
            ],
            order="sequence, id",
            limit=1,
        )

    def action_draft(self):
        for subscription in self:
            stage = subscription._get_stage_by_category("draft")
            values = {"active": True, "to_renew": False}
            if stage:
                values["stage_id"] = stage.id
            subscription.write(values)
        return True

    def action_start_subscription(self):
        today = fields.Date.context_today(self)
        for subscription in self:
            stage = subscription._get_stage_by_category("progress")
            values = {"active": True}
            if stage:
                values["stage_id"] = stage.id
            if not subscription.date_start:
                values["date_start"] = today
            start_point = subscription.recurring_next_date or values.get("date_start") or subscription.date_start
            if not subscription.recurring_next_date and start_point:
                values["recurring_next_date"] = subscription.calculate_recurring_next_date(start_point)
            subscription.write(values)
        return True

    def action_set_to_renew(self):
        for subscription in self:
            stage = subscription._get_stage_by_category("renew")
            values = {"to_renew": True}
            if stage:
                values["stage_id"] = stage.id
            subscription.write(values)
        return True

    def _subscription_cancel(self):
        for subscription in self:
            stage = subscription._get_stage_by_category("closed")
            values = {"active": False, "to_renew": False}
            if stage:
                values["stage_id"] = stage.id
            subscription.write(values)
        return True

    def action_subscription_cancel(self):
        return self._subscription_cancel()

    def _subscription_close(self):
        for subscription in self:
            stage = subscription._get_stage_by_category("closed")
            values = {"active": False, "to_renew": False}
            if stage:
                values["stage_id"] = stage.id
            subscription.write(values)
        return True

    def action_subscription_close(self):
        return self._subscription_close()

    def calculate_recurring_next_date(self, date_start):
        self.ensure_one()
        base_date = fields.Date.to_date(date_start) if date_start else fields.Date.context_today(self)
        interval = max(self.recurring_interval or 1, 1)
        if self.recurring_rule_type == "daily":
            delta = relativedelta(days=interval)
        elif self.recurring_rule_type == "weekly":
            delta = relativedelta(weeks=interval)
        elif self.recurring_rule_type == "yearly":
            delta = relativedelta(years=interval)
        else:
            delta = relativedelta(months=interval)
        return base_date + delta

    def _prepare_invoice_line_data(self, line):
        self.ensure_one()
        taxes = line.tax_ids.filtered(
            lambda tax: not tax.company_id or tax.company_id == self.company_id
        )
        vals = {
            "name": line.name,
            "product_id": line.product_id.id,
            "quantity": line.quantity,
            "price_unit": line.price_unit,
            "discount": line.discount,
            "tax_ids": [Command.set(taxes.ids)],
        }
        if self.analytic_account_id:
            vals["analytic_distribution"] = {str(self.analytic_account_id.id): 100}
        return vals

    def _prepare_invoice_data(self):
        self.ensure_one()
        if not self.line_ids:
            raise ValidationError("A subscription needs at least one line to create an invoice.")
        journal = self.journal_id or self.env["account.journal"].search(
            [("type", "=", "sale"), ("company_id", "=", self.company_id.id)],
            limit=1,
        )
        if not journal:
            raise ValidationError("No sales journal found for the subscription company.")

        line_commands = [
            Command.create(self._prepare_invoice_line_data(line))
            for line in self.line_ids
        ]

        # Produces account.move vals compatible with
        # om_account_accountant._get_invoice_in_payment_state()
        # Ensure move_type is set explicitly to 'out_invoice'
        # so the payment state compute resolves correctly.
        vals = {
            "move_type": "out_invoice",
            "company_id": self.company_id.id,
            "partner_id": self.partner_id.id,
            "invoice_user_id": self.user_id.id,
            "currency_id": self.currency_id.id,
            "invoice_date": self.recurring_next_date or fields.Date.context_today(self),
            "invoice_origin": "sale_subscription",
            "ref": self.code or self.name,
            "journal_id": journal.id,
            "subscription_id": self.id,
            "invoice_line_ids": line_commands,
        }
        if self.partner_id.property_payment_term_id:
            vals["invoice_payment_term_id"] = self.partner_id.property_payment_term_id.id
        return vals

    def _get_recurring_domain(self, date_ref):
        return [
            ("active", "=", True),
            ("stage_id.category", "in", ["progress", "renew"]),
            ("recurring_next_date", "<=", date_ref),
        ]

    # ── QBO MIGRATION BOUNDARY ────────────────────────────────
    # When qbo_online_mirror is activated, invoices generated by
    # this method for the pre-cutover period must be excluded
    # from the mirror sync to prevent double-counting.
    # Filter condition for exclusion:
    #   move.origin == 'sale_subscription'
    #   AND move.invoice_date < [cutover_date ir.config_parameter]
    # ─────────────────────────────────────────────────────────
    def _recurring_create_invoice(self):
        today = fields.Date.context_today(self)
        subscriptions = self if self else self.search(self._get_recurring_domain(today))
        moves = self.env["account.move"]
        for subscription in subscriptions:
            if not subscription.recurring_next_date:
                continue
            if subscription.date and subscription.recurring_next_date > subscription.date:
                subscription.to_renew = True
                continue
            try:
                move_vals = subscription._prepare_invoice_data()
                move = self.env["account.move"].create(move_vals)
                moves |= move
                next_date = subscription.calculate_recurring_next_date(
                    subscription.recurring_next_date
                )
                values = {"recurring_next_date": next_date, "to_renew": False}
                if subscription.date and next_date and next_date > subscription.date:
                    values["to_renew"] = True
                subscription.write(values)
            except Exception:
                _logger.exception(
                    "sale_subscription: recurring invoice generation failed for subscription %s",
                    subscription.id,
                )
        return moves

    def create_invoice(self):
        self.ensure_one()
        return self._recurring_create_invoice()

    @api.model
    def generate_invoice(self):
        today = fields.Date.context_today(self)
        subscriptions = self.search(self._get_recurring_domain(today))
        return subscriptions._recurring_create_invoice()

    def action_view_invoice_ids(self):
        self.ensure_one()
        action = self.env.ref("account.action_move_out_invoice_type", raise_if_not_found=False)
        if action:
            values = action.read()[0]
        else:
            values = {
                "type": "ir.actions.act_window",
                "name": "Invoices",
                "res_model": "account.move",
                "view_mode": "list,form",
            }
        values["domain"] = [("id", "in", self.invoice_ids.ids)]
        values["context"] = {
            "default_move_type": "out_invoice",
            "default_partner_id": self.partner_id.id,
            "default_subscription_id": self.id,
        }
        return values
