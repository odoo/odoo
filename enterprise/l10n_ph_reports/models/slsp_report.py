# Part of Odoo. See LICENSE file for full copyright and licensing details.
import contextlib
import io
import re
import xlsxwriter

from importlib import metadata
from PIL import ImageFont

from odoo import api, models, _, fields
from odoo.osv import expression
from odoo.exceptions import UserError
from odoo.tools import date_utils, float_repr, SQL, parse_version
from odoo.tools.misc import format_date, file_path


class SlspCustomHandler(models.AbstractModel):
    _name = 'l10n_ph.slsp.report.handler'
    _inherit = 'l10n_ph.generic.report.handler'
    _description = 'Summary Lists of Sales and Purchases Custom Handler'

    def _get_custom_display_config(self):
        return {
            'templates': {
                'AccountReportFilters': 'l10n_ph_reports.SlspReportFilters',
            },
        }

    def _custom_options_initializer(self, report, options, previous_options):
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
        options['include_no_tin'] = previous_options.get('include_no_tin', False)
        # Initialise the custom options for this report.
        options['include_imports'] = previous_options.get('include_imports', False)

    # First level, month rows
    def _build_month_lines(self, report, options):
        """ Fetches the months for which we have entries *that have tax grids* and build a report line for each of them. """
        month_lines = []
        queries = []

        # 1) Build the queries to get the months
        for column_group_key, column_group_options in report._split_options_per_column_group(options).items():
            query = self._get_report_query(report, column_group_options)
            # The joins are there to filter out months for which we would not have any lines in the report.
            queries.append(SQL(
                """
                  SELECT (date_trunc('month', account_move_line.date::date) + interval '1 month' - interval '1 day')::date AS taxable_month,
                         %(column_group_key)s                                                                              AS column_group_key
                    FROM %(table_references)s
                   WHERE %(search_condition)s
                GROUP BY taxable_month
                ORDER BY taxable_month DESC
                """,
                column_group_key=column_group_key,
                table_references=query.from_clause,
                search_condition=query.where_clause,
            ))

        self.env.cr.execute(SQL(" UNION ALL ").join(queries))

        # 2) Make the lines
        unfold_all = options['export_mode'] == 'print' or options.get('unfold_all')
        for res in self._cr.dictfetchall():
            line_id = report._get_generic_line_id('', '', markup=str(res['taxable_month']))
            month_lines.append({
                'id': line_id,
                'name': format_date(self.env, res['taxable_month'], date_format='MMMM y'),
                'unfoldable': True,
                'unfolded': line_id in options['unfolded_lines'] or unfold_all,
                'columns': [report._build_column_dict(None, _column) for _column in options['columns']],
                'level': 0,
                'expand_function': '_report_expand_unfoldable_line_l10n_ph_expand_month',
            })

        return month_lines

    def _report_expand_unfoldable_line_l10n_ph_expand_month(self, line_dict_id, groupby, options, progress, offset, unfold_all_batch_data=None):
        """ Used to expand a month line and load the second level, being the partner lines. """
        report = self.env['account.report'].browse(options['report_id'])
        month = report._get_markup(line_dict_id)
        partner_lines_values = self._query_partners(report, options, month, offset)
        return self._get_report_expand_unfoldable_line_value(report, options, line_dict_id, progress, partner_lines_values,
                                                             report_line_method=self._get_report_line_partner)

    def _query_partners(self, report, options, month, offset):
        """ Query the values for the partner lines.
        The partner lines will sum up the values for the different columns while only being filtered for the given month.
        """
        limit = report.load_more_limit + 1 if report.load_more_limit and options['export_mode'] != 'print' else None
        end_date = fields.Date.from_string(month)  # Month is already set to the last day of the month.
        start_date = date_utils.start_of(end_date, 'month')
        queries = []
        extra_domain = [
            # Make sure to only fetch records that are in the parent's row month
            ('date', '>=', start_date),
            ('date', '<=', end_date),
        ]
        for column_group_key, column_group_options in report._split_options_per_column_group(options).items():
            query = self._get_report_query(report, column_group_options, extra_domain=extra_domain)
            tail_query = report._get_engine_query_tail(offset, limit)
            account_tag_name = self.env['account.account.tag']._field_to_sql('account_tag', 'name', query)
            queries.append(SQL(
                """
                  SELECT %(column_group_key)s                                                                   AS column_group_key,
                         cp.vat                                                                                 AS partner_vat,
                         case when (cp.id = p.id and cp.is_company) or cp.id != p.id then cp.name else '' end   AS register_name,
                         p.id                                                                                   AS partner_id,
                         case when p.is_company = false then p.name else '' end                                 AS partner_name,
                         p.last_name || ' ' || p.first_name || ' ' || p.middle_name                             AS formatted_partner_name,
                         p.is_company                                                                           AS is_company,
                         REGEXP_REPLACE(%(account_tag_name)s, '^[+-]', '')                                      AS tag_name,
                         SUM(%(balance_select)s
                             * CASE WHEN account_tag.tax_negate THEN -1 ELSE 1 END
                             * CASE WHEN account_move_line.tax_tag_invert THEN -1 ELSE 1 END
                         )                                                                                      AS balance
                    FROM %(table_references)s
                    JOIN res_partner p ON p.id = account_move_line__move_id.partner_id
                    JOIN res_partner cp ON cp.id = p.commercial_partner_id
                    %(currency_table_join)s
                   WHERE %(search_condition)s
                GROUP BY p.id, cp.id, %(account_tag_name)s
                %(tail_query)s
                """,
                balance_select=report._currency_table_apply_rate(SQL("account_move_line.balance")),
                column_group_key=column_group_key,
                account_tag_name=account_tag_name,
                table_references=query.from_clause,
                currency_table_join=report._currency_table_aml_join(column_group_options),
                search_condition=query.where_clause,
                tail_query=tail_query,
            ))

        self.env.cr.execute(SQL(" UNION ALL ").join(queries))
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
            self._eval_report_grids_map(options, values, column_values=lines_values[values['partner_id']][values['column_group_key']])
        return self._filter_lines_with_values(options, lines_values)

    def _get_report_line_partner(self, report, options, partner_id, line_values, parent_line_id):
        """ Format the given values to match the report line format. """
        month = report._get_markup(parent_line_id)
        line_columns = self._get_line_columns(report, options, line_values)
        # Set the markup with the month, we can reuse it to filter the detailed move lines
        line_id = report._get_generic_line_id('res.partner', partner_id, markup=month, parent_line_id=parent_line_id)
        unfold_all = options['export_mode'] == 'print' or options.get('unfold_all')
        return {
            'id': line_id,
            'parent_id': parent_line_id,
            'name': line_values['name'] or line_values['register_name'],
            'is_company': line_values['is_company'],  # This is only used when building the export, as we expect a slightly different behavior for companies
            'unfoldable': True,
            'unfolded': line_id in options['unfolded_lines'] or unfold_all,
            'columns': line_columns,
            'level': 1,
            'caret_options': 'res.partner',
            'expand_function': '_report_expand_unfoldable_line_l10n_ph_expand_partner',
        }

    def _report_expand_unfoldable_line_l10n_ph_expand_partner(self, line_dict_id, groupby, options, progress, offset, unfold_all_batch_data=None):
        """ Used to expand a partner line and load the third level, being the account move lines. """
        report = self.env['account.report'].browse(options['report_id'])
        month = report._get_markup(line_dict_id)
        partner_id = report._get_res_id_from_line_id(line_dict_id, 'res.partner')
        lines_values = self._query_moves(report, options, partner_id, month, offset)
        return self._get_report_expand_unfoldable_line_value(report, options, line_dict_id, progress, lines_values, report_line_method=self._get_report_line_move)

    def _query_moves(self, report, options, partner_id, month, offset):
        """ Query the values for the partner line.
        The move line will sum up the values for the different columns, while being filtered for the given month only.
        """
        limit = report.load_more_limit + 1 if report.load_more_limit and options['export_mode'] != 'print' else None
        end_date = fields.Date.from_string(month)
        start_date = date_utils.start_of(end_date, 'month')
        queries = []

        extra_domain = [
            ('date', '>=', start_date),
            ('date', '<=', end_date),
            ('move_id.partner_id', '=', partner_id),
        ]
        for column_group_key, column_group_options in report._split_options_per_column_group(options).items():
            query = self._get_report_query(report, column_group_options, extra_domain=extra_domain)
            tail_query = report._get_engine_query_tail(offset, limit)
            account_tag_name = self.env['account.account.tag']._field_to_sql('account_tag', 'name', query)
            queries.append(SQL(
                """
                  SELECT %(column_group_key)s                                                                   AS column_group_key,
                         account_move_line__move_id.id                                                          AS move_id,
                         account_move_line__move_id.name                                                        AS move_name,
                         REGEXP_REPLACE(%(account_tag_name)s, '^[+-]', '')                                      AS tag_name,
                         SUM(%(balance_select)s
                             * CASE WHEN account_tag.tax_negate THEN -1 ELSE 1 END
                             * CASE WHEN account_move_line.tax_tag_invert THEN -1 ELSE 1 END
                         )                                                                                      AS balance
                    FROM %(table_references)s
                    %(currency_table_join)s
                   WHERE %(search_condition)s
                GROUP BY account_move_line__move_id.id, %(account_tag_name)s
                ORDER BY account_move_line__move_id.date DESC, account_move_line__move_id.name DESC, account_move_line__move_id.invoice_date DESC, account_move_line__move_id.id DESC
                %(tail_query)s
                """,
                balance_select=report._currency_table_apply_rate(SQL("account_move_line.balance")),
                column_group_key=column_group_key,
                account_tag_name=account_tag_name,
                table_references=query.from_clause,
                currency_table_join=report._currency_table_aml_join(column_group_options),
                search_condition=query.where_clause,
                tail_query=tail_query,
            ))

        self.env.cr.execute(SQL(" UNION ALL ").join(queries))
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
            self._eval_report_grids_map(options, values, column_values=lines_values[values['move_id']][values['column_group_key']])
        return self._filter_lines_with_values(options, lines_values)

    def _get_report_line_move(self, report, options, move_id, line_values, parent_line_id):
        """ Format the given values to match the report line format. """
        line_columns = self._get_line_columns(report, options, line_values)
        line_id = report._get_generic_line_id('account.move', move_id, parent_line_id=parent_line_id)
        return {
            'id': line_id,
            'parent_id': parent_line_id,
            'name': line_values['name'],
            'unfoldable': False,
            'unfolded': False,
            'columns': line_columns,
            'level': 2,
            'caret_options': 'account.move',
        }

    def _get_grand_total_line_domain(self, options):
        domain = super()._get_grand_total_line_domain(options)
        if not options.get("include_no_tin"):
            domain = expression.AND([domain, [("partner_id.vat", "!=", False)]])
        return domain

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
                'journal_type': section_options['journal_type'],
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
        sheet = workbook.add_worksheet(_('sls') if options['journal_type'] == 'sale' else _('slp'))
        # Add the styles to the sheet to make it easier to get them later.
        sheet.styles = {
            'text': workbook.add_format({'font_name': 'Arial', 'border': 1, 'align': 'left'}),
            'title': workbook.add_format({'font_name': 'Arial', 'bold': True, 'border': 1, 'align': 'left'}),
            'monetary': workbook.add_format({'font_name': 'Arial', 'border': 1, 'align': 'right', 'num_format': '#,##0.00'}),
            'total': workbook.add_format({'font_name': 'Arial', 'bold': True, 'border': 1, 'align': 'right', 'num_format': '#,##0.00'}),
            'date': workbook.add_format({'font_name': 'Arial', 'border': 1, 'align': 'left', "num_format": "yyyy-mm-dd"}),
        }
        # Write the header part.
        self._slsp_write_header_data(sheet, fonts, options['journal_type'])
        # Write the data part.
        self._slsp_write_invoice_data(sheet, fonts, lines, options['journal_type'], report)
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
            'file_name': _('sl_sales') if options['journal_type'] == 'sale' else _('sl_purchases'),
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
            [(_('PURCHASE TRANSACTION') if move_type == 'purchase' else _('SALES TRANSACTION'), 3, title_style)]
            + [('', 1, text_style)] * (8 if move_type == 'sale' else 11)  # We need to add empty cells to align everything. Done only the first time, for the others we'll get the amount of col from the sheet.
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
        if move_type == 'sale':
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
            (_('NAME OF CUSTOMER') if move_type == 'sale' else _('NAME OF SUPPLIER'), 1, title_style),
            (_('CUSTOMER\'S ADDRESS') if move_type == 'sale' else _('SUPPLIER\'S ADDRESS'), 1, title_style),
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
        amount_expression_labels = [amount_column[0] for amount_column in amount_columns]

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
                # Make sure to only override the amount values (we want to keep the partner info)
                line_vals.update({
                    col['expression_label']: col['no_format'] for col in line['columns'] if col["expression_label"] in amount_expression_labels
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
            return font.getlength(string) / 5

        # Get the correct font for the row style
        font_type = ('Bol' if style.bold else 'Reg') + ('Ita' if style.italic else '')
        report_font = fonts[font_type]

        # 8.43 is the default width of a column in Excel.
        if parse_version(metadata.version('xlsxwriter')) >= parse_version('3.0.6'):
            # cols_sizes was removed in 3.0.6 and colinfo was replaced by col_info
            # see https://github.com/jmcnamara/XlsxWriter/commit/860f4a2404549aca1eccf9bf8361df95dc574f44
            try:
                col_width = sheet.col_info[col][0]
            except KeyError:
                col_width = 8.43
        else:
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
