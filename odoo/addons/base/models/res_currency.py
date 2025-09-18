import logging
import math
from collections.abc import Iterable
from typing import TYPE_CHECKING, Any, Self

from num2words import num2words

if TYPE_CHECKING:
    from lxml import etree

from odoo import api, fields, models, tools
from odoo.exceptions import UserError, ValidationError
from odoo.tools import SQL, ormcache, parse_date
from odoo.orm._typing import ValuesType

_logger = logging.getLogger(__name__)

# Maximum significant digits for currency float display (total digits in the
# ``digits`` tuple used by Float fields).  69 is the practical upper bound for
# IEEE 754 double precision — effectively "no upper limit on integer digits".
_CURRENCY_TOTAL_DIGITS = 69


class ResCurrency(models.Model):
    _name = "res.currency"
    _description = "Currency"
    _rec_names_search = ["name", "full_name"]
    _order = "active desc, name"

    # Note: 'code' column was removed as of v6.0, the 'name' should now hold the ISO code.
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
        help="Currency sign, to be used when printing amounts.", required=True
    )
    rate = fields.Float(
        compute="_compute_current_rate",
        string="Current Rate",
        digits=0,
        help="The rate of the currency to the currency of rate 1.",
    )
    inverse_rate = fields.Float(
        compute="_compute_current_rate",
        digits=0,
        readonly=True,
        help="The currency of rate 1 to the rate of the currency.",
    )
    rate_string = fields.Char(compute="_compute_current_rate")
    rate_ids = fields.One2many("res.currency.rate", "currency_id", string="Rates")
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
        [("after", "After Amount"), ("before", "Before Amount")],
        default="after",
        string="Symbol Position",
        help="Determines where the currency symbol should be placed after or before the amount.",
    )
    date = fields.Date(compute="_compute_date")
    currency_unit_label = fields.Char(string="Currency Unit", translate=True)
    currency_subunit_label = fields.Char(string="Currency Subunit", translate=True)
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
        self._toggle_group_multi_currency()
        # invalidate cache for get_all_currencies
        self.env.registry.clear_cache("stable")
        return res

    def unlink(self) -> bool:
        res = super().unlink()
        self._toggle_group_multi_currency()
        # invalidate cache for get_all_currencies
        self.env.registry.clear_cache("stable")
        return res

    def write(self, vals: dict[str, Any]) -> bool:
        res = super().write(vals)
        if vals.keys() & {"active", "name", "position", "symbol", "rounding"}:
            # invalidate cache for get_all_currencies
            self.env.registry.clear_cache("stable")
        if "active" not in vals:
            return res
        self._toggle_group_multi_currency()
        return res

    @api.model
    def _toggle_group_multi_currency(self) -> None:
        """
        Automatically activate group_multi_currency if there is more than 1 active currency; deactivate it otherwise
        """
        active_currency_count = self.search_count([("active", "=", True)])
        if active_currency_count > 1:
            self._activate_group_multi_currency()
        elif active_currency_count <= 1:
            self._deactivate_group_multi_currency()

    @api.model
    def _activate_group_multi_currency(self) -> None:
        group_user = self.env.ref("base.group_user", raise_if_not_found=False)
        group_mc = self.env.ref("base.group_multi_currency", raise_if_not_found=False)
        if group_user and group_mc:
            group_user.sudo()._apply_group(group_mc)

    @api.model
    def _deactivate_group_multi_currency(self) -> None:
        group_user = self.env.ref("base.group_user", raise_if_not_found=False)
        group_mc = self.env.ref("base.group_multi_currency", raise_if_not_found=False)
        if group_user and group_mc:
            group_user.sudo()._remove_group(group_mc.sudo())

    @api.constrains("active")
    def _check_company_currency_stays_active(self) -> None:
        if self.env.context.get("install_mode") or self.env.context.get(
            "force_deactivate"
        ):
            # install_mode : At install, when this check is run, the "active" field of a currency added to a company will
            #                still be evaluated as False, despite it's automatically set at True when added to the company.
            # force_deactivate : Allows deactivation of a currency in tests to enable non multi_currency behaviors
            return

        currencies = self.filtered(lambda c: not c.active)
        if self.env["res.company"].search_count(
            [("currency_id", "in", currencies.ids)], limit=1
        ):
            raise UserError(
                self.env._(
                    "This currency is set on a company and therefore cannot be deactivated."
                )
            )

    def _get_rates(self, company: Self, date: Any) -> dict[int, float]:
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

    @api.depends_context("company")
    def _compute_is_current_company_currency(self) -> None:
        company_currency = self.env.company.currency_id
        for currency in self:
            currency.is_current_company_currency = company_currency == currency

    @api.depends("rate_ids.rate")
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
        # the subquery selects the last rate before 'date' for the given currency/company
        currency_rates = (self + to_currency)._get_rates(company, date)
        to_rate = currency_rates.get(to_currency.id) or 1.0
        to_name = to_currency.name
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
        self.ensure_one()

        def _num2words(number, lang):
            try:
                return num2words(number, lang=lang).title()
            except NotImplementedError:
                return num2words(number, lang="en").title()

        integral, _sep, fractional = f"{amount:.{self.decimal_places}f}".partition(".")
        integer_value = int(integral)
        lang = tools.get_lang(self.env)
        integral_text = _num2words(integer_value, lang=lang.iso_code)
        # For amounts in (-1, 0), int("-0") == 0 silently loses the sign.
        # num2words also drops "minus" for such values, so prepend manually.
        if amount < 0 and integer_value == 0:
            integral_text = f"Minus {integral_text}"
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
        """Return ``amount`` formatted according to ``self``'s rounding rules, symbols and positions.

        Also take care of removing the minus sign when 0.0 is negative

        :param float amount: the amount to round
        :return: formatted str
        """
        self.ensure_one()
        return tools.format_amount(self.env, amount + 0.0, self)

    def round(self, amount: float) -> float:
        """Return ``amount`` rounded  according to ``self``'s rounding rules.

        :param float amount: the amount to round
        :return: rounded float
        """
        self.ensure_one()
        return tools.float_round(amount, precision_rounding=self.rounding)

    def compare_amounts(self, amount1: float, amount2: float) -> int:
        """Compare ``amount1`` and ``amount2`` after rounding them according to the
        given currency's precision..
        An amount is considered lower/greater than another amount if their rounded
        value is different. This is not the same as having a non-zero difference!

        For example 1.432 and 1.431 are equal at 2 digits precision,
        so this method would return 0.
        However 0.006 and 0.002 are considered different (returns 1) because
        they respectively round to 0.01 and 0.0, even though
        0.006-0.002 = 0.004 which would be considered zero at 2 digits precision.

        :param float amount1: first amount to compare
        :param float amount2: second amount to compare
        :return: (resp.) -1, 0 or 1, if ``amount1`` is (resp.) lower than,
                 equal to, or greater than ``amount2``, according to
                 ``currency``'s rounding.

        With the new API, call it like: ``currency.compare_amounts(amount1, amount2)``.
        """
        self.ensure_one()
        return tools.float_compare(amount1, amount2, precision_rounding=self.rounding)

    def is_zero(self, amount: float) -> bool:
        """Returns true if ``amount`` is small enough to be treated as
        zero according to current currency's rounding rules.
        Warning: ``is_zero(amount1-amount2)`` is not always equivalent to
        ``compare_amounts(amount1,amount2) == 0``, as the former will round after
        computing the difference, while the latter will round before, giving
        different results for e.g. 0.006 and 0.002 at 2 digits precision.

        :param float amount: amount to compare with currency's zero

        With the new API, call it like: ``currency.is_zero(amount)``.
        """
        self.ensure_one()
        return tools.float_is_zero(amount, precision_rounding=self.rounding)

    @ormcache(cache="stable")
    @api.model
    def get_all_currencies(self) -> dict[int, dict[str, Any]]:
        currencies = self.sudo().search_fetch(
            [("active", "=", True)],
            ["name", "symbol", "position", "decimal_places"],
        )
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
        return (
            from_currency.with_company(company)
            .with_context(to_currency=to_currency.id, date=str(date))
            .inverse_rate
        )

    def _convert(
        self,
        from_amount: float,
        to_currency: Self,
        company: Any = None,
        date: Any = None,
        round: bool = True,
    ) -> float:
        """Return ``from_amount`` converted from ``self`` to ``to_currency``.

        :param float from_amount: the amount to convert
        :param to_currency: target currency
        :param company: company used to look up the conversion rate
        :param date: date used to look up the conversion rate
        :param bool round: whether to round the result to ``to_currency``'s precision
        :return: converted amount
        :rtype: float
        """
        if from_amount is None:
            raise ValueError("_convert() requires a numeric amount, got None")
        self, to_currency = self or to_currency, to_currency or self
        if not self:
            raise UserError(
                self.env._("Cannot convert amount: source currency is not set.")
            )
        if not to_currency:
            raise UserError(
                self.env._("Cannot convert amount: target currency is not set.")
            )
        # Short-circuit on zero to avoid a needless rate lookup.
        if not from_amount:
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
    def _get_view_cache_key(
        self, view_id: int | None = None, view_type: str = "form", **options
    ) -> tuple:
        """The override of _get_view changing the rate field labels according to the company currency
        makes the view cache dependent on the company currency"""
        key = super()._get_view_cache_key(view_id, view_type, **options)
        return key + (
            (
                self.env["res.company"].browse(self.env.context.get("company_id"))
                or self.env.company
            ).currency_id.name,
        )

    @api.model
    def _get_view(
        self, view_id: int | None = None, view_type: str = "form", **options
    ) -> tuple[etree._Element, Any]:
        arch, view = super()._get_view(view_id, view_type, **options)
        if view_type in ("list", "form"):
            currency_name = (
                self.env["res.company"].browse(self.env.context.get("company_id"))
                or self.env.company
            ).currency_id.name
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
        return arch, view


