# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import _, api, models, fields
from odoo.tools import date_utils
from odoo.tools.sql import SQL
from odoo.tools.misc import format_date
from odoo.exceptions import UserError
from odoo.addons.l10n_ph import utils


class SawtQapCustomHandler(models.AbstractModel):
    _name = 'l10n_ph.sawt_qap.report.handler'
    _inherit = ['l10n_ph.generic.report.handler', 'account.tax.report.handler']
    _description = 'Withholding Taxes Custom Handler'

    def _custom_options_initializer(self, report, options, previous_options=None):
        super()._custom_options_initializer(report, options, previous_options=previous_options)
        options.setdefault('buttons', []).append(
            {
                'name': _('Export SAWT & QAP'),
                'sequence': 5,  # As the export is a particular format from the BIR, we assume it will be the primary format used when exporting.
                'action': 'export_file',
                'action_param': 'export_sawt_qap',
                'file_export_type': _('XLSX'),
            }
        )

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
                   WHERE %(search_condition)s AND account_tax.l10n_ph_atc IS NOT NULL
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
                  SELECT %(column_group_key)s                                                                               AS column_group_key,
                         cp.vat                                                                                             AS partner_vat,
                         case when (cp.id = p.id and cp.is_company) or cp.id != p.id then cp.name else '' end               AS register_name,
                         p.id                                                                                               AS partner_id,
                         case when p.is_company = false then p.name else '' end                                             AS partner_name,
                         p.last_name || ' ' || p.first_name || ' ' || p.middle_name                                         AS formatted_partner_name,
                         REGEXP_REPLACE(%(account_tag_name)s, '^[+-]', '')                                                  AS tag_name,
                         SUM(%(balance_select)s
                             * CASE WHEN account_tag.tax_negate THEN -1 ELSE 1 END
                             * CASE WHEN account_move_line.tax_tag_invert THEN -1 ELSE 1 END
                         )                                                                                                  AS balance
                    FROM %(table_references)s
                    JOIN res_partner p ON p.id = account_move_line__move_id.partner_id
                    JOIN res_partner cp ON cp.id = p.commercial_partner_id
                    %(currency_table_join)s
                   WHERE %(search_condition)s
                GROUP BY p.id, cp.id, %(account_tag_name)s
                ORDER BY p.id
                %(tail_query)s
                """,
                balance_select=report._currency_table_apply_rate(SQL('account_move_line.balance')),
                column_group_key=column_group_key,
                account_tag_name=account_tag_name,
                currency_table_join=report._currency_table_aml_join(options),
                table_references=query.from_clause,
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
        return self._get_report_expand_unfoldable_line_value(report, options, line_dict_id, progress, lines_values,
                                                             report_line_method=self._get_report_line_move)

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
            ('move_id.commercial_partner_id', '=', partner_id),
        ]
        for column_group_key, column_group_options in report._split_options_per_column_group(options).items():
            tail_query = report._get_engine_query_tail(offset, limit)
            query = self._get_report_query(report, column_group_options, extra_domain=extra_domain)
            account_tag_name = self.env['account.account.tag']._field_to_sql('account_tag', 'name', query)
            queries.append(SQL(
                """
                  SELECT %(column_group_key)s                                                                               AS column_group_key,
                         REGEXP_REPLACE(%(account_tag_name)s, '^[+-]', '')                                                  AS tag_name,
                         account_move_line__move_id.id                                                                      AS move_id,
                         account_move_line__move_id.name                                                                    AS move_name,
                         SUM(%(balance_select)s
                             * CASE WHEN account_tag.tax_negate THEN -1 ELSE 1 END
                             * CASE WHEN account_move_line.tax_tag_invert THEN -1 ELSE 1 END
                         )                                                                                                  AS balance
                    FROM %(table_references)s
                    %(currency_table_join)s
                    WHERE %(search_condition)s
                GROUP BY account_move_line__move_id.id, %(account_tag_name)s
                ORDER BY account_move_line__move_id.id
                %(tail_query)s
                """,
                balance_select=report._currency_table_apply_rate(SQL('account_move_line.balance')),
                column_group_key=column_group_key,
                account_tag_name=account_tag_name,
                currency_table_join=report._currency_table_aml_join(options),
                table_references=query.from_clause,
                search_condition=query.where_clause,
                tail_query=tail_query,
            ))

        self.env.cr.execute(SQL(" UNION ALL ").join(queries))
        return self._process_moves(self.env.cr.dictfetchall(), options)

    def _process_moves(self, data_dict, options):
        """ Taking in the values from the database, this will construct the column values by using the tax grid mapping
        set in the option of each report section.
        """
        lines_values = {}
        for values in data_dict:
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
        unfold_all = options['export_mode'] == 'print' or options.get('unfold_all')
        return {
            'id': line_id,
            'parent_id': parent_line_id,
            'name': line_values['name'],
            'unfoldable': True,
            'unfolded': line_id in options['unfolded_lines'] or unfold_all,
            'columns': line_columns,
            'level': 2,
            'caret_options': 'account.move',
            'expand_function': '_report_expand_unfoldable_line_l10n_ph_expand_move',
        }

    def _report_expand_unfoldable_line_l10n_ph_expand_move(self, line_dict_id, groupby, options, progress, offset, unfold_all_batch_data=None):
        """ Used to expand an account move line and load the third level, being the tax lines. """
        report = self.env['account.report'].browse(options['report_id'])
        move_id = report._get_res_id_from_line_id(line_dict_id, 'account.move')
        lines_values = self._query_tax_lines(report, options, move_id, offset)
        return self._get_report_expand_unfoldable_line_value(report, options, line_dict_id, progress, lines_values,
                                                             report_line_method=self._get_report_line_tax)

    def _query_tax_lines(self, report, options, move_id, offset):
        """ Query the values for the partner line.
        The move line will sum up the values for the different columns, while being filtered for the given move id only.
        """
        limit = report.load_more_limit + 1 if report.load_more_limit and options['export_mode'] != 'print' else None
        queries = []

        extra_domain = [('move_id', '=', move_id)]
        for column_group_key, column_group_options in report._split_options_per_column_group(options).items():
            query = self._get_report_query(report, column_group_options, with_base_lines=False, extra_domain=extra_domain)
            tail_query = report._get_engine_query_tail(offset, limit)
            account_tag_name = self.env['account.account.tag'].with_context(lang='en_US')._field_to_sql('account_tag', 'name', query)
            account_tax_description = self.env['account.tax']._field_to_sql('account_tax', 'description', query)
            queries.append(SQL(
                """
                  SELECT %(column_group_key)s                                                                               AS column_group_key,
                         account_move_line__move_id.id                                                                      AS move_id,
                         account_move_line__move_id.name                                                                    AS move_name,
                         account_tax.id                                                                                     AS tax_id,
                         account_tax.l10n_ph_atc                                                                            AS atc,
                         REGEXP_REPLACE(%(account_tax_description)s, '(<([^>]+)>)', '', 'g')                                AS tax_description,
                         ABS(account_tax.amount)                                                                            AS tax_rate,
                         REGEXP_REPLACE(%(account_tag_name)s, '^[+-]', '')                                                  AS tag_name,
                         account_move_line.tax_base_amount                                                                  AS tax_base_amount,
                         SUM(%(balance_select)s
                             * CASE WHEN account_tag.tax_negate THEN -1 ELSE 1 END
                             * CASE WHEN account_move_line.tax_tag_invert THEN -1 ELSE 1 END
                         )                                                                                                  AS balance
                    FROM %(table_references)s
                    %(currency_table_join)s
                   WHERE %(search_condition)s AND account_tax.l10n_ph_atc IS NOT NULL
                GROUP BY account_move_line__move_id.id, %(account_tag_name)s, account_move_line.id, account_tax.id
                ORDER BY account_tax.id
                %(tail_query)s
                """,
                balance_select=report._currency_table_apply_rate(SQL('account_move_line.balance')),
                column_group_key=column_group_key,
                account_tax_description=account_tax_description,
                account_tag_name=account_tag_name,
                currency_table_join=report._currency_table_aml_join(options),
                table_references=query.from_clause,
                search_condition=query.where_clause,
                tail_query=tail_query,
            ))

        self.env.cr.execute(SQL(" UNION ALL ").join(queries))
        return self._process_tax_lines(self.env.cr.dictfetchall(), options)

    def _process_tax_lines(self, data_dict, options):
        """ Taking in the values from the database, this will construct the column values by using the tax grid mapping
        set in the option of each report section.
        """
        lines_values = {}
        for values in data_dict:
            if values['tax_id'] not in lines_values:
                lines_values[values['tax_id']] = {
                    'name': values['tax_description'],
                    values['column_group_key']: {
                        'column_group_key': values['column_group_key'],
                        'atc': values['atc'],
                        'tax_base_amount': values['tax_base_amount'],
                        'tax_rate': values['tax_rate'],
                        'withholding_tax_amount': values['balance'],
                    }
                }
        return lines_values

    def _get_report_line_tax(self, report, options, tax_id, line_values, parent_line_id):
        """ Format the given values to match the report line format. """
        line_columns = self._get_line_columns(report, options, line_values)
        line_id = report._get_generic_line_id('account.tax', tax_id, parent_line_id=parent_line_id)
        return {
            'id': line_id,
            'parent_id': parent_line_id,
            'name': line_values['name'],
            'unfoldable': False,
            'unfolded': False,
            'columns': line_columns,
            'level': 3,
            'caret_options': 'account.tax',
        }

    @api.model
    def export_sawt_qap(self, options):
        """ Export the report to a XLSX file formatted base on the BIR standards """
        report = self.env['account.report'].browse(options['report_id'])

        # If we are exporting from the composite report, we get the important options from the selected section.
        # Otherwise, we assume we are on a "custom" report that's only QAP or SAWT
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

        options.update({
            'unfold_all': True,
            'export_mode': 'print',
            'ignore_totals_below_sections': True,
        })

        # Get the lines, according to the options.
        lines = report._get_lines(options)

        move_ids = []
        for line in lines:
            model, res_id = report._get_model_info_from_id(line['id'])
            if model != 'account.move':
                continue
            move_ids.append(res_id)
        moves = self.env['account.move'].browse(move_ids)
        file_name = 'sawt' if options['journal_type'] == 'sale' else 'qap'
        generated_file = utils._export_bir_2307(file_name, moves, file_format='xlsx')

        return {
            'file_name': 'sawt' if options['journal_type'] == 'sale' else 'qap',
            'file_content': generated_file,
            'file_type': 'xlsx',
        }


class SawtCustomHandler(models.AbstractModel):
    _name = 'l10n_ph.sawt.report.handler'
    _inherit = 'l10n_ph.sawt_qap.report.handler'
    _description = 'Sales Withholding Taxes Custom Handler'

    def _custom_options_initializer(self, report, options, previous_options=None):
        super()._custom_options_initializer(report, options, previous_options=previous_options)
        options.update({
            'journal_type': 'sale',
            # This mapping will be used to build the amount for each expression_label based on the grid names.
            'report_grids_map': {
                'tax_base_amount': ['SAWTA'],
                'withholding_tax_amount': ['SAWTB'],
            }
        })


class QapCustomHandler(models.AbstractModel):
    _name = 'l10n_ph.qap.report.handler'
    _inherit = 'l10n_ph.sawt_qap.report.handler'
    _description = 'Purchase Withholding Taxes Custom Handler'

    def _custom_options_initializer(self, report, options, previous_options=None):
        super()._custom_options_initializer(report, options, previous_options=previous_options)
        options.update({
            'journal_type': 'purchase',
            # This mapping will be used to build the amount for each expression_label based on the grid names.
            'report_grids_map': {
                'tax_base_amount': ['QAPA'],
                'withholding_tax_amount': ['QAPB'],
            }
        })
