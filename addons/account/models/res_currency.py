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
        currency_translation = self.env.context.get('currency_translation', 'current')
        date_from, date_to = bool(date_from) and str(date_from), bool(date_to) and str(date_to)
        current_date = str(current_date) if current_date else date_to

        if currency_translation == 'current':
            fetch_from = date_to
        else:
            first_date = str(self.env['account.move']._first_date())
            fetch_from = min(first_date, date_from) if date_from else first_date
            fetch_from = min(fetch_from, date_to)

        fetch_from = min(fetch_from, current_date)
        fetch_to = max(date_to, current_date)

        raw_cache = self.env.cr.cache.setdefault('res_currency_to_company_rates', {})
        cached_min, cached_max, historical = raw_cache.get(companies, (None, None, {}))
        new_min, new_max = cached_min, cached_max

        if cached_min is None:
            for company_id, rate_date, rate in self._get_raw_rates(companies, fetch_from, fetch_to):
                historical.setdefault(company_id, {})[str(rate_date)] = rate
            new_min, new_max = fetch_from, fetch_to
        else:
            if fetch_from < cached_min:
                for company_id, rate_date, rate in self._get_raw_rates(companies, fetch_from, cached_min):
                    historical[company_id][str(rate_date)] = rate
                new_min = fetch_from
            if fetch_to > cached_max:
                for company_id, rate_date, rate in self._get_raw_rates(companies, cached_max, fetch_to):
                    historical[company_id][str(rate_date)] = rate
                new_max = fetch_to

        if new_min != cached_min or new_max != cached_max:
            raw_cache[companies] = (new_min, new_max, historical)

        current = {company_id: date2rate[current_date] for company_id, date2rate in historical.items()}
        average = self._get_fiscalyear_average_rates(companies, historical, date_from, date_to) if currency_translation == 'cta' else {}

        return historical, average, current

    def _get_fiscalyear_average_rates(self, companies, historical, date_from, date_to):
        """ Per company, a list of {date_from, date_to, rate} intervals giving the
            average rate to apply to a P&L move dated within that interval.
        """
        if date_from:
            # date_from is set (for example, a bounded report column - even one whose window straddles a fiscal year-end,
            #  e.g., a custom Nov-Feb range): the whole window is treated as ONE period with one average.
            single_window = [(date_from, date_to)]
            average = {}
            for company in companies:
                date2rate = historical.get(company.id)
                if date2rate:
                    average[company.id] = self._average_rate_intervals(date2rate, single_window, date_from, date_to)
            return average

        # date_from is empty (e.g., initial balance scopes reaching back to "the beginning"): split per fiscal year.
        custom_fiscal_years = self._prefetch_custom_fiscal_years(companies)
        boundaries_cache = self.env.cr.cache.setdefault('res_currency_fiscalyear_boundaries', {})
        average = {}
        for company in companies:
            date2rate = historical.get(company.id)
            if not date2rate:
                continue
            window_start = min(date2rate)
            boundaries = self._get_fiscalyear_boundaries(company, custom_fiscal_years[company.id], window_start, date_to, boundaries_cache)
            average[company.id] = self._average_rate_intervals(date2rate, boundaries, window_start, date_to)

        return average

    @api.model
    def _average_rate_intervals(self, date2rate, boundaries, window_start, window_end):
        sorted_dates = sorted(d for d in date2rate if window_start <= d <= window_end)
        intervals = []

        bucket_start = 0
        nb_dates = len(sorted_dates)
        boundary_idx = 0

        while bucket_start < nb_dates:
            while boundaries[boundary_idx][1] < sorted_dates[bucket_start]:
                boundary_idx += 1
            fiscalyear_date_to = boundaries[boundary_idx][1]

            bucket_end = bucket_start
            rate_sum = 0.0
            while bucket_end < nb_dates and sorted_dates[bucket_end] <= fiscalyear_date_to:
                rate_sum += date2rate[sorted_dates[bucket_end]]
                bucket_end += 1

            nb_days_in_bucket = bucket_end - bucket_start
            intervals.append({
                'date_from': sorted_dates[bucket_start],
                'date_to': sorted_dates[bucket_end - 1],
                'rate': rate_sum / nb_days_in_bucket,
            })
            bucket_start = bucket_end

        return intervals

    @api.model
    def _get_fiscalyear_boundaries(self, company, custom_records, window_start, window_end, boundaries_cache):
        cache_entry = boundaries_cache.setdefault(company.id, {'min': None, 'max': None, 'boundaries': []})

        def fiscalyear_covering(date_str):
            for custom_date_from, custom_date_to in custom_records:
                if custom_date_from <= date_str <= custom_date_to:
                    return custom_date_from, custom_date_to

            default_date_from, default_date_to = date_utils.get_fiscal_year(
                fields.Date.to_date(date_str),
                day=company.fiscalyear_last_day,
                month=int(company.fiscalyear_last_month),
            )
            fy_date_from, fy_date_to = str(default_date_from), str(default_date_to)
            for custom_date_from, custom_date_to in custom_records:
                if custom_date_from <= fy_date_from <= custom_date_to:
                    fy_date_from = fields.Date.to_string(fields.Date.to_date(custom_date_to) + timedelta(days=1))
                if custom_date_from <= fy_date_to <= custom_date_to:
                    fy_date_to = fields.Date.to_string(fields.Date.to_date(custom_date_from) - timedelta(days=1))
            return fy_date_from, fy_date_to

        def append_boundaries_covering(range_from, range_to):
            date_cursor = range_from
            while date_cursor <= range_to:
                fy_date_from, fy_date_to = fiscalyear_covering(date_cursor)
                if not cache_entry['boundaries'] or cache_entry['boundaries'][-1] != (fy_date_from, fy_date_to):
                    cache_entry['boundaries'].append((fy_date_from, fy_date_to))
                date_cursor = fields.Date.to_string(fields.Date.to_date(fy_date_to) + timedelta(days=1))

        if cache_entry['min'] is None:
            append_boundaries_covering(window_start, window_end)
            cache_entry['min'], cache_entry['max'] = window_start, window_end
        else:
            if window_start < cache_entry['min']:
                cache_entry['boundaries'] = []
                append_boundaries_covering(window_start, cache_entry['max'])
                cache_entry['min'] = window_start
            if window_end > cache_entry['max']:
                append_boundaries_covering(cache_entry['max'], window_end)
                cache_entry['max'] = window_end

        return cache_entry['boundaries']

    @api.model
    def _prefetch_custom_fiscal_years(self, companies):
        return {company.id: [] for company in companies}


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
