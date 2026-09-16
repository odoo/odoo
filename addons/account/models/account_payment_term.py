from functools import partial

from dateutil.relativedelta import relativedelta
from markupsafe import Markup

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.libs.debug_log import DebugLog
from odoo.libs.numbers import float_compare
from odoo.tools import date_utils, format_date, formatLang

_debug = DebugLog(__name__)


class AccountPaymentTerm(models.Model):
    _name = "account.payment.term"
    _inherit = ["mixin.fiscal.country.codes"]
    _description = "Payment Terms"
    _order = "sequence, id"
    _check_company_domain = models.check_company_domain_parent_of

    def _default_line_ids(self):
        return [
            Command.create({"value": "percent", "value_amount": 100.0, "nb_days": 0})
        ]

    def _default_example_amount(self):
        return self.env.context.get("example_amount") or 1000.0

    def _default_example_tax_amount(self):
        return self.env.context.get("example_tax_amount") or 0.0

    def _default_example_date(self):
        return self.env.context.get("example_date") or fields.Date.today()

    name = fields.Char(
        string="Payment Terms",
        translate=True,
        required=True,
    )
    active = fields.Boolean(
        default=True,
        help="If the active field is set to False, it will allow you to hide the payment terms without removing it.",
    )
    note = fields.Html(
        string="Description on the Invoice",
        translate=True,
    )
    line_ids = fields.One2many(
        comodel_name="account.payment.term.line",
        inverse_name="payment_id",
        string="Terms",
        default=_default_line_ids,
        copy=True,
    )
    company_id = fields.Many2one(comodel_name="res.company")
    sequence = fields.Integer(
        default=10,
        required=True,
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        compute="_compute_currency_id",
    )

    display_on_invoice = fields.Boolean(
        string="Show installment dates",
        default=True,
    )
    example_amount = fields.Monetary(
        currency_field="currency_id",
        default=_default_example_amount,
        store=False,
        readonly=True,
    )
    example_tax_amount = fields.Monetary(
        string="Tax in the example",
        currency_field="currency_id",
        default=_default_example_tax_amount,
        store=False,
        readonly=True,
    )
    example_date = fields.Date(
        string="Date example",
        default=_default_example_date,
        store=False,
    )
    example_preview = fields.Html(compute="_compute_example_previews")
    example_preview_discount = fields.Html(compute="_compute_example_previews")

    discount_percentage = fields.Float(
        string="Discount %",
        default=2.0,
        help="Early Payment Discount granted for this payment term",
    )
    discount_days = fields.Integer(
        default=10,
        help="Number of days before the early payment proposition expires",
    )
    early_pay_discount_computation = fields.Selection(
        selection=[
            ("included", "On early payment"),
            ("excluded", "Never"),
            ("mixed", "Always (upon invoice)"),
        ],
        string="Cash Discount Tax Reduction",
        compute="_compute_early_pay_discount_computation",
        store=True,
        readonly=False,
    )
    early_discount = fields.Boolean()
    is_immediate = fields.Boolean(
        string="Immediate Payment Term",
        compute="_compute_is_immediate",
        store=True,
        help="True when the whole amount falls due on the invoice date itself: "
        "a single 100% line, no delay, counted from the invoice date.",
    )

    def _get_percent_precision(self):
        return self.env["decimal.precision"].get_precision("Payment Terms")

    @api.depends("company_id")
    def _compute_fiscal_country_codes(self):
        return super()._compute_fiscal_country_codes()

    def _get_fiscal_country_companies(self):
        return self.company_id or super()._get_fiscal_country_companies()

    @api.depends_context("company")
    @api.depends("company_id")
    def _compute_currency_id(self):
        for payment_term in self:
            payment_term.currency_id = (
                payment_term.company_id.currency_id or self.env.company.currency_id
            )

    def _get_amount_due_after_discount(self, total_amount, untaxed_amount, currency):
        self.check_singleton()
        if not self.early_discount:
            return currency.round(total_amount)
        percentage = self.discount_percentage / 100.0
        if self.early_pay_discount_computation in ("excluded", "mixed"):
            return currency.round(total_amount - untaxed_amount * percentage)
        return currency.round(total_amount * (1 - percentage))

    @api.depends("company_id")
    def _compute_early_pay_discount_computation(self):
        for pay_term in self:
            if pay_term.early_pay_discount_computation:
                continue
            country_code = (
                pay_term.company_id.country_code or self.env.company.country_code
            )
            if country_code == "BE":
                pay_term.early_pay_discount_computation = "mixed"
            elif country_code == "NL":
                pay_term.early_pay_discount_computation = "excluded"
            else:
                pay_term.early_pay_discount_computation = "included"

    @api.depends(
        "line_ids.nb_days",
        "line_ids.value_amount",
        "line_ids.value",
        "line_ids.delay_type",
    )
    def _compute_is_immediate(self):
        precision = self._get_percent_precision()
        for term in self:
            line = term.line_ids
            term.is_immediate = (
                len(line) == 1
                and line.value == "percent"
                and line.delay_type == "days_after"
                and line.nb_days == 0
                and float_compare(line.value_amount, 100.0, precision_digits=precision)
                == 0
            )

    @api.depends(
        "currency_id",
        "example_amount",
        "example_tax_amount",
        "example_date",
        "line_ids.value",
        "line_ids.value_amount",
        "line_ids.nb_days",
        "line_ids.delay_type",
        "line_ids.days_next_month",
        "early_discount",
        "early_pay_discount_computation",
        "discount_percentage",
        "discount_days",
    )
    @api.depends_context("lang")
    @_debug.perf.timed
    def _compute_example_previews(self):
        for record in self:
            currency = record.currency_id
            date_ref = record.example_date or fields.Date.context_today(record)
            record.example_preview_discount = ""
            record.example_preview = ""

            untaxed_example = record.example_amount - record.example_tax_amount

            if record.early_discount:
                amount_due = record._get_amount_due_after_discount(
                    record.example_amount, untaxed_example, currency
                )
                record.example_preview_discount = Markup(
                    _(
                        "Early Payment Discount: <b>%(amount)s</b> if paid before <b>%(date)s</b>"
                    )
                ) % {
                    "amount": formatLang(self.env, amount_due, currency_obj=currency),
                    "date": format_date(
                        self.env, record._get_last_discount_date(date_ref)
                    ),
                }

            if not record.line_ids:
                _debug.logic(
                    "example_preview_skipped",
                    term=record,
                    reason="no_lines",
                    early_discount=record.early_discount,
                )
                continue

            terms = record._get_terms(
                date_ref=date_ref,
                currency=currency,
                company=record.company_id or self.env.company,
                tax_amount=record.example_tax_amount,
                tax_amount_currency=record.example_tax_amount,
                untaxed_amount=untaxed_example,
                untaxed_amount_currency=untaxed_example,
                sign=1,
            )
            example_preview = Markup()
            for count, info_by_dates in enumerate(
                record._get_amount_by_date(terms).values(), start=1
            ):
                example_preview += (
                    Markup("<div>%s</div>")
                    % Markup(
                        _(
                            "<b>%(count)s#</b> Installment of <b>%(amount)s</b> due on <b style='color: #704A66;'>%(date)s</b>"
                        )
                    )
                    % {
                        "count": count,
                        "amount": formatLang(
                            self.env, info_by_dates["amount"], currency_obj=currency
                        ),
                        "date": info_by_dates["date"],
                    }
                )
            record.example_preview = example_preview
            _debug.pipeline(
                "example_preview_built",
                term=record,
                early_discount=record.early_discount,
                installments=len(terms.get("line_ids") or ()),
            )

    @api.model
    def _get_amount_by_date(self, terms):
        amount_by_date = {}
        for term in sorted(terms["line_ids"], key=lambda t: t["date"]):
            results = amount_by_date.setdefault(
                term["date"],
                {"date": format_date(self.env, term["date"]), "amount": 0.0},
            )
            results["amount"] += term["foreign_amount"]
        return amount_by_date

    @api.constrains(
        "line_ids", "early_discount", "discount_percentage", "discount_days"
    )
    @_debug.perf.timed
    def _check_lines(self):
        precision = self._get_percent_precision()
        for terms in self:
            total_percent = sum(
                line.value_amount for line in terms.line_ids if line.value == "percent"
            )
            if float_compare(total_percent, 100.0, precision_digits=precision) != 0:
                _debug.logic(
                    "term_rejected",
                    term=terms,
                    reason="percent_total",
                    total_percent=total_percent,
                )
                raise ValidationError(
                    _(
                        "The Payment Term must have at least one percent line and the sum of the percent must be 100%."
                    )
                )
            if len(terms.line_ids) > 1 and terms.early_discount:
                _debug.logic(
                    "term_rejected", term=terms, reason="early_discount_multi_line"
                )
                raise ValidationError(
                    _(
                        "The Early Payment Discount functionality can only be used with payment terms using a single 100% line. "
                    )
                )
            if terms.early_discount and terms.discount_percentage <= 0.0:
                _debug.logic(
                    "term_rejected", term=terms, reason="early_discount_percentage"
                )
                raise ValidationError(
                    _("The Early Payment Discount must be strictly positive.")
                )
            if terms.early_discount and terms.discount_days <= 0:
                _debug.logic("term_rejected", term=terms, reason="early_discount_days")
                raise ValidationError(
                    _("The Early Payment Discount days must be strictly positive.")
                )

    @api.model
    def _get_cash_rounded_pair(
        self,
        foreign_amount,
        company_amount,
        *,
        cash_rounding,
        currency,
        company_currency,
        rate,
    ):
        if not cash_rounding:
            return foreign_amount, company_amount
        difference = cash_rounding.compute_difference(currency, foreign_amount)
        if currency.is_zero(difference):
            return foreign_amount, company_amount
        foreign_amount += difference
        return foreign_amount, (
            company_currency.round(foreign_amount / rate) if rate else 0.0
        )

    @_debug.perf.timed
    def _get_terms(
        self,
        *,
        date_ref,
        currency,
        company,
        tax_amount,
        tax_amount_currency,
        untaxed_amount,
        untaxed_amount_currency,
        sign,
        cash_rounding=None,
    ):
        self.check_singleton()
        company_currency = company.currency_id
        total_amount = tax_amount + untaxed_amount
        total_amount_currency = tax_amount_currency + untaxed_amount_currency
        rate = abs(total_amount_currency / total_amount) if total_amount else 0.0
        cash_rounded_pair = partial(
            self._get_cash_rounded_pair,
            cash_rounding=cash_rounding,
            currency=currency,
            company_currency=company_currency,
            rate=rate,
        )

        pay_term = {
            "total_amount": total_amount,
            "discount_percentage": self.discount_percentage
            if self.early_discount
            else 0.0,
            "discount_date": self._get_last_discount_date(date_ref),
            "discount_balance": 0,
            "discount_amount_currency": 0,
            "line_ids": [],
        }

        if self.early_discount:
            pay_term["discount_balance"] = self._get_amount_due_after_discount(
                total_amount, untaxed_amount, company_currency
            )
            pay_term["discount_amount_currency"] = self._get_amount_due_after_discount(
                total_amount_currency, untaxed_amount_currency, currency
            )

            pay_term["discount_amount_currency"], pay_term["discount_balance"] = (
                cash_rounded_pair(
                    pay_term["discount_amount_currency"],
                    pay_term["discount_balance"],
                )
            )

        residual_amount = total_amount
        residual_amount_currency = total_amount_currency

        for i, line in enumerate(self.line_ids):
            term_vals = {"date": line._get_due_date(date_ref)}

            if i == len(self.line_ids) - 1:
                term_vals["company_amount"] = residual_amount
                term_vals["foreign_amount"] = residual_amount_currency
            else:
                company_amount, foreign_amount = line._get_allocated_amounts(
                    currency=currency,
                    company_currency=company_currency,
                    rate=rate,
                    sign=sign,
                    total_amount=total_amount,
                    total_amount_currency=total_amount_currency,
                )
                term_vals["foreign_amount"], term_vals["company_amount"] = (
                    cash_rounded_pair(foreign_amount, company_amount)
                )

            residual_amount -= term_vals["company_amount"]
            residual_amount_currency -= term_vals["foreign_amount"]
            pay_term["line_ids"].append(term_vals)

        if _debug.logic.enabled:
            _debug.logic(
                "_get_terms",
                term=self,
                ref=date_ref,
                total=total_amount_currency,
                discount=pay_term["discount_percentage"],
                discount_date=pay_term["discount_date"],
                terms=[(t["date"], t["foreign_amount"]) for t in pay_term["line_ids"]],
            )
        return pay_term

    @api.ondelete(at_uninstall=False)
    @_debug.perf.timed
    def _unlink_except_referenced_terms(self):
        _debug.lifecycle("_unlink_except_referenced_terms", records=self)
        if self.env["account.move"].search_count(
            [("invoice_payment_term_id", "in", self.ids)], limit=1
        ):
            raise UserError(
                _(
                    "Uh-oh! Those payment terms are quite popular and can't be deleted since there are still some records referencing them. How about archiving them instead?"
                )
            )

    def _get_last_discount_date(self, date_ref):
        self.check_singleton()
        if not (self.early_discount and date_ref):
            return False
        return date_ref + relativedelta(days=self.discount_days)

    @_debug.perf.timed
    def copy_data(self, default=None):
        _debug.lifecycle("copy_data", records=self)
        default = dict(default or {})
        vals_list = super().copy_data(default=default)
        return [
            dict(vals, name=_("%s (copy)", term.name))
            for term, vals in zip(self, vals_list, strict=True)
        ]

    def copy_translations(self, new, excluded=()):
        super().copy_translations(new, excluded=(*excluded, "name"))
        self._copy_translations_of_renamed_field(
            new, "name", lambda record, term: record.env._("%s (copy)", term)
        )


