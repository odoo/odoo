# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from collections import defaultdict

from odoo import _, api, fields, models
from odoo.tools import float_compare, format_list

from ..models.l10n_lu_tax_report_data import MULTI_COLUMN_FIELDS


class LuAnnualTaxReportCustomHandler(models.AbstractModel):
    _name = 'l10n_lu.annual.tax.report.handler'
    _inherit = 'l10n_lu.tax.report.handler'
    _description = 'Luxembourgish Annual Tax Report Custom Handler'

    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(report, options, previous_options=previous_options)
        # closing entry button shouldn't be visible in the annual tax report
        options['buttons'] = [button for button in options['buttons'] if button['action'] != 'action_periodic_vat_entries']

    def _get_field_values(self, lines):
        field_types_dict = {
            'string': 'char',
            'boolean': 'boolean',
        }
        values = {}
        for line in lines:
            # tax report's `code` would contain alpha-numeric string like `LUTAX_XXX` where characters
            # at last three positions will be digits, hence we split `code` with `_` and build dictionary
            # having `code` as dictionary key
            line_code = code = line.get('code', '') and line['code'].split('_')[-1]
            if not (line_code and line_code.isdigit()):
                continue

            for column in line['columns']:
                value = column['no_format']
                if value is None:
                    continue

                # every expression in such line corresponds to a different field in the report
                # so we match the correct field using the line code and the expression_label (column)
                if code in MULTI_COLUMN_FIELDS:
                    line_code = MULTI_COLUMN_FIELDS[code][column['expression_label']]

                field_type = field_types_dict.get(column['figure_type']) or 'float'
                if field_type == 'boolean':
                    value = str(int(value))
                if line_code == '998' and value == '0': # we set either 998 or 999 depending on the value
                    line_code, value = '999', '1'

                values[line_code] = {'value': value, 'field_type': field_type}

        return values

    def _get_value_from_totals(self, expr_map, totals, field_name, label):
        field_submap = expr_map.get(field_name)
        if field_submap:
            field_expression = expr_map[field_name][label]
            field_value = totals.get(field_expression, {'value': False})['value']
            return field_value
        return False

    def _check_dependent_fields(self, expr_map, totals):
        """
        If any of the dependent fields of a main field are filled in, the
        main field should not be empty.
        As the report expressions don't have codes, we take the target code to be the code of the report line
        that corresponds to the expression that needs to be found
        and the actual expressions can be found using the combination of the line code and
        the target label. field_name is for user information.

        the structure of the fields dictionary:
            {
                'field to check': [
                    'field_name': the name of the dependent field to be checked,
                    'target_code': the code of the line that actually contains that dependent field,
                    'label': the label of the expression with which we can find the expression that corresponds to the dependent field
                ]
            }
        """
        dependent_fields = {
            '206': [{'field_name': '007', 'target_code': '007', 'label': 'balance'}],
            '229': [{'field_name': '100', 'target_code': '100', 'label': 'balance'}],
            '264': [
                {'field_name': '265', 'target_code': '265', 'label': 'total'},
                {'field_name': '266', 'target_code': '265', 'label': 'percent'},
                {'field_name': '267', 'target_code': '265', 'label': 'vat_excluded'},
                {'field_name': '268', 'target_code': '265', 'label': 'vat_invoiced'},
            ],
            '273': [
                {'field_name': '274', 'target_code': '274', 'label': 'total'},
                {'field_name': '275', 'target_code': '274', 'label': 'percent'},
                {'field_name': '276', 'target_code': '274', 'label': 'vat_excluded'},
                {'field_name': '277', 'target_code': '274', 'label': 'vat_invoiced'},
            ],
            '278': [
                {'field_name': '279', 'target_code': '279', 'label': 'total'},
                {'field_name': '280', 'target_code': '279', 'label': 'percent'},
                {'field_name': '281', 'target_code': '279', 'label': 'vat_excluded'},
                {'field_name': '282', 'target_code': '279', 'label': 'vat_invoiced'},
            ],
            '318': [
                {'field_name': '319', 'target_code': '319', 'label': 'vat_excluded'},
                {'field_name': '320', 'target_code': '319', 'label': 'vat_invoiced'},
            ],
            '321': [
                {'field_name': '322', 'target_code': '322', 'label': 'vat_excluded'},
                {'field_name': '323', 'target_code': '322', 'label': 'vat_invoiced'},
            ],
            '357': [
                {'field_name': '358', 'target_code': '358', 'label': 'vat_excluded'},
                {'field_name': '359', 'target_code': '358', 'label': 'vat_invoiced'},
            ],
            '368': [{'field_name': '369', 'target_code': '369', 'label': 'balance'}],
            '369': [{'field_name': '368', 'target_code': '368', 'label': 'balance'}],
            '387': [{'field_name': '388', 'target_code': '388', 'label': 'balance'}],
            '388': [{'field_name': '387', 'target_code': '387', 'label': 'balance'}],
        }

        errors = set()
        for check_field in dependent_fields:
            # if the main field is not in line_ids, then it is not the right report
            if check_field not in expr_map:
                continue
            for related_field in dependent_fields[check_field]:
                # if the main expression already has a value, we don't need to check related fields
                check_label = 'total' if check_field in ('264', '273', '278', '318', '321', '357') else 'balance'
                if self._get_value_from_totals(expr_map, totals, check_field, check_label):
                    continue

                related_field_value = self._get_value_from_totals(expr_map, totals, related_field['target_code'], related_field['label'])
                if related_field_value:
                    # display the warning with the field name and all related fields
                    errors.add(
                        _("The field %(field)s must be filled in because one of the dependent fields (%(dependent_fields)s) is filled in.",
                        field=check_field,
                        dependent_fields=format_list(self.env, [related['field_name'] for related in dependent_fields[check_field]])),
                    )

        return errors

    def _customize_warnings(self, report, options, all_column_groups_expression_totals, warnings):
        super()._customize_warnings(report, options, all_column_groups_expression_totals, warnings)
        # we need a map between the line code (corresponds to report field code)
        # and each expression label to the expression itself
        expr_map = {
            line.code.split('_')[3]: {expr.label: expr for expr in line.expression_ids}
            for line in report.line_ids
            if line.code
        }

        failed_controls = set()
        # field 010 from Section 1 needs to be filled in when field 389 from Appendix B is filled in
        # so we added a cross-report check expression that is not displayed in the tax report
        # and only used for this warning
        additional_checks = [
            {
                'fields': (('010', 'check'), ('010', 'balance')),
                'check_function': lambda field_389, field_010: field_389 and not field_010,
                'warning_message': _("The field 010 in Section 1 is mandatory if you fill in the field 389 in 'Appendix B'. Field 010 must be equal to field 389"),
            },
            {
                'fields': (('368', 'balance'), ('369', 'balance')),
                'check_function': lambda field_368, field_369: field_368 and field_369 and float_compare(field_369, field_368, 2) > 0,
                'warning_message': _("The value of the field 369 must be lower than the value of the field 368 (Appendix B)."),
            },
            {
                'fields': (('163', 'year_start'), ('164', 'year_start'), ('165', 'year_start')),
                'check_function': lambda field_163, field_164, field_165: field_163 and not (field_164 and field_165) or  all([field_163, field_164, field_165]) and float_compare(field_163, field_164 + field_165, 2) != 0,
                'warning_message': _("Fields 164 and 165 are mandatory when 163 is filled in and must add up to field 163."),
            },
        ]
        for totals in all_column_groups_expression_totals.values():
            # checking a list of main fields: if one of the related fields is filled in
            # the main field should be filled as well
            failed_controls.update(self._check_dependent_fields(expr_map, totals))
            for check in additional_checks:
                vals = [self._get_value_from_totals(expr_map, totals, field_name, label) for field_name, label in check['fields']]
                if check['check_function'](*vals):
                    failed_controls.add(check['warning_message'])
            for monthly_field in ('472', '455', '456', '457', '458', '459', '460', '461'):
                monthly_field_value = self._get_value_from_totals(expr_map, totals, monthly_field, 'balance')
                if not self.env.company.currency_id.is_zero(monthly_field_value):
                    failed_controls.add(_("The following monthly fields haven't been completely allocated yet: %s", monthly_field))

        if failed_controls:
            warnings['l10n_lu_reports.annual_tax_report_warning_checks'] = {'failed_controls': list(failed_controls), 'alert_type': 'danger'}


