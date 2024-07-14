# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _
from odoo.tools.misc import get_lang


class DisallowedExpensesFleetCustomHandler(models.AbstractModel):
    _name = 'account.disallowed.expenses.fleet.report.handler'
    _inherit = 'account.disallowed.expenses.report.handler'
    _description = 'Disallowed Expenses Fleet Custom Handler'

    def _get_custom_display_config(self):
        return {
            'templates': {
                'AccountReportFilters': 'account_disallowed_expenses_fleet.DisallowedExpensesFleetReportFilters',
            }
        }

    def _custom_options_initializer(self, report, options, previous_options=None):
        super()._custom_options_initializer(report, options, previous_options=previous_options)

        # Initialize vehicle_split filter by default
        options['vehicle_split'] = previous_options.get('vehicle_split', True)

        # Check if there are multiple rates
        period_domain = [('date_from', '>=', options['date']['date_from']), ('date_from', '<=', options['date']['date_to'])]
        rg = self.env['fleet.disallowed.expenses.rate']._read_group(
            period_domain,
            ['vehicle_id'],
            having=[('__count', '>', 1)],
            limit=1,
        )
        options['multi_rate_in_period'] = options.get('multi_rate_in_period') or bool(rg)

    def _custom_line_postprocessor(self, report, options, lines, warnings=None):
        if warnings is not None:
            # Check for expense accounts without disallowed expense category
            accounts = self.env['account.move.line']._read_group(
                [
                    ('date', '<=', options['date']['date_to']),
                    ('date', '>=', options['date']['date_from']),
                    ('parent_state', '=', 'posted'),
                    ('account_type', '=', 'expense'),
                    ('vehicle_id', '!=', None),
                    ('account_id.disallowed_expenses_category_id', '=', None),
                ],
                ['account_id'],
            )
            if accounts:
                warnings['account_disallowed_expenses_fleet.warning_missing_disallowed_category'] = {
                    'alert_type': 'warning',
                    'args': [account[0].id for account in accounts],
                }
        return lines

    def _get_query(self, options, line_dict_id=None):
        # EXTENDS account_disallowed_expenses.
        select, from_, where, group_by, order_by, order_by_rate, params = super()._get_query(options, line_dict_id)
        current = self._parse_line_id(options, line_dict_id)
        params.update(current)
        lang = self.env.user.lang or get_lang(self.env).code

        select += """,
            ARRAY_AGG(fleet_rate.rate) fleet_rate,
            ARRAY_AGG(vehicle.id) vehicle_id,
            ARRAY_AGG(vehicle.name) vehicle_name,
            SUM(aml.balance * (
                CASE WHEN fleet_rate.rate IS NOT NULL
                THEN
                    CASE WHEN rate.rate IS NOT NULL
                    THEN
                        CASE WHEN fleet_rate.rate < rate.rate
                        THEN fleet_rate.rate
                        ELSE rate.rate
                        END
                    ELSE fleet_rate.rate
                    END
                ELSE rate.rate
                END)) / 100 AS fleet_disallowed_amount
        """
        from_ += """
            LEFT JOIN fleet_vehicle vehicle ON aml.vehicle_id = vehicle.id
            LEFT JOIN fleet_disallowed_expenses_rate fleet_rate ON fleet_rate.id = (
                SELECT r2.id FROm fleet_disallowed_expenses_rate r2
                JOIN fleet_vehicle v2 ON r2.vehicle_id = v2.id
                WHERE r2.date_from <= aml.date
                  AND v2.id = vehicle.id
                ORDER BY r2.date_from DESC LIMIT 1
            )
        """
        where += current.get('vehicle_id') and """
              AND vehicle.id = %(vehicle_id)s""" or ""
        where += current.get('account_id') and not current.get('vehicle_id') and options.get('vehicle_split') and """
              AND vehicle.id IS NULL""" or ""

        group_by = f" GROUP BY category.id, COALESCE(category.name->>'{lang}', category.name->>'en_US')"

        if len(current) == 1 and current.get('category_id'):
            # Expanding a category
            if options.get('vehicle_split'):
                group_by += ", (CASE WHEN aml.vehicle_id IS NOT NULL THEN aml.vehicle_id ELSE aml.account_id END)"
                order_by = " ORDER BY (CASE WHEN aml.vehicle_id IS NOT NULL THEN aml.vehicle_id ELSE aml.account_id END)"
            else:
                group_by += ", account.id"
                order_by = " ORDER BY account.id"
        elif current.get('vehicle_id') and not current.get('account_id'):
            # Expanding a vehicle
            group_by += ", vehicle.id, vehicle.name, account.id"
            order_by = " ORDER BY vehicle.id, vehicle.name, account.id"
        elif current.get('account_id') and options.get('multi_rate_in_period'):
            # Expanding an account
            if options.get('vehicle_split'):
                group_by += ",vehicle.id, vehicle.name, rate.rate, fleet_rate.rate"
                order_by = " ORDER BY vehicle.id, vehicle.name, rate.rate, fleet_rate.rate"
            else:
                group_by += ", rate.rate, fleet_rate.rate"
                order_by = " ORDER BY rate.rate, fleet_rate.rate"

        return select, from_, where, group_by, order_by, order_by_rate, params

    def _parse_line_id(self, options, line_id):
        # OVERRIDES account_disallowed_expenses.

        current = {'category_id': None}

        if not line_id:
            return current

        for dummy, model, record_id in self.env['account.report']._parse_line_id(line_id):
            if model == 'account.disallowed.expenses.category':
                current.update({'category_id': record_id})
            if model == 'fleet.vehicle':
                current.update({'vehicle_id': record_id})
            if model == 'account.account':
                current.update({'account_id': record_id})
            if model == 'account.disallowed.expenses.rate':
                if model == 'fleet.vehicle':
                    current.update({'fleet_rate': record_id})
                else:
                    current.update({'account_rate': record_id})

        return current

    def _build_line_id(self, options, current, level, parent=False, markup=None):
        # OVERRIDES account_disallowed_expenses.

        report = self.env['account.report'].browse(options['report_id'])
        parent_line_id = None
        line_id = report._get_generic_line_id('account.disallowed.expenses.category', current['category_id'])
        if current.get('vehicle_id') and options.get('vehicle_split'):
            parent_line_id = line_id
            line_id = report._get_generic_line_id('fleet.vehicle', current['vehicle_id'], parent_line_id=line_id)
        if current.get('account_id'):
            parent_line_id = line_id
            line_id = report._get_generic_line_id('account.account', current['account_id'], parent_line_id=line_id)
            # This handles the case of child account lines without any rate.
            # We replicate the account_id in the line id in order to differentiate the child's line id from its parent.
            if len(current) != level and not (current.get('account_rate') or current.get('fleet_rate')):
                parent_line_id = line_id
                line_id = report._get_generic_line_id('account.account', current['account_id'], parent_line_id=line_id)
        if current.get('account_rate'):
            parent_line_id = line_id
            line_id = report._get_generic_line_id('account.disallowed.expenses.rate', current['account_rate'], markup=markup, parent_line_id=line_id)
        if current.get('fleet_rate'):
            parent_line_id = line_id
            line_id = report._get_generic_line_id('fleet.disallowed.expenses.rate', current['fleet_rate'], markup=markup, parent_line_id=line_id)

        return parent_line_id if parent else line_id

    def _report_expand_unfoldable_line_category_line(self, line_dict_id, groupby, options, progress, offset, unfold_all_batch_data=None):
        # OVERRIDES account_disallowed_expenses.

        primary_fields = ['category_id', 'vehicle_id']
        secondary_fields = ['category_id', 'account_id']

        if options.get('vehicle_split'):
            results = self._get_query_results(options, line_dict_id, primary_fields, secondary_fields, 'vehicle_id')
        else:
            results = self._get_query_results(options, line_dict_id, secondary_fields)

        # We want to display non-unfoldable lines before unfoldable ones.
        # So we need 2 lists to store them separately.
        lines = []
        unfoldable_lines = []

        for group_key, result in results.items():
            current = self._parse_hierarchy_group_key(group_key)
            level = len(self._parse_line_id(options, line_dict_id)) + 1

            if options.get('vehicle_split') and current.get('vehicle_id'):
                current = self._filter_current(current, primary_fields)
                line = self._disallowed_expenses_get_vehicle_line(options, result, current, level)
            else:
                current = self._filter_current(current, secondary_fields)
                line = self._get_account_line(options, result, current, level)

            if line.get('unfoldable'):
                unfoldable_lines.append(line)
            else:
                lines.append(line)

        return {'lines': lines + unfoldable_lines}

    def _report_expand_unfoldable_line_account_line(self, line_dict_id, groupby, options, progress, offset, unfold_all_batch_data=None):
        # OVERRIDES account_disallowed_expenses.

        primary_fields = ['category_id', 'vehicle_id', 'account_id', 'fleet_rate']
        secondary_fields = ['category_id', 'account_id', 'account_rate', 'fleet_rate']

        if options.get('vehicle_split'):
            results = self._get_query_results(options, line_dict_id, primary_fields, secondary_fields, 'vehicle_id')
        else:
            results = self._get_query_results(options, line_dict_id, secondary_fields)

        lines = []

        for group_key, result in results.items():
            current = self._parse_hierarchy_group_key(group_key)
            level = len(self._parse_line_id(options, line_dict_id)) + 1

            if options.get('vehicle_split') and current.get('vehicle_id'):
                current = self._filter_current(current, primary_fields)
            else:
                current = self._filter_current(current, secondary_fields)

            base_line_values = list(result.values())[0]
            account_id = self._get_single_value(base_line_values, 'account_id')
            lines.append(self._get_rate_line(options, result, current, level, account_id))

        return {'lines': lines}

    def _report_expand_unfoldable_line_vehicle_line(self, line_dict_id, groupby, options, progress, offset, unfold_all_batch_data=None):
        results = self._get_query_results(options, line_dict_id, ['category_id', 'vehicle_id', 'account_id'])
        lines = []

        for group_key, result in results.items():
            current = self._parse_hierarchy_group_key(group_key)
            level = len(self._parse_line_id(options, line_dict_id)) + 1

            if options.get('vehicle_split') and current.get('fleet_rate'):
                base_line_values = list(result.values())[0]
                account_id = self._get_single_value(base_line_values, 'account_id')
                lines.append(self._get_rate_line(options, result, current, level, account_id))
            else:
                lines.append(self._get_account_line(options, result, current, level))

        return {'lines': lines}

    def _disallowed_expenses_get_vehicle_line(self, options, values, current, level):
        base_line_values = list(values.values())[0]
        return {
            **self._get_base_line(options, current, level),
            'name': base_line_values['vehicle_name'][0],
            'columns': self._get_column_values(options, values),
            'level': level,
            'unfoldable': True,
            'caret_options': False,
            'expand_function': '_report_expand_unfoldable_line_vehicle_line',
        }

    def _get_current_rate(self, values):
        # OVERRIDES account_disallowed_expenses.
        fleet_rate = self._get_single_value(values, 'fleet_rate')
        account_rate = self._get_single_value(values, 'account_rate')

        current_rate = None
        if fleet_rate is not False:
            if fleet_rate is not None:
                if account_rate:
                    current_rate = min(account_rate, fleet_rate)
                else:
                    current_rate = fleet_rate
            elif account_rate:
                current_rate = account_rate

        return current_rate

    def _get_current_disallowed_amount(self, values):
        # EXTENDS account_disallowed_expenses.
        res = super()._get_current_disallowed_amount(values)
        return values['fleet_disallowed_amount'] if any(values['vehicle_id']) else res

    def _filter_current(self, current, fields):
        return {key: val for key, val in current.items() if key in fields}

    def action_open_accounts(self, options, params):
        return {
            'type': 'ir.actions.act_window',
            'name': _("Accounts missing a disallowed expense category"),
            'res_model': 'account.account',
            'views': [(False, 'list'), (False, 'form')],
            'domain': [('id', 'in', params['args'])],
        }
