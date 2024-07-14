from odoo import models, fields, api, _
from odoo.tools import date_utils, float_repr, float_is_zero, float_compare
from odoo.exceptions import UserError, RedirectWarning

from datetime import datetime

import pytz


class PolishTaxReportCustomHandler(models.AbstractModel):
    """
    Handler for generating the JPK V7M and V7K declarations.
    The V7M is for taxpayers filing monthly VAT declarations, and includes a list of invoices /
    vendor bills as well as the content of the VAT declaration.
    The V7K is for taxpayers filing quarterly VAT declarations: for the two first months of a
    quarter, it includes the list of invoices / vendor bills for the month; on the last month of
    the quarter, it includes the list of invoices / vendor bills for the last month and the VAT
    declaration for the entire quarter.
    """
    _name = 'l10n_pl.tax.report.handler'
    _inherit = 'account.tax.report.handler'
    _description = 'Polish Tax Report Custom Handler'

    def _custom_options_initializer(self, report, options, previous_options=None):
        super()._custom_options_initializer(report, options, previous_options=previous_options)

        options.setdefault('buttons', []).append({
            'name': 'JPK',
            'sequence': 30,
            'action': 'print_tax_report_to_xml',
            'file_export_type': 'XML',
        })

    def print_tax_report_to_xml(self, options):
        # add options to context and return action to open transient model
        message = ""
        if not self.env.company.vat:
            message += _("Please configure the vat number in the company's contact.\n")
        if not self.env.company.email:
            message += _("Please configure the email in the company's contact.\n")
        if not self.env.company.partner_id.is_company and len(self.env.company.name.split()) <= 1:
            message += _("As your company is an individual, please put your name and surname separated by a space in the company's contact.\n")
        if self.env.company.account_tax_periodicity not in ('monthly', 'trimester'):
            message += _("The company's tax periodicity needs to be quarterly (for JPK_v7k) or monthly (for JPK_v7m).\n")
        if message:
            message = _("Some information is needed to generate the file:\n") + message
            self._l10n_pl_redirect_to_misconfigured_company(message)
        if not self.env.company.l10n_pl_reports_tax_office_id:
            raise UserError(
                _('Please configure the tax office in the Accounting Settings.'),
            )

        new_wizard = self.env['l10n_pl_reports.periodic.vat.xml.export'].create({})
        view_id = self.env.ref('l10n_pl_reports.view_account_financial_report_export').id
        return {
            'name': 'XML Export Options',
            'view_mode': 'form',
            'views': [[view_id, 'form']],
            'res_model': 'l10n_pl_reports.periodic.vat.xml.export',
            'type': 'ir.actions.act_window',
            'res_id': new_wizard.id,
            'target': 'new',
            'context': dict(self._context, l10n_pl_reports_generation_options=options),
        }

    @api.model
    def _l10n_pl_redirect_to_misconfigured_company(self, message):
        """ Raises a RedirectWarning informing the user his company is missing configuration, redirecting him to the
         tree view of res.company
        """
        action = self.env.ref('base.action_res_company_form')

        raise RedirectWarning(
            message,
            action.id,
            _("Configure your company"),
        )

    @api.model
    def _l10n_pl_get_query_parts(self):
        """ This creates the query to get all information for JPK
            We split it, to be overridable (for example with point_of_sale)
            The query gets the information on moves and information aggregated from their lines for the whole move
            like the tax amounts that are grouped by tax grid and move """
        dict_query_parts = {
            'select_query_part': r"""
            WITH 
              -- payment_date is necessary in case of payment received before the invoice_date
              -- invoice_date_due in case of payment overdue, where we need the due date of the invoice
              partial_reconcile_date AS (
                    SELECT "counterpart_line".date,
                           "counterpart_move".invoice_date_due,
                           "account_move_line__move_id".id as id
                      FROM {tables}
                      JOIN account_partial_reconcile part ON part.debit_move_id = "account_move_line".id
                      JOIN account_account ON "account_move_line".account_id = account_account.id
                      JOIN account_move_line "counterpart_line" ON part.credit_move_id = "counterpart_line".id
                      JOIN account_move "counterpart_move" ON "counterpart_line".move_id = "counterpart_move".id
                     WHERE account_account.account_type IN ('asset_receivable', 'liability_payable')
                       AND {where_clause}
                 UNION ALL
                    SELECT "counterpart_line".date,
                           "counterpart_move".invoice_date_due,
                           "account_move_line__move_id".id as id
                      FROM {tables}
                      JOIN account_partial_reconcile part ON part.credit_move_id = "account_move_line".id
                      JOIN account_account ON "account_move_line".account_id = account_account.id
                      JOIN account_move_line "counterpart_line" ON part.debit_move_id = "counterpart_line".id
                      JOIN account_move "counterpart_move" ON "counterpart_line".move_id = "counterpart_move".id
                     WHERE account_account.account_type IN ('asset_receivable', 'liability_payable')
                       AND {where_clause}
                  ),
                  -- aml_aggregates corresponds to aggregate aml amount per tax tag for each move
                  aml_aggregates as (
                    SELECT SUM( 
                               CASE WHEN account_move_line.tax_tag_invert THEN -1 ELSE 1 END
                               * CASE WHEN tag.tax_negate THEN -1 ELSE 1 END
                               * account_move_line.balance
                           ) AS amounts,
                           {move_to_group_by} AS move_id,
                           SUBSTRING({tag_name}, 4) AS tag_number 
                      FROM {tables}
                      JOIN account_account_tag_account_move_line_rel aatamlr ON aatamlr.account_move_line_id = "account_move_line".id
                      JOIN account_account_tag tag ON aatamlr.account_account_tag_id = tag.id
                      {additional_join_for_with}
                     WHERE {where_clause}
                       AND {tag_name} SIMILAR TO '(-|\+)K_\d\d'
                       AND tag.country_id = {country_id}
                  GROUP BY tag_number, {move_to_group_by}
              )
            SELECT jsonb_object_agg(aml_aggregates.tag_number, aml_aggregates.amounts) FILTER(WHERE aml_aggregates.tag_number IS NOT NULL) AS tax_values,
                   array_agg(DISTINCT pt.l10n_pl_vat_gtu) FILTER (WHERE pt.l10n_pl_vat_gtu IS NOT NULL) AS gtus,
                   COUNT(1) FILTER (WHERE tag.id IN %s) AS oss_tag,
                   COUNT(1) FILTER (WHERE tag.id IN %s) AS l10n_pl_vat_tt_d,
                   COUNT(1) FILTER (WHERE tag.id IN %s) AS l10n_pl_vat_tt_wnt,
                   COUNT(1) FILTER (WHERE tag.id IN %s) AS l10n_pl_vat_i_42,
                   COUNT(1) FILTER (WHERE tag.id IN %s) AS l10n_pl_vat_i_63,
                   "account_move_line__move_id".l10n_pl_vat_b_spv,
                   "account_move_line__move_id".l10n_pl_vat_b_spv_dostawa,
                   "account_move_line__move_id".l10n_pl_vat_b_mpv_prowizja,
                   "account_move_line__move_id".move_type,
                   "account_move_line__move_id".date AS move_date,
                   COALESCE("account_move_line__move_id".invoice_date, "account_move_line__move_id".date) AS invoice_date,
                   DATE("account_move_line__move_id".create_date) AS create_date,
                   partn.vat AS vat,
                   partn.l10n_pl_links_with_customer AS l10n_pl_links_with_customer,
                   country.code AS country_code,
                   partn.complete_name AS partner_complete_name,
                   "account_move_line__move_id".name AS move_name,
                   "account_move_line__move_id".id AS move_id,
                   min(partial_reconcile_date.invoice_date_due) AS reversed_move_date_due,
                   -- If the first payment/delivery arrives before the invoice date else null
                   NULLIF(
                          LEAST(
                                min(partial_reconcile_date.date), 
                                "account_move_line__move_id".delivery_date, 
                                COALESCE("account_move_line__move_id".invoice_date, "account_move_line__move_id".date)
                                ), 
                          COALESCE("account_move_line__move_id".invoice_date, "account_move_line__move_id".date)
                          ) as sale_date
                """,

            'from_query_part': """
                     FROM {tables}
                LEFT JOIN product_product pp ON "account_move_line".product_id = pp.id
                LEFT JOIN product_template pt ON pp.product_tmpl_id = pt.id
                LEFT JOIN aml_aggregates ON aml_aggregates.move_id = "account_move_line__move_id".id
                LEFT JOIN res_partner partn ON "account_move_line__move_id".partner_id = partn.id
                LEFT JOIN res_country country ON partn.country_id = country.id
                LEFT JOIN account_account_tag_account_move_line_rel aa_tag_aml_rel ON aa_tag_aml_rel.account_move_line_id = "account_move_line".id
                LEFT JOIN account_account_tag tag ON aa_tag_aml_rel.account_account_tag_id = tag.id
                LEFT JOIN partial_reconcile_date ON partial_reconcile_date.id = "account_move_line__move_id".id
            """,

            'where_query_part': """
                WHERE {where_clause}
             GROUP BY "account_move_line__move_id".id, partn.id, country.code;
            """,
            'from_moves_to_aggregate': "account_move_line__move_id.id",
            'additional_joins_for_aml_aggregate': ""
        }

        return dict_query_parts

    @api.model
    def _l10n_pl_get_record_values_grouped_by_move(self, options, report):
        """ Get the result of the query to get all values for each move """
        dict_query_parts = self._l10n_pl_get_query_parts()

        # To get if the line contains a tag, we get the expression (if needed), to get the id. It is then given to the params
        list_tag_params = []
        oss_tag = self.env.ref('l10n_eu_oss.tag_oss', raise_if_not_found=False)
        list_tag_params.append(tuple(oss_tag.ids if oss_tag else [oss_tag]))

        triangular_sale_expression = self.env.ref('l10n_pl.account_tax_report_line_triangular_2nd_payer_tag', raise_if_not_found=False)
        triangular_sale_tags = triangular_sale_expression._get_matching_tags()
        list_tag_params.append(tuple(triangular_sale_tags.ids if triangular_sale_tags else []))

        triangular_purchase_expression = self.env.ref('l10n_pl.account_tax_report_line_triangular_buyer_2nd_payer_tag', raise_if_not_found=False)
        triangular_purchase_tags = triangular_purchase_expression._get_matching_tags()
        list_tag_params.append(tuple(triangular_purchase_tags.ids if triangular_purchase_tags else []))

        i_42_expression = self.env.ref('l10n_pl.account_tax_report_line_intracom_procedure_i_42_tag', raise_if_not_found=False)
        i_42_tags = i_42_expression._get_matching_tags()
        list_tag_params.append(tuple(i_42_tags.ids if i_42_tags else []))

        i_63_expression = self.env.ref('l10n_pl.account_tax_report_line_intracom_procedure_i_63_tag', raise_if_not_found=False)
        i_63_tags = i_63_expression._get_matching_tags()
        list_tag_params.append(tuple(i_63_tags.ids if i_63_tags else []))

        tables, where_clause, where_param = report._query_get(options, 'strict_range')
        select = dict_query_parts.get('select_query_part', '') + dict_query_parts.get('from_query_part', '') + dict_query_parts.get('where_query_part', '')

        where_param = where_param * (select.count('{where_clause}') - 1) + list_tag_params + where_param
        tag_name = "tag.name ->> 'en_US'" if self.pool['account.account.tag'].name.translate else "tag.name"

        self.env.cr.execute(
            select.format(
                where_clause=where_clause,
                tables=tables,
                tag_name=tag_name,
                country_id=self.env.ref('base.pl').id,
                additional_join_for_with=dict_query_parts.get('additional_joins_for_aml_aggregate', ''),
                move_to_group_by=dict_query_parts.get('from_moves_to_aggregate', ''),
            ),
            where_param,
        )
        return self.env.cr.dictfetchall()

    @api.model
    def _l10n_pl_prepare_values(self, options):
        """ Prepare miscellaneous information and function needed for the JPK template rendering """
        now = datetime.strftime(pytz.utc.localize(fields.Datetime.now()), '%Y-%m-%dT%H:%M:%SZ')
        if options.get('date').get('period_type') == 'month':
            date_to = fields.Date.from_string(options.get('date').get('date_to'))
            date_month = datetime.strftime(date_to, '%-m')
            date_year = datetime.strftime(date_to, '%Y')
        else:
            raise UserError(_('JPK export can only be done for monthly periods.'))

        return {
            'date_now': now,
            'date_year': date_year,
            'date_month': date_month,
            'company': self.env.company,
            'float_compare': float_compare,
            'float_is_zero': float_is_zero,
            'float_repr': float_repr,
            'options': options,
        }

    @api.model
    def _l10n_pl_fill_move_values(self, options, values, report):
        list_values = self._l10n_pl_get_record_values_grouped_by_move(options, report)
        # list_values contains all the moves, as it will be used to compute the tax amounts to declare

        output_tax_moves = []
        input_tax_moves = []
        for move_data in list_values:
            move_data['tax_values'] = move_data.get('tax_values') or {}
            tax_keys = move_data['tax_values'].keys()

            if any(int(key) in range(10, 37) for key in tax_keys) or move_data.get('oss_tag') or move_data.get('pos_order_id'):
                output_tax_moves.append(move_data)

            if any(int(key) in range(40, 48) for key in tax_keys):
                input_tax_moves.append(move_data)

        values.update({
            'output_tax_moves': output_tax_moves,
            'input_tax_moves': input_tax_moves,
            'list_values': list_values,
        })

    @api.model
    def _l10n_pl_fill_aggregate_values(self, options, values, report):
        """ Fill values aggregated from all moves or taken from tax report lines"""

        sum_output_tax = sum(
            sum(
                move_data.get('tax_values', {}).get(str(i), 0)
                for i in ('16', '18', '20', '24', '26', '28', '30', '32', '33', '34')
            ) - move_data.get('tax_values', {}).get('35', 0) - move_data.get('tax_values', {}).get('36', 0)
            for move_data in values['list_values']
        )

        sum_input_tax = sum(
            move_data.get('tax_values', {}).get(str(i), 0)
            for i in ('39', '41', '43', '44', '45', '46', '47')
            for move_data in values['list_values']
        )

        # Grid filled by hand on tax reported or computed from previous declarations
        expr_cash_register = self.env.ref('l10n_pl.account_tax_report_line_podatek_okresie_tag')
        expr_tax_waived = self.env.ref('l10n_pl.account_tax_report_line_zaniechaniem_poboru_tag')
        expr_prev_decla = self.env.ref('l10n_pl.account_tax_report_line_podatek_deklaracji_applied_carryover')

        if self.env.company.account_tax_periodicity == 'trimester':
            if fields.Date.to_date(options['date']['date_from']).month % 3 != 0:
                # We don't need the aggregation of all the tax grid amounts because we're not at the end of the quarter

                values.update({
                    'agg_values': {},
                    'sum_output_tax': sum_output_tax,
                    'sum_input_tax': sum_input_tax,
                })
                return

            # Need the values for the whole quarter, so we get all the values by getting the values for all the
            # expressions of the tax report, for a different date scope than the moves
            new_options_date = report._get_dates_period(*date_utils.get_quarter(fields.Date.to_date(options['date']['date_from'])), 'range', 'quarter')
            new_options = report.get_options(previous_options={
                **options,
                'date': new_options_date,
                'comparison': {}
            })

            agg_values = {}
            lines = report._compute_expression_totals_for_each_column_group(report.line_ids.expression_ids, new_options)
            line_38 = self.env.ref('l10n_pl.account_tax_report_line_podatek_razem_c')
            line_48 = self.env.ref('l10n_pl.account_tax_report_line_podatek_razem_d')

            for expression, expression_values in list(lines.values())[0].items():
                if expression.formula and expression.formula[:2] == 'K_':
                    agg_values[expression.formula[2:]] = expression_values.get('value')
                if expression == line_38.expression_ids[0]:
                    agg_values['38'] = expression_values.get('value')
                if expression == line_48.expression_ids[0]:
                    agg_values['48'] = expression_values.get('value')
                if expression == expr_cash_register:
                    cash_register_value = expression_values.get('value')
                if expression == expr_tax_waived:
                    tax_waived_value = expression_values.get('value')
                if expression == expr_prev_decla:
                    agg_values['39'] = expression_values.get('value')
        else:
            # monthly, we can just aggregate values of the moves and get values from the expressions filled by hand
            agg_values = {
                str(i): sum(
                    move_data.get('tax_values', {}).get(str(i), 0)
                    for move_data in values['list_values']
                ) for i in range(10, 48)}

            additional_expression_totals = report._compute_expression_totals_for_each_column_group(expr_cash_register + expr_tax_waived + expr_prev_decla, options)
            dict_expr = next(iter(additional_expression_totals.values()))
            cash_register_value = dict_expr.get(expr_cash_register).get('value')
            tax_waived_value = dict_expr.get(expr_tax_waived).get('value')
            agg_values['39'] = dict_expr.get(expr_prev_decla).get('value')
            agg_values['38'] = sum_output_tax
            agg_values['48'] = sum_input_tax

            new_options = options.copy()

        # We need the date scope that might be redefined in quarterly, so new_options are used
        gold_tags = self.env.ref('l10n_pl.gold_tag', raise_if_not_found=False)
        if gold_tags:
            domain = [*report._get_options_domain(new_options, 'strict_range'), ('tax_tag_ids', 'in', gold_tags.ids)]
            agg_values['65'] = self.env['account.move.line'].search_count(domain, limit=1)  # Gold has been traded

        agg_values['37'] = sum(amount for key, amount in agg_values.items() if key in ('10', '11', '13', '15', '17', '19', '21', '22', '23', '25', '27', '29', '31'))

        excess_output = agg_values.get('38', 0) - agg_values.get('48', 0)
        if float_compare(excess_output, 0, 0) > 0:
            agg_values['49'] = min(excess_output, cash_register_value)  # deducted from the purchase of cash register up to the excess
            excess_output -= agg_values['49']
            cash_register_value -= agg_values['49']
        agg_values['52'] = cash_register_value  # excess from the purchase of cash register over the excess of output taxes
        if float_compare(excess_output, 0, 0) > 0:
            agg_values['50'] = min(excess_output, tax_waived_value)  # deducted from tax waived up to the excess minus what has been deducted from the cash register purchase
            excess_output -= agg_values['50']
            tax_waived_value -= agg_values['50']
        if float_compare(excess_output, 0, 0) > 0:
            agg_values['51'] = excess_output  # excess left
        else:
            agg_values['51'] = 0
            agg_values['53'] = -excess_output + tax_waived_value + cash_register_value  # excess of input tax
            agg_values['54'] = min(agg_values['53'], options.get('l10n_pl_repayment_amount', 0))  # excess of input tax to be repaid

        values.update({
            'agg_values': agg_values,
            'sum_output_tax': sum_output_tax,
            'sum_input_tax': sum_input_tax,
        })

    def export_tax_report_to_xml(self, options):
        report = self.env['account.report'].browse(options['report_id'])

        values = self._l10n_pl_prepare_values(options)
        self._l10n_pl_fill_move_values(options, values, report)
        self._l10n_pl_fill_aggregate_values(options, values, report)

        if self.env.company.account_tax_periodicity == 'trimester':
            values.update({
                'xmlns':  "http://crd.gov.pl/wzor/2021/12/27/11149/"
            })
            audit_content = self.env['ir.qweb']._render('l10n_pl_reports.jpk_export_quarterly_template', values)
            return {
                'file_name': f'jpk_vat_k_{values["date_month"]}_{values["date_year"]}.xml',
                'file_content': audit_content,
                'file_type': 'xml',
            }
        else:
            values.update({
                'xmlns':  "http://crd.gov.pl/wzor/2021/12/27/11148/"
            })
            audit_content = self.env['ir.qweb']._render('l10n_pl_reports.jpk_export_monthly_template', values)
            return {
                'file_name': f'jpk_vat_m_{values["date_month"]}_{values["date_year"]}.xml',
                'file_content': audit_content,
                'file_type': 'xml',
            }
