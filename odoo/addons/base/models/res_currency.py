import logging
import math
from bisect import bisect_left, bisect_right
from collections.abc import Iterable
from typing import TYPE_CHECKING, Any, Self

from num2words import num2words

if TYPE_CHECKING:
    from lxml import etree

from odoo import api, fields, models, tools
from odoo.api import ValuesType
from odoo.exceptions import UserError, ValidationError
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL, TransactionMemo, ormcache, parse_date

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)

_CURRENCY_TOTAL_DIGITS = 69

RATE_HISTORY = TransactionMemo(
    "res_currency_rate_history", invalidated_by=("res.currency.rate",)
)


class ResCurrency(models.Model):
    _name = "res.currency"
    _description = "Currency"
    _rec_names_search = ["name", "full_name"]
    _order = "active desc, name"

    name = fields.Char(
        string="Currency",
        size=3,
        required=True,
        help="Currency Code (ISO 4217)",
    )
    iso_numeric = fields.Integer(
        string="Currency numeric code.",
        help="Currency Numeric Code (ISO 4217).",
    )
    full_name = fields.Char(string="Name")
    symbol = fields.Char(
        required=True,
        help="Currency sign, to be used when printing amounts.",
    )
    rate = fields.Float(
        string="Current Rate",
        digits=0,
        compute="_compute_current_rate",
        help="The rate of the currency to the currency of rate 1.",
    )
    inverse_rate = fields.Float(
        digits=0,
        compute="_compute_current_rate",
        readonly=True,
        help="The currency of rate 1 to the rate of the currency.",
    )
    rate_string = fields.Char(compute="_compute_current_rate")
    rate_ids = fields.One2many(
        comodel_name="res.currency.rate",
        inverse_name="currency_id",
        string="Rates",
    )
    rounding = fields.Float(
        string="Rounding Factor",
        digits=(12, 6),
        default=0.01,
        help="Amounts in this currency are rounded off to the nearest multiple of the rounding factor.",
    )
    decimal_places = fields.Integer(
        compute="_compute_decimal_places",
        store=True,
        help="Decimal places taken into account for operations on amounts in this currency. It is determined by the rounding factor.",
    )
    active = fields.Boolean(default=True)
    position = fields.Selection(
        selection=[("after", "After Amount"), ("before", "Before Amount")],
        string="Symbol Position",
        default="after",
        help="Determines where the currency symbol should be placed after or before the amount.",
    )
    date = fields.Date(compute="_compute_date")
    currency_unit_label = fields.Char(
        string="Currency Unit",
        translate=True,
    )
    currency_subunit_label = fields.Char(
        string="Currency Subunit",
        translate=True,
    )
    is_current_company_currency = fields.Boolean(
        compute="_compute_is_current_company_currency"
    )

    _unique_name = models.Constraint(
        "unique (name)",
        "The currency code must be unique!",
    )
    _rounding_gt_zero = models.Constraint(
        "CHECK (rounding>0)",
        "The rounding factor must be greater than 0!",
    )

    @api.model_create_multi
    def create(self, vals_list: list[ValuesType]) -> Self:
        res = super().create(vals_list)
        _debug.lifecycle("create", count=len(res), names=res.mapped("name"))
        self._toggle_group_multi_currency()
        self.env.registry.clear_cache("stable")
        return res

    def unlink(self) -> bool:
        _debug.lifecycle("unlink", count=len(self), names=self.mapped("name"))
        res = super().unlink()
        self._toggle_group_multi_currency()
        self.env.registry.clear_cache("stable")
        return res

    def write(self, vals: dict[str, Any]) -> bool:
        _debug.lifecycle("write", count=len(self), fields=list(vals))
        res = super().write(vals)
        if vals.keys() & {"active", "name", "position", "symbol", "rounding"}:
            _debug.lifecycle("stable_cache_cleared", by="write", count=len(self))
            self.env.registry.clear_cache("stable")
        if "active" not in vals:
            return res
        self._toggle_group_multi_currency()
        return res

    @api.model
    def _toggle_group_multi_currency(self) -> None:
        active_currency_count = self.search_count([("active", "=", True)])
        _debug.logic("multi_currency_group", active_currencies=active_currency_count)
        if active_currency_count > 1:
            self._activate_group_multi_currency()
        else:
            self._deactivate_group_multi_currency()

    @api.model
    def _activate_group_multi_currency(self) -> None:
        group_user = self.env.ref("base.group_user", raise_if_not_found=False)
        group_mc = self.env.ref("base.group_multi_currency", raise_if_not_found=False)
        _debug.lifecycle(
            "multi_currency_group_toggled",
            enabled=True,
            applied=bool(group_user and group_mc),
        )
        if group_user and group_mc:
            group_user.sudo()._add_implied_group(group_mc)

    @api.model
    def _deactivate_group_multi_currency(self) -> None:
        group_user = self.env.ref("base.group_user", raise_if_not_found=False)
        group_mc = self.env.ref("base.group_multi_currency", raise_if_not_found=False)
        _debug.lifecycle(
            "multi_currency_group_toggled",
            enabled=False,
            applied=bool(group_user and group_mc),
        )
        if group_user and group_mc:
            group_user.sudo()._remove_group(group_mc.sudo())

    @api.constrains("active")
    def _check_company_currency_stays_active(self) -> None:
        if self.env.context.get("install_mode") or self.env.context.get(
            "force_deactivate"
        ):
            _debug.logic(
                "deactivation_check_skipped",
                currencies=self.ids,
                reason="install_or_forced",
            )
            return

        currencies = self.filtered(lambda c: not c.active)
        if self.env["res.company"].search_count(
            [("currency_id", "in", currencies.ids)], limit=1
        ):
            _debug.logic("deactivation_refused", currencies=currencies.mapped("name"))
            raise UserError(
                self.env._(
                    "This currency is set on a company and therefore cannot be deactivated."
                )
            )

    def _get_rates(self, company: Self, date: Any) -> dict[int, float]:
        if not self.ids:
            return {}
        rates = self._get_rates_from_memo(company, date)
        if rates is not None:
            _debug.perf.count("rates_via_memo", currencies=len(self), date=date)
            return rates
        _debug.logic("rates_via_sql", currencies=self.ids, date=date)
        return self._get_rates_sql(company, date)

    def _get_rates_sql(self, company: Self, date: Any) -> dict[int, float]:
        if not self.ids:
            return {}
        currency_query = self._as_query(ordered=False)
        currency_id = self.env["res.currency"]._field_to_sql(currency_query.table, "id")
        Rate = self.env["res.currency.rate"]
        rate_query = Rate._search(
            [
                ("name", "<=", date),
                ("company_id", "in", (False, company.root_id.id)),
            ],
            order="company_id.id, name DESC",
            limit=1,
        )
        rate_query.add_where(
            SQL(
                "%s = %s",
                Rate._field_to_sql(rate_query.table, "currency_id"),
                currency_id,
            )
        )
        rate_fallback = Rate._search(
            [
                ("company_id", "in", (False, company.root_id.id)),
            ],
            order="company_id.id, name ASC",
            limit=1,
        )
        rate_fallback.add_where(
            SQL(
                "%s = %s",
                Rate._field_to_sql(rate_fallback.table, "currency_id"),
                currency_id,
            )
        )
        rate = Rate._field_to_sql(rate_query.table, "rate")
        with _debug.perf(
            "rates_sql", cr=self.env.cr, currencies=len(self), company=company.id
        ):
            return dict(
                self.env.execute_query(
                    currency_query.select(
                        currency_id,
                        SQL(
                            "COALESCE((%s), (%s), 1.0)",
                            rate_query.select(rate),
                            rate_fallback.select(rate),
                        ),
                    )
                )
            )

    def _get_rate_history_scope(self) -> tuple:
        return (self.env.su, self.env.uid, tuple(sorted(self.env.companies.ids)))

    def _get_rates_from_memo(self, company: Self, date: Any) -> dict[int, float] | None:
        try:
            date = fields.Date.to_date(date)
        except ValueError, TypeError:
            _debug.logic("rate_memo_bypassed", reason="unparseable_date")
            return None
        if not date:
            _debug.logic("rate_memo_bypassed", reason="no_date")
            return None
        root_id = company.root_id.id
        scope = self._get_rate_history_scope()
        memo = RATE_HISTORY(self.env)
        missing = {
            currency_id
            for currency_id in self.ids
            if (currency_id, root_id, scope) not in memo
        }
        if missing:
            histories = {currency_id: (([], []), ([], [])) for currency_id in missing}
            rates = self.env["res.currency.rate"].search_fetch(
                [
                    ("currency_id", "in", tuple(missing)),
                    ("company_id", "in", (False, root_id)),
                ],
                ["currency_id", "company_id", "name", "rate"],
                order="name, id",
            )
            for rate in rates:
                specific, global_ = histories[rate.currency_id.id]
                dates, values = specific if rate.company_id else global_
                dates.append(rate.name)
                values.append(rate.rate or None)
            for currency_id, history in histories.items():
                memo[currency_id, root_id, scope] = history
            _debug.perf.count(
                "rate_history_loaded",
                currencies=sorted(missing),
                company=root_id,
                rates=len(rates),
            )
        return {
            currency_id: self._get_rate_from_history(
                memo[currency_id, root_id, scope], date
            )
            for currency_id in self.ids
        }

    @staticmethod
    def _get_rate_from_history(history: tuple, date: Any) -> float:
        (specific_dates, specific_values), (global_dates, global_values) = history
        value = None
        if index := bisect_right(specific_dates, date):
            value = specific_values[index - 1]
        elif index := bisect_right(global_dates, date):
            value = global_values[index - 1]
        if value is None:
            if specific_values:
                value = specific_values[0]
            elif global_values:
                value = global_values[0]
        return 1.0 if value is None else value

    @api.depends_context("company")
    def _compute_is_current_company_currency(self) -> None:
        company_currency = self.env.company.currency_id
        for currency in self:
            currency.is_current_company_currency = company_currency == currency

    @api.depends("name", "rate_ids.rate", "rate_ids.name", "rate_ids.company_id")
    @api.depends_context("to_currency", "date", "company", "company_id")
    def _compute_current_rate(self) -> None:
        date = self.env.context.get("date") or fields.Date.context_today(self)
        company = (
            self.env["res.company"].browse(self.env.context.get("company_id"))
            or self.env.company
        )
        company_currency = company.currency_id
        to_currency = (
            self.browse(self.env.context.get("to_currency")) or company_currency
        )
        currency_rates = (self + to_currency)._get_rates(company, date)
        to_rate = currency_rates.get(to_currency.id) or 1.0
        to_name = to_currency.name
        _debug.pipeline(
            "current_rate_computed",
            currencies=len(self),
            to_currency=to_currency.id,
            company=company.id,
            date=str(date),
            rates=len(currency_rates),
        )
        for currency in self:
            rate = (currency_rates.get(currency.id) or 1.0) / to_rate
            currency.rate = rate
            currency.inverse_rate = 1 / rate if rate else 0.0
            if currency != company_currency:
                currency.rate_string = f"1 {to_name} = {rate:.6f} {currency.name}"
            else:
                currency.rate_string = ""

    @api.depends("rounding")
    def _compute_decimal_places(self) -> None:
        for currency in self:
            if 0 < currency.rounding < 1:
                currency.decimal_places = math.ceil(math.log10(1 / currency.rounding))
            else:
                currency.decimal_places = 0

    @api.depends("rate_ids.name")
    def _compute_date(self) -> None:
        for currency in self:
            currency.date = currency.rate_ids[:1].name

    def amount_to_text(self, amount: float) -> str:
        self.check_singleton()

        def _num2words(number, lang):
            try:
                return num2words(number, lang=lang).title()
            except NotImplementedError:
                _logger.warning(
                    "The library 'num2words' does not support language %r; "
                    "falling back to English words.",
                    lang,
                )
                return num2words(number, lang="en").title()

        integral, _sep, fractional = f"{amount:.{self.decimal_places}f}".partition(".")
        integer_value = int(integral)
        lang = tools.get_lang(self.env)
        _debug.logic(
            "amount_to_text",
            currency=self.name,
            lang=lang.iso_code,
            negative=amount < 0,
            has_fraction=not self.is_zero(amount - integer_value),
        )
        integral_text = _num2words(integer_value, lang=lang.iso_code)
        if amount < 0 and integer_value == 0:
            integral_text = self.env._("Minus %s", integral_text)
        if self.is_zero(amount - integer_value):
            return self.env._(
                "%(integral_amount)s %(currency_unit)s",
                integral_amount=integral_text,
                currency_unit=self.currency_unit_label,
            )
        else:
            return self.env._(
                "%(integral_amount)s %(currency_unit)s and %(fractional_amount)s %(currency_subunit)s",
                integral_amount=integral_text,
                currency_unit=self.currency_unit_label,
                fractional_amount=_num2words(int(fractional or 0), lang=lang.iso_code),
                currency_subunit=self.currency_subunit_label,
            )

    def format(self, amount: float) -> str:
        self.check_singleton()
        return tools.format_amount(self.env, amount + 0.0, self)

    def round(self, amount: float) -> float:
        self.check_singleton()
        return tools.float_round(amount, precision_rounding=self.rounding)

    def compare_amounts(self, amount1: float, amount2: float) -> int:
        self.check_singleton()
        return tools.float_compare(amount1, amount2, precision_rounding=self.rounding)

    def is_zero(self, amount: float) -> bool:
        self.check_singleton()
        return tools.float_is_zero(amount, precision_rounding=self.rounding)

    @ormcache(cache="stable")
    @api.model
    def get_all_currencies(self) -> dict[int, dict[str, Any]]:
        currencies = self.sudo().search_fetch(
            [("active", "=", True)],
            ["name", "symbol", "position", "decimal_places"],
        )
        _debug.perf.count("all_currencies_computed", currencies=len(currencies))
        return {
            c.id: {
                "name": c.name,
                "symbol": c.symbol,
                "position": c.position,
                "digits": [_CURRENCY_TOTAL_DIGITS, c.decimal_places],
            }
            for c in currencies
        }

    @api.model
    def _get_conversion_rate(
        self,
        from_currency: Self,
        to_currency: Self,
        company: Any = None,
        date: Any = None,
    ) -> float:
        if from_currency == to_currency:
            return 1
        company = company or self.env.company
        date = date or fields.Date.context_today(self)
        rate = (
            from_currency.with_company(company)
            .with_context(to_currency=to_currency.id, date=str(date))
            .inverse_rate
        )
        _debug.logic(
            "conversion_rate",
            from_currency=from_currency.id,
            to_currency=to_currency.id,
            company=company.id,
            date=str(date),
            rate=rate,
        )
        return rate

    def _convert(
        self,
        from_amount: float,
        to_currency: Self,
        company: Any = None,
        date: Any = None,
        round: bool = True,
    ) -> float:
        if from_amount is None:
            msg = "_convert() requires a numeric amount, got None"
            raise ValueError(msg)
        self, to_currency = self or to_currency, to_currency or self
        if not self:
            _debug.logic("convert_refused", reason="no_source_currency")
            raise UserError(
                self.env._("Cannot convert amount: source currency is not set.")
            )
        if not to_currency:
            _debug.logic("convert_refused", reason="no_target_currency")
            raise UserError(
                self.env._("Cannot convert amount: target currency is not set.")
            )
        self.check_singleton()
        to_currency.check_singleton()
        if not from_amount:
            _debug.logic("convert_shortcut", reason="zero_amount")
            return 0.0
        to_amount = from_amount * self._get_conversion_rate(
            self, to_currency, company, date
        )
        return to_currency.round(to_amount) if round else to_amount

    def _select_companies_rates(self) -> str:
        return """
            SELECT
                r.currency_id,
                COALESCE(r.company_id, c.id) as company_id,
                r.rate,
                r.name AS date_start,
                (SELECT name FROM res_currency_rate r2
                 WHERE r2.name > r.name AND
                       r2.currency_id = r.currency_id AND
                       (r2.company_id is null or r2.company_id = c.id)
                 ORDER BY r2.name ASC
                 LIMIT 1) AS date_end
            FROM res_currency_rate r
            JOIN res_company c ON (r.company_id is null or r.company_id = c.id)
        """

    @api.model
    def _get_context_company_currency_name(self) -> str:
        return (
            self.env["res.company"].browse(self.env.context.get("company_id"))
            or self.env.company
        ).currency_id.name

    @api.model
    def _get_view_cache_key(
        self, view_id: int | None = None, view_type: str = "form", **options
    ) -> tuple:
        key = super()._get_view_cache_key(view_id, view_type, **options)
        return key + (self._get_context_company_currency_name(),)

    @api.model
    def _get_view(
        self, view_id: int | None = None, view_type: str = "form", **options
    ) -> tuple[etree._Element, Any]:
        arch, view = super()._get_view(view_id, view_type, **options)
        if view_type in ("list", "form"):
            currency_name = self._get_context_company_currency_name()
            fields_maps = [
                [
                    ["company_rate", "rate"],
                    self.env._("Unit per %s", currency_name),
                ],
                [
                    ["inverse_company_rate", "inverse_rate"],
                    self.env._("%s per Unit", currency_name),
                ],
            ]
            for fnames, label in fields_maps:
                xpath_expression = (
                    "//list//field["
                    + " or ".join(f"@name='{f}'" for f in fnames)
                    + "][1]"
                )
                node = arch.xpath(xpath_expression)
                if node:
                    node[0].set("string", label)
            _debug.logic(
                "rate_labels_applied", view_type=view_type, currency=currency_name
            )
        return arch, view