class LuReportAppendixA(models.AbstractModel):
    _name = 'l10n_lu.appendix.a.tax.report.handler'
    _inherit = 'l10n_lu.annual.tax.report.handler'
    _description = 'Custom Handler for the Appendix A of the LU Annual Tax Report'

    def _get_account_details(self, ln):
        model, active_id = self.env['account.report']._get_model_info_from_id(ln['id'])
        if model == 'account.account':
            account = self.env['account.account'].browse(active_id)
            return account.tag_ids, account.name
        return False, False

    @api.model
    def _get_precomputed_lines(self, year, lines, annex_options, result=None):
        expenditures_table = []
        excluded_index, invoiced_index = 0, 1
        # in case the columns are manually reordered
        for i, column in enumerate(annex_options['columns']):
            if column['expression_label'] == 'net':
                excluded_index = i
            elif column['expression_label'] == 'tax':
                invoiced_index = i

        for ln in lines:
            account_tag_ids, account_name = self._get_account_details(ln)
            if account_tag_ids:
                # The tags are formatted to end with the code. So in the loop we get this code and concatenate to L10N_LU_TAX
                # Which will be used in the appendix A of the report.
                matching = ["L10N_LU_TAX_" + tag.get_external_id()[tag.id].split("_")[-1] for tag in account_tag_ids]
                for code in matching:
                    vat_excluded = ln['columns'][excluded_index]['no_format']
                    vat_invoiced = ln['columns'][invoiced_index]['no_format']
                    if code == 'L10N_LU_TAX_361':
                        expenditures_table.append({
                            'year': year,
                            'company_id': self.env.company.id,
                            'report_section_411': account_name[:31].rstrip(), # The maximum length for the "Detail of Expense" field is 30 characters
                            'report_section_412': vat_excluded,
                            'report_section_413': vat_invoiced,
                        })
                    elif result and f'{code}_vat_excluded' in result and f'{code}_vat_invoiced' in result:
                        result[f'{code}_vat_excluded'] += vat_excluded
                        result[f'{code}_vat_invoiced'] += vat_invoiced

        return result, expenditures_table

    def _report_custom_engine_l10n_lu_annual_vat(self, expressions, options, date_scope, current_groupby, next_groupby, offset=0, limit=None, warnings=None):
        # precompute values based on the account codes mapping
        grouped_tax_report = self.env.ref('account.generic_tax_report_tax_account')
        annex_options = grouped_tax_report.get_options(options)
        lines = grouped_tax_report._get_lines(annex_options)
        date_to = options['date']['date_to']
        year = fields.Date.from_string(date_to).year
        result = {}
        for expression in expressions:
            result.update({
                f'{expression.report_line_id.code}_vat_excluded': 0.0,
                f'{expression.report_line_id.code}_vat_invoiced': 0.0,
            })
        result, _expenditures_table = self._get_precomputed_lines(year=year, lines=lines, annex_options=annex_options, result=result)

        return result


