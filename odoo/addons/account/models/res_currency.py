# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields, _
from odoo.exceptions import UserError


class ResCurrency(models.Model):
    _inherit = 'res.currency'

    display_rounding_warning = fields.Boolean(string="Display Rounding Warning", compute='_compute_display_rounding_warning',
        help="The warning informs a rounding factor change might be dangerous on res.currency's form view.")
    fiscal_country_codes = fields.Char(compute='_compute_fiscal_country_codes')

    @api.depends('rounding')
    def _compute_display_rounding_warning(self):
        for record in self:
            record.display_rounding_warning = record.id \
                                              and record._origin.rounding != record.rounding \
                                              and record._origin._has_accounting_entries()

    @api.depends_context('allowed_company_ids')
    def _compute_fiscal_country_codes(self):
        for record in self:
            companies = self.env['res.company'].search([('id', 'in', self.env.context.get('allowed_company_ids', []))])
            record.fiscal_country_codes = ",".join(companies.mapped('account_fiscal_country_id.code'))

    def write(self, vals):
        if 'rounding' in vals:
            rounding_val = vals['rounding']
            for record in self:
                if (rounding_val > record.rounding or rounding_val == 0) and record._has_accounting_entries():
                    raise UserError(_("You cannot reduce the number of decimal places of a currency which has already been used to make accounting entries."))

        return super(ResCurrency, self).write(vals)

    def _has_accounting_entries(self):
        """ Returns True iff this currency has been used to generate (hence, round)
        some move lines (either as their foreign currency, or as the main currency).
        """
        self.ensure_one()
        return bool(self.env['account.move.line'].sudo().search_count(['|', ('currency_id', '=', self.id), ('company_currency_id', '=', self.id)]))

    @api.model
    def _get_query_currency_table(self, company_ids, conversion_date):
        ''' Construct the currency table as a mapping company -> rate to convert the amount to the user's company
        currency in a multi-company/multi-currency environment.
        The currency_table is a small postgresql table construct with VALUES.
        :param company_ids: list of company ids
        :param conversion_date: date, used to determine the currency rate between the individual companies and the user's company
        :return:        The query representing the currency table.
        '''

        companies = self.env['res.company'].browse(company_ids)
        user_company = self.env.company
        if companies == user_company:
            currency_rates = {user_company.currency_id.id: 1.0}
        else:
            if user_company not in companies:
                companies |= user_company
            currency_rates = companies.mapped('currency_id')._get_rates(user_company, conversion_date)

        conversion_rates = []
        for company in companies:
            conversion_rates.extend((
                company.id,
                currency_rates[user_company.currency_id.id] / currency_rates[company.currency_id.id],
                user_company.currency_id.decimal_places,
            ))
        query = '(VALUES %s) AS currency_table(company_id, rate, precision)' % ','.join('(%s, %s, %s)' for i in companies)
        return self.env.cr.mogrify(query, conversion_rates).decode(self.env.cr.connection.encoding)
