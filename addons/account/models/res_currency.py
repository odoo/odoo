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

    def _get_parsed_rates(self, companies, date_from, date_to):

        def get_fy_and_avg(parsed_company, parsed_date, date2rate):
            if parsed_date not in fy_cache:
                fy = parsed_company.compute_fiscalyear_dates(parsed_date)
                fy_periods = list(date_utils.date_range(fy['date_from'], fy['date_to'], timedelta(days=1)))
                fy_rates = [date2rate[fields.Date.to_string(period)] for period in fy_periods if fields.Date.to_string(period) in date2rate]
                avg_cache[parsed_date] = sum(fy_rates) / len(fy_rates) if fy_rates else 1.0

                for fy_period in fy_periods:
                    fy_cache[fy_period] = fy
                    avg_cache[fy_period] = avg_cache[parsed_date]
            return fy_cache[parsed_date], avg_cache[parsed_date]

        currency_translation = self.env.context.get('currency_translation', 'current')
        date_from, date_to = bool(date_from) and str(date_from), bool(date_to) and str(date_to)

        if not date_from:
            # When there is no start date, we want to compute the average rate on the current year only
            fy_dates = self.env.company.compute_fiscalyear_dates(fields.Date.from_string(date_to))
            date_from = fields.Date.to_string(fy_dates['date_from'])

        if currency_translation == 'current':
            fetch_from = date_to
        else:
            fetch_from = min(str(self.env['account.move']._first_date()), date_from)
            base_date = fields.Date.to_date(fetch_from)

            # Get earliest date of previous fiscal year from all companies
            fetch_from = min([fetch_from] + [
                str(c.compute_fiscalyear_dates(c.compute_fiscalyear_dates(base_date)['date_from'] - timedelta(days=1))['date_from'])
                for c in companies
            ])

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
                    historical.setdefault(company_id, {})[str(rate_date)] = rate
                new_min = fetch_from
            if date_to > cached_max:
                for company_id, rate_date, rate in self._get_raw_rates(companies, cached_max, date_to):
                    historical.setdefault(company_id, {})[str(rate_date)] = rate
                new_max = date_to

        if new_min != cached_min or new_max != cached_max:
            raw_cache[companies] = (new_min, new_max, historical)

        current = {company_id: date2rate.get(date_to, 1.0) for company_id, date2rate in historical.items()}

        period = list(date_utils.date_range(
            fields.Date.to_date(date_to if currency_translation == 'current' else date_from),
            fields.Date.to_date(date_to),
            timedelta(days=1),
        ))

        average = {company.id: {} for company in companies}
        average_previous_year = {company.id: {} for company in companies}

        if currency_translation == 'cta':
            start_date = fields.Date.to_date(min((str(self.env['account.move']._first_date()), date_from)))
            end_date = fields.Date.to_date(date_to)

            viewed_start = fields.Date.to_date(date_from)
            viewed_end = fields.Date.to_date(date_to)

            for company in companies:
                date2rate = historical.get(company.id, {})
                fy_cache = {}
                avg_cache = {}

                period_rates = [date2rate.get(fields.Date.to_string(d), 1.0) for d in period]
                period_avg = sum(period_rates) / len(period_rates) if period_rates else 1.0

                for dt in date_utils.date_range(start_date, end_date, timedelta(days=1)):
                    dt_str = fields.Date.to_string(dt)
                    fy, current_avg = get_fy_and_avg(company, dt, date2rate)

                    # Equity Retained accounts should use average of previous fiscal year except for last day of fiscal year
                    if dt == fy['date_to']:
                        average_previous_year[company.id][dt_str] = current_avg
                    else:
                        prev_fy_date = fy['date_from'] - timedelta(days=1)
                        _fy, prev_avg = get_fy_and_avg(company, prev_fy_date, date2rate)
                        average_previous_year[company.id][dt_str] = prev_avg

                    if viewed_start <= dt <= viewed_end:
                        average[company.id][dt_str] = period_avg
                    else:
                        average[company.id][dt_str] = current_avg

        elif currency_translation == 'current':
            # Not sure if it's useful since average isn't used if cta option isn't set
            for company in companies:
                date2rate = historical.get(company.id, {})
                period_rates = [date2rate.get(fields.Date.to_string(d), 1.0) for d in period]
                flat_avg = sum(period_rates) / len(period_rates) if period_rates else 1.0
                average[company.id] = flat_avg

        return historical, average, current, average_previous_year


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
