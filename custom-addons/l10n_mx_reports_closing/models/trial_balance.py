# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, _

class L10nMXTrialBalanceCustomHandler(models.AbstractModel):
    _inherit = 'account.trial.balance.report.handler'

    def _get_custom_display_config(self):
        return {
            'templates': {
                'AccountReportFilters': 'l10n_mx_reports_closing.TrialBalanceFilters',
            },
        }

    def _l10n_mx_set_options_month_13(self, options):
        ''' Configure the options dict if the 'Month 13' option is active.

            We change the report period to the last day of the current fiscal year,
            because the Month 13 Trial Balance makes no sense on any other day.

            Our objective is to have everything before the closing entry under Initial Balance,
            and just the closing entry under Current Period.

            So:
            - we stretch the initial balance's period to also cover the report period,
              but excluding Month 13 entries during the report period; and
            - we restrict the current period to Month 13 entries.
        '''
        options['column_headers'][0][1]['name'] = _('Month 13')

        # Change the report date so that it coincides with the end of the fiscal year,
        # if that is not already the case.
        report_date_to = fields.Date.to_date(options['date']['date_to'])
        last_day_of_fiscalyear = self.env.company.compute_fiscalyear_dates(report_date_to)['date_to']
        last_day_of_fiscalyear_str = fields.Date.to_string(last_day_of_fiscalyear)
        options['date']['date_from'] = last_day_of_fiscalyear_str
        options['date']['date_to'] = last_day_of_fiscalyear_str
        options['date']['string'] = '%s, %s' % (_('Month 13'), last_day_of_fiscalyear.year)

        # We do this to force the date filter box to display 'Month 13, <year>'
        # instead of 'From: <date>; To: <date>' even when a custom date range is used.
        # This is a bit hacky but works because of the logic in the `search_template_date_filter` template.
        del options['date']['period_type']

        # Retrieve the options dictionaries corresponding to each column group.
        initial_col_group_key = options['columns'][0]['column_group_key']
        current_col_group_key = options['columns'][2]['column_group_key']
        end_col_group_key = options['columns'][4]['column_group_key']

        initial_col_group_data = options['column_groups'][initial_col_group_key]
        current_col_group_data = options['column_groups'][current_col_group_key]
        end_col_group_data = options['column_groups'][end_col_group_key]

        # Set the options dict for the initial balance col group.
        # We need to stretch the period all the way to the end of the report period,
        # and exclude the Month 13 entries within the report period.
        initial_col_group_data['forced_options']['date']['date_to'] = last_day_of_fiscalyear_str
        initial_col_group_data['forced_domain'] += [
            '|',
            ('move_id.l10n_mx_closing_move', '=', False),
            ('date', '<', last_day_of_fiscalyear_str),
        ]

        # Set the options dict for the current period col group.
        # We need to include only Month 13 entries.
        current_col_group_data['forced_options']['date']['date_from'] = last_day_of_fiscalyear_str
        current_col_group_data['forced_options']['date']['date_to'] = last_day_of_fiscalyear_str
        current_col_group_data['forced_domain'] += [('move_id.l10n_mx_closing_move', '=', True)]

        # Set the options dict for the end period col group.
        end_col_group_data['forced_options']['date']['date_from'] = last_day_of_fiscalyear_str
        end_col_group_data['forced_options']['date']['date_to'] = last_day_of_fiscalyear_str

    def _l10n_mx_set_options_non_month_13(self, options):
        ''' Configure the options dict if the 'Month 13' option is inactive.

            In this case, the idea is to pretend that Month 13 entries fall between the last day of the fiscal year
            and the first day of the next fiscal year.

            So, we only take into account Month 13 entries that fall before the first day of the fiscal year within
            the report end date.
        '''
        report_date_to = fields.Date.to_date(options['date']['date_to'])
        first_day_of_fiscalyear = self.env.company.compute_fiscalyear_dates(report_date_to)['date_from']
        first_day_of_fiscalyear_str = fields.Date.to_string(first_day_of_fiscalyear)

        forced_domain = options.setdefault('forced_domain', [])
        forced_domain += [
            '|',
            ('move_id.l10n_mx_closing_move', '=', False),
            '&', ('move_id.l10n_mx_closing_move', '=', True), ('date', '<', first_day_of_fiscalyear_str),
        ]

    def _custom_options_initializer(self, report, options, previous_options=None):
        # OVERRIDE
        super()._custom_options_initializer(report, options, previous_options=previous_options)
        if self.env.company.account_fiscal_country_id.code == 'MX':
            options['l10n_mx_month_13'] = (previous_options or {}).get('l10n_mx_month_13', False)
            # Properly supporting comparisons with a Month 13 period is too complicated, so we turn the Month 13 filter off if the user does a comparison.
            # When doing a comparison, any Month 13 entries are included in the following (January) period.
            if options.get('comparison', {}).get('filter') != 'no_comparison':
                options['l10n_mx_month_13'] = False
            if options['l10n_mx_month_13']:
                self._l10n_mx_set_options_month_13(options)
            else:
                self._l10n_mx_set_options_non_month_13(options)

    def _l10n_mx_get_sat_values(self, options):
        # OVERRIDE
        values = super()._l10n_mx_get_sat_values(options)
        if options.get('l10n_mx_month_13'):
            values.update({'month': '13'})
        return values
