# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from collections import defaultdict

from odoo import _, api, fields, models
from odoo.tools import get_lang


class ECSalesReportCustomHandler(models.AbstractModel):
    _name = 'account.ec.sales.report.handler'
    _inherit = 'account.report.custom.handler'
    _description = 'EC Sales Report Custom Handler'

    def _get_custom_display_config(self):
        return {
            'components': {
                'AccountReportFilters': 'account_reports.SalesReportFilters',
            },
        }

    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals, warnings=None):
        """
        Generate the dynamic lines for the report in a vertical style (one line per tax per partner).
        """
        lines = []
        totals_by_column_group = {
            column_group_key: {
                'balance': 0.0,
                'goods': 0.0,
                'triangular': 0.0,
                'services': 0.0,
                'vat_number': '',
                'country_code': '',
                'sales_type_code': '',
            }
            for column_group_key in options['column_groups']
        }

        operation_categories = options['sales_report_taxes'].get('operation_category', {})
        ec_tax_filter_selection = {v.get('id'): v.get('selected') for v in options.get('ec_tax_filter_selection', [])}
        for partner, results in self._query_partners(report, options, warnings):
            for tax_ec_category in ('goods', 'triangular', 'services'):
                if not ec_tax_filter_selection[tax_ec_category]:
                    # Skip the line if the tax is not selected
                    continue
                partner_values = defaultdict(dict)
                country_specific_code = operation_categories.get(tax_ec_category)
                has_found_a_line = False
                for col_grp_key in options['column_groups']:
                    partner_sum = results.get(col_grp_key, {})
                    partner_values[col_grp_key]['vat_number'] = partner_sum.get('vat_number', 'UNKNOWN')
                    partner_values[col_grp_key]['country_code'] = partner_sum.get('country_code', 'UNKNOWN')
                    partner_values[col_grp_key]['sales_type_code'] = []
                    partner_values[col_grp_key]['balance'] = partner_sum.get(tax_ec_category, 0.0)
                    totals_by_column_group[col_grp_key]['balance'] += partner_sum.get(tax_ec_category, 0.0)
                    for i, operation_id in enumerate(partner_sum.get('tax_element_id', [])):
                        if operation_id in options['sales_report_taxes'][tax_ec_category]:
                            has_found_a_line = True
                            partner_values[col_grp_key]['sales_type_code'] += [
                                country_specific_code or
                                (partner_sum.get('sales_type_code') and partner_sum.get('sales_type_code')[i])
                                or None]
                    partner_values[col_grp_key]['sales_type_code'] = ', '.join(set(partner_values[col_grp_key]['sales_type_code']))
                if has_found_a_line:
                    lines.append((0, self._get_report_line_partner(report, options, partner, partner_values, markup=tax_ec_category)))

        # Report total line.
        if lines:
            lines.append((0, self._get_report_line_total(report, options, totals_by_column_group)))

        return lines

    def _caret_options_initializer(self):
        """
        Add custom caret option for the report to link to the partner and allow cleaner overrides.
        """
        return {
            'ec_sales': [
                {'name': _("View Partner"), 'action': 'caret_option_open_record_form'}
            ],
        }

    def _custom_options_initializer(self, report, options, previous_options=None):
        """
        Add the invoice lines search domain that is specific to the country.
        Typically, the taxes tag_ids relative to the country for the triangular, sale of goods or services
        :param dict options: Report options
        :param dict previous_options: Previous report options
        """
        super()._custom_options_initializer(report, options, previous_options=previous_options)
        self._init_core_custom_options(report, options, previous_options)
        options.update({
            'sales_report_taxes': {
                'goods': tuple(self.env['account.tax'].search([
                    *self.env['account.tax']._check_company_domain(self.env.company),
                    ('amount', '=', 0.0),
                    ('amount_type', '=', 'percent'),
                    ('type_tax_use', '=', 'sale'),
                ]).ids),
                'services': tuple(),
                'triangular': tuple(),
                'use_taxes_instead_of_tags': True,
                # We can't use tags as we don't have a country tax report correctly set, 'use_taxes_instead_of_tags'
                # should never be used outside this case
            }
        })
        country_ids = self.env['res.country'].search([
            ('code', 'in', tuple(self._get_ec_country_codes(options)))
        ]).ids
        other_country_ids = tuple(set(country_ids) - {self.env.company.account_fiscal_country_id.id})
        options.setdefault('forced_domain', []).append(('partner_id.country_id', 'in', other_country_ids))

        report._init_options_journals(options, previous_options=previous_options)

        self._enable_export_buttons_for_common_vat_groups_in_branches(options)

    def _init_core_custom_options(self, report, options, previous_options=None):
        """
        Add the invoice lines search domain that is common to all countries.
        :param dict options: Report options
        :param dict previous_options: Previous report options
        """
        default_tax_filter = [
            {'id': 'goods', 'name': _('Goods'), 'selected': True},
            {'id': 'triangular', 'name': _('Triangular'), 'selected': True},
            {'id': 'services', 'name': _('Services'), 'selected': True},
        ]
        options['ec_tax_filter_selection'] = (previous_options or {}).get('ec_tax_filter_selection', default_tax_filter)

    def _get_report_line_partner(self, report, options, partner, partner_values, markup=''):
        """
        Convert the partner values to a report line.
        :param dict options: Report options
        :param recordset partner: the corresponding res.partner record
        :param dict partner_values: Dictionary of values for the report line
        :return dict: Return a dict with the values for the report line.
        """
        column_values = []
        for column in options['columns']:
            value = partner_values[column['column_group_key']].get(column['expression_label'])
            column_values.append(report._build_column_dict(value, column, options=options))

        return {
            'id': report._get_generic_line_id('res.partner', partner.id, markup=markup),
            'name': partner is not None and (partner.name or '')[:128] or _('Unknown Partner'),
            'columns': column_values,
            'level': 2,
            'trust': partner.trust if partner else None,
            'caret_options': 'ec_sales',
        }

    def _get_report_line_total(self, report, options, totals_by_column_group):
        """
        Convert the total values to a report line.
        :param dict options: Report options
        :param dict totals_by_column_group: Dictionary of values for the total line
        :return dict: Return a dict with the values for the report line.
        """
        column_values = []
        for column in options['columns']:
            col_value = totals_by_column_group[column['column_group_key']].get(column['expression_label'])
            col_value = col_value if column['figure_type'] == 'monetary' else ''

            column_values.append(report._build_column_dict(col_value, column, options=options))

        return {
            'id': report._get_generic_line_id(None, None, markup='total'),
            'name': _('Total'),
            'class': 'total',
            'level': 1,
            'columns': column_values,
        }

    def _query_partners(self, report, options, warnings=None):
        ''' Execute the queries, perform all the computation, then
        returns a lists of tuple (partner, fetched_values) sorted by the table's model _order:
            - partner is a res.parter record.
            - fetched_values is a dictionary containing:
                - sums by operation type:           {'goods': float,
                                                     'triangular': float,
                                                     'services': float,

                - tax identifiers:                   'tax_element_id': list[int], > the tag_id in almost every case
                                                     'sales_type_code': list[str],

                - partner identifier elements:       'vat_number': str,
                                                     'full_vat_number': str,
                                                     'country_code': str}

        :param options:             The report options.
        :return:                    (accounts_values, taxes_results)
        '''
        groupby_partners = {}

        def assign_sum(row):
            """
            Assign corresponding values from the SQL querry row to the groupby_partners dictionary.
            If the line balance isn't 0, find the tax tag_id and check in which column/report line the SQL line balance
            should be displayed.

            The tricky part is to allow for the report to be displayed in vertical or horizontal format.
            In vertical, you have up to 3 lines per partner (one for each operation type).
            In horizontal, you have one line with 3 columns per partner (one for each operation type).

            Add then the more straightforward data (vat number, country code, ...)
            :param dict row:
            """
            if not company_currency.is_zero(row['balance']):
                groupby_partners.setdefault(row['groupby'], defaultdict(lambda: defaultdict(float)))

                groupby_partners_keyed = groupby_partners[row['groupby']][row['column_group_key']]
                if row['tax_element_id'] in options['sales_report_taxes']['goods']:
                    groupby_partners_keyed['goods'] += row['balance']
                elif row['tax_element_id'] in options['sales_report_taxes']['triangular']:
                    groupby_partners_keyed['triangular'] += row['balance']
                elif row['tax_element_id'] in options['sales_report_taxes']['services']:
                    groupby_partners_keyed['services'] += row['balance']

                groupby_partners_keyed.setdefault('tax_element_id', []).append(row['tax_element_id'])
                groupby_partners_keyed.setdefault('sales_type_code', []).append(row['sales_type_code'])

                vat = row['vat_number'] or ''
                groupby_partners_keyed.setdefault('vat_number', vat[2:])
                groupby_partners_keyed.setdefault('full_vat_number', vat)
                groupby_partners_keyed.setdefault('country_code', vat[:2])

                if warnings is not None:
                    if row['country_code'] not in self._get_ec_country_codes(options):
                        warnings['account_reports.sales_report_warning_non_ec_country'] = {'alert_type': 'warning'}
                    elif not row.get('vat_number'):
                        warnings['account_reports.sales_report_warning_missing_vat'] = {'alert_type': 'warning'}
                    if row.get('same_country') and row['country_code']:
                        warnings['account_reports.sales_report_warning_same_country'] = {'alert_type': 'warning'}

        company_currency = self.env.company.currency_id

        # Execute the queries and dispatch the results.
        query, params = self._get_query_sums(report, options)
        self._cr.execute(query, params)

        dictfetchall = self._cr.dictfetchall()
        for res in dictfetchall:
            assign_sum(res)

        if groupby_partners:
            partners = self.env['res.partner'].with_context(active_test=False).browse(groupby_partners.keys())
        else:
            partners = self.env['res.partner']

        return [(partner, groupby_partners[partner.id]) for partner in partners.sorted()]

    def _get_query_sums(self, report, options):
        ''' Construct a query retrieving all the aggregated sums to build the report. It includes:
        - sums for all partners.
        - sums for the initial balances.
        :param options:             The report options.
        :return:                    (query, params)
        '''
        params = []
        queries = []
        # Create the currency table.
        ct_query = report._get_query_currency_table(options)
        allowed_ids = self._get_tag_ids_filtered(options)

        # In the case of the generic report, we don't have a country defined. So no reliable tax report whose
        # tag_ids can be used. So we have a fallback to tax_ids.

        lang = self.env.user.lang or get_lang(self.env).code
        if options.get('sales_report_taxes', {}).get('use_taxes_instead_of_tags'):
            tax_elem_table = 'account_tax'
            aml_rel_table = 'account_move_line_account_tax_rel'
            tax_elem_table_name = f"COALESCE(account_tax.name->>'{lang}', account_tax.name->>'en_US')" if \
                self.pool['account.tax'].name.translate else 'account_tax.name'
        else:
            tax_elem_table = 'account_account_tag'
            aml_rel_table = 'account_account_tag_account_move_line_rel'
            tax_elem_table_name = f"COALESCE(account_account_tag.name->>'{lang}', account_account_tag.name->>'en_US')" if \
                self.pool['account.account.tag'].name.translate else 'account_account_tag.name'


        for column_group_key, column_group_options in report._split_options_per_column_group(options).items():
            tables, where_clause, where_params = report._query_get(column_group_options, 'strict_range')
            params.append(column_group_key)
            params += where_params
            if allowed_ids:
                where_clause += f" AND {tax_elem_table}.id IN %s"  # Add the tax element filter.
                params.append(tuple(allowed_ids))
            queries.append(f"""
                SELECT
                    %s                              AS column_group_key,
                    account_move_line.partner_id    AS groupby,
                    res_partner.vat                 AS vat_number,
                    res_country.code                AS country_code,
                    -SUM(account_move_line.balance) AS balance,
                    {tax_elem_table_name}           AS sales_type_code,
                    {tax_elem_table}.id             AS tax_element_id,
                    (comp_partner.country_id = res_partner.country_id) AS same_country
                FROM {tables}
                JOIN {ct_query} ON currency_table.company_id = account_move_line.company_id
                JOIN {aml_rel_table} ON {aml_rel_table}.account_move_line_id = account_move_line.id
                JOIN {tax_elem_table} ON {aml_rel_table}.{tax_elem_table}_id = {tax_elem_table}.id
                JOIN res_partner ON account_move_line.partner_id = res_partner.id
                JOIN res_country ON res_partner.country_id = res_country.id
                JOIN res_company ON res_company.id = account_move_line.company_id
                JOIN res_partner comp_partner ON comp_partner.id = res_company.partner_id
                WHERE {where_clause}
                GROUP BY {tax_elem_table}.id, {tax_elem_table}.name, account_move_line.partner_id,
                res_partner.vat, res_country.code, comp_partner.country_id, res_partner.country_id
            """)
        return ' UNION ALL '.join(queries), params

    @api.model
    def _get_tag_ids_filtered(self, options):
        """
        Helper function to get all the tag_ids concerned by the report for the given options.
        :param dict options: Report options
        :return tuple: tag_ids untyped after filtering
        """
        allowed_taxes = set()
        for operation_type in options.get('ec_tax_filter_selection', []):
            if operation_type.get('selected'):
                allowed_taxes.update(options['sales_report_taxes'][operation_type.get('id')])
        return allowed_taxes

    @api.model
    def _get_ec_country_codes(self, options):
        """
        Return the list of country codes for the EC countries.
        :param dict options: Report options
        :return set: List of country codes for a given date (UK case)
        """
        rslt = {'AT', 'BE', 'BG', 'HR', 'CY', 'CZ', 'DK', 'EE', 'FI', 'FR', 'DE', 'GR', 'HU',
                'IE', 'IT', 'LV', 'LT', 'LU', 'MT', 'NL', 'PL', 'PT', 'RO', 'SK', 'SI', 'ES', 'SE'}

        # GB left the EU on January 1st 2021. But before this date, it's still to be considered as a EC country
        if fields.Date.from_string(options['date']['date_from']) < fields.Date.from_string('2021-01-01'):
            rslt.add('GB')
        return rslt

    def get_warning_act_window(self, options, params):
        act_window = {'type': 'ir.actions.act_window', 'context': {}}
        if params['type'] == 'no_vat':
            aml_domains = [
                ('partner_id.vat', '=', None),
                ('partner_id.country_id.code', 'in', tuple(self._get_ec_country_codes(options))),
            ]
            act_window.update({
                'name': _("Entries with partners with no VAT"),
                'context': {'search_default_group_by_partner': 1, 'expand': 1}
            })
        elif params['type'] == 'non_ec_country':
            aml_domains = [('partner_id.country_id.code', 'not in', tuple(self._get_ec_country_codes(options)))]
            act_window['name'] = _("EC tax on non EC countries")
        else:
            aml_domains = [('partner_id.country_id.code', '=', options.get('same_country_warning'))]
            act_window['name'] = _("EC tax on same country")
        use_taxes_instead_of_tags = options.get('sales_report_taxes', {}).get('use_taxes_instead_of_tags')
        tax_or_tag_field = 'tax_ids.id' if use_taxes_instead_of_tags else 'tax_tag_ids.id'
        amls = self.env['account.move.line'].search([
            *aml_domains,
            *self.env['account.report']._get_options_date_domain(options, 'strict_range'),
            (tax_or_tag_field, 'in', tuple(self._get_tag_ids_filtered(options)))
        ])

        if params['model'] == 'move':
            act_window.update({
                'views': [[self.env.ref('account.view_move_tree').id, 'list'], (False, 'form')],
                'res_model': 'account.move',
                'domain': [('id', 'in', amls.move_id.ids)],
            })
        else:
            act_window.update({
                'views': [(False, 'list'), (False, 'form')],
                'res_model': 'res.partner',
                'domain': [('id', 'in', amls.move_id.partner_id.ids)],
            })

        return act_window
