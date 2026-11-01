from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AccountAdvance(models.Model):
    _name = "account.advance"
    _description = "Advance Payment"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date desc, id desc"

    name = fields.Char(
        string="Number",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _("New"),
    )
    advance_type = fields.Selection(
        [
            ("customer", "Customer Advance"),
            ("supplier", "Supplier Advance"),
        ],
        string="Type",
        required=True,
        default="customer",
        tracking=True,
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="Partner",
        required=True,
        tracking=True,
    )
    amount = fields.Monetary(
        string="Amount",
        currency_field="currency_id",
        required=True,
        tracking=True,
    )
    used_amount = fields.Monetary(
        string="Used Amount",
        currency_field="currency_id",
        compute="_compute_used_amount",
        store=True,
    )
    remaining_amount = fields.Monetary(
        string="Remaining Amount",
        currency_field="currency_id",
        compute="_compute_remaining_amount",
        store=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        required=True,
        default=lambda self: self.env.company.currency_id,
    )
    date = fields.Date(
        string="Date",
        required=True,
        default=fields.Date.context_today,
        tracking=True,
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("posted", "Posted"),
            ("reconciled", "Reconciled"),
            ("cancel", "Cancelled"),
        ],
        string="Status",
        default="draft",
        tracking=True,
        copy=False,
    )
    move_id = fields.Many2one(
        "account.move",
        string="Journal Entry",
        readonly=True,
        copy=False,
    )
    advance_account_id = fields.Many2one(
        "account.account",
        string="Advance Account",
        required=True,
    )
    journal_id = fields.Many2one(
        "account.journal",
        string="Journal",
    )
    note = fields.Text(string="Notes")

    @api.depends("amount", "used_amount")
    def _compute_remaining_amount(self):
        for advance in self:
            advance.remaining_amount = advance.amount - advance.used_amount

    @api.depends("move_id.line_ids.amount_residual")
    def _compute_used_amount(self):
        for advance in self:
            used = 0.0
            if advance.move_id:
                advance_lines = advance.move_id.line_ids.filtered(
                    lambda l: l.account_id == advance.advance_account_id
                )
                for line in advance_lines:
                    used += abs(line.amount_residual)
                advance.used_amount = advance.amount - used if advance.amount else 0.0
            else:
                advance.used_amount = 0.0

    @api.constrains("amount")
    def _check_amount(self):
        for advance in self:
            if advance.amount <= 0:
                raise ValidationError(
                    _("Advance amount must be greater than zero.")
                )

    @api.constrains("partner_id")
    def _check_partner(self):
        for advance in self:
            if not advance.partner_id:
                raise ValidationError(_("Partner is required."))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "account.advance"
                ) or _("New")
        return super().create(vals_list)

    def action_post(self):
        for advance in self:
            if advance.state != "draft":
                continue
            if not advance.journal_id:
                raise ValidationError(_("Please select a journal."))
            move_vals = advance._prepare_move_vals()
            move = self.env["account.move"].create(move_vals)
            move.action_post()
            advance.move_id = move
            advance.state = "posted"

    def action_reconcile(self):
        """ตัดบัญชีเงินล่วงหน้ากับรายการคู่ที่เกี่ยวข้อง (reconcile)."""
        for advance in self:
            if advance.state != "posted":
                raise ValidationError(_("Only posted advances can be reconciled."))
            if not advance.move_id:
                raise ValidationError(_("Please post the advance first."))
            advance.move_id._od19_reconcile_account_lines(
                advance.advance_account_id.id, advance.partner_id.id
            )
            advance.invalidate_recordset(["used_amount", "remaining_amount"])
            if advance.currency_id.is_zero(advance.remaining_amount):
                advance.state = "reconciled"
        return True

    def action_cancel(self):
        for advance in self:
            if advance.state not in ("posted", "reconciled"):
                raise ValidationError(
                    _("Only posted or reconciled advances can be cancelled.")
                )
            if advance.move_id:
                advance.move_id.button_cancel()
            advance.state = "cancel"

    def action_draft(self):
        for advance in self:
            if advance.state != "cancel":
                raise ValidationError(
                    _("Only cancelled advances can be reset to draft.")
                )
            if advance.move_id:
                advance.move_id.button_draft()
                advance.move_id.unlink()
            advance.state = "draft"

    def _prepare_move_vals(self):
        self.ensure_one()
        if self.advance_type == "customer":
            debit_account = self.journal_id.default_account_id
            credit_account = self.advance_account_id
        else:
            debit_account = self.advance_account_id
            credit_account = self.journal_id.default_account_id

        return {
            "date": self.date,
            "journal_id": self.journal_id.id,
            "ref": self.name,
            "line_ids": [
                (
                    0,
                    0,
                    {
                        "account_id": debit_account.id,
                        "partner_id": self.partner_id.id,
                        "debit": self.amount,
                        "credit": 0.0,
                        "name": self.name,
                    },
                ),
                (
                    0,
                    0,
                    {
                        "account_id": credit_account.id,
                        "partner_id": self.partner_id.id,
                        "debit": 0.0,
                        "credit": self.amount,
                        "name": self.name,
                    },
                ),
            ],
        }
