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
