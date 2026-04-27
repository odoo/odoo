# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _
from odoo.tools import format_date, SQL, Query
from collections import defaultdict

MAX_NAME_LENGTH = 50


class AssetsReportCustomHandler(models.AbstractModel):
    _name = 'account.asset.report.handler'
    _inherit = 'account.report.custom.handler'
    _description = 'Assets Report Custom Handler'

    def _get_custom_display_config(self):
        return {
            'client_css_custom_class': 'depreciation_schedule',
            'templates': {
                'AccountReportFilters': 'account_asset.DepreciationScheduleFilters',
            }
        }

    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals, warnings=None):
        lines, totals_by_column_group = self._generate_report_lines_without_grouping(report, options)
        # add the groups by grouping_field
        if options['assets_grouping_field'] != 'none':
            lines = self._group_by_field(report, lines, options)
        else:
            lines = report._regroup_lines_by_name_prefix(options, lines, '_report_expand_unfoldable_line_assets_report_prefix_group', 0)

        # add the total line
        total_columns = []
        for column_data in options['columns']:
            col_value = totals_by_column_group[column_data['column_group_key']].get(column_data['expression_label'])
            col_value = col_value if column_data.get('figure_type') == 'monetary' else ''

            total_columns.append(report._build_column_dict(col_value, column_data, options=options))

        if lines:
            lines.append({
                'id': report._get_generic_line_id(None, None, markup='total'),
                'level': 1,
                'name': _('Total'),
                'columns': total_columns,
                'unfoldable': False,
                'unfolded': False,
            })

        return [(0, line) for line in lines]

    def _generate_report_lines_without_grouping(self, report, options, prefix_to_match=None, parent_id=None, forced_account_id=None):
        # construct a dictionary:
        #   {(account_id, asset_id, asset_group_id): {col_group_key: {expression_label_1: value, expression_label_2: value, ...}}}
        all_asset_ids = set()
        all_lines_data = {}
        for column_group_key, column_group_options in report._split_options_per_column_group(options).items():
            # the lines returned are already sorted by account_id!
            lines_query_results = self._query_lines(column_group_options, prefix_to_match=prefix_to_match, forced_account_id=forced_account_id)
            for account_id, asset_id, asset_group_id, cols_by_expr_label in lines_query_results:
                line_id = (account_id, asset_id, asset_group_id)
                all_asset_ids.add(asset_id)
                if line_id not in all_lines_data:
                    all_lines_data[line_id] = {column_group_key: []}
                all_lines_data[line_id][column_group_key] = cols_by_expr_label

        column_names = [
            'assets_date_from', 'assets_plus', 'assets_minus', 'assets_date_to', 'depre_date_from',
            'depre_plus', 'depre_minus', 'depre_date_to', 'balance'
        ]
        totals_by_column_group = defaultdict(lambda: dict.fromkeys(column_names, 0.0))

        # Browse all the necessary assets in one go, to minimize the number of queries
        assets_cache = {asset.id: asset for asset in self.env['account.asset'].browse(all_asset_ids)}

        # construct the lines, 1 at a time
        lines = []
        company_currency = self.env.company.currency_id
        column_expression = self.env['account.report.expression']
        for (account_id, asset_id, asset_group_id), col_group_totals in all_lines_data.items():
            all_columns = []
            for column_data in options['columns']:
                col_group_key = column_data['column_group_key']
                expr_label = column_data['expression_label']
                if col_group_key not in col_group_totals or expr_label not in col_group_totals[col_group_key]:
                    all_columns.append(report._build_column_dict(None, None))
                    continue

                col_value = col_group_totals[col_group_key][expr_label]
                col_data = None if col_value is None else column_data

                all_columns.append(report._build_column_dict(col_value, col_data, options=options, column_expression=column_expression, currency=company_currency))

                # add to the total line
                if column_data['figure_type'] == 'monetary':
                    totals_by_column_group[column_data['column_group_key']][column_data['expression_label']] += col_value

            name = assets_cache[asset_id].name
            line = {
                'id': report._get_generic_line_id('account.asset', asset_id, parent_line_id=parent_id),
                'level': 2,
                'name': name,
                'columns': all_columns,
                'unfoldable': False,
                'unfolded': False,
                'caret_options': 'account_asset_line',
                'assets_account_id': account_id,
                'assets_asset_group_id': asset_group_id,
            }
            if parent_id:
                line['parent_id'] = parent_id
            if len(name) >= MAX_NAME_LENGTH:
                line['title_hover'] = name
            lines.append(line)

        return lines, totals_by_column_group

    def _caret_options_initializer(self):
        # Use 'caret_option_open_record_form' defined in account_reports rather than a custom function
        return {
            'account_asset_line': [
                {'name': _("Open Asset"), 'action': 'caret_option_open_record_form'},
            ]
        }

    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(report, options, previous_options=previous_options)
        column_group_options_map = report._split_options_per_column_group(options)

        for col in options['columns']:
            column_group_options = column_group_options_map[col['column_group_key']]
            # Dynamic naming of columns containing dates
            if col['expression_label'] == 'balance':
                col['name'] = '' # The column label will be displayed in the subheader
            if col['expression_label'] in ['assets_date_from', 'depre_date_from']:
                col['name'] = format_date(self.env, column_group_options['date']['date_from'])
            elif col['expression_label'] in ['assets_date_to', 'depre_date_to']:
                col['name'] = format_date(self.env, column_group_options['date']['date_to'])

        options['custom_columns_subheaders'] = [
            {"name": _("Characteristics"), "colspan": 4},
            {"name": _("Assets"), "colspan": 4},
            {"name": _("Depreciation"), "colspan": 4},
            {"name": _("Book Value"), "colspan": 1}
        ]

        # Group by account by default
        options['assets_grouping_field'] = previous_options.get('assets_grouping_field') or 'account_id'
        # If group by account is activated, activate the hierarchy (which will group by account group as well) if
        # the company has at least one account group, otherwise only group by account
        has_account_group = self.env['account.group'].search_count([('company_id', '=', self.env.company.id)], limit=1)
        hierarchy_activated = previous_options.get('hierarchy', True)
        options['hierarchy'] = has_account_group and hierarchy_activated or False

    def _query_lines(self, options, prefix_to_match=None, forced_account_id=None):
        """
        Returns a list of tuples: [(asset_id, account_id, asset_group_id, [{expression_label: value}])]
        """
        lines = []
        asset_lines = self._query_values(options, prefix_to_match=prefix_to_match, forced_account_id=forced_account_id)

        # Assign the gross increases sub assets to their main asset (parent)
        parent_lines = []
        children_lines = defaultdict(list)
        for al in asset_lines:
            if al['parent_id']:
                children_lines[al['parent_id']] += [al]
            else:
                parent_lines += [al]

        for al in parent_lines:

            asset_children_lines = children_lines[al['asset_id']]
            asset_parent_values = self._get_parent_asset_values(options, al, asset_children_lines)

            # Format the data
            columns_by_expr_label = {
                "acquisition_date": al["asset_acquisition_date"] and format_date(self.env, al["asset_acquisition_date"]) or "",  # Characteristics
                "first_depreciation": al["asset_date"] and format_date(self.env, al["asset_date"]) or "",
                "method": (al["asset_method"] == "linear" and _("Linear")) or (al["asset_method"] == "degressive" and _("Declining")) or _("Dec. then Straight"),
                **asset_parent_values
            }

            lines.append((al['account_id'], al['asset_id'], al['asset_group_id'], columns_by_expr_label))
        return lines

    def _get_parent_asset_values(self, options, asset_line, asset_children_lines):
        """ Compute the values needed for the depreciation schedule for each parent asset
        Overridden in l10n_ro_saft.account_general_ledger"""

        # Compute the depreciation rate string
        if asset_line['asset_method'] == 'linear' and asset_line['asset_method_number']:  # some assets might have 0 depreciation because they don't lose value
            total_months = int(asset_line['asset_method_number']) * int(asset_line['asset_method_period'])
            months = total_months % 12
            years = total_months // 12
            asset_depreciation_rate = " ".join(part for part in [
                years and _("%(years)s y", years=years),
                months and _("%(months)s m", months=months),
            ] if part)
        elif asset_line['asset_method'] == 'linear':
            asset_depreciation_rate = '0.00 %'
        else:
            asset_depreciation_rate = ('{:.2f} %').format(float(asset_line['asset_method_progress_factor']) * 100)

        # Manage the opening of the asset
        opening = (asset_line['asset_acquisition_date'] or asset_line['asset_date']) < fields.Date.to_date(options['date']['date_from'])

        # Get the main values of the board for the asset
        depreciation_opening = asset_line['depreciated_before']
        depreciation_add = asset_line['depreciated_during']
        depreciation_minus = 0.0

        asset_disposal_value = (
            asset_line['asset_disposal_value']
            if (
                asset_line['asset_disposal_date']
                and asset_line['asset_disposal_date'] <= fields.Date.to_date(options['date']['date_to'])
            )
            else 0.0
        )

        asset_opening = asset_line['asset_original_value'] if opening else 0.0
        asset_add = 0.0 if opening else asset_line['asset_original_value']
        asset_minus = 0.0
        asset_salvage_value = asset_line.get('asset_salvage_value', 0.0)

        # Add the main values of the board for all the sub assets (gross increases)
        for child in asset_children_lines:
            depreciation_opening += child['depreciated_before']
            depreciation_add += child['depreciated_during']

            opening = (child['asset_acquisition_date'] or child['asset_date']) < fields.Date.to_date(options['date']['date_from'])
            asset_opening += child['asset_original_value'] if opening else 0.0
            asset_add += 0.0 if opening else child['asset_original_value']

        # Compute the closing values
        asset_closing = asset_opening + asset_add - asset_minus
        depreciation_closing = depreciation_opening + depreciation_add - depreciation_minus
        asset_currency = self.env['res.currency'].browse(asset_line['asset_currency_id'])

        # Manage the closing of the asset
        if (
            asset_line['asset_state'] == 'close'
            and asset_line['asset_disposal_date']
            and asset_line['asset_disposal_date'] <= fields.Date.to_date(options['date']['date_to'])
            and asset_currency.compare_amounts(depreciation_closing, asset_closing - asset_salvage_value) == 0
        ):
            depreciation_add -= asset_disposal_value
            depreciation_minus += depreciation_closing - asset_disposal_value
            depreciation_closing = 0.0
            asset_minus += asset_closing
            asset_closing = 0.0

        # Manage negative assets (credit notes)
        if asset_currency.compare_amounts(asset_line['asset_original_value'], 0) < 0:
            asset_add, asset_minus = -asset_minus, -asset_add
            depreciation_add, depreciation_minus = -depreciation_minus, -depreciation_add

        return {
            'duration_rate': asset_depreciation_rate,
            'asset_disposal_value': asset_disposal_value,
            'assets_date_from': asset_opening,
            'assets_plus': asset_add,
            'assets_minus': asset_minus,
            'assets_date_to': asset_closing,
            'depre_date_from': depreciation_opening,
            'depre_plus': depreciation_add,
            'depre_minus': depreciation_minus,
            'depre_date_to': depreciation_closing,
            'balance': asset_closing - depreciation_closing,
        }

    def _group_by_field(self, report, lines, options):
        """
        This function adds the grouping lines on top of each group of account.asset
        It iterates over the lines, change the line_id of each line to include the account.account.id and the
        account.asset.id.
        """
        if not lines:
            return lines

        line_vals_per_grouping_field_id = {}
        parent_model = 'account.account' if options['assets_grouping_field'] == 'account_id' else 'account.asset.group'
        for line in lines:
            parent_id = line.get('assets_account_id') if options['assets_grouping_field'] == 'account_id' else line.get('assets_asset_group_id')

            model, res_id = report._get_model_info_from_id(line['id'])

            # replace the line['id'] to add the parent id
            line['id'] = report._build_line_id([
                (None, parent_model, parent_id),
                (None, 'account.asset', res_id)
            ])

            is_parent_in_unfolded_lines = any(
                report._get_model_info_from_id(unfolded_line_id) == (parent_model, parent_id)
                for unfolded_line_id in options.get('unfolded_lines')
            )
            line_vals_per_grouping_field_id.setdefault(parent_id, {
                # We don't assign a name to the line yet, so that we can batch the browsing of the parent objects
                'id': report._build_line_id([(None, parent_model, parent_id)]),
                'columns': [], # Filled later
                'unfoldable': True,
                'unfolded': is_parent_in_unfolded_lines or options.get('unfold_all'),
                'level': 1,

                # This value is stored here for convenience; it will be removed from the result
                'group_lines': [],
            })['group_lines'].append(line)

        # Generate the result
        rslt_lines = []
        idx_monetary_columns = [idx_col for idx_col, col in enumerate(options['columns']) if col['figure_type'] == 'monetary']
        parent_recordset = self.env[parent_model].browse(line_vals_per_grouping_field_id.keys())

        for parent_field in parent_recordset:
            parent_line_vals = line_vals_per_grouping_field_id[parent_field.id]
            if options['assets_grouping_field'] == 'account_id':
                parent_line_vals['name'] = f"{parent_field.code} {parent_field.name}"
            else:
                parent_line_vals['name'] = parent_field.name or _('(No %s)', parent_field._description)

            rslt_lines.append(parent_line_vals)

            group_totals = {column_index: 0 for column_index in idx_monetary_columns}
            group_lines = report._regroup_lines_by_name_prefix(
                options,
                parent_line_vals.pop('group_lines'),
                '_report_expand_unfoldable_line_assets_report_prefix_group',
                parent_line_vals['level'],
                parent_line_dict_id=parent_line_vals['id'],
            )

            for parent_subline in group_lines:
                # Add this line to the group totals
                for column_index in idx_monetary_columns:
                    group_totals[column_index] += parent_subline['columns'][column_index].get('no_format', 0)

                # Setup the parent and add the line to the result
                parent_subline['parent_id'] = parent_line_vals['id']
                rslt_lines.append(parent_subline)

            # Add totals (columns) to the parent line
            for column_index in range(len(options['columns'])):
                parent_line_vals['columns'].append(report._build_column_dict(
                    group_totals.get(column_index, ''),
                    options['columns'][column_index],
                    options=options,
                ))

        return rslt_lines

    def _query_values(self, options, prefix_to_match=None, forced_account_id=None):
        "Get the data from the database"

        self.env['account.move.line'].check_access('read')
        self.env['account.asset'].check_access('read')

        query = Query(self.env, alias='asset', table=SQL.identifier('account_asset'))
        account_alias = query.join(lhs_alias='asset', lhs_column='account_asset_id', rhs_table='account_account', rhs_column='id', link='account_asset_id')
        query.add_join('LEFT JOIN', alias='move', table='account_move', condition=SQL(f"""
            move.asset_id = asset.id AND move.state {"!= 'cancel'" if options.get('all_entries') else "= 'posted'"}
        """))

        account_code = self.env['account.account']._field_to_sql(account_alias, 'code', query)
        account_name = self.env['account.account']._field_to_sql(account_alias, 'name')
        account_id = SQL.identifier(account_alias, 'id')

        if prefix_to_match:
            query.add_where(SQL("asset.name ILIKE %s", f"{prefix_to_match}%"))
        if forced_account_id:
            query.add_where(SQL("%s = %s", account_id, forced_account_id))

        analytic_account_ids = []
        if options.get('analytic_accounts') and not any(x in options.get('analytic_accounts_list', []) for x in options['analytic_accounts']):
            analytic_account_ids += [[str(account_id) for account_id in options['analytic_accounts']]]
        if options.get('analytic_accounts_list'):
            analytic_account_ids += [[str(account_id) for account_id in options.get('analytic_accounts_list')]]
        if analytic_account_ids:
            query.add_where(SQL('%s && %s', analytic_account_ids, self.env['account.asset']._query_analytic_accounts('asset')))

        selected_journals = tuple(journal['id'] for journal in options.get('journals', []) if journal['model'] == 'account.journal' and journal['selected'])
        if selected_journals:
            query.add_where(SQL("asset.journal_id in %s", selected_journals))

        sql = SQL(
            """
            SELECT asset.id AS asset_id,
                   asset.parent_id AS parent_id,
                   asset.name AS asset_name,
                   asset.asset_group_id AS asset_group_id,
                   asset.original_value AS asset_original_value,
                   asset.currency_id AS asset_currency_id,
                   COALESCE(asset.salvage_value, 0) as asset_salvage_value,
                   MIN(move.date) AS asset_date,
                   asset.disposal_date AS asset_disposal_date,
                   asset.acquisition_date AS asset_acquisition_date,
                   asset.method AS asset_method,
                   asset.method_number AS asset_method_number,
                   asset.method_period AS asset_method_period,
                   asset.method_progress_factor AS asset_method_progress_factor,
                   asset.state AS asset_state,
                   asset.company_id AS company_id,
                   %(account_code)s AS account_code,
                   %(account_name)s AS account_name,
                   %(account_id)s AS account_id,
                   COALESCE(SUM(move.depreciation_value) FILTER (WHERE move.date < %(date_from)s), 0) + COALESCE(asset.already_depreciated_amount_import, 0) AS depreciated_before,
                   COALESCE(SUM(move.depreciation_value) FILTER (WHERE move.date BETWEEN %(date_from)s AND %(date_to)s), 0) AS depreciated_during,
                   COALESCE(SUM(move.depreciation_value) FILTER (WHERE move.date BETWEEN %(date_from)s AND %(date_to)s AND move.asset_number_days IS NULL), 0) AS asset_disposal_value
              FROM %(from_clause)s
             WHERE %(where_clause)s
               AND asset.company_id in %(company_ids)s
               AND (asset.acquisition_date <= %(date_to)s OR move.date <= %(date_to)s)
               AND (asset.disposal_date >= %(date_from)s OR asset.disposal_date IS NULL)
               AND (asset.state not in ('model', 'draft', 'cancelled') OR (asset.state = 'draft' AND %(include_draft)s))
               AND asset.active = 't'
          GROUP BY asset.id, account_id, account_code, account_name
          ORDER BY account_code, asset.acquisition_date, asset.id;
            """,
            account_code=account_code,
            account_name=account_name,
            account_id=account_id,
            date_from=options['date']['date_from'],
            date_to=options['date']['date_to'],
            from_clause=query.from_clause,
            where_clause=query.where_clause or SQL('TRUE'),
            company_ids=tuple(self.env['account.report'].get_report_company_ids(options)),
            include_draft=options.get('all_entries', False),
        )

        self._cr.execute(sql)
        results = self._cr.dictfetchall()
        return results

    def _report_expand_unfoldable_line_assets_report_prefix_group(self, line_dict_id, groupby, options, progress, offset, unfold_all_batch_data=None):
        matched_prefix = self.env['account.report']._get_prefix_groups_matched_prefix_from_line_id(line_dict_id)
        report = self.env['account.report'].browse(options['report_id'])

        lines, _totals_by_column_group = self._generate_report_lines_without_grouping(
            report,
            options,
            prefix_to_match=matched_prefix,
            parent_id=line_dict_id,
            forced_account_id=self.env['account.report']._get_res_id_from_line_id(line_dict_id, 'account.account'),
        )

        lines = report._regroup_lines_by_name_prefix(
            options,
            lines,
            '_report_expand_unfoldable_line_assets_report_prefix_group',
            len(matched_prefix),
            matched_prefix=matched_prefix,
            parent_line_dict_id=line_dict_id,
        )

        return {
            'lines': lines,
            'offset_increment': len(lines),
            'has_more': False,
        }


class AssetsReport(models.Model):
    _inherit = 'account.report'

    def _get_caret_option_view_map(self):
        view_map = super()._get_caret_option_view_map()
        view_map['account.asset.line'] = 'account_asset.view_account_asset_expense_form'
        return view_map
