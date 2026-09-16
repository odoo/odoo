from dataclasses import dataclass

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL, date_utils

_debug = DebugLog(__name__)

CURRENCY_TABLE_COLUMNS = (
    "company_id",
    "period_key",
    "date_from",
    "date_next",
    "rate_type",
    "rate",
)

SIMPLE_RATE_TYPES = ("current",)
CTA_RATE_TYPES = ("current", "historical", "average")


@dataclass(frozen=True, slots=True)
class CurrencyTableScope:
    main_company_id: int
    other_company_ids: tuple


class ResCurrency(models.Model):
    _name = "res.currency"
    _inherit = ["res.currency", "mixin.fiscal.country.codes"]

    display_rounding_warning = fields.Boolean(
        compute="_compute_display_rounding_warning",
        help="The warning informs a rounding factor change might be dangerous on res.currency's form view.",
    )

    @api.depends("rounding")
    def _compute_display_rounding_warning(self):
        for record in self:
            record.display_rounding_warning = bool(record._origin) and (
                record._origin.rounding != record.rounding
            )

    @_debug.perf.timed
    def write(self, vals):
        _debug.lifecycle("write", records=self, fields=sorted(vals))
        if "rounding" in vals:
            new_decimal_places = self._decimal_places_for_rounding(vals["rounding"])
            for record in self:
                if (
                    new_decimal_places < record.decimal_places
                    and record._has_accounting_entries()
                ):
                    _debug.logic(
                        "rounding_reduction_rejected",
                        currency=record,
                        decimal_places=new_decimal_places,
                    )
                    raise UserError(
                        _(
                            "You cannot reduce the number of decimal places of a currency which has already been used to make accounting entries."
                        )
                    )

        return super().write(vals)

    def _decimal_places_for_rounding(self, rounding):
        return self.new({"rounding": rounding}).decimal_places

    def _has_accounting_entries(self):
        self.check_singleton()
        return bool(
            self.env["account.move.line"]
            .sudo()
            .search_count(
                [
                    "|",
                    ("currency_id", "=", self.id),
                    ("company_currency_id", "=", self.id),
                ],
                limit=1,
            )
        )

    def _get_simple_currency_table(self, companies) -> SQL:
        if self._is_currency_table_monocurrency(companies):
            return self._get_monocurrency_currency_table_sql(companies)

        self._create_currency_table(
            companies, [("period", None, fields.Date.context_today(self))]
        )
        return SQL("account_currency_table")

    @_debug.perf.timed
    def _is_currency_table_monocurrency(self, companies):
        return len(companies.currency_id) == 1

    def _currency_table_rate_types(self, use_cta_rates):
        return CTA_RATE_TYPES if use_cta_rates else SIMPLE_RATE_TYPES

    def _currency_table_unit_rows(self, companies, use_cta_rates) -> list[SQL]:
        return [
            SQL(
                "(%(company_id)s, CAST(NULL AS VARCHAR), CAST(NULL AS DATE), CAST(NULL AS DATE), %(rate_type)s, 1)",
                company_id=company.id,
                rate_type=rate_type,
            )
            for company in companies
            for rate_type in self._currency_table_rate_types(use_cta_rates)
        ]

    def _get_monocurrency_currency_table_sql(self, companies, use_cta_rates=False):
        return SQL(
            "(VALUES %(rows)s) AS account_currency_table(%(columns)s)",
            rows=SQL(", ").join(
                self._currency_table_unit_rows(companies, use_cta_rates)
            ),
            columns=SQL(", ").join(
                SQL.identifier(col) for col in CURRENCY_TABLE_COLUMNS
            ),
        )

    @_debug.perf.timed
    def _create_currency_table(self, companies, date_periods, use_cta_rates=False):
        main_company = self.env.company
        domestic_currency_companies = companies.filtered(
            lambda x: x.currency_id == main_company.currency_id
        )
        other_companies = companies - domestic_currency_companies

        table_builders = []
        if domestic_currency_companies:
            table_builders.append(
                self._get_table_builder_domestic_currency(
                    domestic_currency_companies, use_cta_rates
                )
            )

        if other_companies:
            scope = CurrencyTableScope(
                main_company_id=main_company.root_id.id,
                other_company_ids=tuple(other_companies.ids),
            )
            last_date_to = None
            for period_key, date_from, date_to in date_periods:
                main_company_unit_factor = main_company.currency_id._get_rates(
                    main_company, date_to
                )[main_company.currency_id.id]

                table_builders.append(
                    self._get_table_builder_current(
                        scope, period_key, date_to, main_company_unit_factor
                    )
                )

                if use_cta_rates:
                    table_builders += [
                        self._get_table_builder_historical(
                            scope, date_to, main_company_unit_factor, last_date_to
                        ),
                        self._get_table_builder_average(
                            scope,
                            period_key,
                            date_from,
                            date_to,
                            main_company_unit_factor,
                        ),
                    ]

                last_date_to = date_to

        currency_table_build_query = SQL(" UNION ALL ").join(
            SQL("(%s)", builder) for builder in table_builders
        )
        cr = self.env.cr
        cr.execute(SQL("DROP TABLE IF EXISTS account_currency_table"))
        cr.execute(
            SQL(
                """CREATE TEMPORARY TABLE
                account_currency_table (%(columns)s)
                ON COMMIT DROP
                AS (%(query)s)""",
                columns=SQL(", ").join(
                    SQL.identifier(col) for col in CURRENCY_TABLE_COLUMNS
                ),
                query=currency_table_build_query,
            )
        )
        _debug.perf.count("currency_table_rows_inserted", rows=cr.rowcount)
        cr.execute(
            SQL(
                "CREATE INDEX account_currency_table_index ON account_currency_table (company_id, rate_type, date_from, date_next)"
            )
        )
        cr.execute(SQL("ANALYZE account_currency_table"))
        _debug.pipeline(
            "currency_table_built",
            companies=companies,
            periods=len(date_periods),
            cta=use_cta_rates,
            builders=len(table_builders),
        )

    def _get_table_builder_domestic_currency(self, companies, use_cta_rates) -> SQL:
        return SQL(
            "SELECT * FROM (VALUES %(rows)s) AS domestic_rates",
            rows=SQL(", ").join(
                self._currency_table_unit_rows(companies, use_cta_rates)
            ),
        )

    @_debug.perf.timed
    def _get_table_builder_current(
        self,
        scope: CurrencyTableScope,
        period_key,
        date_to,
        main_company_unit_factor,
    ) -> SQL:
        return SQL(
            """
                SELECT DISTINCT ON (other_company.id)
                    other_company.id,
                    %(period_key)s,
                    CAST(NULL AS DATE),
                    CAST(NULL AS DATE),
                    'current',
                    CASE WHEN rate.id IS NOT NULL THEN %(main_company_unit_factor)s / rate.rate ELSE 1 END
                FROM res_company other_company
                LEFT JOIN res_currency_rate rate
                    ON rate.currency_id = other_company.currency_id
                    AND rate.name <= %(date_to)s
                    AND rate.company_id = %(main_company_id)s
                WHERE
                    other_company.id IN %(other_company_ids)s
                ORDER BY other_company.id, rate.name DESC
            """,
            period_key=period_key,
            main_company_id=scope.main_company_id,
            other_company_ids=scope.other_company_ids,
            date_to=date_to,
            main_company_unit_factor=main_company_unit_factor,
        )

    @_debug.perf.timed
    def _get_table_builder_historical(
        self,
        scope: CurrencyTableScope,
        date_to,
        main_company_unit_factor,
        date_exclude,
    ) -> SQL:
        _debug.logic(
            "historical_rates_window",
            date_to=date_to,
            date_exclude=date_exclude,
            exclusion_applied=bool(date_exclude),
        )
        return SQL(
            """
                SELECT
                    other_company.id,
                    CAST(NULL AS VARCHAR),
                    rate.name,
                    LAG(rate.name, 1) OVER (PARTITION BY other_company.id, rate.currency_id ORDER BY rate.name DESC),
                    'historical',
                    %(main_company_unit_factor)s / rate.rate
                FROM res_company other_company
                JOIN res_currency_rate rate
                    ON rate.currency_id = other_company.currency_id
                WHERE
                    other_company.id IN %(other_company_ids)s
                    AND rate.company_id = %(main_company_id)s
                    AND rate.name <= %(date_to)s
                    %(exclusion_condition)s
            """,
            main_company_id=scope.main_company_id,
            other_company_ids=scope.other_company_ids,
            main_company_unit_factor=main_company_unit_factor,
            date_to=date_to,
            exclusion_condition=SQL(
                "AND rate.name > %(date_exclude)s", date_exclude=date_exclude
            )
            if date_exclude
            else SQL(),
        )

    @_debug.perf.timed
    def _get_table_builder_average(
        self,
        scope: CurrencyTableScope,
        period_key,
        date_from,
        date_to,
        main_company_unit_factor,
    ) -> SQL:
        _debug.logic(
            "average_rates_window",
            period_key=period_key,
            date_from=date_from,
            date_to=date_to,
            date_from_defaulted=not date_from,
        )
        if not date_from:
            date_from = date_utils.start_of(fields.Date.from_string(date_to), "year")

        return SQL(
            """
                SELECT
                    rate_with_days.other_company_id,
                    %(period_key)s,
                    CAST(NULL AS DATE),
                    CAST(NULL AS DATE),
                    'average',
                    SUM(%(main_company_unit_factor)s / rate_with_days.rate * rate_with_days.number_of_days) / SUM(rate_with_days.number_of_days)
                FROM (
                    SELECT
                        other_company.id as other_company_id,
                        rate.rate AS rate,
                        EXTRACT (
                            'Day' FROM COALESCE(
                                LEAD(rate.name, 1) OVER (PARTITION BY other_company.id, rate.currency_id ORDER BY rate.name ASC)::TIMESTAMP,
                                %(date_to)s::TIMESTAMP + INTERVAL '1' DAY
                            ) - rate.name::TIMESTAMP
                        ) AS number_of_days
                    FROM res_company other_company
                    JOIN res_currency_rate rate
                        ON rate.currency_id = other_company.currency_id
                    WHERE
                    rate.name <= %(date_to)s
                    AND rate.name >= %(date_from)s
                    AND other_company.id IN %(other_company_ids)s
                    AND rate.company_id = %(main_company_id)s

                    UNION ALL

                    (
                        SELECT DISTINCT ON (other_company.id)
                            other_company.id as other_company_id,
                            COALESCE(out_period_rate.rate, 1.0) AS rate,
                            EXTRACT('Day' FROM COALESCE(in_period_rate.name::TIMESTAMP, %(date_to)s::TIMESTAMP + INTERVAL '1' DAY) - %(date_from)s::TIMESTAMP) AS number_of_days

                        FROM res_company other_company

                        LEFT JOIN res_currency_rate in_period_rate
                            ON in_period_rate.currency_id = other_company.currency_id
                            AND in_period_rate.name <= %(date_to)s
                            AND in_period_rate.name >= %(date_from)s
                            AND in_period_rate.company_id = %(main_company_id)s

                        LEFT JOIN res_currency_rate out_period_rate
                            ON out_period_rate.currency_id = other_company.currency_id
                            AND out_period_rate.company_id = %(main_company_id)s
                            AND out_period_rate.name < %(date_from)s

                        WHERE
                        other_company.id IN %(other_company_ids)s
                        ORDER BY other_company.id, in_period_rate.name ASC, out_period_rate.name DESC
                    )
                ) rate_with_days
                GROUP BY rate_with_days.other_company_id
            """,
            period_key=period_key,
            main_company_id=scope.main_company_id,
            other_company_ids=scope.other_company_ids,
            date_from=date_from,
            date_to=date_to,
            main_company_unit_factor=main_company_unit_factor,
        )
