from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class Od19ContractRevenueLine(models.Model):
    """TFRS 15 performance obligation and its revenue recognition schedule."""

    _name = "od19.contract.revenue.line"
    _description = "Contract Revenue Schedule Line"
    _order = "contract_id, sequence, id"

    name = fields.Char(required=True)
    contract_id = fields.Many2one(
        "od19.sales.contract", required=True, ondelete="cascade", index=True
    )
    sequence = fields.Integer(default=10)
    recognition_method = fields.Selection(
        [
            ("milestone", "Milestone"),
            ("percent", "Percent of Completion"),
            ("progress", "Progress / POC"),
        ],
        default="percent",
        required=True,
    )
    percent = fields.Float(
        string="Allocation (%)",
        help="Share of the contract value allocated to this performance "
        "obligation. When set, the allocated amount is derived from it.",
    )
    total_amount = fields.Float(
        compute="_compute_total_amount",
        store=True,
        readonly=False,
        help="Allocated transaction price for this performance obligation. "
        "Derived from the allocation percent when that is set, otherwise "
        "entered manually.",
    )
    progress_percent = fields.Float(
        string="Progress (%)",
        help="Cumulative progress (percentage of completion) used to recognize "
        "revenue when the method is 'Progress / POC'.",
    )
    recognized_amount = fields.Float(
        compute="_compute_recognized_amount",
        store=True,
        help="Revenue already recognized, read back from the posted journal "
        "entries so it always reconciles with the general ledger.",
    )
    remaining_amount = fields.Float(
        compute="_compute_remaining_amount",
        store=True,
        help="Allocated amount still to be recognized.",
    )
    state = fields.Selection(
        [
            ("pending", "Pending"),
            ("partial", "Partially Recognized"),
            ("recognized", "Recognized"),
        ],
        compute="_compute_state",
        store=True,
    )
    move_ids = fields.One2many(
        "account.move",
        "od19_revenue_line_id",
        string="Revenue Entries",
        readonly=True,
    )

    @api.depends("percent", "contract_id.limit_amount")
    def _compute_total_amount(self):
        for line in self:
            if line.percent:
                line.total_amount = (
                    (line.percent or 0.0)
                    / 100.0
                    * (line.contract_id.limit_amount or 0.0)
                )

    @api.depends(
        "move_ids.state",
        "move_ids.line_ids.credit",
        "move_ids.line_ids.account_id",
        "contract_id.revenue_account_id",
    )
    def _compute_recognized_amount(self):
        for line in self:
            revenue_account = line.contract_id.revenue_account_id
            if not revenue_account:
                line.recognized_amount = 0.0
                continue
            revenue_lines = line.move_ids.filtered(
                lambda move: move.state == "posted"
            ).line_ids.filtered(
                lambda move_line: move_line.account_id == revenue_account
            )
            line.recognized_amount = sum(revenue_lines.mapped("credit"))

    @api.depends("total_amount", "recognized_amount")
    def _compute_remaining_amount(self):
        for line in self:
            line.remaining_amount = line.total_amount - line.recognized_amount

    @api.depends("total_amount", "recognized_amount")
    def _compute_state(self):
        for line in self:
            if line.total_amount and line.recognized_amount >= line.total_amount - 1e-6:
                line.state = "recognized"
            elif line.recognized_amount > 0:
                line.state = "partial"
            else:
                line.state = "pending"

    @api.constrains("percent", "progress_percent")
    def _check_percent_range(self):
        for line in self:
            if line.percent < 0 or line.percent > 100:
                raise ValidationError(
                    _("Allocation percent must be between 0 and 100.")
                )
            if line.progress_percent < 0 or line.progress_percent > 100:
                raise ValidationError(
                    _("Progress percent must be between 0 and 100.")
                )

    @api.constrains("total_amount")
    def _check_total_amount(self):
        for line in self:
            if line.total_amount < 0:
                raise ValidationError(
                    _("Allocated revenue amount cannot be negative.")
                )

    @api.constrains("total_amount", "contract_id")
    def _check_total_within_limit(self):
        for line in self:
            if not line.contract_id:
                continue
            total = sum(line.contract_id.revenue_line_ids.mapped("total_amount"))
            limit = line.contract_id.limit_amount
            if limit and total > limit:
                raise ValidationError(
                    _(
                        "Total revenue allocation (%.2f) exceeds the contract "
                        "limit (%.2f)."
                    )
                    % (total, limit)
                )

    def _od19_target_recognized_amount(self):
        """Cumulative revenue that should be recognized for this obligation."""
        self.ensure_one()
        if self.recognition_method == "progress":
            return (self.progress_percent or 0.0) / 100.0 * self.total_amount
        return self.total_amount

    def _prepare_revenue_move_vals(self, amount):
        self.ensure_one()
        contract = self.contract_id
        label = _("Revenue recognition - %s") % self.name
        return {
            "journal_id": contract.revenue_journal_id.id,
            "date": fields.Date.context_today(self),
            "ref": label,
            "od19_revenue_line_id": self.id,
            "line_ids": [
                (
                    0,
                    0,
                    {
                        "account_id": contract.deferred_revenue_account_id.id,
                        "partner_id": contract.partner_id.id,
                        "name": label,
                        "debit": amount,
                        "credit": 0.0,
                    },
                ),
                (
                    0,
                    0,
                    {
                        "account_id": contract.revenue_account_id.id,
                        "partner_id": contract.partner_id.id,
                        "name": label,
                        "debit": 0.0,
                        "credit": amount,
                    },
                ),
            ],
        }

    def action_recognize(self, amount=None):
        """Recognize revenue by posting a deferred revenue -> revenue entry."""
        self.ensure_one()
        contract = self.contract_id
        if (
            not contract.revenue_journal_id
            or not contract.deferred_revenue_account_id
            or not contract.revenue_account_id
        ):
            raise UserError(
                _(
                    "Please configure the revenue journal, deferred revenue "
                    "account and revenue account on contract '%s' first."
                )
                % contract.name
            )
        target = self._od19_target_recognized_amount()
        to_recognize = target - self.recognized_amount if amount is None else amount
        if to_recognize <= 0:
            raise UserError(
                _("There is no remaining revenue to recognize for '%s'.") % self.name
            )
        if self.recognized_amount + to_recognize > self.total_amount + 1e-6:
            raise UserError(
                _(
                    "Recognized revenue cannot exceed the allocated amount of "
                    "'%s' (%.2f)."
                )
                % (self.name, self.total_amount)
            )
        move = self.env["account.move"].create(
            self._prepare_revenue_move_vals(to_recognize)
        )
        move.action_post()
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "res_id": move.id,
            "view_mode": "form",
            "target": "current",
        }
