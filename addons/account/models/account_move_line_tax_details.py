# -*- coding: utf-8 -*-

from odoo import api, models
from odoo.tools import SQL


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.model
    def _get_extra_query_base_tax_line_mapping(self) -> SQL:
        # TO OVERRIDE
        return SQL()

    @api.model
    def _get_query_tax_details_aml_fields(self):
        return (
            'id',
            'move_id',
            'currency_id',
            'company_currency_id',
            'partner_id',
            'tax_repartition_line_id',
            'group_tax_id',
            'tax_line_id',
            'balance',
            'amount_currency',
            'quantity',
            'display_type',
            'account_id',
            'analytic_distribution',
        )

    @api.model
    def _get_query_tax_details(self, domain_query) -> SQL:
        extra_query_base_tax_line_mapping = self._get_extra_query_base_tax_line_mapping()
        aml_fields = self._get_query_tax_details_aml_fields()
        filtered_aml_fields_select = SQL(',\n                    ').join(
            SQL(
                '%(field)s AS %(alias)s',
                field=SQL.identifier('account_move_line', field_name),
                alias=SQL.identifier(field_name),
            )
            for field_name in aml_fields
        )
        aml_fields_select = SQL(',\n                    ').join(
            SQL.identifier('aml', field_name)
            if field_name == 'id'
            else SQL(
                'ANY_VALUE(%(field)s) AS %(alias)s',
                field=SQL.identifier('aml', field_name),
                alias=SQL.identifier(field_name),
            )
            for field_name in aml_fields
        )

        return SQL('''
            WITH filtered_aml AS MATERIALIZED (
                SELECT %(filtered_aml_fields_select)s
                FROM %(table_references)s
                WHERE %(search_condition)s
            ),
            base_lines AS (
                SELECT
                    %(aml_fields_select)s,
                    ARRAY_AGG(tax.id ORDER BY tax.sequence, tax.id) AS direct_tax_ids,
                    ARRAY_AGG(tax.id) FILTER (WHERE tax.amount_type = 'group') AS group_tax_ids,
                    ARRAY_AGG(COALESCE(child_tax.id, tax.id) ORDER BY tax.sequence, tax.id, child_tax.sequence, child_tax.id)
                        FILTER (
                            WHERE CASE
                                WHEN child_tax.id IS NULL
                                THEN tax.is_base_affected
                                ELSE child_tax.is_base_affected
                            END
                        ) AS applied_tax_ids
                FROM filtered_aml aml
                JOIN account_move_line_account_tax_rel rel ON aml.id = rel.account_move_line_id
                JOIN account_tax tax ON tax.id = rel.account_tax_id
                LEFT JOIN account_tax_filiation_rel tax_filiation ON tax_filiation.parent_tax = tax.id
                LEFT JOIN account_tax child_tax ON child_tax.id = tax_filiation.child_tax
                GROUP BY aml.id
            ),
            tax_lines AS (
                SELECT
                    %(aml_fields_select)s,
                    ANY_VALUE(tax_rep.account_id) AS rep_account_id,
                    ANY_VALUE(tax_rep.factor_percent) AS factor_percent,
                    ANY_VALUE(tax_rep.use_in_tax_closing) AS use_in_tax_closing,
                    ANY_VALUE(COALESCE(aml.group_tax_id, aml.tax_line_id)) AS applied_tax_id,
                    COALESCE(
                        ARRAY_AGG(rel.account_tax_id ORDER BY tax.sequence, tax.id) FILTER (WHERE rel.account_tax_id IS NOT NULL),
                        ARRAY[]::integer[]
                    ) AS applied_tax_ids
                FROM filtered_aml aml
                JOIN account_tax_repartition_line tax_rep ON tax_rep.id = aml.tax_repartition_line_id
                JOIN account_tax line_tax ON line_tax.id = aml.tax_line_id
                LEFT JOIN account_move_line_account_tax_rel rel ON aml.id = rel.account_move_line_id
                LEFT JOIN account_tax tax ON tax.id = rel.account_tax_id
                GROUP BY aml.id
            ),
            tax_data AS (
                SELECT
                    tax_line.id AS tax_line_id,
                    tax_line.balance AS tax_amount,
                    tax_line.amount_currency AS tax_amount_currency,
                    base_line.id AS base_line_id,
                    base_line.move_id,
                    tax_line.display_type,
                    tax_line.tax_line_id AS tax_id,
                    tax_line.group_tax_id,
                    tax_line.tax_repartition_line_id,
                    base_line.account_id AS base_account_id,
                    tax.sequence,
                    CASE WHEN tax.amount_type <> 'fixed' THEN base_line.balance ELSE base_line.quantity END AS base_value,
                    base_line.balance AS base_amount,
                    CASE WHEN tax.amount_type <> 'fixed' THEN base_line.amount_currency ELSE base_line.quantity END AS base_value_currency,
                    base_line.amount_currency AS base_amount_currency,
                    curr.decimal_places AS curr_prec,
                    comp_curr.decimal_places AS comp_curr_prec,
                    (
                        tax.tax_exigibility != 'on_payment'
                        OR move.tax_cash_basis_rec_id IS NOT NULL
                        OR move.always_tax_exigible
                    ) AS tax_exigible
                FROM base_lines base_line
                JOIN account_move move ON move.id = base_line.move_id
                JOIN tax_lines tax_line
                    ON tax_line.move_id = base_line.move_id
                    AND tax_line.currency_id = base_line.currency_id
                    AND tax_line.partner_id IS NOT DISTINCT FROM base_line.partner_id
                    AND (
                        (
                            base_line.tax_repartition_line_id IS NULL
                            AND tax_line.applied_tax_id = ANY(base_line.direct_tax_ids)
                        )
                        OR (
                            base_line.tax_repartition_line_id IS NOT NULL
                            AND tax_line.tax_line_id = ANY(base_line.direct_tax_ids)
                            AND (
                                tax_line.group_tax_id = base_line.group_tax_id
                                OR (
                                    NOT EXISTS (
                                        SELECT 1
                                        FROM account_tax_filiation_rel tax_filiation
                                        WHERE tax_filiation.parent_tax IN (tax_line.group_tax_id, base_line.group_tax_id)
                                        AND tax_filiation.child_tax = tax_line.tax_line_id
                                    )
                                )
                            )
                        )
                    )
                JOIN account_tax tax ON tax_line.tax_line_id = tax.id
                JOIN res_currency curr ON curr.id = tax_line.currency_id
                JOIN res_currency comp_curr ON comp_curr.id = tax_line.company_currency_id
                WHERE (
                        move.move_type != 'entry'
                    OR (tax.tax_exigibility = 'on_payment' AND tax.cash_basis_transition_account_id IS NOT NULL)
                    OR sign(base_line.balance) = sign(tax_line.balance * tax.amount * tax_line.factor_percent)
                ) AND (
                    NOT tax.include_base_amount
                    OR NOT tax.is_base_affected
                    OR base_line.applied_tax_ids[
                        ARRAY_LENGTH(base_line.applied_tax_ids, 1) - COALESCE(ARRAY_LENGTH(tax_line.applied_tax_ids, 1), 0):ARRAY_LENGTH(base_line.applied_tax_ids, 1)
                    ] = ARRAY[tax_line.tax_line_id] || tax_line.applied_tax_ids
                ) AND (
                    tax_line.rep_account_id IS NOT NULL
                    OR (
                        tax.tax_exigibility = 'on_payment'
                        AND tax.cash_basis_transition_account_id IS NOT NULL
                    )
                    OR base_line.account_id = tax_line.account_id
                ) AND (
                    (tax.analytic IS NOT TRUE AND tax_line.use_in_tax_closing IS TRUE)
                    OR base_line.analytic_distribution IS NOT DISTINCT FROM tax_line.analytic_distribution
                )
                %(extra_query_base_tax_line_mapping)s
            ),
            aggregated AS (
                SELECT
                    *,
                    SUM(base_value) OVER tax_partition_ordered AS base_cumul,
                    SUM(base_value) OVER tax_partition AS base,
                    SUM(base_value_currency) OVER tax_partition_ordered AS base_cumul_currency,
                    SUM(base_value_currency) OVER tax_partition AS base_currency
                FROM tax_data
                WINDOW
                    tax_partition AS (PARTITION BY tax_line_id, tax_id),
                    tax_partition_ordered AS (tax_partition ORDER BY sequence, base_line_id)
            )
            SELECT
                tax_line_id || '-' || base_line_id AS id,
                base_line_id,
                tax_line_id,
                display_type,
                tax_id,
                group_tax_id,
                tax_exigible,
                base_account_id,
                tax_repartition_line_id,
                base_amount,
                COALESCE(
                    ROUND(tax_amount * base_cumul / NULLIF(base, 0), comp_curr_prec)
                    - LAG(ROUND(tax_amount * base_cumul / NULLIF(base, 0), comp_curr_prec), 1, 0.0)
                        OVER tax_detail_partition,
                    0.0
                ) AS tax_amount,
                base_amount_currency,
                COALESCE(
                    ROUND(tax_amount_currency * base_cumul_currency / NULLIF(base_currency, 0), curr_prec)
                    - LAG(ROUND(tax_amount_currency * base_cumul_currency / NULLIF(base_currency, 0), curr_prec), 1, 0.0)
                        OVER tax_detail_partition,
                    0.0
                ) AS tax_amount_currency
            FROM aggregated
            WINDOW tax_detail_partition AS (PARTITION BY tax_line_id, tax_id ORDER BY tax_line_id, base_line_id)
            ORDER BY tax_line_id, base_line_id
            ''',
            table_references=domain_query.from_clause,
            search_condition=domain_query.where_clause,
            filtered_aml_fields_select=filtered_aml_fields_select,
            aml_fields_select=aml_fields_select,
            extra_query_base_tax_line_mapping=extra_query_base_tax_line_mapping,
        )

    @api.model
    def _get_query_tax_details_from_domain(self, domain) -> SQL:
        """Create the tax details sub-query based on the orm domain passed as parameter.
        """
        query = self.env['account.move.line']._search(domain)
        return self._get_query_tax_details(query)
