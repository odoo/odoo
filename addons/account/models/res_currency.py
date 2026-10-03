# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Domain
from odoo.tools import SQL


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
            date_from=date_from,
            date_to=date_to,
        ))

    def _get_parsed_rates(self, companies, date_from, date_to, current_date=None):
        """ Returns the rates converting the amounts of `companies` into the currency of the current company, as JSON:
        the disjoint periods of each company over which the average and retained earnings rates are constant, along
        with the historical rate of each of their days (CTA only), and the closing rate of each company at `current_date`.
        """

        def average(date2rate, start, end):
            period_rates = [date2rate[start + timedelta(days=i)] for i in range((end - start).days + 1)]
            return sum(period_rates) / len(period_rates) if period_rates else None

        currency_translation = self.env.context.get('currency_translation', 'current')
        date_from = date_from and fields.Date.to_date(date_from)
        date_to = fields.Date.to_date(date_to) if date_to else fields.Date.context_today(self)
        current_date = fields.Date.to_date(current_date) if current_date else date_to
        first_date = currency_translation == 'cta' and self.env['account.move']._first_date()

        # raw_cache: {(target_company_id, companies): (min_date, max_date, {company_id: {date: rate}}, {args: parsed rates}),
        #             'fiscalyears': {(company_id, date): (date_from, date_to)}}
        # Stores all fetched rates; extended on either end as needed to avoid redundant DB queries.
        raw_cache = self.env.cr.cache.setdefault('res_currency_to_company_rates', {})
        raw_key = (self.env.company.id, companies)
        cached_min, cached_max, historical, parsed = raw_cache.get(raw_key, (None, None, {}, {}))
        parsed_key = (currency_translation, date_from, date_to, current_date, first_date)
        if parsed_key in parsed:
            return parsed[parsed_key]
        new_min, new_max = cached_min, cached_max

        fiscalyears = {}
        fetch_from, fetch_to = current_date, max(date_to, current_date)
        if currency_translation == 'cta':
            fiscalyears = {company.id: self._get_fiscalyears(company, date_from, date_to, first_date) for company in companies}
            fetch_from = min(date_from or first_date, current_date, *(start for years in fiscalyears.values() for start, _end in years))

        if cached_min is None:
            for company_id, rate_date, rate in self._get_raw_rates(companies, fetch_from, fetch_to):
                historical.setdefault(company_id, {})[rate_date] = rate
            new_min, new_max = fetch_from, fetch_to
        else:
            if fetch_from < cached_min:
                for company_id, rate_date, rate in self._get_raw_rates(companies, fetch_from, cached_min):
                    historical[company_id][rate_date] = rate
                new_min = fetch_from
            if fetch_to > cached_max:
                for company_id, rate_date, rate in self._get_raw_rates(companies, cached_max, fetch_to):
                    historical[company_id][rate_date] = rate
                new_max = fetch_to

        if new_min != cached_min or new_max != cached_max:
            raw_cache[raw_key] = (new_min, new_max, historical, parsed)

        rates = []
        for company_id, company_fiscalyears in fiscalyears.items():
            date2rate = historical[company_id]
            period_average = date_from and average(date2rate, date_from, date_to)
            previous_average = None
            # Each day must be listed once, the join would otherwise duplicate the lines.
            next_day = date_from or first_date
            for fiscalyear_from, fiscalyear_to in company_fiscalyears:
                fiscalyear_average = average(date2rate, fiscalyear_from, min(fiscalyear_to, date_to))
                period_from, period_to = max(fiscalyear_from, next_day), min(fiscalyear_to, date_to)
                # Retained earnings use the average of the previous fiscal year, except on the last day of a fiscal year
                for start, end, retained in (
                    (period_from, min(period_to, fiscalyear_to - timedelta(days=1)), previous_average or fiscalyear_average),
                    (max(period_from, fiscalyear_to), period_to, fiscalyear_average),
                ):
                    if start <= end:
                        rates.append({
                            'company_id': company_id,
                            'date_from': str(start),
                            'average': period_average or fiscalyear_average,
                            'retained': retained,
                            'historical': [date2rate[start + timedelta(days=i)] for i in range((end - start).days + 1)],
                        })
                next_day = max(next_day, period_to + timedelta(days=1))
                previous_average = fiscalyear_average

        current = {company_id: date2rate[current_date] for company_id, date2rate in historical.items()}
        parsed[parsed_key] = json.dumps(rates), json.dumps(current)
        return parsed[parsed_key]

    def _get_fiscalyears(self, company, date_from, date_to, first_date):
        """ Returns the fiscal years of `company` until `date_to`, from the one of `first_date` for an unbounded period,
        otherwise from the one preceding `date_from`, whose average rate is used by the retained earnings.
        """
        # Computing a fiscal year may cost several queries, while most of them are shared by every period.
        fiscalyears_cache = self.env.cr.cache.setdefault('res_currency_to_company_rates', {}).setdefault('fiscalyears', {})

        def get_fiscalyear(day):
            if (company.id, day) not in fiscalyears_cache:
                fiscalyear = company.compute_fiscalyear_dates(day)
                fiscalyears_cache[company.id, day] = fiscalyear['date_from'], fiscalyear['date_to']
            return fiscalyears_cache[company.id, day]

        date_cursor = first_date
        if date_from:
            date_cursor = max(first_date, get_fiscalyear(date_from)[0] - timedelta(days=1))
        fiscalyears = []
        while date_cursor <= date_to:
            fiscalyears.append(get_fiscalyear(date_cursor))
            date_cursor = fiscalyears[-1][1] + timedelta(days=1)
        return fiscalyears


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
