# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml import etree, objectify

from odoo import _, fields, models
from odoo.exceptions import RedirectWarning, UserError

class EstonianTaxReportCustomHandler(models.AbstractModel):
    _name = 'l10n_ee.tax.report.handler'
    _inherit = 'account.tax.report.handler'
    _description = 'Estonian Tax Report Custom Handler'

    def _custom_options_initializer(self, report, options, previous_options=None):
        super()._custom_options_initializer(report, options, previous_options=previous_options)

        options.setdefault('buttons', []).append({
            'name': _('XML'),
            'sequence': 30,
            'action': 'export_file',
            'action_param': 'export_to_xml',
            'file_export_type': _('XML'),
        })

    def export_to_xml(self, options):
        report = self.env['account.report'].browse(options['report_id'])
        date_to = fields.Date.from_string(options['date'].get('date_to'))

        if options['date']['period_type'] != 'month':
            raise UserError(_('Choose a month to export the VAT Report'))

        company = self.env.company
        if not company.company_registry:
            action = self.env.ref('base.action_res_company_form')
            raise RedirectWarning(
                _('No company registry number associated with your company. Please define one.'),
                action.id,
                _('Company Settings')
            )

        xml_data = {
            'tax_payer_reg_code': company.company_registry,
            # Not needed when uploaded personally, since you logged in at the Estonian government platform with your ID
            'submitter_person_code': '',
            'year': date_to.year,
            'month': date_to.month,
            'declaration_type': 1,  # Normal period
            'sale_lines': [],
            'purchase_lines': [],
        }

        lines = report._get_lines(options)
        tax_line_prefix = 'l10n_ee.tax_report_line_'
        tax_line_numbers = ('1', '1_1', '2', '2_1', '3', '3_1', '3_1_1', '3_2', '3_2_1',
                            '5', '5_1', '5_2', '5_3', '5_3_cars', '5_4', '5_4_cars',
                            '6', '6_1', '7', '7_1', '8', '9', '10', '11',)
        tax_line_mapping = {
            self.env.ref(tax_line_prefix + line_number).id: f'line_{line_number}' for line_number in tax_line_numbers
            }
        colexpr_to_idx = {col['expression_label']: idx for idx, col in enumerate(options.get('columns', []))}

        for line in lines:
            if 'report_line_id' not in line['columns'][0]:
                continue
            line_id = line['columns'][0]['report_line_id']
            if (line_id not in tax_line_mapping):
                continue
            xml_variable = tax_line_mapping[line_id]
            balance = line['columns'][colexpr_to_idx['balance']]['no_format']
            if balance and xml_variable.endswith('_cars'):
                xml_data[xml_variable] = '{:.0f}'.format(balance)
            elif balance:
                xml_data[xml_variable] = '{:.2f}'.format(balance)

        kmd_inf_report = self.env.ref('l10n_ee_reports.kmd_inf_report')
        kmd_inf_report_options = kmd_inf_report.get_options(options)
        kmd_inf_report_options['unfold_all'] = True

        kmd_inf_lines = kmd_inf_report._get_lines(kmd_inf_report_options)
        current_kmd_part = 0
        monetary_lines = ('invoice_total', 'sum_for_rate_in_period', 'vat_in_period')

        for line in kmd_inf_lines:
            # The level 1 lines indicate the section where the next lines should go.
            # The first one is the KMD INF Part A (Invoices Issued).
            # The second one is the KMD INF Part B (Invoices Received).
            if line.get('level') == 1:
                current_kmd_part += 1

            # The grouping lines do not need to be included in the KMD INF, since they do not represent invoice values.
            if not line.get('groupby'):
                annex_line = {}
                for column in line.get('columns'):
                    label = column.get('expression_label')
                    value = column.get('no_format')
                    if value and label in monetary_lines:
                        value = '{:.2f}'.format(value)
                    annex_line[label] = value

                if current_kmd_part == 1:
                    xml_data['sale_lines'].append(annex_line)
                elif current_kmd_part == 2:
                    xml_data['purchase_lines'].append(annex_line)

        rendered_content = self.env['ir.qweb']._render('l10n_ee_reports.vat_report_xml', xml_data)
        tree = objectify.fromstring(rendered_content)

        return {
            'file_name': report.get_default_report_filename(options, 'xml'),
            'file_content': etree.tostring(tree, pretty_print=True, xml_declaration=True, encoding='utf-8'),
            'file_type': 'xml',
        }