class ResCurrencyRate(models.Model):
    _name = "res.currency.rate"
    _description = "Currency Rate"
    _rec_names_search = ["name", "rate"]
    _order = "name desc, id"
    _check_company_domain = models.check_company_domain_parent_of

    name = fields.Date(
        string="Date",
        required=True,
        index=True,
        default=fields.Date.context_today,
    )
    rate = fields.Float(
        digits=0,
        aggregator="avg",
        help="The rate of the currency to the currency of rate 1",
        string="Technical Rate",
    )
    company_rate = fields.Float(
        digits=0,
        compute="_compute_company_rate",
        inverse="_inverse_company_rate",
        aggregator="avg",
        help="The currency of rate 1 to the rate of the currency.",
    )
    inverse_company_rate = fields.Float(
        digits=0,
        compute="_compute_inverse_company_rate",
        inverse="_inverse_inverse_company_rate",
        aggregator="avg",
        help="The rate of the currency to the currency of rate 1 ",
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        readonly=True,
        required=True,
        index=True,
        ondelete="cascade",
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.company.root_id,
    )

    _unique_name_per_day = models.Constraint(
        "unique (name,currency_id,company_id)",
        "Only one currency rate per day allowed!",
    )
    _currency_rate_check = models.Constraint(
        "CHECK (rate>0)",
        "The currency rate must be strictly positive.",
    )

    def _sanitize_vals(self, vals: dict[str, Any]) -> dict[str, Any]:
        if "inverse_company_rate" in vals and (
            "company_rate" in vals or "rate" in vals
        ):
            del vals["inverse_company_rate"]
        if "company_rate" in vals and "rate" in vals:
            del vals["company_rate"]
        return vals

    def write(self, vals: dict[str, Any]) -> bool:
        self.env["res.currency"].invalidate_model(["inverse_rate"])
        return super().write(self._sanitize_vals(vals))

    @api.model_create_multi
    def create(self, vals_list: list[ValuesType]) -> Self:
        self.env["res.currency"].invalidate_model(["inverse_rate"])
        return super().create([self._sanitize_vals(vals) for vals in vals_list])

    def _get_latest_rate(self) -> Self:
        # Make sure 'name' is defined when creating a new rate.
        if not self.name:
            raise UserError(
                self.env._("The name for the current rate is empty.\nPlease set it.")
            )
        return (
            self.currency_id.rate_ids.sudo()
            .filtered(
                lambda x: (
                    x.rate
                    and x.company_id == (self.company_id or self.env.company.root_id)
                    and x.name < (self.name or fields.Date.today())
                )
            )
            .sorted("name")[-1:]
        )

    def _get_last_rates_for_companies(self, companies: Any) -> dict:
        return {
            company: company.sudo()
            .currency_id.rate_ids.filtered(
                lambda x, company=company: (x.rate and x.company_id == company)
                or not x.company_id
            )
            .sorted("name")[-1:]
            .rate
            or 1
            for company in companies
        }

    @api.depends("currency_id", "company_id", "name")
    def _compute_rate(self) -> None:
        for currency_rate in self:
            currency_rate.rate = (
                currency_rate.rate or currency_rate._get_latest_rate().rate or 1.0
            )

    @api.depends(
        "rate", "name", "currency_id", "company_id", "currency_id.rate_ids.rate"
    )
    @api.depends_context("company")
    def _compute_company_rate(self) -> None:
        env_company_root = self.env.company.root_id
        last_rate = self.env["res.currency.rate"]._get_last_rates_for_companies(
            self.company_id | env_company_root
        )
        for currency_rate in self:
            company = currency_rate.company_id or env_company_root
            currency_rate.company_rate = (
                currency_rate.rate or currency_rate._get_latest_rate().rate or 1.0
            ) / last_rate[company]

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
            if not currency_rate.company_rate:
                currency_rate.company_rate = 1.0
            currency_rate.inverse_company_rate = 1.0 / currency_rate.company_rate

    @api.onchange("inverse_company_rate")
    def _inverse_inverse_company_rate(self) -> None:
        for currency_rate in self:
            if not currency_rate.inverse_company_rate:
                currency_rate.inverse_company_rate = 1.0
            currency_rate.company_rate = 1.0 / currency_rate.inverse_company_rate

    @api.onchange("company_rate")
    def _onchange_rate_warning(self) -> dict[str, Any] | None:
        latest_rate = self._get_latest_rate()
        if latest_rate:
            diff = (latest_rate.rate - self.rate) / latest_rate.rate
            if abs(diff) > 0.2:
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
        return super()._search_display_name(operator, value)

    @api.model
    def _get_view_cache_key(
        self, view_id: int | None = None, view_type: str = "form", **options
    ) -> tuple:
        """The override of _get_view changing the rate field labels according to the company currency
        makes the view cache dependent on the company currency"""
        key = super()._get_view_cache_key(view_id, view_type, **options)
        return key + (
            (
                self.env["res.company"].browse(self.env.context.get("company_id"))
                or self.env.company
            ).currency_id.name,
        )

    @api.model
    def _get_view(
        self, view_id: int | None = None, view_type: str = "form", **options
    ) -> tuple[etree._Element, Any]:
        arch, view = super()._get_view(view_id, view_type, **options)
        if view_type == "list":
            names = {
                "company_currency_name": (
                    self.env["res.company"].browse(self.env.context.get("company_id"))
                    or self.env.company
                ).currency_id.name,
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
        return arch, view
