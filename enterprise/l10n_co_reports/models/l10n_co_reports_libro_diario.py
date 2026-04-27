# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.tools import SQL


class LibroDiarioReportCustomHandler(models.AbstractModel):
    _name = 'l10n_co.libro.diario.report.handler'
    _inherit = 'l10n_co.report.handler'
    _description = 'Libro Diario Report Custom Handler'

    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals, warnings=None):
        domain = self._get_domain(report, options)
        query_results = self._get_query_results(report, options, domain)
        return self._transform_query_results_into_report_lines(report, options, query_results)

    def _transform_query_results_into_report_lines(self, report, options, query_results):
        processed_results = {}
        for results in query_results:
            processed_results.setdefault(results['line_id'], {})[results['column_group_key']] = results
        lines = []
        for key, value in processed_results.items():
            line_id = report._get_generic_line_id('account.move', key)
            columns = self._get_column_values(report, options, value)
            columns_data = next(iter(value.values()))
            parts = [
                columns_data.get('move_name'),
                columns_data.get('partner_name'),
                columns_data.get('account_name'),
                columns_data.get('line_label')
            ]
            line_name = " ".join(str(p) for p in parts if p).strip()
            lines.append((0, {
                'id': line_id,
                'name': line_name,
                'level': 1,
                'unfoldable': False,
                'columns': columns
            }))
        return lines

    def _get_query_results(self, report, options, domain):
        queries = []
        for column_group_key, column_group_options in report._split_options_per_column_group(options).items():

            query = report._get_report_query(column_group_options, 'strict_range', domain=domain)
            account_alias = query.left_join(lhs_alias='account_move_line', lhs_column='account_id', rhs_table='account_account', rhs_column='id', link='account_id')
            account_code = self.env['account.account']._field_to_sql(account_alias, 'code', query)
            account_name = self.env['account.account']._field_to_sql(account_alias, 'name')
            account_id = SQL.identifier(account_alias, 'id')
            account_name = SQL("%s || ' ' || (%s)", account_code, account_name)
            queries.append(SQL(
                """
                SELECT
                    %(column_group_key)s AS column_group_key,
                    account_move_line.id AS line_id,
                    account_move_line.date AS line_date,
                    account_move.id AS move_id,
                    account_move.name AS move_name,
                    %(account_id)s AS account_id,
                    %(account_name)s AS account_name,
                    res_partner.id AS partner_id,
                    res_partner.name AS partner_name,
                    account_move_line.name AS line_label,
                    account_move_line.debit AS line_debit,
                    account_move_line.credit AS line_credit
                FROM %(table_references)s
                JOIN account_move ON account_move_line.move_id = account_move.id
                JOIN res_partner ON account_move_line.partner_id = res_partner.id
                WHERE %(search_condition)s
                ORDER BY account_move_line.date DESC
                """,
                column_group_key=column_group_key,
                account_id=account_id,
                account_name=account_name,
                table_references=query.from_clause,
                search_condition=query.where_clause,
            ))

        self._cr.execute(SQL(' UNION ALL ').join(queries))
        return self._cr.dictfetchall()

    def _get_domain(self, report, options, line_dict_id=None):
        domain = super()._get_domain(report, options, line_dict_id=line_dict_id)
        domain += [('company_id', '=', self.env.company.id)]
        return domain

    def print_pdf(self, options, action_param):
        return self.env.ref('l10n_co_reports.action_report_libro_diario').with_context(options=options).report_action([])