class ResCurrencyRate(models.Model):
    _name = "res.currency.rate"
    _description = "Currency Rate"
    _rec_names_search = ["name", "rate"]
    _order = "name desc, id"
    _check_company_domain = models.check_company_domain_parent_of

    name = fields.Date(
        string="Date",
        default=fields.Date.context_today,
        index=True,
        required=True,
    )
    rate = fields.Float(
        string="Technical Rate",
        digits=0,
        aggregator="avg",
        help="The rate of the currency to the currency of rate 1",
    )
    company_rate = fields.Float(
        digits=0,
        compute="_compute_company_rate",
        inverse="_inverse_company_rate",
        aggregator="avg",
        help="The rate of the currency to the currency of rate 1",
    )
    inverse_company_rate = fields.Float(
        digits=0,
        compute="_compute_inverse_company_rate",
        inverse="_inverse_inverse_company_rate",
        aggregator="avg",
        help="The currency of rate 1 to the rate of the currency.",
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        index=True,
        readonly=True,
        required=True,
        ondelete="cascade",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company.root_id,
    )

    _unique_name_per_day = models.UniqueIndex(
        "(name, currency_id, company_id) WHERE company_id IS NOT NULL",
        "Only one currency rate per day allowed!",
    )
    _currency_rate_check = models.Constraint(
        "CHECK (rate>0)",
        "The currency rate must be strictly positive.",
    )

    def _normalize_vals(self, vals: dict[str, Any]) -> dict[str, Any]:
        drop = set()
        if "inverse_company_rate" in vals and (
            "company_rate" in vals or "rate" in vals
        ):
            drop.add("inverse_company_rate")
        if "company_rate" in vals and "rate" in vals:
            drop.add("company_rate")
        if drop:
            _debug.logic("rate_vals_dropped", fields=sorted(drop))
            return {name: value for name, value in vals.items() if name not in drop}
        return vals

    def write(self, vals: dict[str, Any]) -> bool:
        self.env["res.currency"].invalidate_model(
            ["rate", "inverse_rate", "rate_string"]
        )
        res = super().write(self._normalize_vals(vals))
        _debug.lifecycle("rate_write", count=len(self), fields=list(vals))
        return res

    @api.model_create_multi
    def create(self, vals_list: list[ValuesType]) -> Self:
        self.env["res.currency"].invalidate_model(
            ["rate", "inverse_rate", "rate_string"]
        )
        records = super().create([self._normalize_vals(vals) for vals in vals_list])
        _debug.lifecycle("rate_create", count=len(records))
        return records

    def unlink(self) -> bool:
        self.env["res.currency"].invalidate_model(
            ["rate", "inverse_rate", "rate_string"]
        )
        res = super().unlink()
        _debug.lifecycle("rate_unlink", count=len(self))
        return res

    def _get_latest_rate(self) -> Self:
        if not self.name:
            _debug.logic("latest_rate_refused", rate=self.id, reason="no_date")
            raise UserError(
                self.env._("The name for the current rate is empty.\nPlease set it.")
            )
        company = self.company_id or self.env.company.root_id
        for rate in self.currency_id.rate_ids.sudo():
            if rate.rate and rate.company_id == company and rate.name < self.name:
                return rate
        _debug.logic(
            "latest_rate_missing",
            currency=self.currency_id.id,
            company=company.id,
            before=str(self.name),
        )
        return self.browse()

    def _get_last_rates_for_companies(self, companies: Any) -> dict:
        result = {}
        for company in companies:
            last = max(
                (
                    rate
                    for rate in company.sudo().currency_id.rate_ids
                    if (rate.rate and rate.company_id == company) or not rate.company_id
                ),
                key=lambda rate: (rate.name, rate.id),
                default=None,
            )
            result[company] = (last.rate if last else 0) or 1
        _debug.perf.count("last_rates_for_companies", companies=len(result))
        return result

    @api.depends(
        "rate", "name", "currency_id", "company_id", "currency_id.rate_ids.rate"
    )
    @api.depends_context("company")
    def _compute_company_rate(self) -> None:
        env_company_root = self.env.company.root_id
        last_rate = self.env["res.currency.rate"]._get_last_rates_for_companies(
            self.company_id | env_company_root
        )
        rates_per_key = {}
        derived = 0  # debuglog
        for currency_rate in self:
            company = currency_rate.company_id or env_company_root
            rate = currency_rate.rate
            if not rate:
                derived += 1  # debuglog
                if not currency_rate.name:
                    _debug.logic(
                        "company_rate_refused", rate=currency_rate.id, reason="no_date"
                    )
                    raise UserError(
                        self.env._(
                            "The name for the current rate is empty.\nPlease set it."
                        )
                    )
                key = (currency_rate.currency_id, company)
                candidates = rates_per_key.get(key)
                if candidates is None:
                    candidates = rates_per_key[key] = [
                        (rate_sudo.name, rate_sudo.rate)
                        for rate_sudo in currency_rate.currency_id.rate_ids.sudo()
                        if rate_sudo.rate and rate_sudo.company_id == company
                    ]
                    candidates.reverse()
                index = bisect_left(candidates, (currency_rate.name,)) - 1
                rate = candidates[index][1] if index >= 0 else 1.0
            currency_rate.company_rate = rate / last_rate[company]
        _debug.perf.count(
            "company_rates_computed",
            rates=len(self),
            derived=derived,
            keys=len(rates_per_key),
        )

    @api.onchange("company_rate")
    def _inverse_company_rate(self) -> None:
        env_company_root = self.env.company.root_id
        last_rate = self.env["res.currency.rate"]._get_last_rates_for_companies(
            self.company_id | env_company_root
        )
        for currency_rate in self:
            company = currency_rate.company_id or env_company_root
            currency_rate.rate = currency_rate.company_rate * last_rate[company]

    @api.depends("company_rate")
    def _compute_inverse_company_rate(self) -> None:
        for currency_rate in self:
            company_rate = currency_rate.company_rate or 1.0
            currency_rate.inverse_company_rate = 1.0 / company_rate

    @api.onchange("inverse_company_rate")
    def _inverse_inverse_company_rate(self) -> None:
        for currency_rate in self:
            if not currency_rate.inverse_company_rate:
                currency_rate.inverse_company_rate = 1.0
            currency_rate.company_rate = 1.0 / currency_rate.inverse_company_rate

    @api.onchange("company_rate")
    def _onchange_company_rate(self) -> dict[str, Any] | None:
        latest_rate = self._get_latest_rate()
        if latest_rate:
            diff = (latest_rate.rate - self.rate) / latest_rate.rate
            if abs(diff) > 0.2:
                _debug.logic(
                    "rate_jump_warned",
                    currency=self.currency_id.id,
                    previous=latest_rate.rate,
                    diff=diff,
                )
                return {
                    "warning": {
                        "title": self.env._("Warning for %s", self.currency_id.name),
                        "message": self.env._(
                            "The new rate is quite far from the previous rate.\n"
                            "Incorrect currency rates may cause critical problems, make sure the rate is correct!"
                        ),
                    }
                }
        return None

    @api.constrains("company_id")
    def _check_company_id(self) -> None:
        for rate in self:
            if rate.company_id.sudo().parent_id:
                _debug.logic(
                    "rate_on_branch_refused", rate=rate.id, company=rate.company_id.id
                )
                raise ValidationError(
                    self.env._(
                        "Currency rates should only be created for main companies"
                    )
                )

    @api.model
    def _search_display_name(self, operator: str, value: Any) -> list:
        if isinstance(value, Iterable) and not isinstance(value, str):
            value = [parse_date(self.env, v) for v in value]
        else:
            value = parse_date(self.env, value)
        _debug.logic("rate_display_name_search", operator=operator, by="parsed_date")
        return super()._search_display_name(operator, value)

    @api.model
    def _get_view_cache_key(
        self, view_id: int | None = None, view_type: str = "form", **options
    ) -> tuple:
        key = super()._get_view_cache_key(view_id, view_type, **options)
        return key + (self.env["res.currency"]._get_context_company_currency_name(),)

    @api.model
    def _get_view(
        self, view_id: int | None = None, view_type: str = "form", **options
    ) -> tuple[etree._Element, Any]:
        arch, view = super()._get_view(view_id, view_type, **options)
        if view_type == "list":
            names = {
                "company_currency_name": self.env[
                    "res.currency"
                ]._get_context_company_currency_name(),
                "rate_currency_name": self.env["res.currency"]
                .browse(self.env.context.get("active_id"))
                .name
                or "Unit",
            }
            for name, label in [
                [
                    "company_rate",
                    self.env._(
                        "%(rate_currency_name)s per %(company_currency_name)s",
                        **names,
                    ),
                ],
                [
                    "inverse_company_rate",
                    self.env._(
                        "%(company_currency_name)s per %(rate_currency_name)s",
                        **names,
                    ),
                ],
            ]:
                if (node := arch.find(f"./field[@name='{name}']")) is not None:
                    node.set("string", label)
            _debug.logic(
                "rate_list_labels_applied",
                company_currency=names["company_currency_name"],
                rate_currency=names["rate_currency_name"],
            )
        return arch, view
