from datetime import timedelta

from odoo import models, _, fields
from odoo.tools.misc import format_date

L10N_RO_TRIAL_BALANCE_TOTAL_COLUMN_GROUP_KEY = '_l10n_ro_trial_balance_total_column_group'


class L10nRoTrialBalance5ColumnReportHandler(models.AbstractModel):
    _name = 'l10n.ro.trial.balance.5.column.report.handler'
    _inherit = 'account.trial.balance.report.handler'
    _description = "Romanian Trial Balance Report (5 Columns)"

    def _show_start_of_year_column(self, options):
        options_date_from = fields.Date.from_string(options['date']['date_from'])
        return options_date_from.month != 1 or options_date_from.day != 1

    def _get_start_of_year_date_options(self, report, options):
        date_to = options['comparison']['periods'][-1]['date_from'] if options.get('comparison', {}).get('periods') else options['date']['date_from']
        new_date_to = fields.Date.from_string(date_to) - timedelta(days=1)
        date_to_fiscal_year_dates = self.env.company.compute_fiscalyear_dates(new_date_to)

        return {
            **report._get_dates_period(date_to_fiscal_year_dates['date_from'], new_date_to, 'range'),
            'currency_table_period_key': '_trial_balance_middle_periods',
        }

    def _get_column_group_creation_data(self, report, options, previous_options=None):
        # Override
        data = super()._get_column_group_creation_data(report, options, previous_options)

        if self._show_start_of_year_column(options):
            return (
                data[0],  # Initial balance
                (self._create_column_group_start_of_year, 'left'),
                (self._create_column_group_total, 'right'),
                data[1],  # End balance
            )
        else:
            return (
                data[0],  # Initial balance
                (self._create_column_group_total, 'right'),
                data[1],  # End balance
            )

    def _get_initial_balance_forced_options(self, report, options, previous_options):
        general_ledger_initial_balance_options = self.env['account.general.ledger.report.handler']._get_options_initial_balance(options)

        if self._show_start_of_year_column(options):
            # If the 'start of year' column is shown we want to exclude it from the initial balance
            first_day_of_year = fields.Date.from_string(general_ledger_initial_balance_options['date']['date_from'])
            initial_date = self.env.company.compute_fiscalyear_dates(first_day_of_year - timedelta(days=1))
        else:
            initial_date = general_ledger_initial_balance_options['date']

        return {
            'date': {
                **general_ledger_initial_balance_options['date'],
                'date_from': initial_date['date_from'] if isinstance(initial_date['date_from'], str) else fields.Date.to_string(initial_date['date_from']),
                'date_to': initial_date['date_to'] if isinstance(initial_date['date_to'], str) else fields.Date.to_string(initial_date['date_to']),
            },
            'include_current_year_in_unaff_earnings': general_ledger_initial_balance_options['include_current_year_in_unaff_earnings'],
        }

    def _create_column_group_initial_balance(self, report, options, previous_options, default_group_vals, side_to_append):
        # Override
        forced_options = self._get_initial_balance_forced_options(report, options, previous_options)

        self._create_and_append_column_group(
            report,
            options,
            _("Initial Balance"),
            forced_options,
            side_to_append,
            default_group_vals,
        )

    def _create_column_group_start_of_year(self, report, options, previous_options, default_group_vals, side_to_append):
        forced_options = {
            'include_current_year_in_unaff_earnings': False,
            'date': self._get_start_of_year_date_options(report, options),
        }

        month_from, year_from = format_date(self.env, forced_options['date']['date_from'], date_format="MMM yyyy").split()
        month_to, year_to = format_date(self.env, forced_options['date']['date_to'], date_format="MMM yyyy").split()

        if year_from != year_to:
            header_name = f"{month_from} {year_from} - {month_to} {year_to}"
        elif month_from != month_to:
            header_name = f"{month_from} - {month_to} {year_from}"
        else:
            header_name = f"{month_from} {year_from}"

        self._create_and_append_column_group(
            report,
            options,
            header_name,
            forced_options,
            side_to_append,
            default_group_vals,
            exclude_initial_balance=True,
        )

    def _create_column_group_total(self, report, options, previous_options, default_group_vals, side_to_append):
        initial_forced_options = self._get_initial_balance_forced_options(report, options, previous_options)

        forced_options = {
            'date': {
                **initial_forced_options['date'],
                'date_to': options['date']['date_to'],
                'currency_table_period_key': '_trial_balance_middle_periods'
            },
            'is_total_column': True,
        }

        self._create_and_append_column_group(
            report,
            options,
            _("Total Amounts"),
            forced_options,
            side_to_append,
            default_group_vals,
            exclude_initial_balance=True,
        )

    def _custom_line_postprocessor(self, report, options, lines):
        # OVERRIDE
        lines = super()._custom_line_postprocessor(report, options, lines)

        # To calculate values in the 'total' columns, we exclude the last 2 column groups (total and end balance)
        sum_excluded_column_group_keys = {options['columns'][i]['column_group_key'] for i in (-1, -1 - len(report.column_ids))}

        for line in lines:
            total_columns = [x for x in line['columns'] if options['column_groups'][x['column_group_key']].get('forced_options').get('is_total_column')]

            for col in report.column_ids:
                total_sub_column = next(x for x in total_columns if x['expression_label'] == col.expression_label)
                total_sub_column['no_format'] = sum(x['no_format']
                                                    for x in line['columns']
                                                    if x['column_group_key'] not in sum_excluded_column_group_keys
                                                    and x['no_format']
                                                    and x['expression_label'] == col.expression_label)

        return lines


class L10nRoTrialBalance4ColumnReportHandler(models.AbstractModel):
    _name = 'l10n.ro.trial.balance.4.column.report.handler'
    _inherit = 'l10n.ro.trial.balance.5.column.report.handler'
    _description = "Romanian Trial Balance Report (4 Columns)"

    def _show_start_of_year_column(self, options):
        # Override
        return False
