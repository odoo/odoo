# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Domain
from odoo.tools import SQL, date_utils


class ResCurrency(models.Model):
    _inherit = 'res.currency'

    def _get_fiscal_country_codes(self):
        return ','.join(self.env.companies.mapped('account_fiscal_country_id.code'))

    display_rounding_warning = fields.Boolean(string="Display Rounding Warning", compute='_compute_display_rounding_warning',
        help="The warning informs a rounding factor change might be dangerous on res.currency's form view.")
    fiscal_country_codes = fields.Char(store=False, default=_get_fiscal_country_codes)

    @api.depends('rounding')
    def _compute_display_rounding_warning(self):
        for record in self:
            record.display_rounding_warning = (
                record._origin.id and record._origin.rounding != record.rounding
            )

    def write(self, vals):
        if 'rounding' in vals:
            rounding_val = vals['rounding']
            for record in self:
                if (rounding_val > record.rounding or rounding_val == 0) and record._has_accounting_entries():
                    raise UserError(_("You cannot reduce the number of decimal places of a currency which has already been used to make accounting entries."))

        return super().write(vals)

    def _has_accounting_entries(self):
        """ Returns True iff this currency has been used to generate (hence, round)
        some move lines (either as their foreign currency, or as the main currency).
        """
        self.ensure_one()
        return bool(self.env['account.move.line'].sudo().search_count(['|', ('currency_id', '=', self.id), ('company_currency_id', '=', self.id)]))

    def _get_raw_rates(self, companies, date_from, date_to):
        before = Domain.custom(to_sql=lambda table: SQL("%s <= date.date", table.name))
        company_match = Domain.custom(to_sql=lambda table: SQL("%s = target_root_company.id", table.company_id))
        company_null = Domain.custom(to_sql=lambda table: SQL("%s IS NULL", table.company_id))
        target_currency = Domain.custom(to_sql=lambda table: SQL("%s = target_company.currency_id", table.currency_id))
        source_currency = Domain.custom(to_sql=lambda table: SQL("%s = source_company.currency_id", table.currency_id))
        CurrencyRate = self.env['res.currency.rate'].sudo()
        return self.env.execute_query(SQL(
            """
                SELECT source_company.id,
                       date.date,
                       %(target_rate)s / %(source_rate)s AS rate
                  FROM (SELECT generate_series(%(date_from)s::timestamp, %(date_to)s::timestamp, '1 day')::date AS date) AS date,
                       res_company source_company,
                       res_company target_company
                  JOIN res_company target_root_company ON target_root_company.id = SPLIT_PART(target_company.parent_path, '/', 1)::int
                 WHERE target_company.id = %(main_company)s
                   AND source_company.id = ANY(%(other_companies)s)
            """,
<<<<<<< 6307940a61f55a168fc80933f9ec856ebbc36432
            target_rate=SQL(
                "COALESCE(%s, %s, %s, %s, 1)",
                CurrencyRate._search(before & company_match & target_currency, order='name DESC', limit=1).subselect('rate'),
                CurrencyRate._search(before & company_null & target_currency, order='name DESC', limit=1).subselect('rate'),
                CurrencyRate._search(company_match & target_currency, order='name ASC', limit=1).subselect('rate'),
                CurrencyRate._search(company_null & target_currency, order='name ASC', limit=1).subselect('rate'),
            ),
            source_rate=SQL(
                "COALESCE(%s, %s, %s, %s, 1)",
                CurrencyRate._search(before & company_match & source_currency, order='name DESC', limit=1).subselect('rate'),
                CurrencyRate._search(before & company_null & source_currency, order='name DESC', limit=1).subselect('rate'),
                CurrencyRate._search(company_match & source_currency, order='name ASC', limit=1).subselect('rate'),
                CurrencyRate._search(company_null & source_currency, order='name ASC', limit=1).subselect('rate'),
            ),
            main_company=self.env.company.id,
            other_companies=companies.ids,
||||||| b07ff5843ee87741b293d9e67f72a77a2ed2ed88
            currency_table_build_query=SQL(" UNION ALL ").join(SQL('(%s)', builder) for builder in table_builders),
        ))

    def _get_table_builder_domestic_currency(self, companies, use_cta_rates) -> SQL:
        """ Returns a query building one rate of each appropriate type equal to 1 for each of the provided companies. Those companies should be
        the ones sharing the same currency as self.env.company.
        """
        rate_values = []
        for company in companies:
            rate_values.append(SQL("(%s, CAST(NULL AS VARCHAR), CAST(NULL AS DATE), CAST(NULL AS DATE), 'current', 1)", company.id))

            if use_cta_rates:
                rate_values += [
                    SQL("(%s, CAST(NULL AS VARCHAR), CAST(NULL AS DATE), CAST(NULL AS DATE), 'average', 1)", company.id),
                    SQL("(%s, CAST(NULL AS VARCHAR), CAST(NULL AS DATE), CAST(NULL AS DATE), 'historical', 1)", company.id),
                ]

        return SQL(
            """
                SELECT *
                FROM ( VALUES
                    %(rate_values)s
                ) values
            """,
            rate_values=SQL(", ").join(rate_values)
        )

    def _get_table_builder_current(self, period_key, main_company, other_companies, date_to, main_company_unit_factor) -> SQL:
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
            main_company_id=main_company.root_id.id,
            other_company_ids=tuple(other_companies.ids),
            date_to=date_to,
            main_company_unit_factor=main_company_unit_factor,
        )

    def _get_table_builder_historical(self, main_company, other_companies, date_to, main_company_unit_factor, date_exclude) -> SQL:
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
            main_company_id=main_company.root_id.id,
            other_company_ids=tuple(other_companies.ids),
            main_company_unit_factor=main_company_unit_factor,
            date_to=date_to,
            exclusion_condition=SQL("AND rate.name > %(date_exclude)s", date_exclude=date_exclude) if date_exclude else SQL(),
        )

    def _get_table_builder_average(self, period_key, main_company, other_companies, date_from, date_to, main_company_unit_factor) -> SQL:
        if not date_from:
            # When there is no start date, we want to compute the average rate on the current year only
            date_from = date_utils.start_of(fields.Date.from_string(date_to), 'year')

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
            main_company_id=main_company.root_id.id,
            other_company_ids=tuple(other_companies.ids),
