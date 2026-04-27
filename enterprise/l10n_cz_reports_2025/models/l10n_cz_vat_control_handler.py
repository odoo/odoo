from lxml import etree

from odoo import models, release, _
from odoo.tools import SQL
from odoo.tools.float_utils import float_repr
from odoo.addons.l10n_cz_reports_2025.models import l10n_cz_reports_utils as cz_utils


class CzechVATControlReportCustomHandler(models.AbstractModel):
    """
        Generate the VAT Control Statement for the Czech Republic.
        Generated using as a reference the documentation at
        https://adisspr.mfcr.cz/dpr/adis/idpr_pub/epo2_info/popis_struktury_detail.faces?zkratka=DPHKH1
    """
    _name = 'l10n_cz.vat.control.report.handler'
    _inherit = 'account.tax.report.handler'
    _description = 'Czech Report Custom Handler (Control Statement)'

    def _custom_options_initializer(self, report, options, previous_options=None):
        super()._custom_options_initializer(report, options, previous_options=previous_options)
        options['ignore_totals_below_sections'] = True

        # Add XML export button
        options.setdefault('buttons', []).append({
            'name': _('XML'),
            'sequence': 30,
            'action': 'export_file',
            'action_param': 'l10n_cz_export_vat_control_report_to_xml',
            'file_export_type': _('XML'),
        })

    ####################################################
    # CUSTOM ENGINES
    ####################################################

    def _report_custom_engine_control_statement_A1(self, expressions, options, date_scope, current_groupby, next_groupby, offset=0, limit=None, warnings=None):
        """ Part A1 consists of reverse charge transactions, which fall under the tax with tag VAT 25 """
        domain = [('tax_tag_ids', 'in', self._get_tag_ids_from_report_lines(['l10n_cz_vat_declaration_line_27']))]
        return self._report_custom_engine_control_statement(options, current_groupby, next_groupby, offset, limit, domain, 'a1')

    def _report_custom_engine_control_statement_A2(self, expressions, options, date_scope, current_groupby, next_groupby, offset=0, limit=None, warnings=None):
        """ Part A2 consists of received taxable supplies, including transactions with taxes with tag VAT 3, 4, 5, 6, 9, 12 and 13 """
        xmlids = [
            'l10n_cz_vat_declaration_line_6',
            'l10n_cz_vat_declaration_line_7',
            'l10n_cz_vat_declaration_line_9',
            'l10n_cz_vat_declaration_line_10',
            'l10n_cz_vat_declaration_line_14',
            'l10n_cz_vat_declaration_line_19',
            'l10n_cz_vat_declaration_line_20',
        ]
        domain = [('tax_tag_ids', 'in', self._get_tag_ids_from_report_lines(xmlids))]
        return self._report_custom_engine_control_statement(options, current_groupby, next_groupby, offset, limit, domain, 'a2')

    def _report_custom_engine_control_statement_A3(self, expressions, options, date_scope, current_groupby, next_groupby, offset=0, limit=None, warnings=None):
        """ Part A3 covers transactions under the special regime of investment gold """
        gold_tax = self.env.ref(f'account.{self.env.company.root_id.id}_l10n_cz_investment_gold', raise_if_not_found=False)
        domain = [('tax_ids', 'in', gold_tax.ids if gold_tax else [0])]
        return self._report_custom_engine_control_statement(options, current_groupby, next_groupby, offset, limit, domain, 'a3')

    def _report_custom_engine_control_statement_A4(self, expressions, options, date_scope, current_groupby, next_groupby, offset=0, limit=None, warnings=None):
        """
            Part A4 consists of realized taxable supplies in the amount above CZK 10,000, including transactions with
            taxes with tag VAT 1 (basic tax rate) and VAT 2 (reduced tax rate).
        """
        domain = [('tax_tag_ids', 'in', self._get_tag_ids_from_report_lines(['l10n_cz_vat_declaration_line_3', 'l10n_cz_vat_declaration_line_4']))]
        return self._report_custom_engine_control_statement(options, current_groupby, next_groupby, offset, limit, domain, 'a4')

    def _report_custom_engine_control_statement_A5(self, expressions, options, date_scope, current_groupby, next_groupby, offset=0, limit=None, warnings=None):
        """
            Part A5 consists of a single line with summary information about realized taxable supplies in the amount
            below CZK 10,000. Includes transactions with taxes with tag VAT 1 (basic tax rate) and VAT 2 (reduced tax)
        """
        domain = [('tax_tag_ids', 'in', self._get_tag_ids_from_report_lines(['l10n_cz_vat_declaration_line_3', 'l10n_cz_vat_declaration_line_4']))]
        return self._report_custom_engine_control_statement(options, current_groupby, next_groupby, offset, limit, domain, 'a5')

    def _report_custom_engine_control_statement_B1(self, expressions, options, date_scope, current_groupby, next_groupby, offset=0, limit=None, warnings=None):
        """ Part B1 refers to reverse tax charges, the transactions with tax tag VAT 10 (basic tax) and VAT 11 (reduced tax) """
        domain = [('tax_tag_ids', 'in', self._get_tag_ids_from_report_lines(['l10n_cz_vat_declaration_line_16', 'l10n_cz_vat_declaration_line_17']))]
        return self._report_custom_engine_control_statement(options, current_groupby, next_groupby, offset, limit, domain, 'b1')

    def _report_custom_engine_control_statement_B2(self, expressions, options, date_scope, current_groupby, next_groupby, offset=0, limit=None, warnings=None):
        """
            Part B2 consists of received taxable supplies in the amount above CZK 10,000 and for which the recipient
            claims VAT deduction (tax tags VAT 40 and VAT 41).
        """
        domain = [('tax_tag_ids', 'in', self._get_tag_ids_from_report_lines(['l10n_cz_vat_declaration_line_39', 'l10n_cz_vat_declaration_line_40']))]
        return self._report_custom_engine_control_statement(options, current_groupby, next_groupby, offset, limit, domain, 'b2')

    def _report_custom_engine_control_statement_B3(self, expressions, options, date_scope, current_groupby, next_groupby, offset=0, limit=None, warnings=None):
        """
            Part B3 is a single line with summary information about received taxable supplies in the amount
            above CZK 10,000 and for which the recipient claims VAT deduction (tax tags VAT 40 and VAT 41).
        """
        domain = [('tax_tag_ids', 'in', self._get_tag_ids_from_report_lines(['l10n_cz_vat_declaration_line_39', 'l10n_cz_vat_declaration_line_40']))]
        return self._report_custom_engine_control_statement(options, current_groupby, next_groupby, offset, limit, domain, 'b3')

    def _result_dict_control_statement(self, country_code=None, vat_number=None, journal_entry=None, taxable_supply_date=None, tax_base_1=0, tax_1=0, tax_base_2=0, tax_2=0, supplies_code=None):
        return {
            'country_code': country_code,
            'vat_number': vat_number,
            'journal_entry': journal_entry,
            'taxable_supply_date': taxable_supply_date,
            'tax_base_1': tax_base_1,
            'tax_1': tax_1,
            'tax_base_2': tax_base_2,
            'tax_2': tax_2,
            'supplies_code': supplies_code,
        }

    def _report_custom_engine_control_statement(self, options, current_groupby, next_groupby, offset=0, limit=None, domain=None, code=None):
        """
            Builds the result list containing lines of the report in the form of tuples of grouping keys (move id or
            code of supply) and dictionaries.
            The query used is built according to the part of the control statement, given by the code. For each code
            the query calculates the sum of tax bases and taxes (for basic tax and reduced tax) per move, and if needed,
            also per supply code within moves. It uses the tax tags to identify the relevant move lines for a
            particular part, including when multiple taxes are used in one move line.

            :param options:             The report options.
            :param current_groupby:     The groupby to evaluate.
            :param next_groupby:        Full groupby string that will have to be evaluated next for these expressions.
            :param where:               Where clause for a particular part of the report.
            :param code:                Code of the subsection, one of 'a1', 'a2', 'a3', 'a4', 'a5', 'b1', 'b2' or 'b3'.
            :return:                    A list of tuples containing the report lines.
        """
        def build_result_dict(query_res_lines):
            if not query_res_lines:
                return self._result_dict_control_statement()
            if current_groupby:
                if current_groupby == 'move_id' and code in {'a1', 'b1'}:
                    # A single move can display several lines (one for each code of supplies) in parts A1 and B1. The
                    # line grouped by move_id should show the sum of tax and tax base amounts and no code of supply
                    res = query_res_lines[0].copy()
                    res['supplies_code'] = ''
                    for line in query_res_lines[1:]:
                        for key in ['tax_base_2', 'tax_base_1', 'tax_2', 'tax_1']:
                            res[key] += line[key]
                else:
                    res = query_res_lines[0]

                vat_number, country_code = self._extract_vat_country_code(res.get('partner_vat'), res.get('country_code'), options)
                purchase_types = self.env['account.move'].get_purchase_types(include_receipts=True)
                # For vendor bills, we should use the original reference provided by the seller
                reference = res.get('ref') if res.get('move_type') in purchase_types else res.get('move_name')
                # For Code B2, "Tax document registration number" is mandatory.
                # As "ref" can be empty, fall back on move name
                if not reference and code == 'b2':
                    reference = res.get('move_name')

                return self._result_dict_control_statement(
                    # Code A1 and B1 are for reverse charges. A4 might include special regime transactions
                    supplies_code=res['supplies_code'] if code in {'a1', 'b1', 'a4'} else None,
                    # A2 and A3 may require information on international partners, requiring the country code separately
                    country_code=country_code if code in {'a2', 'a3'} else None,
                    vat_number=vat_number,
                    journal_entry=reference,
                    taxable_supply_date=res['taxable_supply_date'].strftime("%d.%m.%Y"),
                    tax_base_1=res['tax_base_1'],
                    tax_1=res['tax_1'],
                    tax_base_2=res['tax_base_2'],
                    tax_2=res['tax_2'],
                )
            tax_base_1 = tax_1 = tax_base_2 = tax_2 = 0
            for res in query_res_lines:
                tax_base_1 += res.get('tax_base_1') or 0
                tax_1 += res.get('tax_1') or 0
                tax_base_2 += res.get('tax_base_2') or 0
                tax_2 += res.get('tax_2') or 0
            return self._result_dict_control_statement(
                tax_base_1=tax_base_1,
                tax_1=tax_1,
                tax_base_2=tax_base_2,
                tax_2=tax_2,
            )

        report = self.env['account.report'].browse(options['report_id'])
        report._check_groupby_fields((next_groupby.split(',') if next_groupby else []) + ([current_groupby] if current_groupby else []))
        query = report._get_report_query(options, 'strict_range', domain=domain)
        tax_group_12 = self.env.ref(f'account.{self.env.company.root_id.id}_tax_group_vat_12', raise_if_not_found=False)

        select_clauses = []
        search_condition_remaining = ''
        # According to the report part, additional select, where and groupby clauses are set.
        groupby_clauses = []
        if code not in {'a5', 'b3'}:  # All codes except aggregated ones require information on individual moves.
            select_clauses.append(SQL("""
                partner.vat AS partner_vat,
                country.code AS country_code,
                account_move_line__move_id.taxable_supply_date AS taxable_supply_date,
                account_move_line__move_id.name AS move_name,
                account_move_line__move_id.move_type AS move_type,
                account_move_line__move_id.ref AS ref
            """))
            groupby_clauses.append(SQL('partner.vat, account_move_line__move_id.name, account_move_line__move_id.taxable_supply_date, country.code, account_move_line__move_id.move_type, account_move_line__move_id.ref'))
        else:
            search_condition_remaining += " AND (ABS(account_move_line__move_id.amount_total_signed) <= 10000 OR partner.vat IS NULL OR partner.vat = '/' OR account_move_line__move_id.l10n_cz_scheme_code IN ('1', '2'))"

        if code in {'a1', 'b1'}:  # A1 and B1 have reverse charges codes.
            select_clauses.append(SQL('account_move_line.l10n_cz_supplies_code AS supplies_code'))
            groupby_clauses.append(SQL('account_move_line.l10n_cz_supplies_code'))

        if code in {'a4', 'b2'}:
            search_condition_remaining += " AND ABS(account_move_line__move_id.amount_total_signed) > 10000 AND partner.vat IS NOT NULL AND partner.vat != '/' AND account_move_line__move_id.l10n_cz_scheme_code NOT IN ('1', '2')"
            if code == 'a4':  # A4 might include special regime transactions.
                select_clauses.append(SQL('account_move_line__move_id.l10n_cz_scheme_code AS supplies_code'))
                groupby_clauses.append(SQL('account_move_line__move_id.l10n_cz_scheme_code'))

        groupby_field_sql = self.env['account.move.line']._field_to_sql('account_move_line', current_groupby, query) if current_groupby else SQL()
        if groupby_field_sql:
            groupby_clauses.append(groupby_field_sql)

        tail_query = report._get_engine_query_tail(offset, limit)
        query = SQL(
            """
                SELECT
                    %(select_from_groupby)s
                    %(select_clause)s
                    SUM(CASE WHEN base_tax.id IS NOT NULL AND base_tax_group.id = %(tax_group_12)s THEN account_move_line.balance ELSE 0 END
                        * CASE WHEN tag.tax_negate THEN -1 ELSE 1 END
                        * CASE WHEN account_move_line.tax_tag_invert THEN -1 ELSE 1 END
                    ) AS tax_base_2,
                    SUM(CASE WHEN base_tax.id IS NOT NULL AND base_tax_group.id != %(tax_group_12)s THEN account_move_line.balance ELSE 0 END
                        * CASE WHEN tag.tax_negate THEN -1 ELSE 1 END
                        * CASE WHEN account_move_line.tax_tag_invert THEN -1 ELSE 1 END
                    ) AS tax_base_1,
                    SUM(CASE WHEN base_tax.id IS NULL AND net_tax_group.id = %(tax_group_12)s THEN account_move_line.balance ELSE 0 END
                        * CASE WHEN tag.tax_negate THEN -1 ELSE 1 END
                        * CASE WHEN account_move_line.tax_tag_invert THEN -1 ELSE 1 END
                    ) AS tax_2,
                    SUM(CASE WHEN base_tax.id IS NULL AND net_tax_group.id != %(tax_group_12)s THEN account_move_line.balance ELSE 0 END
                        * CASE WHEN tag.tax_negate THEN -1 ELSE 1 END
                        * CASE WHEN account_move_line.tax_tag_invert THEN -1 ELSE 1 END
                    ) AS tax_1

                FROM %(table_references)s

                LEFT JOIN res_partner partner ON partner.id = account_move_line__move_id.commercial_partner_id
                LEFT JOIN res_country country ON country.id = partner.country_id
                LEFT JOIN account_account_tag_account_move_line_rel tag_aml_rel ON tag_aml_rel.account_move_line_id = account_move_line.id
                LEFT JOIN account_account_tag tag ON tag.id = tag_aml_rel.account_account_tag_id
                LEFT JOIN account_tax net_tax ON account_move_line.tax_line_id = net_tax.id
                LEFT JOIN account_move_line_account_tax_rel aml_tax_rel ON account_move_line.id = aml_tax_rel.account_move_line_id
                LEFT JOIN account_tax base_tax ON aml_tax_rel.account_tax_id = base_tax.id
                LEFT JOIN account_tax_group base_tax_group ON base_tax_group.id = base_tax.tax_group_id
                LEFT JOIN account_tax_group net_tax_group ON net_tax_group.id = net_tax.tax_group_id

                WHERE %(search_condition)s %(search_condition_remaining)s

                %(groupby_clause)s
                %(orderby_clause)s
                %(tail_query)s
            """,
            select_from_groupby=SQL('%s AS grouping_key,', groupby_field_sql) if groupby_field_sql else SQL(''),
            select_clause=SQL("%s,", SQL(", ").join(select_clauses)) if select_clauses else SQL(),
            tax_group_12=tax_group_12.id if tax_group_12 else 0,
            table_references=query.from_clause,
            search_condition=query.where_clause,
            search_condition_remaining=SQL(search_condition_remaining),
            groupby_clause=SQL("GROUP BY %s", SQL(", ").join(groupby_clauses)) if groupby_clauses else SQL(),
            orderby_clause=SQL("ORDER BY %s", SQL(", ").join(groupby_clauses)) if groupby_clauses else SQL(),
            tail_query=SQL(tail_query),
        )
        self._cr.execute(query)
        query_res_lines = self._cr.dictfetchall()

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

    ####################################################
    # EXPORT
    ####################################################

    def l10n_cz_export_vat_control_report_to_xml(self, options):
        """
            Create export of the Regular filling of the Control Statement (with no bad debt correction, so
            khdph_forma="B" and zdph_44="N"). Requires the company's tax id and tax office to be set.
        """
        def get_column_values_from_line(report_line):
            line_values = {}
            for col in report_line['columns']:
                if col['figure_type'] == 'monetary' and col['no_format']:
                    value = float_repr(currency.round(col['no_format']), currency.decimal_places)
                else:
                    value = col['no_format']
                line_values[col['expression_label']] = value
            return line_values

        report = self.env['account.report'].browse(options['report_id'])
        sender_company = report._get_sender_company_for_export(options)
        cz_utils.validate_czech_company_fields(sender_company)

        currency = self.env.company.currency_id
        report_line_to_code_dict = {}
        # Dictionary of the key in the export template and a list containing its lines (dictionaries with column name and its value)
        values = {}
        for line in report._get_lines({**options, 'unfold_all': True, 'export_mode': 'file'}):
            # Loop through all report lines, getting the highest level sublines of parts A1-A4, B1 and B2,
            # or the summary lines of part A5, B3 and C-lines.
            models = report._get_res_ids_from_line_id(line['id'], ['account.move', 'account.report.line'])
            if code := line.get('code'):
                line_name = f'line_{code}'
                values[line_name] = []
                report_line_to_code_dict[models['account.report.line']] = line_name
                if not line['groupby']:  # include lines which sum totals, (A5, B3, C-lines) and skip headings
                    line_values = get_column_values_from_line(line)
                    values[line_name].append(line_values)
            # skip intermediary groupings in A1 and B1 (move level information is not needed, only at the supplies code level)
            elif 'account.move' in models and not line['groupby']:
                line_name = report_line_to_code_dict[models['account.report.line']]
                line_values = get_column_values_from_line(line)
                values[line_name].append(line_values)

        # Aggregate lines A5 and B3 can be empty, in which case they can be removed
        for line in ['line_A5', 'line_B3']:
            if all(value in (0, None) for value in values[line][0].values()):
                del values[line]

        data = {
            'odoo_version': release.version,
            'veta_d': cz_utils.get_veta_d_vals(report, options),
            'veta_p': cz_utils.get_veta_p_vals(sender_company),
            **values,
        }
        xml_content = self.env['ir.qweb']._render('l10n_cz_reports_2025.control_statement_export_template', values=data)
        tree = etree.fromstring(xml_content)
        formatted_xml = etree.tostring(tree, pretty_print=True, xml_declaration=True, encoding='UTF-8')

        return {
            'file_name': report.get_default_report_filename(options, 'xml'),
            'file_content': formatted_xml,
            'file_type': 'xml',
        }

    ####################################################
    # HELPER FUNCTIONS
    ####################################################

    def _get_tag_ids_from_report_lines(self, report_lines_xmlids):
        tag_ids = set()
        for xmlid in report_lines_xmlids:
            tag_ids.update(set(self.env.ref(f'l10n_cz.{xmlid}').expression_ids._get_matching_tags().ids))
        return tag_ids

    def _extract_vat_country_code(self, vat_number, country_code, options):
        """
            Returns the relevant part of the VAT according to CZ specifications.
            VAT number should not include the country code, which is reported separately in part A2
            and A3. For countries outside the EU, vat number and country code should be blank.
        """
        if not vat_number:
            return '', ''
        eu_country_codes = cz_utils.get_eu_country_codes(self.env, options)
        if vat_number[0].isalpha():  # else, use passed country_code and vat_number
            country_code, vat_number = self.env['res.partner']._split_vat(vat_number)
            country_code = country_code.upper()
        if country_code in eu_country_codes:
            return vat_number, country_code
        return '', ''
