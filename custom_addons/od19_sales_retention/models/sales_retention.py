from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class Od19SalesRetention(models.Model):
    """Retention (เงินประกันผลงาน) carved out of a progress payment.

    A progress invoice is always issued for the **full** amount (net + VAT) as
    required by the Revenue Department ruling กค 0706/พ.789.  The retained part
    is then moved from the regular trade receivable to a dedicated retention
    receivable account so the output VAT reported on ภ.พ.30 stays correct.
    """

    _name = "od19.sales.retention"
    _description = "Sales Retention (เงินประกันผลงาน)"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "release_date asc, id desc"

    name = fields.Char(
        string="Reference",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _("New"),
    )
    contract_id = fields.Many2one(
        "od19.sales.contract",
        string="Sales Contract",
        required=True,
        ondelete="cascade",
        index=True,
        tracking=True,
    )
    billing_line_id = fields.Many2one(
        "od19.contract.billing.line",
        string="Installment",
        ondelete="set null",
        index=True,
        help="Progress payment the retention is withheld from.",
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="Customer",
        required=True,
        index=True,
        tracking=True,
    )
    invoice_id = fields.Many2one(
        "account.move",
        string="Tax Invoice",
        readonly=True,
        copy=False,
        index=True,
        help="Full amount tax invoice the retention is separated from.",
    )
    invoice_date = fields.Date(
        related="invoice_id.invoice_date",
        store=True,
        readonly=True,
    )
    invoice_amount_untaxed = fields.Monetary(
        related="invoice_id.amount_untaxed",
        currency_field="currency_id",
        store=True,
        readonly=True,
    )
    invoice_amount_total = fields.Monetary(
        related="invoice_id.amount_total",
        currency_field="currency_id",
        store=True,
        readonly=True,
    )
    base_amount = fields.Monetary(
        string="Base Amount",
        currency_field="currency_id",
        tracking=True,
        help="Net installment amount the retention is calculated on.",
    )
    retention_rate = fields.Float(
        string="Retention Rate (%)",
        digits=(5, 2),
        tracking=True,
    )
    retention_amount = fields.Monetary(
        string="Retention Amount",
        currency_field="currency_id",
        tracking=True,
        help="Amount carved out from the trade receivable into the retention "
        "receivable account (VAT inclusive).",
    )
    release_date = fields.Date(
        string="Release Date",
        compute="_compute_release_date",
        store=True,
        readonly=False,
        index=True,
        tracking=True,
        help="Date the retention is due to be released back to the customer.",
    )
    released_date = fields.Date(
        string="Released On",
        readonly=True,
        copy=False,
        tracking=True,
    )
    is_overdue = fields.Boolean(
        string="Overdue",
        compute="_compute_is_overdue",
        store=True,
        help="Retention is past its release date and still held.",
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("held", "Held"),
            ("released", "Released"),
            ("closed", "Closed"),
            ("cancelled", "Cancelled"),
        ],
        default="draft",
        required=True,
        tracking=True,
        copy=False,
        index=True,
    )
    move_id = fields.Many2one(
        "account.move",
        string="Retention Entry",
        readonly=True,
        copy=False,
    )
    release_move_id = fields.Many2one(
        "account.move",
        string="Release Entry",
        readonly=True,
        copy=False,
    )
    note = fields.Text()
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        required=True,
        default=lambda self: self.env.company.currency_id,
    )
    journal_id = fields.Many2one(
        related="contract_id.od19_retention_journal_id",
        string="Journal",
    )
    retention_account_id = fields.Many2one(
        related="contract_id.od19_retention_account_id",
        string="Retention Account",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code("od19.sales.retention")
                    or _("New")
                )
        return super().create(vals_list)

    @api.depends("invoice_date", "contract_id.od19_default_retention_days")
    def _compute_release_date(self):
        for record in self:
            days = record.contract_id.od19_default_retention_days
            if record.invoice_date and days:
                record.release_date = record.invoice_date + relativedelta(days=days)
            elif not record.release_date:
                record.release_date = False

    @api.depends("state", "release_date")
    def _compute_is_overdue(self):
        today = fields.Date.context_today(self)
        for record in self:
            record.is_overdue = bool(
                record.state == "held"
                and record.release_date
                and record.release_date < today
            )

    @api.constrains("retention_rate")
    def _check_retention_rate(self):
        for record in self:
            if record.retention_rate < 0 or record.retention_rate > 100:
                raise ValidationError(
                    _("Retention rate must be between 0 and 100.")
                )

    @api.constrains("retention_amount")
    def _check_retention_amount(self):
        for record in self:
            if record.retention_amount < 0:
                raise ValidationError(
                    _("Retention amount cannot be negative.")
                )

    def _od19_check_configuration(self):
        self.ensure_one()
        contract = self.contract_id
        if not contract.od19_retention_journal_id:
            raise UserError(
                _(
                    "Please configure the retention journal on contract '%s' "
                    "first."
                )
                % contract.name
            )
        if not contract.od19_retention_account_id:
            raise UserError(
                _(
                    "Please configure the retention receivable account on "
                    "contract '%s' first."
                )
                % contract.name
            )
        receivable = self.partner_id.property_account_receivable_id
        if contract.od19_retention_account_id == receivable:
            raise UserError(
                _(
                    "The retention receivable account must be different from "
                    "the customer receivable account (%s)."
                )
                % (receivable.display_name or "-")
            )

    def _od19_return_move(self, move):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "res_id": move.id,
            "view_mode": "form",
            "target": "current",
        }

    def _prepare_hold_move_vals(self):
        """Journal entry moving the retention out of the trade receivable."""
        self.ensure_one()
        contract = self.contract_id
        label = _("Retention held - %s (%s)") % (self.name, self.contract_id.name)
        return {
            "journal_id": contract.od19_retention_journal_id.id,
            "date": self.invoice_date or fields.Date.context_today(self),
            "ref": label,
            "company_id": self.company_id.id,
            "od19_retention_id": self.id,
            "line_ids": [
                (
                    0,
                    0,
                    {
                        "account_id": contract.od19_retention_account_id.id,
                        "partner_id": self.partner_id.id,
                        "name": label,
                        "debit": self.retention_amount,
                        "credit": 0.0,
                    },
                ),
                (
                    0,
                    0,
                    {
                        "account_id": self.partner_id.property_account_receivable_id.id,
                        "partner_id": self.partner_id.id,
                        "name": label,
                        "debit": 0.0,
                        "credit": self.retention_amount,
                    },
                ),
            ],
        }

    def _prepare_release_move_vals(self):
        """Reverse entry: retention receivable back to the trade receivable."""
        self.ensure_one()
        contract = self.contract_id
        label = _("Retention released - %s (%s)") % (self.name, contract.name)
        return {
            "journal_id": contract.od19_retention_journal_id.id,
            "date": fields.Date.context_today(self),
            "ref": label,
            "company_id": self.company_id.id,
            "od19_retention_id": self.id,
            "line_ids": [
                (
                    0,
                    0,
                    {
                        "account_id": self.partner_id.property_account_receivable_id.id,
                        "partner_id": self.partner_id.id,
                        "name": label,
                        "debit": self.retention_amount,
                        "credit": 0.0,
                    },
                ),
                (
                    0,
                    0,
                    {
                        "account_id": contract.od19_retention_account_id.id,
                        "partner_id": self.partner_id.id,
                        "name": label,
                        "debit": 0.0,
                        "credit": self.retention_amount,
                    },
                ),
            ],
        }

    def action_hold(self):
        """Post the entry that carves the retention out of the receivable."""
        self.ensure_one()
        if self.state != "draft":
            raise UserError(
                _("Only draft retentions can be held (current state: %s).")
                % self.state
            )
        if self.retention_amount <= 0:
            raise UserError(
                _("Retention amount must be greater than zero to hold it.")
            )
        self._od19_check_configuration()
        move = self.env["account.move"].create(self._prepare_hold_move_vals())
        move.action_post()
        self.write({"state": "held", "move_id": move.id})
        return self._od19_return_move(move)

    def action_release(self):
        """Release the retention back to the trade receivable."""
        self.ensure_one()
        if self.state != "held":
            raise UserError(
                _("Only held retentions can be released (current state: %s).")
                % self.state
            )
        move = self.env["account.move"].create(self._prepare_release_move_vals())
        move.action_post()
        self.write(
            {
                "state": "released",
                "release_move_id": move.id,
                "released_date": fields.Date.context_today(self),
            }
        )
        return self._od19_return_move(move)

    def action_close(self):
        for record in self:
            if record.state != "released":
                raise UserError(
                    _("Only released retentions can be closed.")
                )
            record.state = "closed"
        return True

    def action_cancel(self):
        for record in self:
            if record.state != "draft":
                raise UserError(
                    _(
                        "Only draft retentions can be cancelled. Release the "
                        "retention first if it is already held."
                    )
                )
            record.state = "cancelled"
        return True

    def action_draft(self):
        for record in self:
            if record.state != "cancelled":
                raise UserError(_("Only cancelled retentions can be reset."))
            record.state = "draft"
        return True

    def _notify_release_due(self):
        self.ensure_one()
        message = _(
            "Retention %(name)s (%(partner)s) is due for release on %(date)s.",
            name=self.name,
            partner=self.partner_id.display_name,
            date=self.release_date,
        )
        self.message_post(body=message)
        self.activity_schedule(
            "mail.mail_activity_data_todo",
            date_deadline=self.release_date,
            summary=_("Release retention %s") % self.name,
            note=message,
        )

    def _notify_release_overdue(self):
        self.ensure_one()
        message = _(
            "Retention %(name)s (%(partner)s) was due for release on "
            "%(date)s and is overdue.",
            name=self.name,
            partner=self.partner_id.display_name,
            date=self.release_date,
        )
        self.message_post(body=message)
        self.activity_schedule(
            "mail.mail_activity_data_todo",
            date_deadline=fields.Date.context_today(self),
            summary=_("Overdue retention release %s") % self.name,
            note=message,
        )

    @api.model
    def _cron_retention_due_reminder(self, days=30):
        """Warn about retentions whose release date is approaching."""
        today = fields.Date.context_today(self)
        horizon = today + relativedelta(days=days)
        records = self.search(
            [
                ("state", "=", "held"),
                ("release_date", "!=", False),
                ("release_date", "<=", horizon),
                ("release_date", ">=", today),
            ]
        )
        for record in records:
            record._notify_release_due()

    @api.model
    def _cron_retention_overdue_alert(self):
        """Alert about retentions whose release date has passed."""
        today = fields.Date.context_today(self)
        records = self.search(
            [
                ("state", "=", "held"),
                ("release_date", "!=", False),
                ("release_date", "<", today),
            ]
        )
        for record in records:
            record._notify_release_overdue()
