from lxml import etree, objectify

from odoo import _, models, release
from odoo.tools import SQL
from odoo.addons.l10n_cz_reports_2025.models import l10n_cz_reports_utils as cz_utils


class CzechVIESSummaryReportCustomHandler(models.AbstractModel):
    """
        Generate Souhrnné hlášení VIES Report for the Czech Republic.
        Generated using as a reference the documentation at
        https://adisspr.mfcr.cz/dpr/adis/idpr_pub/epo2_info/popis_struktury_detail.faces?zkratka=DPHSHV
    """
    _name = 'l10n_cz.vies.summary.report.handler'
    _inherit = 'account.report.custom.handler'
    _description = 'Czech Report Custom Handler (VIES Summary)'

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
        sender_company = report._get_sender_company_for_export(options)
        cz_utils.validate_czech_company_fields(sender_company)

        report_options = {**options, 'export_mode': 'file'}
        report_lines = report._get_lines({**report_options, 'unfold_all': True})

        lines = []
        for report_line in report_lines:
            markup = report._get_markup(report_line['id'])
            if not isinstance(markup, dict) or markup.get('groupby') != 'l10n_cz_transaction_code':
                continue

            line = {}
            for col in report_line['columns']:
                line[col['expression_label']] = col['no_format']
            lines.append(line)

        data = {
            'odoo_version': release.version,
            'veta_d': cz_utils.get_veta_d_vals(report, options),
            'veta_p': cz_utils.get_veta_p_vals(sender_company),
            'lines': lines,
        }
        xml_content = self.env['ir.qweb']._render('l10n_cz_reports_2025.cz_vies_summary_template', values=data)
        tree = objectify.fromstring(xml_content)
        formatted_xml = etree.tostring(tree, pretty_print=True, xml_declaration=True, encoding='UTF-8')

        return {
            'file_name': report.get_default_report_filename(options, 'xml'),
            'file_content': formatted_xml,
            'file_type': 'xml',
        }

    def _report_custom_engine_vies_summary(self, expressions, options, date_scope, current_groupby, next_groupby, offset=0, limit=None, warnings=None):
        def build_result_dict(query_res_lines):
            result = {
                'country_code': None,
                'vat_number': None,
                'supplies_code': None,
                'transaction_code': None,
                'supplies_number': None,
                'total_value': sum(query_res_line['total_value'] for query_res_line in query_res_lines),
            }
            if current_groupby:
                result['country_code'] = query_res_lines[0]['country_code']
                result['vat_number'] = query_res_lines[0]['vat_number']
                if current_groupby != 'partner_id':
                    result['transaction_code'] = query_res_lines[0]['transaction_code']
            if current_groupby != 'move_id':
                result['supplies_number'] = int(sum(query_res_line['supplies_number'] for query_res_line in query_res_lines))
            return result

        def build_result(query_res_lines):
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
            ([current_groupby] if current_groupby else [])
        )

        query = report._get_report_query(options, 'strict_range')

        groupby_field_sql = self.env['account.move.line']._field_to_sql('account_move_line', current_groupby, query) if current_groupby else SQL()
        groupby_clause = SQL('country.code, partner.vat, l10n_cz_transaction_code')
        if groupby_field_sql:
            groupby_clause = SQL("%s, %s", groupby_clause, groupby_field_sql)

        tail_query = report._get_engine_query_tail(offset, limit)
        query = SQL(
            """
                SELECT %(select_from_groupby)s
                    country.code                                                                                                            AS country_code,
                    partner.vat                                                                                                             AS vat_number,
                    l10n_cz_transaction_code                                                                                                AS transaction_code,
                    l10n_cz_transaction_code                                                                                                AS supplies_code,
                    COUNT(DISTINCT account_move_line.move_id * (CASE WHEN am.move_type IN ('out_refund', 'in_refund') THEN -1 ELSE 1 END))  AS supplies_number,
                    CEIL(SUM(ABS(account_move_line.balance) * (CASE WHEN am.move_type IN ('out_refund', 'in_refund') THEN -1 ELSE 1 END)))  AS total_value
                FROM %(table_references)s
                JOIN account_move am ON am.id = account_move_line.move_id
                JOIN res_partner                partner         ON account_move_line.partner_id                 = partner.id
                JOIN res_country                country         ON partner.country_id                           = country.id
                LEFT JOIN account_move          move            ON account_move_line.move_id                    = move.id
                WHERE
                    %(search_condition)s
                    AND l10n_cz_transaction_code IS NOT NULL
                    AND country.code IN %(eu_countries)s
                    AND move.move_type IN %(move_types)s
                %(groupby_clause)s
                %(orderby_clause)s
                %(tail_query)s
            """,
            select_from_groupby=SQL('%s AS grouping_key,', groupby_field_sql) if groupby_field_sql else SQL(''),
            table_references=query.from_clause,
            search_condition=query.where_clause,
            eu_countries=tuple(cz_utils.get_eu_country_codes(self.env, options)),
            move_types=tuple(self.env['account.move'].get_invoice_types()),
            groupby_clause=SQL("GROUP BY %s", groupby_clause),
            orderby_clause=SQL("ORDER BY %s", groupby_clause),
            tail_query=SQL(tail_query),
        )
        self._cr.execute(query)
        query_res_lines = self._cr.dictfetchall()

        return build_result(query_res_lines)