=======
            currency_table_build_query=SQL(" UNION ALL ").join(SQL('(%s)', builder) for builder in table_builders),
        ))

    def _get_table_builder_domestic_currency(self, companies, use_cta_rates) -> SQL:
        """ Returns a query building one rate of each appropriate type equal to 1 for each of the provided companies. Those companies should be
        the ones sharing the same currency as self.env.company.
        """
        rate_values = []
        for company in companies:
            rate_values.append(SQL("(%s, CAST(NULL AS VARCHAR), CAST(NULL AS DATE), CAST(NULL AS DATE), 'current', 1)", company.id))

            if use_cta_rates:
                rate_values += [
                    SQL("(%s, CAST(NULL AS VARCHAR), CAST(NULL AS DATE), CAST(NULL AS DATE), 'average', 1)", company.id),
                    SQL("(%s, CAST(NULL AS VARCHAR), CAST(NULL AS DATE), CAST(NULL AS DATE), 'historical', 1)", company.id),
                ]

        return SQL(
            """
                SELECT *
                FROM ( VALUES
                    %(rate_values)s
                ) values
            """,
            rate_values=SQL(", ").join(rate_values)
        )

    def _get_table_builder_current(self, period_key, main_company, other_companies, date_to, main_company_unit_factor) -> SQL:
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
                    AND (rate.company_id = %(root_company_id)s OR rate.company_id IS NULL)
                WHERE
                    other_company.id IN %(other_company_ids)s
                ORDER BY other_company.id, rate.name DESC
            """,
            period_key=period_key,
            root_company_id=main_company.root_id.id,
            other_company_ids=tuple(other_companies.ids),
            date_to=date_to,
            main_company_unit_factor=main_company_unit_factor,
        )

    def _get_table_builder_historical(self, main_company, other_companies, date_to, main_company_unit_factor, date_exclude) -> SQL:
        # main_company_unit_factor is kept for API stability but superseded: the domestic
        # rate is now looked up per-date via a lateral join so that fluctuations in the
        # domestic currency's own rate are correctly reflected in historical entries.
        return SQL(
            """
                SELECT
                    other_company.id,
                    CAST(NULL AS VARCHAR),
                    rate.name,
                    LAG(rate.name, 1) OVER (PARTITION BY other_company.id, rate.currency_id ORDER BY rate.name DESC),
                    'historical',
                    COALESCE(domestic_rate.rate, 1) / rate.rate
                FROM res_company other_company
                JOIN res_currency_rate rate
                    ON rate.currency_id = other_company.currency_id
                LEFT JOIN LATERAL (
                    SELECT dr.rate
                    FROM res_currency_rate dr
                    WHERE dr.currency_id = %(domestic_currency_id)s
                      AND dr.name <= rate.name
                      AND (dr.company_id = %(root_company_id)s OR dr.company_id IS NULL)
                    ORDER BY dr.name DESC
                    LIMIT 1
                ) domestic_rate ON true
                WHERE
                    other_company.id IN %(other_company_ids)s
                    AND (rate.company_id = %(root_company_id)s OR rate.company_id IS NULL)
                    AND rate.name <= %(date_to)s
                    %(exclusion_condition)s
            """,
            domestic_currency_id=main_company.currency_id.id,
            root_company_id=main_company.root_id.id,
            other_company_ids=tuple(other_companies.ids),
            date_to=date_to,
            exclusion_condition=SQL("AND rate.name > %(date_exclude)s", date_exclude=date_exclude) if date_exclude else SQL(),
        )

    def _get_table_builder_average(self, period_key, main_company, other_companies, date_from, date_to, main_company_unit_factor) -> SQL:
        if not date_from:
            # When there is no start date, we want to compute the average rate on the current year only
            date_from = date_utils.start_of(fields.Date.from_string(date_to), 'year')

        # main_company_unit_factor is kept for API stability but superseded: the domestic
        # rate is now looked up per-segment via lateral joins so that fluctuations in the
        # domestic currency's own rate are correctly weighted in the average.
        #
        # The period is split into segments on every rate change of either the foreign
        # currency or the domestic currency. Within each segment both rates are constant,
        # so the conversion factor is (domestic_rate / foreign_rate) for that segment.
        return SQL(
            """
                SELECT
                    rate_with_days.other_company_id,
                    %(period_key)s,
                    CAST(NULL AS DATE),
                    CAST(NULL AS DATE),
                    'average',
                    SUM(rate_with_days.domestic_rate / rate_with_days.foreign_rate * rate_with_days.number_of_days)
                        / SUM(rate_with_days.number_of_days)
                FROM (
                    SELECT
                        seg.other_company_id,
                        EXTRACT(
                            'Day' FROM COALESCE(seg.next_date, %(date_to)s::TIMESTAMP + INTERVAL '1' DAY)
                                     - seg.seg_date::TIMESTAMP
                        ) AS number_of_days,
                        COALESCE(foreign_rate.rate, 1.0) AS foreign_rate,
                        COALESCE(domestic_rate.rate, 1.0) AS domestic_rate
                    FROM (
                        -- One row per (company, breakpoint). Breakpoints are the start of the
                        -- period plus every rate change — for the foreign OR domestic currency —
                        -- that falls strictly inside the period.
                        SELECT
                            other_company.id AS other_company_id,
                            other_company.currency_id AS foreign_currency_id,
                            breakpoint.date AS seg_date,
                            LEAD(breakpoint.date) OVER (PARTITION BY other_company.id ORDER BY breakpoint.date) AS next_date
                        FROM res_company other_company
                        JOIN LATERAL (
                            SELECT %(date_from)s AS date
                            UNION
                            SELECT rate.name
                            FROM res_currency_rate rate
                            WHERE rate.currency_id = other_company.currency_id
                              AND rate.name > %(date_from)s
                              AND rate.name <= %(date_to)s
                              AND (rate.company_id = %(root_company_id)s OR rate.company_id IS NULL)
                            UNION
                            SELECT dr.name
                            FROM res_currency_rate dr
                            WHERE dr.currency_id = %(domestic_currency_id)s
                              AND dr.name > %(date_from)s
                              AND dr.name <= %(date_to)s
                              AND (dr.company_id = %(root_company_id)s OR dr.company_id IS NULL)
                        ) breakpoint ON true
                        WHERE other_company.id IN %(other_company_ids)s
                    ) seg
                    -- Foreign rate in effect at the start of this segment
                    LEFT JOIN LATERAL (
                        SELECT cr.rate
                        FROM res_currency_rate cr
                        WHERE cr.currency_id = seg.foreign_currency_id
                          AND cr.name <= seg.seg_date
                          AND (cr.company_id = %(root_company_id)s OR cr.company_id IS NULL)
                        ORDER BY cr.name DESC
                        LIMIT 1
                    ) foreign_rate ON true
                    -- Domestic rate in effect at the start of this segment
                    LEFT JOIN LATERAL (
                        SELECT cr.rate
                        FROM res_currency_rate cr
                        WHERE cr.currency_id = %(domestic_currency_id)s
                          AND cr.name <= seg.seg_date
                          AND (cr.company_id = %(root_company_id)s OR cr.company_id IS NULL)
                        ORDER BY cr.name DESC
                        LIMIT 1
                    ) domestic_rate ON true
                ) rate_with_days
                WHERE rate_with_days.number_of_days > 0
                GROUP BY rate_with_days.other_company_id
            """,
            period_key=period_key,
            root_company_id=main_company.root_id.id,
            other_company_ids=tuple(other_companies.ids),
>>>>>>> 487a2a9376eb430a376b56973e1e53341261363b
            date_from=date_from,
            date_to=date_to,
<<<<<<< 6307940a61f55a168fc80933f9ec856ebbc36432
        ))

    def _get_parsed_rates(self, companies, date_from, date_to):
        currency_translation = self.env.context.get('currency_translation', 'current')
        date_from, date_to = bool(date_from) and str(date_from), bool(date_to) and str(date_to)
        if not date_from:
            # When there is no start date, we want to compute the average rate on the current year only
            date_from = str(date_utils.start_of(fields.Date.from_string(date_to), 'year'))

        if currency_translation == 'current':
            fetch_from = date_to
        else:
            fetch_from = min((str(self.env['account.move']._first_date()), date_from))

        # raw_cache: {companies: (min_date, max_date, {company_id: {date: rate}})}
        # Stores all fetched rates; extended on either end as needed to avoid redundant DB queries.
        raw_cache = self.env.cr.cache.setdefault('res_currency_to_company_rates', {})
        cached_min, cached_max, historical = raw_cache.get(companies, (None, None, {}))
        new_min, new_max = cached_min, cached_max

        if cached_min is None:
            for company_id, rate_date, rate in self._get_raw_rates(companies, fetch_from, date_to):
                historical.setdefault(company_id, {})[str(rate_date)] = rate
            new_min, new_max = fetch_from, date_to
        else:
            if fetch_from < cached_min:
                for company_id, rate_date, rate in self._get_raw_rates(companies, fetch_from, cached_min):
                    historical[company_id][str(rate_date)] = rate
                new_min = fetch_from
            if date_to > cached_max:
                for company_id, rate_date, rate in self._get_raw_rates(companies, cached_max, date_to):
                    historical[company_id][str(rate_date)] = rate
                new_max = date_to

        if new_min != cached_min or new_max != cached_max:
            raw_cache[companies] = (new_min, new_max, historical)

        current = {company_id: date2rate[date_to] for company_id, date2rate in historical.items()}
        period = list(date_utils.date_range(
            fields.Date.to_date(date_to if currency_translation == 'current' else date_from),
            fields.Date.to_date(date_to),
            timedelta(days=1),
        ))
        average = {
            company_id: sum(date2rate[str(d)] for d in period) / len(period)
            for company_id, date2rate in historical.items()
        }
        return historical, average, current


class ResCurrencyRate(models.Model):
    _inherit = 'res.currency.rate'

    @api.model_create_multi
    def create(self, vals_list):
        self.env.cr.cache.pop('res_currency_to_company_rates', None)
        return super().create(vals_list)

    @api.ondelete(at_uninstall=False)
    def _unlink_clear_company_rate_cache(self):
        self.env.cr.cache.pop('res_currency_to_company_rates', None)

    def write(self, vals):
        self.env.cr.cache.pop('res_currency_to_company_rates', None)
        return super().write(vals)
||||||| b07ff5843ee87741b293d9e67f72a77a2ed2ed88
            main_company_unit_factor=main_company_unit_factor,
        )
=======
            domestic_currency_id=main_company.currency_id.id,
        )
>>>>>>> 487a2a9376eb430a376b56973e1e53341261363b
