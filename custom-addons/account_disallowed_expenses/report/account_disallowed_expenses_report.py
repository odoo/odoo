# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _
from odoo.tools.misc import get_lang


class DisallowedExpensesCustomHandler(models.AbstractModel):
    _name = 'account.disallowed.expenses.report.handler'
    _inherit = 'account.report.custom.handler'
    _description = 'Disallowed Expenses Custom Handler'

    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals, warnings=None):
        results = self._get_query_results(options, primary_fields=['category_id'])
        lines = []

        totals = {
            column_group_key: {key: 0.0 for key in ['total_amount', 'disallowed_amount']}
            for column_group_key in options['column_groups']
        }

        for group_key, result in results.items():
            current = self._parse_hierarchy_group_key(group_key)
            lines.append((0, self._get_category_line(options, result, current, len(current))))
            self._update_total_values(totals, options, result)

        if (lines):
            lines.append((0, self._get_total_line(report, options, totals)))

        return lines

    def _custom_options_initializer(self, report, options, previous_options=None):
        # Check if there are multiple rates
        super()._custom_options_initializer(report, options, previous_options=previous_options)
        period_domain = [('date_from', '>=', options['date']['date_from']), ('date_from', '<=', options['date']['date_to'])]
        rg = self.env['account.disallowed.expenses.rate']._read_group(
            period_domain,
            ['category_id'],
            having=[('__count', '>', 1)],
            limit=1,
        )
        options['multi_rate_in_period'] = bool(rg)

    def _custom_line_postprocessor(self, report, options, lines, warnings=None):
        if warnings is not None and options['multi_rate_in_period']:
            warnings['account_disallowed_expenses.warning_multi_rate'] = {}
        return lines

    def _caret_options_initializer(self):
        return {
            'account.account': [
                {'name': _("General Ledger"), 'action': 'caret_option_open_general_ledger'},
                {'name': _("Journal Items"), 'action': 'open_journal_items'},
            ],
        }

    def open_journal_items(self, options, params):
        ctx = {
            'search_default_group_by_account': 1,
            'search_default_posted': 0 if options.get('all_entries') else 1,
            'date_from': options.get('date', {}).get('date_from'),
            'date_to': options.get('date', {}).get('date_to'),
            'expand': 1,
        }

        if options.get('date', {}).get('date_from'):
            ctx['search_default_date_between'] = 1
        else:
            ctx['search_default_date_before'] = 1

        domain = [('display_type', 'not in', ('line_section', 'line_note'))]

        model_to_domain = {
            'account.disallowed.expenses.category': 'account_id.disallowed_expenses_category_id',
            'account.account': 'account_id',
            'fleet.vehicle': 'vehicle_id',
        }

        for markup, res_model, res_id in self.env['account.report']._parse_line_id(params.get('line_id')):
            if model_to_domain.get(res_model):
                domain.append((model_to_domain[res_model], '=', res_id))
            if markup:
                ctx['search_default_account_id'] = int(markup)

        return {
            'name': 'Journal Items',
            'view_mode': 'tree',
            'res_model': 'account.move.line',
            'views': [(False, 'list')],
            'type': 'ir.actions.act_window',
            'domain': domain,
            'context': ctx,
        }

    def _get_query(self, options, line_dict_id=None):
        """ Generates all the query elements based on the 'options' and the 'line_dict_id'.
            :param options:         The report options.
            :param line_dict_id:    The generic id of the line being expanded (optional).
            :return:                The query, split into several elements that can be overridden in child reports.
        """
        company_ids = tuple(self.env['account.report'].get_report_company_ids(options))
        current = self._parse_line_id(options, line_dict_id)
        params = {
            'date_to': options['date']['date_to'],
            'date_from': options['date']['date_from'],
            'company_ids': company_ids,
            'lang': self.env.user.lang or get_lang(self.env).code,
            **current,
        }

        lang = self.env.user.lang or get_lang(self.env).code
        if self.pool['account.account'].name.translate:
            account_name = f"COALESCE(account.name->>'{lang}', account.name->>'en_US')"
        else:
            account_name = 'account.name'

        select = f"""
            SELECT
                %(column_group_key)s AS column_group_key,
                SUM(aml.balance) AS total_amount,
                ARRAY_AGG({account_name}) account_name,
                ARRAY_AGG(account.code) account_code,
                ARRAY_AGG(category.id) category_id,
                ARRAY_AGG(COALESCE(category.name->>'{lang}', category.name->>'en_US')) category_name,
                ARRAY_AGG(category.code) category_code,
                ARRAY_AGG(account.company_id) company_id,
                ARRAY_AGG(aml.account_id) account_id,
                ARRAY_AGG(rate.rate) account_rate,
                SUM(aml.balance * rate.rate) / 100 AS account_disallowed_amount"""

        from_ = """
            FROM account_move_line aml
            JOIN account_move move ON aml.move_id = move.id
            JOIN account_account account ON aml.account_id = account.id
            JOIN account_disallowed_expenses_category category ON account.disallowed_expenses_category_id = category.id
            LEFT JOIN account_disallowed_expenses_rate rate ON rate.id = (
                SELECT r2.id FROM account_disallowed_expenses_rate r2
                LEFT JOIN account_disallowed_expenses_category c2 ON r2.category_id = c2.id
                WHERE r2.date_from <= aml.date
                  AND c2.id = category.id
                ORDER BY r2.date_from DESC LIMIT 1
            )"""
        where = """
            WHERE aml.company_id in %(company_ids)s
              AND aml.date >= %(date_from)s AND aml.date <= %(date_to)s
              AND move.state != 'cancel'"""
        where += current.get('category_id') and " AND category.id = %(category_id)s" or ""
        where += current.get('account_id') and " AND aml.account_id = %(account_id)s" or ""
        where += current.get('account_rate') and " AND rate.rate = %(account_rate)s" or ""
        where += not options.get('all_entries') and " AND move.state = 'posted'" or ""

        group_by = f" GROUP BY category.id, COALESCE(category.name->>'{lang}', category.name->>'en_US')"
        group_by += current.get('category_id') and ", account_id" or ""
        group_by += current.get('account_id') and options['multi_rate_in_period'] and ", rate.rate" or ""

        order_by = " ORDER BY category_id, account_id"
        order_by_rate = ", account_rate"

        return select, from_, where, group_by, order_by, order_by_rate, params

    def _parse_line_id(self, options, line_id):
        current = {'category_id': None}

        if not line_id:
            return current

        for dummy, model, record_id in self.env['account.report']._parse_line_id(line_id):
            if model == 'account.disallowed.expenses.category':
                current['category_id'] = record_id
            if model == 'account.account':
                current['account_id'] = record_id
            if model == 'account.disallowed.expenses.rate':
                current['account_rate'] = record_id

        return current

    def _build_line_id(self, options, current, level, parent=False, markup=None):
        report = self.env['account.report'].browse(options['report_id'])
        parent_line_id = None
        line_id = report._get_generic_line_id('account.disallowed.expenses.category', current['category_id'])
        if current.get('account_id'):
            parent_line_id = line_id
            line_id = report._get_generic_line_id('account.account', current['account_id'], parent_line_id=line_id)
        if current.get('account_rate'):
            parent_line_id = line_id
            line_id = report._get_generic_line_id('account.disallowed.expenses.rate', current['account_rate'], markup=markup, parent_line_id=line_id)

        return parent_line_id if parent else line_id

    def _get_query_results(self, options, line_dict_id=None, primary_fields=None, secondary_fields=None, selector=None):
        grouped_results = {}

        for column_group_key, column_group_options in self.env['account.report']._split_options_per_column_group(options).items():
            select, from_, where, group_by, order_by, order_by_rate, params = self._get_query(column_group_options, line_dict_id)
            params['column_group_key'] = column_group_key
            self.env.cr.execute(select + from_ + where + group_by + order_by + order_by_rate, params)

            for results in self.env.cr.dictfetchall():
                key = self._get_group_key(results, primary_fields, secondary_fields, selector)
                grouped_results.setdefault(key, {})[column_group_key] = results

        return grouped_results

    def _get_group_key(self, results, primary_fields, secondary_fields, selector):
        fields = []
        if selector is None or self._get_single_value(results, selector):
            fields = primary_fields
        elif secondary_fields is not None:
            fields = secondary_fields

        group_key_list = []
        for group_key in fields:
            group_key_id = self._get_single_value(results, group_key)
            if group_key_id:
                group_key_list.append(group_key + '~' + (group_key_id and str(group_key_id) or ''))

        return '|'.join(group_key_list)

    def _parse_hierarchy_group_key(self, group_key):
        return {
            item: int(float(item_id))
            for item, item_id
            in [
                full_id.split('~')
                for full_id
                in (group_key.split('|'))
            ]
        }

    def _report_expand_unfoldable_line_category_line(self, line_dict_id, groupby, options, progress, offset, unfold_all_batch_data=None):
        results = self._get_query_results(options, line_dict_id, ['category_id', 'account_id'])
        lines = []

        for group_key, result in results.items():
            current = self._parse_hierarchy_group_key(group_key)
            lines.append(self._get_account_line(options, result, current, len(current)))

        return {'lines': lines}

    def _report_expand_unfoldable_line_account_line(self, line_dict_id, groupby, options, progress, offset, unfold_all_batch_data=None):
        results = self._get_query_results(options, line_dict_id, ['category_id', 'account_id', 'account_rate'])
        lines = []

        for group_key, result in results.items():
            current = self._parse_hierarchy_group_key(group_key)
            base_line_values = list(result.values())[0]
            account_id = self._get_single_value(base_line_values, 'account_id')
            lines.append(self._get_rate_line(options, result, current, len(current), account_id))

        return {'lines': lines}

    def _get_column_values(self, options, values, is_total_line=False):
        column_values = []

        report = self.env['account.report'].browse(options['report_id'])
        for column in options['columns']:
            vals = values.get(column['column_group_key'], {})
            if vals and not is_total_line:
                vals['rate'] = self._get_current_rate(vals)
                vals['disallowed_amount'] = self._get_current_disallowed_amount(vals)
            col_val = vals.get(column['expression_label'])

            column_values.append(report._build_column_dict(
                col_val,
                column,
                options=options,
                digits=2 if column['figure_type'] == 'percentage' else None,
            ))

        return column_values

    def _update_total_values(self, total, options, values):
        for column_group_key in options['column_groups']:
            for key in total[column_group_key]:
                total[column_group_key][key] += values.get(column_group_key, {}).get(key) or 0.0

    def _get_total_line(self, report, options, totals):
        return {
            'id': report._get_generic_line_id(None, None, markup='total'),
            'name': _('Total'),
            'level': 1,
            'columns': self._get_column_values(options, totals, is_total_line=True),
        }

    def _get_category_line(self, options, values, current, level):
        base_line_values = list(values.values())[0]
        return {
            **self._get_base_line(options, current, level),
            'name': '%s %s' % (base_line_values['category_code'][0], base_line_values['category_name'][0]),
            'columns': self._get_column_values(options, values),
            'level': level,
            'unfoldable': True,
            'expand_function': '_report_expand_unfoldable_line_category_line',
        }

    def _get_account_line(self, options, values, current, level):
        base_line_values = list(values.values())[0]
        unfoldable = options.get('multi_rate_in_period')
        return {
            **self._get_base_line(options, current, level),
            'name': '%s %s' % (base_line_values['account_code'][0], base_line_values['account_name'][0]),
            'columns': self._get_column_values(options, values),
            'level': level,
            'unfoldable': unfoldable,
            'caret_options': False if unfoldable else 'account.account',
            'account_id': base_line_values['account_id'][0],
            'expand_function': unfoldable and '_report_expand_unfoldable_line_account_line',
        }

    def _get_rate_line(self, options, values, current, level, markup=None):
        base_line_values = list(values.values())[0]
        return {
            **self._get_base_line(options, current, level, markup),
            'name': f"{base_line_values['account_code'][0]} {base_line_values['account_name'][0]}",
            'columns': self._get_column_values(options, values),
            'level': level,
            'unfoldable': False,
            'caret_options': 'account.account',
            'account_id': base_line_values['account_id'][0],
        }

    def _get_base_line(self, options, current, level, markup=None):
        current_line_id = self._build_line_id(options, current, level, markup=markup)
        return {
            'id': current_line_id,
            'parent_id': self._build_line_id(options, current, level, parent=True, markup=markup, ),
            'unfolded': current_line_id in options.get('unfolded_lines') or options.get('unfold_all'),
        }

    def _get_single_value(self, values, key):
        return all(values[key][0] == x for x in values[key]) and values[key][0]

    def _get_current_rate(self, values):
        return self._get_single_value(values, 'account_rate') or None

    def _get_current_disallowed_amount(self, values):
        return values['account_disallowed_amount']