class EstonianKmdInfReportCustomHandler(models.AbstractModel):
    _name = 'l10n_ee.kmd.inf.report.handler'
    _inherit = 'account.tax.report.handler'
    _description = 'Estonian KMD INF Report Custom Handler'

    def _report_custom_engine_kmd_inf_common(self, options, current_groupby, next_groupby, kmd_inf_part):
        def build_result(query_res_lines):
            def build_result_dict(query_res_lines):
                result = {
                    'partner_reg_code': None,
                    'partner_name': None,
                    'invoice_number': None,
                    'invoice_date': None,
                    'invoice_total': None,
                    'tax_rate': None,
                    'sum_for_rate_in_period': None,
                    'vat_in_period': None,
                    'comments': None,
                }
                if current_groupby and query_res_lines:
                    result['partner_reg_code'] = query_res_lines[0]['partner_reg_code']
                    result['partner_name'] = query_res_lines[0]['partner_name']
                    result['invoice_number'] = query_res_lines[0]['invoice_number']
                    result['invoice_date'] = query_res_lines[0]['invoice_date']
                    result['invoice_total'] = query_res_lines[0]['invoice_total']

                    if kmd_inf_part == 'a':
                        result['tax_rate'] = query_res_lines[0]['tax_rate'] if current_groupby == 'tax_group_id' else None
                        result['sum_for_rate_in_period'] = query_res_lines[0]['sum_for_rate_in_period']
                        result['comments'] = query_res_lines[0]['comments'] if current_groupby == 'tax_group_id' else None

                    elif kmd_inf_part == 'b':
                        result['vat_in_period'] = query_res_lines[0]['vat_in_period']
                        result['comments'] = query_res_lines[0]['comments']

                return result

            if not current_groupby:
                return build_result_dict(query_res_lines)
            else:
                result = []
                all_res_per_grouping_key = {}

                for query_res in query_res_lines:
                    grouping_key = query_res['grouping_key']
                    all_res_per_grouping_key.setdefault(grouping_key, []).append(query_res)

                for grouping_key, query_res_lines in all_res_per_grouping_key.items():
                    result.append((grouping_key, build_result_dict(query_res_lines)))

                return result

        report = self.env['account.report'].browse(options['report_id'])
        report._check_groupby_fields(
            (next_groupby.split(',') if next_groupby else []) +
            ([current_groupby] if current_groupby else []))

        tables, where_clause, where_params = report._query_get(options, 'strict_range')

        if current_groupby:
            select_from_groupby = f'account_move_line.{current_groupby} AS grouping_key,'
            groupby_clause = f', account_move_line.{current_groupby}'
        else:
            select_from_groupby = ''
            groupby_clause = ''

        with_clause = ''
        select_part_specific = ''
        select_comments = ''
        where_part_specific = ''

        if kmd_inf_part == 'a':
            if current_groupby == 'tax_group_id':
                # Select one or more of the codes 1, 2 or 3.
                #
                # Codes 1 and 2 are saved on the taxes and only need to be set on the line of the tax
                # Code 3 is used on every line of an invoice if:
                # -> There are 2 or more standard taxes of 20, 9 or 5 percent
                # -> There is a 0 percent or exempt tax on the invoice, amongst others
                select_comments = """,
                    CONCAT_WS(
                      ',',
                      STRING_AGG(DISTINCT account_tax.l10n_ee_kmd_inf_code, ','),
                      (
                        CASE
                          WHEN MAX(move_taxes.tax_rates_count) > 1
                          THEN '3'
                          ELSE NULL
                        END
                      )
                    ) AS comments
                """
                # Temporary table to list per invoice:
                # * how many of the 20, 9 and 5 percent taxes we have
                # * whether we have 0 percent taxes
                with_clause = """
                    WITH move_taxes AS (
                          SELECT aml.move_id AS move_id,
                                 COUNT(DISTINCT account_tax.amount) AS tax_rates_count
                            FROM account_move_line AS aml
                      INNER JOIN account_move_line_account_tax_rel AS aml_tax_rel
                              ON aml_tax_rel.account_move_line_id = aml.id
                      INNER JOIN account_tax
                              ON account_tax.id = aml_tax_rel.account_tax_id
                             AND (account_tax.l10n_ee_kmd_inf_code IS NULL
                              OR account_tax.l10n_ee_kmd_inf_code != '2')
                        GROUP BY aml.move_id
                    )
                """
                tables += """
                    LEFT JOIN move_taxes
                           ON move_taxes.move_id = account_move_line__move_id.id
                """

            select_part_specific = """
                account_move_line__move_id.amount_untaxed_signed AS invoice_total,
                (
                  CASE
                    WHEN '1' = ANY (ARRAY_AGG(account_tax.l10n_ee_kmd_inf_code))
                    THEN CONCAT(CAST(MAX(account_tax.amount) AS INTEGER), 'erikord')
                    ELSE CAST(CAST(MAX(account_tax.amount) AS INTEGER) AS VARCHAR)
                  END
                ) AS tax_rate,
                SUM(
                  CASE
                    -- Only base amounts reported on lines 1, 1_1, 2 or 2_1 of the tax report are reported here
                    WHEN account_account_tag.name->>'en_US' IN ('+1', '-1', '+1_1', '-1_1', '+2', '-2', '+2_1', '-2_1')
                    THEN -aml_base.balance
                    ELSE 0
                  END
                ) AS sum_for_rate_in_period
            """

            # When we are in part A, we only want the invoices that have one or more lines reported on lines 1, 1¹, 2 or 2¹
            # of the tax report
            groupby_clause += """
                HAVING SUM(
                         CASE
                           WHEN account_account_tag.name->>'en_US' IN ('+1', '-1', '+1_1', '-1_1', '+2', '-2', '+2_1', '-2_1')
                           THEN -aml_base.balance
                           ELSE 0
                         END
                       ) != 0
            """

        elif kmd_inf_part == 'b':
            if current_groupby == 'move_id':
                select_comments = """,
                    STRING_AGG(DISTINCT account_tax.l10n_ee_kmd_inf_code, ',') AS comments
                """

            select_part_specific = """
                -account_move_line__move_id.amount_total_signed AS invoice_total,
                SUM(account_move_line.balance) AS vat_in_period
            """
            where_part_specific = "AND account_account_tag.name->>'en_US' IN ('+5', '-5', '+5_1', '-5_1', '+5_2', '-5_2', '+5_3', '-5_3', '+5_4', '-5_4')"

        # Depending on the KMD INF Part, we need to find:
        #
        # Part A
        # ======
        # All invoices and credit notes issued to Estonian companies for the current period
        # grouped by:
        #   * invoice number, then
        #   * tax rate class (20, 9, 5, 20erikord, 9erikord, 5erikord)
        # where we have at least one line reported on lines 1, 2 or 2¹ of the VAT report.
        #
        # Part B
        # ======
        # All invoices and credit notes received from Estonian companies for the current period
        # grouped by:
        #   * invoice number
        # where we have at least one line reported on line 5 of the VAT report.
        #
        query = f"""
                {with_clause}
                SELECT {select_from_groupby}
                       res_partner.company_registry AS partner_reg_code,
                       res_partner.name AS partner_name,
                       account_move_line__move_id.{'name' if kmd_inf_part == 'a' else 'ref'} AS invoice_number,
                       account_move_line__move_id.invoice_date AS invoice_date,
                       {select_part_specific}
                       {select_comments}
                       -- The `account_move_line` table are the tax lines
                  FROM {tables}
            INNER JOIN account_move_line_account_tax_rel AS aml_tax_rel
                    ON aml_tax_rel.account_tax_id = account_move_line.tax_line_id
                       -- These are the base amounts linked to the tax line
             LEFT JOIN account_move_line AS aml_base
                    ON aml_base.id = aml_tax_rel.account_move_line_id
             LEFT JOIN account_tax
                    ON account_tax.id = aml_tax_rel.account_tax_id
            INNER JOIN res_partner
                    ON res_partner.id = account_move_line__move_id.partner_id
            INNER JOIN res_country
                    ON res_country.id = res_partner.country_id
            INNER JOIN account_account_tag_account_move_line_rel
                    ON account_account_tag_account_move_line_rel.account_move_line_id = {'aml_base' if kmd_inf_part == 'a' else 'account_move_line'}.id
            INNER JOIN account_account_tag
                    ON account_account_tag.id = account_account_tag_account_move_line_rel.account_account_tag_id
                 WHERE {where_clause}
                   AND res_country.code = 'EE'
                   AND res_partner.is_company IS TRUE
                   AND account_move_line__move_id.move_type IN %s
                       -- Only link tax and base lines from the same invoice
                   AND account_move_line.move_id = aml_base.move_id
                   {where_part_specific}
              GROUP BY res_partner.id,
                       account_move_line__move_id.id
                       {groupby_clause}
              ORDER BY invoice_date,
                       invoice_number
        """
        where_params.extend([
            ('out_invoice', 'out_refund') if kmd_inf_part == 'a' else ('in_invoice', 'in_refund')
        ])

        self.env.cr.execute(query, where_params)
        query_res_lines = self.env.cr.dictfetchall()

        return build_result(query_res_lines)


    def _report_custom_engine_kmd_inf_a(self, expressions, options, date_scope, current_groupby, next_groupby, offset=0, limit=None, warnings=None):
        return self._report_custom_engine_kmd_inf_common(options, current_groupby, next_groupby, 'a')


    def _report_custom_engine_kmd_inf_b(self, expressions, options, date_scope, current_groupby, next_groupby, offset=0, limit=None, warnings=None):
        return self._report_custom_engine_kmd_inf_common(options, current_groupby, next_groupby, 'b')