class LuReportAppendixOpEx(models.AbstractModel):
    _name = 'l10n_lu.appendix.opex.tax.report.handler'
    _inherit = 'account.tax.report.handler'
    _description = 'Custom Handler for the Appendix to Operational Expenditures of the LU Annual Tax Report'

    def _get_custom_display_config(self):
        parent_config = super()._get_custom_display_config()
        parent_config['components']['AccountReportLineName'] = 'l10n_lu_reports.AppendixLineName'
        return parent_config

    def action_open_appendix_view(self, options, params=None):
        date_to = options['date']['date_to']
        year = fields.Date.from_string(date_to).year
        domain = [
            ('company_id', 'in', [comp['id'] for comp in options['companies']]),
            ('year', '=', year),
        ]
        if params and params.get('recompute'):
            grouped_tax_report = self.env.ref('account.generic_tax_report_tax_account')
            annex_options = grouped_tax_report.get_options(options)
            lines = grouped_tax_report._get_lines(annex_options)
            _result, expenditures_table = self.env['l10n_lu.appendix.a.tax.report.handler']._get_precomputed_lines(year, lines, annex_options)
            # unlink existing appendix lines because we are recomputing from scratch
            # and there is no way to know what has been already computed before and what was manually created
            self.env['l10n_lu_reports.report.appendix.expenditures'].search(domain).unlink()
            self.env['l10n_lu_reports.report.appendix.expenditures'].create(expenditures_table)

        return {
            'name': _("Appendix to the Operational Expenditures"),
            'type': 'ir.actions.act_window',
            'views': [(
                self.env.ref('l10n_lu_reports.l10n_lu_yearly_tax_report_appendix_view_tree').id,
                'list',
            )],
            'res_model': 'l10n_lu_reports.report.appendix.expenditures',
            'context': {'year': year},
            'domain': domain,
            'target': 'current',
        }

    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals, warnings=None):
        # it only makes sense to compare appendix lines based on the year
        grouped_columns = defaultdict(list)
        for column_group_key, column_group_options in report._split_options_per_column_group(options).items():
            date_to = column_group_options['date']['date_to']
            year = str(fields.Date.from_string(date_to).year)
            grouped_columns[year].append((column_group_key, column_group_options)) # grouping to avoid duplicate computation later

        appendix_lines = self.env['l10n_lu_reports.report.appendix.expenditures'].search_read(
            domain=[
                ('company_id', 'in', [comp['id'] for comp in options['companies']]),
                ('year', 'in', list(grouped_columns.keys())),
            ],
            fields=['id', 'report_section_411', 'report_section_412', 'report_section_413', 'year']
        )

        totals_by_column_group = {
            column_group_key: {
                'vat_excluded': 0.0,
                'vat_invoiced': 0.0,
            }
            for column_group_key in options['column_groups']
        }

        lines = []
        if options['export_mode'] != 'print': # don't print "add lines" in the pdf report
            # this is a line that just has an action that opens the appendix list view
            # to add as many appendix lines as the user needs
            action_line = self._get_appendix_line(report, options, {}, _('Add appendix lines'))
            action_line[1]['unfoldable'] = True
            lines.append(action_line)

        for appendix_line in appendix_lines:
            values = {}
            year = appendix_line['year']
            for column_group_key, column_group_options in grouped_columns[year]:
                values[column_group_key] = {
                    'vat_excluded': appendix_line['report_section_412'],
                    'vat_invoiced': appendix_line['report_section_413'],
                }
            lines.append(self._get_appendix_line(report, column_group_options, values,
                appendix_line['report_section_411'], level=2, line_id=appendix_line["id"]))
            self._update_total_values(totals_by_column_group, column_group_options, values)

        lines.append(self._get_appendix_line(report, options, totals_by_column_group,
            _('Total to be carried forward to line 43'), is_line_total=True))
        return lines

    def _get_appendix_line(self, report, options, column_vals, name, level=1, line_id=None, is_line_total=False):
        markup = 'total' if is_line_total else ''
        column_values = []

        for column in options['columns']:
            vals = column_vals.get(column['column_group_key'], {})
            col_val = vals.get(column['expression_label'])
            column_values.append(
                report._build_column_dict(col_val, column, options=options, digits=2)
            )

        vals = {
            'id': report._get_generic_line_id('l10n_lu_reports.report.appendix.expenditures', line_id, markup=markup),
            'name': name,
            'level': level,
            'columns': column_values,
        }
        if is_line_total:
            vals['code'] = 'L10N_LU_TAX_43'
        return (0, vals)

    def _update_total_values(self, totals_by_column_group, options, values):
        for column_group_key in options['column_groups']:
            for key in totals_by_column_group[column_group_key]:
                totals_by_column_group[column_group_key][key] += values.get(column_group_key, {}).get(key) or 0.0
