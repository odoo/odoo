from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AssetLoan(models.Model):
    _name = "asset.loan"
    _description = "Asset Loan"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "loan_date desc, id desc"
    _check_company_auto = True

    name = fields.Char(
        string="Reference",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _("New"),
    )
    borrower_id = fields.Many2one(
        comodel_name="res.partner",
        string="Borrower",
        required=True,
        tracking=True,
        index=True,
    )
    loan_date = fields.Date(
        string="Loan Date",
        required=True,
        default=fields.Date.context_today,
        tracking=True,
    )
    expected_return_date = fields.Date(
        string="Expected Return Date",
        tracking=True,
        index=True,
    )
    actual_return_date = fields.Date(
        string="Actual Return Date",
        readonly=True,
        tracking=True,
    )
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("borrowed", "Borrowed"),
            ("returned", "Returned"),
            ("lost", "Lost"),
            ("cancelled", "Cancelled"),
        ],
        string="Status",
        default="draft",
        required=True,
        tracking=True,
        copy=False,
        index=True,
    )
    is_overdue = fields.Boolean(
        string="Overdue",
        compute="_compute_is_overdue",
        store=True,
        help="Loan is past its expected return date and not yet returned.",
    )
    line_ids = fields.One2many(
        comodel_name="asset.loan.line",
        inverse_name="loan_id",
        string="Loan Lines",
        copy=True,
    )
    purpose = fields.Text(string="Purpose")
    note = fields.Html(string="Notes")
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains("expected_return_date", "loan_date")
    def _check_dates(self):
        for record in self:
            if (
                record.expected_return_date
                and record.loan_date
                and record.expected_return_date < record.loan_date
            ):
                raise UserError(
                    _("Expected return date must be after the loan date.")
                )

    @api.depends("expected_return_date", "state")
    def _compute_is_overdue(self):
        today = fields.Date.context_today(self)
        for record in self:
            record.is_overdue = bool(
                record.expected_return_date
                and record.expected_return_date < today
                and record.state not in ("returned", "lost", "cancelled")
            )

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "asset.loan"
                ) or _("New")
        return super().create(vals_list)

    def action_confirm(self):
        for record in self:
            if record.state != "draft":
                raise UserError(
                    _("Only draft asset loans can be confirmed.")
                )
            if not record.line_ids:
                raise UserError(_("Please add at least one equipment to borrow."))
            record.write(
                {
                    "state": "borrowed",
                    "actual_return_date": False,
                }
            )
            record.line_ids.write({"state": "borrowed"})

    def action_return(self):
        for record in self:
            if record.state != "borrowed":
                raise UserError(
                    _("Only borrowed asset loans can be returned.")
                )
            record.write(
                {
                    "state": "returned",
                    "actual_return_date": fields.Date.context_today(record),
                }
            )
            for line in record.line_ids:
                line.write(
                    {
                        "state": "returned",
                        "returned_quantity": line.quantity,
                    }
                )

    def action_lost(self):
        for record in self:
            if record.state != "borrowed":
                raise UserError(
                    _("Only borrowed asset loans can be marked as lost.")
                )
            record.write({"state": "lost"})
            record.line_ids.write({"state": "lost"})

    def action_cancel(self):
        for record in self:
            if record.state in ("returned", "lost"):
                raise UserError(
                    _("Cannot cancel a %s asset loan.") % record.state
                )
            record.write({"state": "cancelled"})

    def action_draft(self):
        for record in self:
            if record.state != "cancelled":
                raise UserError(
                    _("Only cancelled asset loans can be reset to draft.")
                )
            record.write({"state": "draft"})

    # ------------------------------------------------------------------
    # Notification helpers
    # ------------------------------------------------------------------
    def _get_notification_partners(self):
        self.ensure_one()
        return self.borrower_id

    def _notify_due(self):
        self.ensure_one()
        partners = self._get_notification_partners()
        if not partners:
            return
        message = _(
            "Reminder: Asset loan %(name)s is due on %(date)s.",
            name=self.name,
            date=self.expected_return_date,
        )
        self.env["notification.service"].notify(
            partners,
            message,
            event="asset_loan_due",
            subject=_("Asset Loan Due Reminder"),
        )

    def _notify_overdue(self):
        self.ensure_one()
        partners = self._get_notification_partners()
        if not partners:
            return
        message = _(
            "Alert: Asset loan %(name)s was due on %(date)s and is now overdue.",
            name=self.name,
            date=self.expected_return_date,
        )
        self.env["notification.service"].notify(
            partners,
            message,
            event="asset_loan_overdue",
            subject=_("Asset Loan Overdue"),
        )

    @api.model
    def _cron_send_due_reminders(self, days=1):
        """Send reminders for loans due within ``days`` days."""
        today = fields.Date.context_today(self)
        due_date = today + relativedelta(days=days)
        loans = self.search(
            [
                ("state", "=", "borrowed"),
                ("expected_return_date", "<=", due_date),
                ("expected_return_date", ">=", today),
            ]
        )
        for loan in loans:
            loan._notify_due()

    @api.model
    def _cron_send_overdue_alerts(self):
        """Send alerts for loans past their expected return date."""
        today = fields.Date.context_today(self)
        loans = self.search(
            [
                ("state", "=", "borrowed"),
                ("expected_return_date", "<", today),
            ]
        )
        for loan in loans:
            loan._notify_overdue()