class AccountPaymentTermLine(models.Model):
    _name = "account.payment.term.line"
    _description = "Payment Terms Line"
    _order = "sequence, id"

    sequence = fields.Integer(
        default=10,
        required=True,
    )
    value = fields.Selection(
        selection=[("percent", "Percent"), ("fixed", "Fixed")],
        default="percent",
        required=True,
        help="Select here the kind of valuation related to this payment terms line.",
    )
    value_amount = fields.Float(
        string="Due",
        digits="Payment Terms",
        compute="_compute_value_amount",
        store=True,
        readonly=False,
        help="For percent enter a ratio between 0-100.",
    )
    delay_type = fields.Selection(
        selection=[
            ("days_after", "Days after invoice date"),
            ("days_after_end_of_month", "Days after end of month"),
            ("days_after_end_of_next_month", "Days after end of next month"),
            ("days_end_of_month_on_the", "Days end of month on the"),
        ],
        default="days_after",
        required=True,
    )
    display_days_next_month = fields.Boolean(compute="_compute_display_days_next_month")
    days_next_month = fields.Integer(
        string="Days on the next month",
        default=10,
    )
    nb_days = fields.Integer(
        string="Days",
        compute="_compute_nb_days",
        store=True,
        readonly=False,
    )
    payment_id = fields.Many2one(
        comodel_name="account.payment.term",
        string="Payment Terms",
        index=True,
        required=True,
        ondelete="cascade",
    )

    def _get_allocated_amounts(
        self,
        *,
        currency,
        company_currency,
        rate,
        sign,
        total_amount,
        total_amount_currency,
    ):
        self.check_singleton()
        if self.value == "fixed":
            if not rate:
                return 0.0, 0.0
            return (
                sign * company_currency.round(self.value_amount / rate),
                sign * currency.round(self.value_amount),
            )
        return (
            company_currency.round(total_amount * (self.value_amount / 100.0)),
            currency.round(total_amount_currency * (self.value_amount / 100.0)),
        )

    def _get_due_date(self, date_ref):
        self.check_singleton()
        due_date = fields.Date.from_string(date_ref) or fields.Date.today()
        if self.delay_type == "days_after_end_of_month":
            return date_utils.end_of(due_date, "month") + relativedelta(
                days=self.nb_days
            )
        if self.delay_type == "days_after_end_of_next_month":
            return date_utils.end_of(
                due_date + relativedelta(months=1), "month"
            ) + relativedelta(days=self.nb_days)
        if self.delay_type == "days_end_of_month_on_the":
            if not self.days_next_month:
                return date_utils.end_of(
                    due_date + relativedelta(days=self.nb_days), "month"
                )
            return (
                due_date
                + relativedelta(days=self.nb_days)
                + relativedelta(months=1, day=self.days_next_month)
            )
        return due_date + relativedelta(days=self.nb_days)

    @api.constrains("days_next_month")
    @_debug.perf.timed
    def _check_days_next_month(self):
        for record in self:
            if not 0 <= record.days_next_month <= 31:
                raise ValidationError(_("The days added must be between 0 and 31."))

    @api.depends("delay_type")
    def _compute_display_days_next_month(self):
        for record in self:
            record.display_days_next_month = (
                record.delay_type == "days_end_of_month_on_the"
            )

    @api.constrains("value", "value_amount", "payment_id")
    @_debug.perf.timed
    def _check_percent(self):
        for term_line in self:
            if term_line.value == "percent" and not (
                0.0 <= term_line.value_amount <= 100.0
            ):
                raise ValidationError(
                    _(
                        "Percentages on the Payment Terms lines must be between 0 and 100."
                    )
                )
        self.payment_id._check_lines()

    @api.depends("payment_id")
    def _compute_nb_days(self):
        for line in self:
            siblings = line.payment_id.line_ids
            index = list(siblings).index(line) if line in siblings else 0
            line.nb_days = (
                siblings[index - 1].nb_days + 30
                if not line.nb_days and index
                else line.nb_days
            )

    @api.depends("payment_id", "value")
    def _compute_value_amount(self):
        for line in self:
            if line.value == "fixed":
                line.value_amount = 0
            else:
                allocated = sum(
                    other.value_amount
                    for other in line.payment_id.line_ids
                    if other.value == "percent" and other != line
                )
                line.value_amount = 100 - allocated
