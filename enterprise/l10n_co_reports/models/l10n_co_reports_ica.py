# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.tools import SQL


class ICAReportCustomHandler(models.AbstractModel):
    _name = 'l10n_co.ica.report.handler'
    _inherit = 'l10n_co.report.handler'
    _description = 'ICA Report Custom Handler'

    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals, warnings=None):
        domain = self._get_domain(report, options)
        query_results = self._get_query_results(report, options, domain)
        return super()._get_partner_values(report, options, query_results, '_report_expand_unfoldable_line_ica')

    def _get_query_results(self, report, options, domain, bimestre=False):
        queries = []
        for column_group_key, column_group_options in report._split_options_per_column_group(options).items():

            query = report._get_report_query(column_group_options, 'strict_range', domain=domain)
            bimestre_expression = SQL('FLOOR((EXTRACT(MONTH FROM account_move_line.date) + 1) / 2)')
            bimestre_column = SQL('%s AS bimestre,', bimestre_expression) if bimestre else SQL()
            bimestre_having = SQL('''
                HAVING SUM(
                    CASE
                    WHEN account_move_line.credit > 0
                        THEN account_move_line.tax_base_amount
                    WHEN account_move_line.debit > 0
                        THEN account_move_line.tax_base_amount * -1
                    ELSE 0
                    END
                ) != 0
            ''') if bimestre else SQL()
            queries.append(SQL(
                """
                SELECT
                    %(column_group_key)s AS column_group_key,
                    SUM(account_move_line.credit - account_move_line.debit) AS balance,
                    SUM(CASE
                        WHEN account_move_line.credit > 0
                            THEN account_move_line.tax_base_amount
                        WHEN account_move_line.debit > 0
                            THEN account_move_line.tax_base_amount * -1
                        ELSE 0
                        END
                    ) AS tax_base_amount,
                    %(bimestre_column)s
                    rp.id AS partner_id,
                    rp.name AS partner_name
                FROM %(table_references)s
                JOIN res_partner rp ON account_move_line.partner_id = rp.id
                JOIN account_account aa ON account_move_line.account_id = aa.id
                WHERE %(search_condition)s
                GROUP BY rp.id %(bimestre_groupby)s
                %(bimestre_having)s
                """,
                column_group_key=column_group_key,
                bimestre_column=bimestre_column,
                table_references=query.from_clause,
                bimestre_groupby=SQL(', %s', bimestre_expression) if bimestre else SQL(),
                search_condition=query.where_clause,
                bimestre_having=bimestre_having,
            ))

        self._cr.execute(SQL(' UNION ALL ').join(queries))
        return self._cr.dictfetchall()

    def _get_domain(self, report, options, line_dict_id=None):
        domain = super()._get_domain(report, options, line_dict_id=line_dict_id)
        domain += [('account_id.code', '=like', '2368%')]
        return domain

    def _report_expand_unfoldable_line_ica(self, line_dict_id, groupby, options, progress, offset, unfold_all_batch_data=None):
        report = self.env['account.report'].browse(options['report_id'])
        domain = self._get_domain(report, options, line_dict_id=line_dict_id)
        query_results = self._get_query_results(report, options, domain, bimestre=True)
        return super()._get_grouped_values(report, options, query_results, group_by='bimestre')
