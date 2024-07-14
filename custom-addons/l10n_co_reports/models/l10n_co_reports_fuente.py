# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.tools.misc import get_lang

class FuenteReportCustomHandler(models.AbstractModel):
    _name = 'l10n_co.fuente.report.handler'
    _inherit = 'l10n_co.report.handler'
    _description = 'Fuente Report Custom Handler'

    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals, warnings=None):
        domain = self._get_domain(report, options)
        query_results = self._get_query_results(report, options, domain)
        return super()._get_partner_values(report, options, query_results, '_report_expand_unfoldable_line_fuente')

    def _get_query_results(self, report, options, domain, account=False):
        queries = []
        params = []
        for column_group_key, column_group_options in report._split_options_per_column_group(options).items():
            lang = self.env.user.lang or get_lang(self.env).code
            account_name = f"COALESCE(aa.name->>'{lang}', aa.name->>'en_US')"

            tables, where_clause, where_params = report._query_get(column_group_options, 'strict_range', domain=domain)
            queries.append(f"""
                SELECT
                    %s AS column_group_key,
                    SUM(account_move_line.credit - account_move_line.debit) AS balance,
                    SUM(CASE
                        WHEN account_move_line.credit > 0
                            THEN account_move_line.tax_base_amount
                        WHEN account_move_line.debit > 0
                            THEN account_move_line.tax_base_amount * -1
                        ELSE 0
                        END
                    ) AS tax_base_amount,
                    {account and f"aa.code || ' ' || {account_name} AS account_name," or ''}
                    {account and "aa.id AS account_id," or ''}
                    rp.id AS partner_id,
                    rp.name AS partner_name
                FROM {tables}
                JOIN res_partner rp ON account_move_line.partner_id = rp.id
                JOIN account_account aa ON account_move_line.account_id = aa.id
                WHERE {where_clause}
                GROUP BY rp.id {account and ', aa.id' or ''}
                {account and '''HAVING SUM(
                        CASE
                        WHEN account_move_line.credit > 0
                            THEN account_move_line.tax_base_amount
                        WHEN account_move_line.debit > 0
                            THEN account_move_line.tax_base_amount * -1
                        ELSE 0
                        END
                    ) != 0''' or ''}
            """)
            params += [column_group_key, *where_params]

        self._cr.execute(' UNION ALL '.join(queries), params)
        return self._cr.dictfetchall()

    def _get_domain(self, report, options, line_dict_id=None):
        domain = super()._get_domain(report, options, line_dict_id=line_dict_id)
        domain += [('account_id.code', '=like', '2365%'), ('account_id.code', '!=', '236505')]
        return domain

    def _report_expand_unfoldable_line_fuente(self, line_dict_id, groupby, options, progress, offset, unfold_all_batch_data=None):
        report = self.env['account.report'].browse(options['report_id'])
        domain = self._get_domain(report, options, line_dict_id=line_dict_id)
        query_results = self._get_query_results(report, options, domain, account=True)
        return super()._get_grouped_values(report, options, query_results, group_by='account_id')
