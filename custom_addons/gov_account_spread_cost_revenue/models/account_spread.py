import logging

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class AccountSpread(models.Model):
    _name = "account.spread"
    _description = "Spread Schedule"
    _order = "date_start desc, id desc"

    name = fields.Char(required=True)
    account_id = fields.Many2one("account.account", required=True, check_company=True)
    journal_id = fields.Many2one("account.journal", required=True, check_company=True)
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        related="company_id.currency_id",
        store=True,
        readonly=True,
    )
    date_start = fields.Date(required=True)
    date_end = fields.Date(required=True)
    period_type = fields.Selection(
        [("monthly", "Monthly"), ("quarterly", "Quarterly"), ("yearly", "Yearly")],
        required=True,
        default="monthly",
    )
    spread_type = fields.Selection(
        [("sale", "Sale"), ("purchase", "Purchase")],
        required=True,
        default="sale",
    )
    move_line_id = fields.Many2one("account.move.line", ondelete="set null", check_company=True)
    move_id = fields.Many2one(
        "account.move",
        string="Source Move",
        compute="_compute_move_id",
        store=True,
        readonly=True,
        index=True,
    )
    estimated_amount = fields.Monetary(currency_field="currency_id")
    spread_line_ids = fields.One2many("account.spread.line", "spread_id", string="Spread Lines")
    unspread_amount = fields.Monetary(
        currency_field="currency_id",
        compute="_compute_unspread_amount",
        store=True,
    )
    spread_progress = fields.Float(compute="_compute_spread_progress", store=True)
    state = fields.Selection(
        [("draft", "Draft"), ("confirmed", "Confirmed"), ("posted", "Posted"), ("done", "Done")],
        required=True,
        default="draft",
        index=True,
    )

    @api.depends("move_line_id.move_id")
    def _compute_move_id(self):
        for spread in self:
            spread.move_id = spread.move_line_id.move_id

    @api.constrains("date_start", "date_end")
    def _check_dates(self):
        for spread in self:
            if spread.date_start and spread.date_end and spread.date_start > spread.date_end:
                raise ValidationError("Spread start date must be before end date.")

    @api.constrains("estimated_amount")
    def _check_estimated_amount(self):
        for spread in self:
            if spread.estimated_amount is not False and spread.estimated_amount <= 0:
                raise ValidationError("Estimated amount must be greater than zero.")

    @api.depends("spread_line_ids.amount", "spread_line_ids.move_id", "estimated_amount")
    def _compute_unspread_amount(self):
        for spread in self:
            if spread.spread_line_ids:
                pending = spread.spread_line_ids.filtered(lambda l: not l.move_id)
                spread.unspread_amount = sum(pending.mapped("amount"))
            else:
                spread.unspread_amount = spread.estimated_amount

    @api.depends("spread_line_ids.amount", "spread_line_ids.move_id", "estimated_amount")
    def _compute_spread_progress(self):
        for spread in self:
            if not spread.estimated_amount:
                spread.spread_progress = 0.0
                continue
            posted_amount = sum(spread.spread_line_ids.filtered(lambda l: l.move_id).mapped("amount"))
            spread.spread_progress = min(max(posted_amount / spread.estimated_amount, 0.0), 1.0)

    def _update_state_from_lines(self):
        for spread in self:
            if spread.state == "draft":
                continue
            lines = spread.spread_line_ids
            if not lines:
                spread.state = "confirmed"
                continue
            posted = lines.filtered("move_id")
            if len(posted) == 0:
                spread.state = "confirmed"
            elif len(posted) < len(lines):
                spread.state = "posted"
            else:
                spread.state = "done"

    def action_confirm(self):
        for spread in self:
            if spread.estimated_amount <= 0:
                raise UserError("Estimated amount must be greater than zero before confirmation.")
            if not spread.move_line_id and not spread.estimated_amount:
                raise UserError("Set an estimated amount or link an invoice line before confirmation.")
            spread._generate_spread_lines()
            spread.state = "confirmed"
        return True

    def _period_months(self):
        self.ensure_one()
        return {"monthly": 1, "quarterly": 3, "yearly": 12}[self.period_type]

    @staticmethod
    def _period_end_for_date(start_date, months):
        return start_date + relativedelta(months=months - 1, day=31)

    def _generate_spread_lines(self):
        for spread in self:
            spread.spread_line_ids.filtered(lambda l: not l.move_id).unlink()

            periods = []
            cursor = spread.date_start
            months = spread._period_months()
            fiscal_year_model = self.env["account.fiscal.year"].with_company(spread.company_id)

            while cursor <= spread.date_end:
                natural_end = self._period_end_for_date(cursor, months)
                period_end = min(natural_end, spread.date_end)

                fy = fiscal_year_model.find_daterange_fy(cursor)
                if fy and fy.date_to and period_end > fy.date_to:
                    period_end = fy.date_to

                if period_end < cursor:
                    period_end = cursor

                periods.append(period_end)
                cursor = period_end + relativedelta(days=1)

            if not periods:
                continue

            rounded_total = spread.currency_id.round(spread.estimated_amount)
            base_amount = spread.currency_id.round(rounded_total / len(periods))
            allocated = 0.0
            line_vals = []
            for idx, period_end in enumerate(periods, start=1):
                if idx == len(periods):
                    amount = spread.currency_id.round(rounded_total - allocated)
                else:
                    amount = base_amount
                    allocated += amount
                line_vals.append({"spread_id": spread.id, "date": period_end, "amount": amount})

            self.env["account.spread.line"].create(line_vals)
            spread._update_state_from_lines()
        return True

    def action_post_all_lines(self):
        today = fields.Date.context_today(self)
        count = 0
        for spread in self:
            lines = spread.spread_line_ids.filtered(lambda l: not l.move_id and l.date <= today)
            for line in lines:
                line._create_move()
                count += 1
            spread._update_state_from_lines()
        return count

    def action_draft(self):
        for spread in self:
            if spread.spread_line_ids.filtered("move_id"):
                raise UserError("Cannot reset to draft after posting spread lines.")
            spread.spread_line_ids.unlink()
            spread.state = "draft"
        return True

    @api.model
    def _cron_post_spread_lines(self):
        try:
            spreads = self.search([("state", "in", ["confirmed", "posted"])])
            today = fields.Date.context_today(self)
            for spread in spreads:
                try:
                    due_lines = spread.spread_line_ids.filtered(
                        lambda l: not l.move_id and l.date <= today
                    )
                    for line in due_lines:
                        line._create_move()
                    spread._update_state_from_lines()
                except Exception:
                    _logger.warning(
                        "Spread cron failed for spread %s (%s).",
                        spread.id,
                        spread.display_name,
                        exc_info=True,
                    )
        except Exception:
            _logger.warning("Spread cron failed unexpectedly.", exc_info=True)
        return True
