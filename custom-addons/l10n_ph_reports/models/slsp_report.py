# Part of Odoo. See LICENSE file for full copyright and licensing details.
import contextlib
import io
import re
import xlsxwriter

from PIL import ImageFont

from odoo import api, models, _, fields
from odoo.exceptions import UserError
from odoo.tools import date_utils, float_repr
from odoo.tools.misc import format_date, get_lang, file_path


class SlspCustomHandler(models.AbstractModel):
    _name = 'l10n_ph.slsp.report.handler'
    _inherit = 'account.report.custom.handler'
    _description = 'Summary Lists of Sales and Purchases Custom Handler'

    def _get_custom_display_config(self):
        return {
            'templates': {
                'AccountReportFilters': 'l10n_ph_reports.SlspReportFilters',
            },
        }

    def _custom_options_initializer(self, report, options, previous_options=None):
        super()._custom_options_initializer(report, options, previous_options=previous_options)
        options.setdefault('buttons', []).append(
            {
                'name': _('Export SLSP'),
                'sequence': 5,  # As the export is a particular format from the BIR, we assume it will be the primary format used when exporting.
                'action': 'export_file',
                'action_param': 'export_slsp',
                'file_export_type': _('XLSX'),
            }
        )
        # Initialise the custom options for this report.
        options['include_no_tin'] = (previous_options or {}).get('include_no_tin', False)
        # Initialise the custom options for this report.
        options['include_imports'] = (previous_options or {}).get('include_imports', False)

    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals, warnings=None):
        report_lines = self._build_month_lines(report, options)
        if grand_total_line := self._build_grand_total_line(options):
            report_lines.append(grand_total_line)

        # Inject sequences on the dynamic lines
        return [(0, line) for line in report_lines]

    # First level, month rows

    def _build_month_lines(self, report, options):
        """ Fetches the months for which we have entries *that have tax grids* and build a report line for each of them. """
        month_lines = []
        params = []
        queries = []

        # 1) Build the queries to get the months
        for column_group_key, column_group_options in report._split_options_per_column_group(options).items():
            domain = [('move_id.move_type', '=', options['move_type'])]
            if not column_group_options.get('include_no_tin'):
                domain.append(('partner_id.vat', '!=', False))
            tables, where_clause, where_params = report._query_get(column_group_options, "strict_range", domain)
            params.append(column_group_key)
            params += where_params
            # The joins are there to filter out months for which we would not have any lines in the report.
            queries.append(
                f"""
                  SELECT (date_trunc('month', account_move_line.date::date) + interval '1 month' - interval '1 day')::date AS taxable_month,
                         %s                                                                                                AS column_group_key
                    FROM {tables}
                    JOIN account_account_tag_account_move_line_rel account_tag_rel ON account_tag_rel.account_move_line_id = account_move_line.id
                    JOIN account_account_tag account_tag ON account_tag.id = account_tag_rel.account_account_tag_id
                   WHERE {where_clause}
                GROUP BY taxable_month
                ORDER BY taxable_month DESC
            """
            )

        self.env.cr.execute(" UNION ALL ".join(queries), params)

        # 2) Make the lines
        unfold_all = options['export_mode'] == 'print' or options.get('unfold_all')
        for res in self._cr.dictfetchall():
            line_id = report._get_generic_line_id('', '', markup=str(res['taxable_month']))
            month_lines.append({
                'id': line_id,
                'name': format_date(self.env, res['taxable_month'], date_format='MMMM y'),
                'unfoldable': True,
                'unfolded': line_id in options['unfolded_lines'] or unfold_all,
                'columns': [{} for _column in options['columns']],
                'level': 0,
                'expand_function': '_report_expand_unfoldable_line_sls_expand_month',
            })

        return month_lines

    def _report_expand_unfoldable_line_sls_expand_month(self, line_dict_id, groupby, options, progress, offset, unfold_all_batch_data=None):
        """ Used to expand a month line and load the second level, being the partner lines. """
        report = self.env.ref("l10n_ph_reports.slsp_report")
        month = report._parse_line_id(line_dict_id)[-1][0]

        partner_lines_values = self._query_partners(options, report, month, offset)

        partner_lines = []
        has_more = False
        treated_results_count = 0
        next_progress = progress
        for partner_id, line_values in partner_lines_values.items():
            if options['export_mode'] != 'print' and report.load_more_limit and treated_results_count == report.load_more_limit:
                # We loaded one more than the limit on purpose: this way we know we need a "load more" line
                has_more = True
                break

            new_line = self._get_report_line_partner(options, partner_id, line_values, month, line_dict_id)
            partner_lines.append(new_line)
            next_progress = {
                column['column_group_key']: line_col.get('no_format', 0)
                for column, line_col in zip(options['columns'], new_line['columns'])
                if column['expression_label'] == 'balance'
            }
            treated_results_count += 1

        return {
            'lines': partner_lines,
            'offset_increment': treated_results_count,
            'has_more': has_more,
            'progress': next_progress,
        }

    def _query_partners(self, options, report, month, offset):
        """ Query the values for the partner line.
        The partner line will sum up the values for the different columns, while being filtered for the given month only.
        """
        limit = report.load_more_limit + 1 if report.load_more_limit and options['export_mode'] != 'print' else None
        end_date = fields.Date.from_string(month)  # Month is already set to the last day of the month.
        start_date = date_utils.start_of(end_date, 'month')
        params = []
        queries = []
        for column_group_key, column_group_options in report._split_options_per_column_group(options).items():
            domain = [
                ('move_id.move_type', '=', options['move_type']),
                # Make sure to only fetch records that are in the parent's row month
                ('date', '>=', start_date),
                ('date', '<=', end_date),
            ]
            if not column_group_options.get('include_no_tin'):
                domain.append(('partner_id.vat', '!=', False))
            tables, where_clause, where_params = report._query_get(column_group_options, "strict_range", domain=domain)
            tail_query, tail_params = report._get_engine_query_tail(offset, limit)
            currency_table_query = self.env['account.report']._get_query_currency_table(column_group_options)
            params.append(column_group_key)
            params += where_params
            params += tail_params
            lang = self.env.user.lang or get_lang(self.env).code
            if self.pool['account.account.tag'].name.translate:
                account_tag_name = f"COALESCE(account_tag.name->>'{lang}', account_tag.name->>'en_US')"
            else:
                account_tag_name = 'account_tag.name'
            queries.append(f"""
                  SELECT %s AS column_group_key,
                         cp.vat as partner_vat,
                         case when (cp.id = p.id and cp.is_company) or cp.id != p.id then cp.name else '' end as register_name,
                         p.id as partner_id,
                         case when p.is_company = false then p.name else '' end as partner_name,
                         p.last_name || ' ' || p.first_name || ' ' || p.middle_name as formatted_partner_name,
                         p.is_company as is_company,
                         REGEXP_REPLACE({account_tag_name}, '^[+-]', '') AS tag_name,
                         SUM(ROUND(COALESCE(account_move_line.balance, 0) * currency_table.rate, currency_table.precision)
                             * CASE WHEN account_tag.tax_negate THEN -1 ELSE 1 END
                             * CASE WHEN account_move_line.tax_tag_invert THEN -1 ELSE 1 END
                         ) AS balance
                    FROM {tables}
                    JOIN res_partner p ON p.id = account_move_line__move_id.partner_id
                    JOIN res_partner cp ON cp.id = p.commercial_partner_id
                    JOIN account_account_tag_account_move_line_rel account_tag_rel ON account_tag_rel.account_move_line_id = account_move_line.id
                    JOIN account_account_tag account_tag ON account_tag.id = account_tag_rel.account_account_tag_id
                    JOIN {currency_table_query}
                      ON currency_table.company_id = account_move_line.company_id
                   WHERE {where_clause}
                GROUP BY p.id, cp.id, {account_tag_name}
                {tail_query}
            """)

        self.env.cr.execute(" UNION ALL ".join(queries), params)
        return self._process_partner_lines(self.env.cr.dictfetchall(), options)

    def _process_partner_lines(self, data_dict, options):
        """ Taking in the values from the database, this will construct the column values by using the tax grid mapping
        set in the option of each report section.
        """
        lines_values = {}
        # We get the partners to get the correctly formatted address as we don't have by default in the db.
        partners = self.env['res.partner'].browse([values['partner_id'] for values in data_dict])
        partner_addresses = {
            partner.id: partner._display_address(without_company=True).replace('\n\n', '\n').replace('\n', ', ')  # Looks better in the Odoo view
            for partner in partners
        }
        for values in data_dict:
            # Initialise the move values
            if values['partner_id'] not in lines_values:
                lines_values[values['partner_id']] = {
                    'name': values['formatted_partner_name'] or values['partner_name'],
                    'register_name': values['register_name'],
                    'is_company': values['is_company'],
                    values['column_group_key']: {
                        'column_group_key': values['column_group_key'],
                        'partner_vat': values['partner_vat'],
                        'register_name': values['register_name'],
                        'partner_address': partner_addresses[values['partner_id']],
                    }
                }
            # Sum the balances on the right expression label.
            # We use a map of tax grids to do that easily.
            for expression_label, grids in options['report_grids_map'].items():
                if expression_label not in lines_values[values['partner_id']][values['column_group_key']]:
                    lines_values[values['partner_id']][values['column_group_key']][expression_label] = 0
                if values['tag_name'] in grids:  # In this report, we always sum, so it's easy
                    lines_values[values['partner_id']][values['column_group_key']][expression_label] += values['balance']

        lines_with_values = {}
        grids = list(options['report_grids_map'].keys())
        for line, value in lines_values.items():
            for column_group_key in options['column_groups']:
                if any(value[column_group_key][grid] != 0 for grid in grids):
                    lines_with_values[line] = value

        return lines_with_values

    def _get_report_line_partner(self, options, partner_id, line_values, month, parent_line):
        """ Format the given values to match the report line format. """
        report = self.env.ref("l10n_ph_reports.sls_report")

        line_columns = []
        for column in options['columns']:
            col_value = line_values[column['column_group_key']].get(column['expression_label'])
            line_columns.append(report._build_column_dict(
                col_value=col_value or '',
                col_data=column,
                options=options,
            ))

        # Set the markup with the month, we can reuse it to filter the detailed move lines
        line_id = report._get_generic_line_id('res.partner', partner_id, markup=month, parent_line_id=parent_line)
        unfold_all = options['export_mode'] == 'print' or options.get('unfold_all')
        return {
            'id': line_id,
            'parent_id': parent_line,
            'name': line_values['name'] or line_values['register_name'],
            'is_company': line_values['is_company'],  # This is only used when building the export, as we expect a slightly different behavior for companies
            'unfoldable': True,
            'unfolded': line_id in options['unfolded_lines'] or unfold_all,
            'columns': line_columns,
            'level': 1,
            'caret_options': 'res.partner',
            'expand_function': '_report_expand_unfoldable_line_sls_expand_partner',
        }

    def _report_expand_unfoldable_line_sls_expand_partner(self, line_dict_id, groupby, options, progress, offset, unfold_all_batch_data=None):
        """ Used to expand a month line and load the third level, being the account move lines. """
        report = self.env.ref("account_reports.partner_ledger_report")
        month, _model, partner_id = report._parse_line_id(line_dict_id)[-1]

        move_lines = []
        lines_values = self._query_moves(options, report, partner_id, month, offset)
        has_more = False
        treated_results_count = 0
        next_progress = progress

        for move_id, line_values in lines_values.items():
            if options['export_mode'] != 'print' and report.load_more_limit and treated_results_count == report.load_more_limit:
                # We loaded one more than the limit on purpose: this way we know we need a "load more" line
                has_more = True
                break

            new_line = self._get_report_line_move(options, move_id, line_values, line_dict_id)
            move_lines.append(new_line)
            next_progress = {
                column['column_group_key']: line_col.get('no_format', 0)
                for column, line_col in zip(options['columns'], new_line['columns'])
                if column['expression_label'] == 'balance'
            }
            treated_results_count += 1

        return {
            'lines': move_lines,
            'offset_increment': treated_results_count,
            'has_more': has_more,
            'progress': next_progress,
        }

    def _query_moves(self, options, report, partner_id, month, offset):
        """ Query the values for the partner line.
        The move line will sum up the values for the different columns, while being filtered for the given month only.
        """
        limit = report.load_more_limit + 1 if report.load_more_limit and options['export_mode'] != 'print' else None
        end_date = fields.Date.from_string(month)
        start_date = date_utils.start_of(end_date, 'month')
        params = []
        queries = []
        for column_group_key, column_group_options in report._split_options_per_column_group(options).items():
            tables, where_clause, where_params = report._query_get(column_group_options, "strict_range", domain=[
                ('move_id.move_type', '=', options['move_type']),
                # Make sure to only fetch records that are in the parent's row month
                ('date', '>=', start_date),
                ('date', '<=', end_date),
                ('move_id.partner_id', '=', partner_id),
            ])
            tail_query, tail_params = report._get_engine_query_tail(offset, limit)
            currency_table_query = self.env['account.report']._get_query_currency_table(column_group_options)
            params.append(column_group_key)
            params.extend(where_params)
            params.extend(tail_params)
            lang = self.env.user.lang or get_lang(self.env).code
            if self.pool['account.account.tag'].name.translate:
                account_tag_name = f"COALESCE(account_tag.name->>'{lang}', account_tag.name->>'en_US')"
            else:
                account_tag_name = 'account_tag.name'
            queries.append(f"""
                  SELECT %s AS column_group_key,
                         account_move_line__move_id.id AS move_id,
                         account_move_line__move_id.name AS move_name,
                         REGEXP_REPLACE({account_tag_name}, '^[+-]', '') AS tag_name,
                         SUM(ROUND(COALESCE(account_move_line.balance, 0) * currency_table.rate, currency_table.precision)
                             * CASE WHEN account_tag.tax_negate THEN -1 ELSE 1 END
                             * CASE WHEN account_move_line.tax_tag_invert THEN -1 ELSE 1 END
                         ) AS balance
                    FROM {tables}
                    JOIN account_account_tag_account_move_line_rel account_tag_rel ON account_tag_rel.account_move_line_id = account_move_line.id
                    JOIN account_account_tag account_tag ON account_tag.id = account_tag_rel.account_account_tag_id
                    JOIN {currency_table_query}
                      ON currency_table.company_id = account_move_line.company_id
                   WHERE {where_clause}
                GROUP BY account_move_line__move_id.id, {account_tag_name}
                {tail_query}
            """)

        self.env.cr.execute(" UNION ALL ".join(queries), params)
        return self._process_move_lines(self.env.cr.dictfetchall(), options)

    def _process_move_lines(self, data_dict, options):
        """ Taking in the values from the database, this will construct the column values by using the tax grid mapping
        set in the option of each report section.
        """
        lines_values = {}
        for values in data_dict:
            # Initialise the move values
            if values['move_id'] not in lines_values:
                lines_values[values['move_id']] = {
                    'name': values['move_name'],
                    values['column_group_key']: {
                        'column_group_key': values['column_group_key'],
                        'move_id': values['move_id'],
                        'move_name': values['move_name'],
                    }
                }
            # Sum the balances on the right expression label.
            # We use a map of tax grids to do that easily
            for expression_label, grids in options['report_grids_map'].items():
                if expression_label not in lines_values[values['move_id']][values['column_group_key']]:
                    lines_values[values['move_id']][values['column_group_key']][expression_label] = 0
                if values['tag_name'] in grids:  # In this report, we always sum so it's easy
                    lines_values[values['move_id']][values['column_group_key']][expression_label] += values['balance']

        lines_with_values = {}
        grids = list(options['report_grids_map'].keys())
        for line, value in lines_values.items():
            for column_group_key in options['column_groups']:
                if any(value[column_group_key][grid] != 0 for grid in grids):
                    lines_with_values[line] = value

        return lines_with_values

    def _get_report_line_move(self, options, move_id, line_values, partner_line_id):
        """ Format the given values to match the report line format. """
        report = self.env.ref("l10n_ph_reports.sls_report")

        line_columns = []
        for column in options['columns']:
            col_value = line_values[column['column_group_key']].get(column['expression_label'])
            line_columns.append(report._build_column_dict(
                col_value=col_value or '',
                col_data=column,
                options=options,
            ))

        line_id = report._get_generic_line_id('account.move', move_id, parent_line_id=partner_line_id)
        return {
            'id': line_id,
            'parent_id': partner_line_id,
            'name': line_values['name'],
            'unfoldable': False,
            'unfolded': False,
            'columns': line_columns,
            'level': 2,
            'caret_options': 'account.move',
        }

    # Grand total

    def _build_grand_total_line(self, options):
        """ The grand total line is the sum of all values in the given reporting period. """
        params = []
        queries = []
        report = self.env.ref("l10n_ph_reports.slp_report")

        for column_group_key, column_group_options in report._split_options_per_column_group(options).items():
            domain = [('move_id.move_type', '=', options['move_type'])]
            if not column_group_options.get('include_no_tin'):
                domain.append(('partner_id.vat', '!=', False))
            tables, where_clause, where_params = report._query_get(column_group_options, "strict_range", domain=domain)
            currency_table_query = self.env['account.report']._get_query_currency_table(column_group_options)
            params.append(column_group_key)
            params += where_params
            lang = self.env.user.lang or get_lang(self.env).code
            if self.pool['account.account.tag'].name.translate:
                account_tag_name = f"COALESCE(account_tag.name->>'{lang}', account_tag.name->>'en_US')"
            else:
                account_tag_name = 'account_tag.name'
            queries.append(f"""
                  SELECT %s AS column_group_key,
                         REGEXP_REPLACE({account_tag_name}, '^[+-]', '') AS tag_name,
                         SUM(ROUND(COALESCE(account_move_line.balance, 0) * currency_table.rate, currency_table.precision)
                             * CASE WHEN account_tag.tax_negate THEN -1 ELSE 1 END
                             * CASE WHEN account_move_line.tax_tag_invert THEN -1 ELSE 1 END
                         ) AS balance
                    FROM {tables}
                    JOIN res_partner p ON p.id = account_move_line__move_id.partner_id
                    JOIN res_partner cp ON cp.id = p.commercial_partner_id
                    JOIN account_account_tag_account_move_line_rel account_tag_rel ON account_tag_rel.account_move_line_id = account_move_line.id
                    JOIN account_account_tag account_tag ON account_tag.id = account_tag_rel.account_account_tag_id
                    JOIN {currency_table_query}
                      ON currency_table.company_id = account_move_line.company_id
                   WHERE {where_clause}
                GROUP BY column_group_key, {account_tag_name}
            """)
        self.env.cr.execute(" UNION ALL ".join(queries), params)
        results = self.env.cr.dictfetchall()
        return results and self._get_report_line_grand_total(options, self._process_grand_total_line(results, options))

    def _process_grand_total_line(self, data_dict, options):
        """ Taking in the values from the database, this will construct the column values by using the tax grid mapping
        set in the option of each report section.
        """
        lines_values = {}
        for values in data_dict:
            if values['column_group_key'] not in lines_values:
                lines_values[values['column_group_key']] = lines_values
            # Sum the balances on the right expression label.
            # We use a map of tax grids to do that easily
            for expression_label, grids in options['report_grids_map'].items():
                if expression_label not in lines_values[values['column_group_key']]:
                    lines_values[values['column_group_key']][expression_label] = 0
                if values['tag_name'] in grids:  # In this report, we always sum so it's easy
                    lines_values[values['column_group_key']][expression_label] += values['balance']
        return lines_values

    def _get_report_line_grand_total(self, options, res):
        """ Format the given values to match the report line format. """
        report = self.env.ref("l10n_ph_reports.sls_report")

        line_columns = []
        for column in options['columns']:
            col_value = res[column['column_group_key']].get(column['expression_label'])
            line_columns.append(report._build_column_dict(
                col_value=col_value or '',
                col_data=column,
                options=options,
            ))

        line_id = report._get_generic_line_id('', '', markup='grand_total')
        return {
            'id': line_id,
            'name': _('Grand Total'),
            'unfoldable': False,
            'unfolded': False,
            'columns': line_columns,
            'level': 0,
        }

    # xlsx export methods

    @api.model
    def export_slsp(self, options):
        """ Export the report to a XLSX file formatted base on the BIR standards """
        # We start by gathering the bold, italic and regular fonts to use later.
        fonts = {}
        for font_type in ('Reg', 'Bol', 'RegIta', 'BolIta'):
            try:
                lato_path = f'web/static/fonts/lato/Lato-{font_type}-webfont.ttf'
                fonts[font_type] = ImageFont.truetype(file_path(lato_path), 12)
            except (OSError, FileNotFoundError):
                # This won't give great result, but it will work.
                fonts[font_type] = ImageFont.load_default()

        report = self.env['account.report'].browse(options['report_id'])

        # If we are exporting from the composite report, we get the important options from the selected section.
        # Otherwise, we assume we are on a "custom" report that's only SLS or SLSP
        # (for example during tests, or if the user want to split the reports in two separate views)
        if report.section_report_ids:
            section = report.section_report_ids.filtered(lambda section: section.id == options['selected_section_id'])[:1]
            if not section:
                # Technically, this should never happen, but better be safe and return an error.
                raise UserError(_('The export can only be executed if a report section has been selected'))
            # We only need to get the move type, grid map and the column from the section. The rest is standard.
            section_options = section.get_options(options)
            options.update({
                'move_type': section_options['move_type'],
                'report_grids_map': section_options['report_grids_map'],
                'columns': section_options['columns'],
            })

        # in any case, we want the export mode and unfold_all set
        options.update({
            'unfold_all': True,
            'export_mode': 'print',
            'ignore_totals_below_sections': True,
        })

        # Get the lines, according to the options.
        lines = report._get_lines(options)

        # Prepare the workbook.
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {
            'in_memory': True,
            'strings_to_formulas': False,  # As we need to give a default value when using formulas, we need to handle them manually so this is not needed.
        })

        # Write the data.
        sheet = workbook.add_worksheet(_('sls') if options['move_type'] == 'out_invoice' else _('slp'))
        # Add the styles to the sheet to make it easier to get them later.
        sheet.styles = {
            'text': workbook.add_format({'font_name': 'Arial', 'border': 1, 'align': 'left'}),
            'title': workbook.add_format({'font_name': 'Arial', 'bold': True, 'border': 1, 'align': 'left'}),
            'monetary': workbook.add_format({'font_name': 'Arial', 'border': 1, 'align': 'right', 'num_format': '#,##0.00'}),
            'total': workbook.add_format({'font_name': 'Arial', 'bold': True, 'border': 1, 'align': 'right', 'num_format': '#,##0.00'}),
            'date': workbook.add_format({'font_name': 'Arial', 'border': 1, 'align': 'left', "num_format": "yyyy-mm-dd"}),
        }
        # Write the header part.
        self._slsp_write_header_data(sheet, fonts, options['move_type'])
        # Write the data part.
        self._slsp_write_invoice_data(sheet, fonts, lines, options['move_type'], report)
        # End of report.
        self._slsp_write_next_row(sheet, fonts, [])  # Empty row.
        self._slsp_write_next_row(sheet, fonts, [(_('END OF REPORT'), 1, sheet.styles['text'])])
        self._slsp_write_next_row(sheet, fonts, [])  # Empty row.

        # Finish the process and get the file.
        workbook.close()
        output.seek(0)
        generated_file = output.read()
        output.close()
        return {
            'file_name': _('sl_sales') if options['move_type'] == 'out_invoice' else _('sl_purchases'),
            'file_content': generated_file,
            'file_type': 'xlsx',
        }

    @api.model
    def _slsp_write_header_data(self, sheet, fonts, move_type):
        """ Write the header data into the sheet """
        company = self.env.company
        text_style = sheet.styles['text']
        title_style = sheet.styles['title']
        self._slsp_write_next_row(
            sheet, fonts,
            [(_('PURCHASE TRANSACTION') if move_type == 'in_invoice' else _('SALES TRANSACTION'), 3, title_style)]
            + [('', 1, text_style)] * (8 if move_type == 'out_invoice' else 11)  # We need to add empty cells to align everything. Done only the first time, for the others we'll get the amount of col from the sheet.
        )
        self._slsp_write_next_row(sheet, fonts, [(_('RECONCILIATION OF LISTING FOR ENFORCEMENT'), 3, title_style)])
        self._slsp_write_next_row(sheet, fonts, [])  # Empty row.
        self._slsp_write_next_row(sheet, fonts, [])  # Empty row.
        self._slsp_write_next_row(sheet, fonts, [])  # Empty row.
        self._slsp_write_next_row(sheet, fonts, [
            (_('TIN:'), 1, title_style),
            (company.vat, 2, text_style),
        ])
        self._slsp_write_next_row(sheet, fonts, [
            (_('OWNER\'S NAME:'), 1, title_style),
            (company.display_name, 2, text_style),
        ])
        self._slsp_write_next_row(sheet, fonts, [
            (_('OWNER\'S TRADE NAME:'), 1, title_style),
            (company.display_name, 2, text_style),
        ])
        self._slsp_write_next_row(sheet, fonts, [
            (_('OWNER\'S ADDRESS:'), 1, title_style),
            (re.sub(r'\n+', '\n', company.partner_id._display_address(without_company=True)), 2, text_style),
        ])
        self._slsp_write_next_row(sheet, fonts, [])  # Empty row.

    @api.model
    def _slsp_write_invoice_data(self, sheet, fonts, lines, move_type, report):
        """ Write the invoice data in the sheet. """
        if move_type == 'out_invoice':
            amount_columns = [
                ('gross_amount', _('GROSS SALES')),
                ('exempt_amount', _('EXEMPT SALES')),
                ('zero_rated_amount', _('ZERO-RATED SALES')),
                ('taxable_amount', _('TAXABLE SALES')),
                ('tax_amount', _('OUTPUT TAX')),
                ('gross_taxable_amount', _('GROSS TAXABLE SALES')),
            ]
        else:
            amount_columns = [
                ('gross_amount', _('GROSS PURCHASE')),
                ('exempt_amount', _('EXEMPT PURCHASE')),
                ('zero_rated_amount', _('ZERO-RATED PURCHASE')),
                ('taxable_amount', _('TAXABLE PURCHASE')),
                ('services_amount', _('PURCHASE OF SERVICES')),
                ('capital_goods_amount', _('PURCHASE OF CAPITAL GOODS')),
                ('non_capital_goods_amount', _('PURCHASE OF OTHER THAN CAPITAL GOODS')),
                ('tax_amount', _('INPUT TAX')),
                ('gross_taxable_amount', _('GROSS TAXABLE PURCHASE')),
            ]

        title_style = sheet.styles['title']
        text_style = sheet.styles['text']
        monetary_style = sheet.styles['monetary']
        total_style = sheet.styles['total']
        date_style = sheet.styles['date']
        # Write the titles.
        self._slsp_write_next_row(sheet, fonts, [
            (_('TAXABLE'), 1, title_style),
            (_('TAXPAYER'), 1, title_style),
            (_('REGISTER NAME'), 1, title_style),
            (_('NAME OF CUSTOMER') if move_type == 'out_invoice' else _('NAME OF SUPPLIER'), 1, title_style),
            (_('CUSTOMER\'S ADDRESS') if move_type == 'out_invoice' else _('SUPPLIER\'S ADDRESS'), 1, title_style),
        ] + [(_('AMOUNT OF'), 1, title_style)] * len(amount_columns))
        self._slsp_write_next_row(sheet, fonts, [
            (_('MONTH'), 1, title_style),
            (_('IDENTIFICATION'), 1, title_style),
            ('', 1, title_style),
            (_('(Last Name, First Name, Middle Name)'), 1, title_style),
            ('', 1, title_style),
        ] + [(column[1], 1, title_style) for column in amount_columns])
        self._slsp_write_next_row(sheet, fonts, [
            ('', 1, title_style),
            (_('NUMBER'), 1, title_style),
        ])
        self._slsp_write_next_row(sheet, fonts, [])  # Empty row.
        amounts_start = len(sheet.table) + 1  # store the y position of the start of the data to be able to use formulas later.

        # Filter the lines to separate report lines, and the frand total.
        report_lines = []
        grand_total_line = None
        for line in lines:
            markup = report._parse_line_id(line['id'])[-1][0]
            if markup == 'grand_total':
                grand_total_line = line
            else:
                report_lines.append(line)

        # Finally write the moves' data.
        line_vals = {}
        for line in report_lines:
            model = report._parse_line_id(line['id'])[-1][1]
            # Lines are ordered, so for month and partner lines we can gather the vals, and then write the lines when we are processing aml.
            if model is None:  # month line
                line_vals['month'] = self.env['account.report']._parse_line_id(line['id'])[-1][0]
                continue
            elif model == 'res.partner':
                line_vals['partner_name'] = line['name'] if not line['is_company'] else ''
                line_vals.update({
                    col['expression_label']: col['no_format'] for col in line['columns']
                })
                continue
            # if we want to group by partner, we add a check here and not update the vals, and not continue above
            elif model == 'account.move':
                # Make sure to only override the values for which we have a value.
                line_vals.update({
                    col['expression_label']: col['no_format'] for col in line['columns'] if col["no_format"]
                })
            # Time to write our line.
            self._slsp_write_next_row(sheet, fonts, [
                (line_vals['month'], 1, date_style),
                (line_vals['partner_vat'], 1, text_style),
                (line_vals['register_name'], 1, text_style),
                (line_vals['partner_name'], 1, text_style),
                (re.sub(r', ', '\n', line_vals['partner_address']), 1, text_style),
            ] + [(line_vals[column[0]], 1, monetary_style) for column in amount_columns])
        amounts_end = len(sheet.table)
        self._slsp_write_next_row(sheet, fonts, [])  # Empty row.
        # Write the totals. We use formulas to compute them so that the sheet can be edited more easily.
        if grand_total_line:
            total_vals = {col['expression_label']: col['no_format'] for col in grand_total_line['columns']}
            total_cols = [(_('Grand total:'), 1, text_style)] + [('', 1, text_style)] * 4
            for i, column in enumerate(amount_columns):
                col = chr(70 + i)  # 70 is the ascii code for 'F'. It matches the first amount column.
                value = total_vals[column[0]]
                total_cols.append((f'=sum({col}{amounts_start}:{col}{amounts_end})', 1, total_style, value))
            self._slsp_write_next_row(sheet, fonts, total_cols)

    @api.model
    def _set_xlsx_cell_sizes(self, sheet, fonts, col, row, value, style, has_colspan):
        """ This small helper will resize the cells if needed, to allow to get a better output.
        Backport of the same method in account_report in 17.1. as it is needed for this report.
        """

        def get_string_width(font, string):
            return font.getsize(string)[0] / 5

        # Get the correct font for the row style
        font_type = ('Bol' if style.bold else 'Reg') + ('Ita' if style.italic else '')
        report_font = fonts[font_type]

        # 8.43 is the default width of a column in Excel.
        col_width = sheet.col_sizes.get(col, [8.43])[0]

        with contextlib.suppress(ValueError):
            # This is needed, otherwise we could compute width on very long number such as 12.0999999998
            # which wouldn't show well in the end result as the numbers are rounded.
            value = float_repr(float(value), self.env.company.currency_id.decimal_places)

        # Start by computing the width of the cell if we are not using colspans.
        if not has_colspan:
            # Ensure to take indents into account when computing the width.
            formatted_value = f"{'  ' * style.indent}{value}"
            width = get_string_width(
                report_font,
                max(formatted_value.split('\n'), key=lambda line: get_string_width(report_font, line))
            )
            # We set the width if it is bigger than the current one, with a limit at 75 (max to avoid taking excessive space).
            if width > col_width:
                sheet.set_column(col, col, min(width, 75))

    @api.model
    def _slsp_write_next_row(self, sheet, fonts, values):
        """ Take a list of tuples (value, colspan, style) and write them on the next row. """
        # We need to be able to write on y in order to increase the offset.
        y = len(sheet.table)
        x = 0
        col_amount = len(sheet.table[0])
        for value, colspan, style, *formula_result in values:
            # Handles resizing the column if needed.
            self._set_xlsx_cell_sizes(sheet, fonts, x, y, value, style, colspan > 1)
            if colspan == 1:
                # For simplicity, it doesn't support merging formula cells.
                if isinstance(value, str) and value.startswith('='):
                    # Some software won't automatically calculate the value upon opening which is an issue.
                    # So we force the calculation of the formula too to ensure a same behaviour everytime.
                    sheet.write_formula(y, x, value, style, formula_result and formula_result[0])
                else:
                    sheet.write(y, x, value, style)
            else:
                sheet.merge_range(y, x, y, x + colspan - 1, value, style)
            x += colspan
        # Fill the remaining cells with empty values so that the style is applied.
        for x in range(x, col_amount):
            sheet.write(y, x, '', sheet.styles['text'])
