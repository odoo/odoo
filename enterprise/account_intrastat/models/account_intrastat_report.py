# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import re
from json import dumps, loads

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.osv import expression
from odoo.tools import get_lang, SQL

_merchandise_export_code = {
    'BE': '29',
    'FR': '21',
    'NL': '7',
}

_merchandise_import_code = {
    'BE': '19',
    'FR': '11',
    'NL': '6',
}

_unknown_country_code = {
    'BE': 'QU',
    'FR': 'QU',  # source: https://www.douane.gouv.fr/debweb/cf.srv when trying with the simulation tool
    'NL': 'QV',
}

_qn_unknown_individual_vat_country_codes = ('FI', 'SE', 'SK', 'DE', 'AT')

_grouping_keys = [
    'intrastat_type',
    'system',
    'country_code',
    'transaction_code',
    'transport_code',
    'region_code',
    'commodity_code',
    'country_name',
    'partner_vat',
    'incoterm_code',
    'intrastat_product_origin_country_code',
    'intrastat_product_origin_country_name',
    'invoice_currency_id',
    'supplementary_units_code',
]

class IntrastatReportCustomHandler(models.AbstractModel):
    _name = 'account.intrastat.report.handler'
    _inherit = 'account.report.custom.handler'
    _description = 'Intrastat Report Custom Handler'

    def _get_custom_display_config(self):
        return {
            'templates': {
                'AccountReportFilters': 'account_intrastat.IntrastatReportFilters',
            },
        }

    def _custom_options_initializer(self, report, options, previous_options):
        # Filter only partners with VAT
        options['intrastat_with_vat'] = previous_options.get('intrastat_with_vat', False)

        # Filter types of invoices
        default_type = [
            {'name': _('Arrival'), 'selected': False, 'id': 'arrival'},
            {'name': _('Dispatch'), 'selected': False, 'id': 'dispatch'},
        ]
        options['intrastat_type'] = previous_options.get('intrastat_type', default_type)
        options['country_format'] = previous_options.get('country_format')
        options['commodity_flow'] = previous_options.get('commodity_flow')

        # Filter the domain based on the types of invoice selected
        include_arrivals, include_dispatches = self._determine_inclusion(options)

        invoice_types = []
        if include_arrivals:
            invoice_types += ['in_invoice', 'out_refund']
        if include_dispatches:
            invoice_types += ['out_invoice', 'in_refund']

        # When only one type is selected, we can display a total line
        options.setdefault('forced_domain', []).append(('move_id.move_type', 'in', invoice_types))

        # Filter report type (extended form)
        options['intrastat_extended'] = previous_options.get('intrastat_extended', True)

        # 2 columns are conditional and should only appear when rendering the extended intrastat report
        # Some countries don't use the region code column; we hide it for them.
        excluded_columns = set()
        if not options['intrastat_extended']:
            excluded_columns |= {'transport_code', 'incoterm_code'}
        if not self._show_region_code():
            excluded_columns.add('region_code')

        new_columns = []
        for col in options['columns']:
            if col['expression_label'] not in excluded_columns:
                new_columns.append(col)

                # Replace country names by codes if necessary (for file exports)
                if options.get('country_format') == 'code':
                    if col['expression_label'] == 'country_name':
                        col['expression_label'] = 'country_code'
                    elif col['expression_label'] == 'intrastat_product_origin_country_name':
                        col['expression_label'] = 'intrastat_product_origin_country_code'
        options['columns'] = new_columns

        # Only pick Sale/Purchase journals (+ divider)
        report._init_options_journals(options, previous_options=previous_options, additional_journals_domain=[('type', 'in', ('sale', 'purchase'))])

        # When printing the report to xlsx, we want to use country codes instead of names
        xlsx_button_option = next(button_opt for button_opt in options['buttons'] if button_opt.get('action_param') == 'export_to_xlsx')
        xlsx_button_option['action_param'] = 'export_to_xlsx'

    @api.model
    def _determine_inclusion(self, options):
        include_arrivals = options['intrastat_type'][0]['selected']
        include_dispatches = options['intrastat_type'][1]['selected']
        if not include_arrivals and not include_dispatches:
            include_arrivals = include_dispatches = True
        return include_arrivals, include_dispatches

    ####################################################
    # OVERRIDES
    ####################################################

    def _show_region_code(self):
        """Return a bool indicating if the region code is to be displayed for the country concerned in this localisation."""
        # TO OVERRIDE
        return True

    def _get_exporting_query_data(self):
        # TO OVERRIDE
        return SQL()

    def _get_exporting_dict_data(self, result_dict, query_res):
        # TO OVERRIDE
        return result_dict

    ####################################################
    # OPTIONS: INIT
    ####################################################

    def export_to_xlsx(self, options, response=None):
        # We need to regenerate the options to make sure we hide the country name columns as expected.
        report = self.env['account.report'].browse(options['report_id'])
        new_options = report.get_options(previous_options={**options, 'country_format': 'code', 'commodity_flow': 'code'})
        return report.export_to_xlsx(new_options, response=response)

    ####################################################
    # REPORT LINES: CORE
    ####################################################

    def _report_custom_engine_intrastat(self, expressions, options, date_scope, current_groupby, next_groupby, offset=0, limit=None, warnings=None):
        def build_result_dict(query_res_lines):
            if current_groupby:
                res = query_res_lines[0]

                if res['supplementary_units']:
                    supplementary_units = f"{sum(line.get('supplementary_units', 0) for line in query_res_lines)}"
                else:
                    supplementary_units = None
                value = res['value'] or None if current_groupby == 'intrastat_grouping' else sum(line['value'] for line in query_res_lines if not line['missing_product'])
                value_currency = res['value_currency'] if res['invoice_currency_id'] != self.env.company.currency_id.id else None
                result_dict = {
                    'system': f"{res['system']} ({res['intrastat_type']})",
                    'intrastat_type': res['intrastat_type'],
                    'country_name': res['country_name'],
                    'country_code': res['country_code'],
                    'transaction_code': res['transaction_code'],
                    'region_code': res['region_code'],
                    'commodity_code': res['commodity_code'],
                    'intrastat_product_origin_country_code': res['intrastat_product_origin_country_code'],
                    'intrastat_product_origin_country_name': res['intrastat_product_origin_country_name'],
                    'partner_vat': res['partner_vat'],
                    'transport_code': res['transport_code'],
                    'incoterm_code': res['incoterm_code'],
                    'weight': res['weight'] or None,
                    'supplementary_units': supplementary_units,
                    'value': value,
                    'value_currency': value_currency,
                    'currency_id_of_value_currency': res['invoice_currency_id'],
                    'has_sublines': True,
                }
                if options.get('export_mode') == 'file':
                    return self._get_exporting_dict_data(result_dict, res)
                return result_dict

            return {
                'system': None,
                'country_name': None,
                'country_code': None,
                'transaction_code': None,
                'region_code': None,
                'commodity_code': None,
                'intrastat_product_origin_country_code': None,
                'intrastat_product_origin_country_name': None,
                'partner_vat': None,
                'transport_code': None,
                'incoterm_code': None,
                'weight': None,
                'supplementary_units': None,
                'value': sum(line.get('value', 0) for line in query_res_lines if not line['missing_product']),
                'value_currency': None,
                'currency_id_of_value_currency': None,
                'has_sublines': len(query_res_lines) > 0,
            }

        report = self.env['account.report'].browse(options['report_id'])
        report._check_groupby_fields([current_groupby] if current_groupby else [])

        query = self._get_intrastat_report_query(
            report=report,
            options=options,
            current_groupby=current_groupby,
            offset=offset,
            limit=limit,
            warnings=warnings,
        )
        self._cr.execute(query)
        query_res_lines = self._cr.dictfetchall()
        query_res_lines = self._fill_missing_values(query_res_lines)

        all_res_per_grouping_key = {}

        for line in query_res_lines:
            if warnings is not None:
                for key, value in line.items():
                    if key.startswith('warning_') and value:
                        warning_params = warnings.setdefault(
                            f'account_intrastat.intrastat_{key}',
                            {'ids': [], 'alert_type': 'warning'}
                        )
                        warning_params['ids'] += value
            if current_groupby and not line['missing_product']:
                if current_groupby == 'intrastat_grouping':
                    grouping_key = dumps({
                        key: line[key]
                        for key in _grouping_keys
                    })
                else:
                    grouping_key = line['grouping_key']
                all_res_per_grouping_key.setdefault(grouping_key, []).append(line)

        if current_groupby:
            return [
                (grouping_key, build_result_dict(query_res_lines)) for
                grouping_key, query_res_lines in all_res_per_grouping_key.items()
            ]
        return build_result_dict(query_res_lines)

    def _get_intrastat_report_query(self, report, options, current_groupby, query_params=None, offset=None, limit=None, warnings=None, order_by=True):
        """ Generates query for intrastat report. """
        query_params = {
            'product_type_condition': SQL("AND (account_move_line.product_id IS NULL OR prodt.type != 'service')"),
            'commodity_warning_suffix': SQL('comm'),
            'country_table_join': SQL("LEFT JOIN res_country country ON account_move.intrastat_country_id = country.id"),
            'country_condition': SQL("AND country.intrastat = TRUE AND (country.code != 'GB' OR account_move.date < '2021-01-01')"),
            'commodity_code': SQL('code.code'),
            **(query_params or {}),
        }
        report_query = report._get_report_query(options, 'strict_range')
        select_from_groupby = (
            SQL() if not current_groupby or current_groupby == 'intrastat_grouping'
            else self.env['account.move.line']._field_to_sql('account_move_line', current_groupby, report_query)
        )
        lang = self.env.user.lang or get_lang(self.env).code
        self_lang = self.with_context(lang=lang)
        query = SQL("""
            SELECT
                %(select_from_groupby)s AS grouping_key,
                CASE WHEN account_move.move_type IN ('in_invoice', 'out_refund') THEN %(import_merchandise_code)s ELSE %(export_merchandise_code)s END AS system,
                country.code AS country_code,
                %(country_name)s AS country_name,
                transaction.code AS transaction_code,
                company_region.code AS region_code,
                CASE WHEN (code.country_id IS NULL OR code.country_id = %(country_id)s) THEN %(commodity_code)s ELSE NULL END AS commodity_code,
                account_move.currency_id AS invoice_currency_id,
                COALESCE(inv_incoterm.code, comp_incoterm.code) AS incoterm_code,
                COALESCE(inv_transport.code, comp_transport.code) AS transport_code,
                %(system)s,
                SUM(ROUND(
                    COALESCE(prod.weight, 0) * account_move_line.quantity / (
                        CASE WHEN inv_line_uom.category_id IS NULL OR inv_line_uom.category_id = prod_uom.category_id
                        THEN inv_line_uom.factor ELSE 1 END
                    ) * (
                        CASE WHEN prod_uom.uom_type <> 'reference'
                        THEN prod_uom.factor ELSE 1 END
                    ),
                    SCALE(ref_weight_uom.rounding)
                )) AS weight,
                CASE WHEN code.supplementary_unit IS NOT NULL and SUM(prod.intrastat_supplementary_unit_amount) != 0
                    THEN CAST(SUM(prod.intrastat_supplementary_unit_amount * (
                        account_move_line.quantity / (
                            CASE WHEN inv_line_uom.category_id IS NULL OR inv_line_uom.category_id = prod_uom.category_id
                            THEN inv_line_uom.factor ELSE 1 END
                        ))) AS numeric)
                    ELSE NULL END AS supplementary_units,
                code.supplementary_unit AS supplementary_units_code,
                -- We double sign the balance to make sure that we keep consistency between invoice/bill and the intrastat report
                -- Example: An invoice selling 10 items (but one is free 10 - 1), in the intrastat report we'll have 2 lines
                -- One for 10 items minus one for the free item
                SUM(SIGN(account_move_line.quantity) * SIGN(account_move_line.price_unit) * ABS(%(balance_select)s)) AS value,
                SUM(SIGN(account_move_line.quantity) * SIGN(account_move_line.price_unit) * ABS(account_move_line.amount_currency)) AS value_currency,
                CASE WHEN product_country.code = 'GB' THEN 'XU' ELSE COALESCE(product_country.code, %(unknown_country_code)s) END AS intrastat_product_origin_country_code,
                %(product_country_name)s AS intrastat_product_origin_country_name,
                CASE WHEN partner.vat IS NOT NULL THEN partner.vat
                     WHEN partner.vat IS NULL AND partner.is_company IS FALSE THEN %(unknown_individual_vat)s
                     ELSE 'QV999999999999'
                END AS partner_vat,
                MAX(CASE WHEN prod.id IS NULL THEN 1 ELSE 0 END) AS missing_product,
                %(warnings)s
                %(exporting_data)s
                COUNT(account_move_line.id) AS amls_count,
                invoice_currency.name AS invoice_currency_name
            FROM
                %(table_references)s
                %(currency_table_join)s
                JOIN account_move ON account_move.id = account_move_line.move_id
                LEFT JOIN account_intrastat_code transaction ON account_move_line.intrastat_transaction_id = transaction.id
                LEFT JOIN res_company company ON account_move.company_id = company.id
                LEFT JOIN account_intrastat_code company_region ON company.intrastat_region_id = company_region.id
                LEFT JOIN res_partner partner ON account_move_line.partner_id = partner.id
                %(country_table_join)s
                LEFT JOIN res_partner comp_partner ON company.partner_id = comp_partner.id
                LEFT JOIN res_country company_country ON comp_partner.country_id = company_country.id
                LEFT JOIN product_product prod ON account_move_line.product_id = prod.id
                LEFT JOIN product_template prodt ON prod.product_tmpl_id = prodt.id
                LEFT JOIN account_intrastat_code code ON code.id = prod.intrastat_code_id
                LEFT JOIN uom_uom inv_line_uom ON account_move_line.product_uom_id = inv_line_uom.id
                LEFT JOIN uom_uom prod_uom ON prodt.uom_id = prod_uom.id
                LEFT JOIN account_incoterms inv_incoterm ON account_move.invoice_incoterm_id = inv_incoterm.id
                LEFT JOIN account_incoterms comp_incoterm ON company.incoterm_id = comp_incoterm.id
                LEFT JOIN account_intrastat_code inv_transport ON account_move.intrastat_transport_mode_id = inv_transport.id
                LEFT JOIN account_intrastat_code comp_transport ON company.intrastat_transport_mode_id = comp_transport.id
                LEFT JOIN res_country product_country ON product_country.id = account_move_line.intrastat_product_origin_country_id
                LEFT JOIN res_country partner_country ON partner.country_id = partner_country.id AND partner_country.intrastat IS TRUE
                LEFT JOIN uom_uom ref_weight_uom on ref_weight_uom.category_id = %(weight_category_id)s and ref_weight_uom.uom_type = 'reference'
                LEFT JOIN res_currency invoice_currency ON invoice_currency.id = account_move.currency_id
            WHERE
                %(search_condition)s
                AND account_move_line.display_type = 'product'
                AND (account_move_line.price_subtotal != 0 OR account_move_line.price_unit * account_move_line.quantity != 0)
                AND (company_country.id != country.id OR country.id IS NULL)
                AND ref_weight_uom.active
                %(product_type_condition)s
                %(vat_condition)s
                %(country_condition)s
            GROUP BY
                %(groupby)s, grouping_key, invoice_currency.name
            """,
            # select
            select_from_groupby=select_from_groupby or '',
            import_merchandise_code=_merchandise_import_code.get(self.env.company.country_id.code, '29'),
            export_merchandise_code=_merchandise_export_code.get(self.env.company.country_id.code, '19'),
            country_name=self_lang.env['res.country']._field_to_sql('country', 'name'),
            country_id=self.env.company.country_id.id,
            commodity_code=query_params['commodity_code'],
            balance_select=report._currency_table_apply_rate(SQL("account_move_line.balance")),
            unknown_country_code=_unknown_country_code.get(self.env.company.country_id.code, 'QV'),
            product_country_name=self_lang.env['res.country']._field_to_sql('product_country', 'name'),
            unknown_individual_vat='QN999999999999' if self.env.company.country_id.code in _qn_unknown_individual_vat_country_codes else 'QV999999999999',
            system=SQL("CASE WHEN account_move.move_type IN ('in_invoice', 'out_refund') THEN %s ELSE %s END AS intrastat_type", _('Arrival'), _('Dispatch')),
            warnings=SQL("""
                ARRAY_AGG(account_move_line.id) FILTER (WHERE transaction.expiry_date <= account_move.invoice_date) AS warning_expired_trans,
                ARRAY_AGG(account_move_line.id) FILTER (WHERE transaction.start_date > account_move.invoice_date) AS warning_premature_trans,
                ARRAY_AGG(account_move_line.id) FILTER (WHERE transaction.id IS NULL AND prodt.type = 'consu') AS warning_missing_trans,
                ARRAY_AGG(account_move_line.id) FILTER (WHERE prod.id IS NULL) AS warning_missing_product,
                ARRAY_AGG(prod.id) FILTER (WHERE COALESCE(prod.intrastat_supplementary_unit_amount, 0) = 0 AND code.supplementary_unit IS NOT NULL) AS warning_missing_unit,
                ARRAY_AGG(prod.id) FILTER (WHERE COALESCE(prod.weight, 0) = 0 AND code.supplementary_unit IS NULL AND prod.id IS NOT NULL AND prodt.type = 'consu') AS warning_missing_weight,
                ARRAY_AGG(prod.id) FILTER (WHERE code.expiry_date <= account_move.invoice_date) AS warning_expired_%(commodity_warning_suffix)s,
                ARRAY_AGG(prod.id) FILTER (WHERE code.start_date > account_move.invoice_date) AS warning_premature_%(commodity_warning_suffix)s,
                ARRAY_AGG(prod.id) FILTER (WHERE code.id IS NULL AND prod.id IS NOT NULL) AS warning_missing_%(commodity_warning_suffix)s,
            """,
                commodity_warning_suffix=query_params['commodity_warning_suffix']
            ) if warnings is not None else SQL(''),
            exporting_data=self._get_exporting_query_data() if options.get('export_mode') == 'file' else SQL(),
            # from
            table_references=report_query.from_clause,
            currency_table_join=report._currency_table_aml_join(options),
            country_table_join=query_params['country_table_join'],
            weight_category_id=self.env['ir.model.data']._xmlid_to_res_id('uom.product_uom_categ_kgm'),
            # where
            search_condition=report_query.where_clause,
            product_type_condition=query_params['product_type_condition'],
            vat_condition=SQL("AND partner.vat IS NOT NULL") if options['intrastat_with_vat'] else SQL(),
            country_condition=query_params['country_condition'],
            # group by
            groupby=SQL(', ').join(SQL(key) for key in _grouping_keys) if options['export_mode'] != 'file' and current_groupby == 'intrastat_grouping' else self._get_export_groupby_clause(),
        )
        if order_by:
            order_by_clause = SQL('grouping_key') if current_groupby != 'id' else SQL('account_move_line.date desc, account_move_line.move_name desc, account_move_line.id')
            query = SQL("\n").join([query, SQL("ORDER BY %s", order_by_clause)])
        # query tail
        query = SQL("\n").join([query, report._get_engine_query_tail(offset, limit)])
        return query

    def _custom_line_postprocessor(self, report, options, lines):
        for line in lines:
            if name := re.search(r"^[A-Za-z]+(/\d+)+", line['name']):
                line['name'] = name.group()
        return lines

    def _get_custom_groupby_map(self):
        return {
            "intrastat_grouping": {
                'model': None,
                'domain_builder': self._build_custom_domain,
                'label_builder': self._intrastat_groupby_label_builder,
            }
        }

    def _intrastat_groupby_label_builder(self, grouping_key):
        parsed_key = loads(grouping_key)
        return f"{parsed_key['intrastat_type']} - {parsed_key['partner_vat']} - {parsed_key['commodity_code']} - {parsed_key['country_code']}"

    def _build_intrastat_custom_domain_blocks(self, grouping_key_dict):
        """
        Build custom domain dict for intrastat report.
        This is a dict to allow easy overrides of domains based on grouping_key_dict keys.
        """
        if grouping_key_dict['intrastat_product_origin_country_code'] == 'XU':
            grouping_key_dict['intrastat_product_origin_country_code'] = 'GB'

        domain_dict = {
            'country_code': [('move_id.intrastat_country_id.code', '=', grouping_key_dict['country_code'])],
            'invoice_currency_id': [('currency_id.id', '=', grouping_key_dict['invoice_currency_id'])],
        }

        if grouping_key_dict['commodity_code']:
            domain_dict['commodity_code'] = [(
                'product_id.intrastat_code_id.code', '=', grouping_key_dict['commodity_code']
            )]
        else:
            domain_dict['commodity_code'] = [('product_id.intrastat_code_id', '=', False)]

        if grouping_key_dict['transaction_code']:
            domain_dict['transaction_code'] = [(
                'intrastat_transaction_id.code', '=', grouping_key_dict['transaction_code']
            )]
        else:
            domain_dict['transaction_code'] = [('intrastat_transaction_id', '=', False)]

        if grouping_key_dict['region_code']:
            domain_dict['region_code'] = [(
                'move_id.company_id.intrastat_region_id.code', '=', grouping_key_dict['region_code']
            )]
        else:
            domain_dict['region_code'] = [('move_id.company_id.intrastat_region_id', '=', False)]

        if grouping_key_dict['system'] == _merchandise_import_code.get(self.env.company.country_id.code, '29'):
            domain_dict['system'] = [('move_id.move_type', 'in', ['in_invoice', 'out_refund'])]
        else:
            domain_dict['system'] = [('move_id.move_type', 'not in', ['in_invoice', 'out_refund'])]

        if grouping_key_dict['intrastat_product_origin_country_code'] in ['QU', 'QV']:
            domain_dict['intrastat_product_origin_country_code'] = [
                ('intrastat_product_origin_country_id', '=', False)
            ]
        else:
            domain_dict['intrastat_product_origin_country_code'] = [(
                'intrastat_product_origin_country_id.code',
                '=',
                grouping_key_dict['intrastat_product_origin_country_code'],
            )]

        if grouping_key_dict['partner_vat'] in ['QN999999999999', 'QV999999999999']:
            domain_dict['partner_vat'] = [('move_id.partner_id.vat', '=', False)]
        else:
            domain_dict['partner_vat'] = [
                ('move_id.partner_id.vat', '=', grouping_key_dict['partner_vat'])
            ]

        if grouping_key_dict['transport_code']:
            domain_dict['transport_code'] = [(
                'move_id.intrastat_transport_mode_id.code', '=', grouping_key_dict['transport_code']
            )]
        else:
            domain_dict['transport_code'] = [('move_id.intrastat_transport_mode_id', '=', False)]

        if grouping_key_dict['incoterm_code']:
            domain_dict['incoterm_code'] = expression.OR([
                [('move_id.invoice_incoterm_id.code', '=', grouping_key_dict['incoterm_code'])],
                [
                    ('move_id.invoice_incoterm_id', '=', False),
                    ('move_id.company_id.incoterm_id.code', '=', grouping_key_dict['incoterm_code']),
                ],
            ])
        else:
            domain_dict['incoterm_code'] = [('move_id.invoice_incoterm_id', '=', False)]

        return domain_dict

    def _build_custom_domain(self, grouping_key):
        return expression.AND(self._build_intrastat_custom_domain_blocks(loads(grouping_key)).values())

    ####################################################
    # REPORT LINES: HELPERS
    ####################################################

    @api.model
    def _fill_missing_values(self, vals_list):
        """ Template method to be overidden to retrieve complex data

            :param vals_list:    A dictionary created by the dictfetchall method.
        """
        return vals_list

    def _get_export_groupby_clause(self):
        return SQL("""country.id, transaction.id, company_region.id, code.id, inv_incoterm.id, comp_incoterm.id,
             inv_transport.id, comp_transport.id, product_country.id, account_move_line.id, account_move.id,
             inv_line_uom.factor, prod_uom.id, ref_weight_uom.rounding, partner.id, prod.id, prodt.id, account_move_line.date, account_move_line.move_name""")

    ####################################################
    # ACTIONS
    ####################################################

    def action_invalid_code_moves(self, options, params):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Invalid transaction intrastat code entries.'),
            'res_model': 'account.move.line',
            'views': [(
                self.env.ref('account_intrastat.account_move_line_tree_view_account_intrastat_transaction_codes').id,
                'list',
            ), (False, 'form')],
            'domain': [('id', 'in', params['ids'])],
            'context': {
                'create': False,
                'delete': False,
                'expand': True,
            },
        }

    def action_invalid_code_products(self, options, params):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Invalid commodity intrastat code products.'),
            'res_model': 'product.product',
            'views': [(
                self.env.ref('account_intrastat.product_product_tree_view_account_intrastat').id,
                'list',
            ), (False, 'form')],
            'domain': [('id', 'in', params['ids'])],
            'context': {
                'create': False,
                'delete': False,
                'expand': True,
            },
        }

    def action_undefined_units_products(self, options, params):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Undefined supplementary unit products.'),
            'res_model': 'product.product',
            'views': [(
                self.env.ref('account_intrastat.product_product_tree_view_account_intrastat_supplementary_unit').id,
                'list',
            ), (False, 'form')],
            'domain': [('id', 'in', params['ids'])],
            'context': {
                'create': False,
                'delete': False,
                'expand': True,
            },
        }

    def action_undefined_weight_products(self, options, params):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Undefined weight products.'),
            'res_model': 'product.product',
            'views': [(
                self.env.ref('account_intrastat.product_product_tree_view_account_intrastat_weight').id,
                'list',
            ), (False, 'form')],
            'domain': [('id', 'in', params['ids'])],
            'context': {
                'create': False,
                'delete': False,
                'expand': True,
            },
        }

    def action_missing_intrastat_product_origin_country_code(self, move_line_ids):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Missing country of origin'),
            'res_model': 'account.move.line',
            'views': [(
                self.env.ref('account_intrastat.account_move_line_tree_view_account_intrastat_product_origin_country_id').id,
                'list',
            ), (False, 'form')],
            'domain': [('id', 'in', move_line_ids)],
            'context': {
                'create': False,
                'delete': False,
                'expand': True,
            },
        }

    def action_invalid_transport_mode_moves(self, move_ids):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Invalid transport mode code entries.'),
            'res_model': 'account.move',
            'views': [(
                self.env.ref('account_intrastat.account_move_tree_view_account_intrastat_transport_codes').id,
                'list',
            ), (False, 'form')],
            'domain': [('id', 'in', move_ids)],
            'context': {
                'create': False,
                'delete': False,
                'expand': True,
            },
        }

    def action_missing_product(self, options, params):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Missing product'),
            'res_model': 'account.move.line',
            'views': [
                (self.env.ref('account_intrastat.account_intrastat_aml_missing_product_tree').id, 'list'),
                (False, 'form'),
            ],
            'domain': [('id', 'in', params['ids'])],
            'context': {
                'create': False,
                'delete': False,
                'expand': True,
            },
        }

    @api.model
    def _check_date_range(self, options, allow_quarterly=True):
        date_from = fields.Date.to_date(options['date']['date_from'])
        date_to = fields.Date.to_date(options['date']['date_to'])
        month_last_day = fields.Date.end_of(date_from, 'month')
        quarter_last_day = fields.Date.end_of(date_from, 'quarter')

        month_ok = date_from.day == 1 and date_to == month_last_day
        quarter_ok = date_from.day == 1 and date_from.month % 3 == 1 and date_to == quarter_last_day

        if not month_ok and not allow_quarterly:
            raise UserError(_('The date range must be a full month'))

        if not month_ok and not quarter_ok:
            raise UserError(_('The date range must be a full month or a full quarter.'))

        return True
