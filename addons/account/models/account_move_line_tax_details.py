# -*- coding: utf-8 -*-

from odoo import api, models
from odoo.tools import SQL


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _get_query_tax_details_simplified(self, table_references, search_condition):
        return SQL('''
            WITH filtered_aml AS MATERIALIZED (
                SELECT account_move_line.*, move.move_type AS move_type
                FROM %(table_references)s
                JOIN account_move move ON move.id = account_move_line.move_id
                WHERE %(search_condition)s
            ),
            base_lines AS (
                SELECT f.*, rel.account_tax_id AS applied_tax_id
                FROM filtered_aml f
                JOIN account_move_line_account_tax_rel rel ON f.id = rel.account_move_line_id
            ),
            tax_lines AS (
                SELECT
                    f.*,
                    tax_rep.account_id AS rep_account_id,
                    tax_rep.factor_percent,
                    tax_rep.use_in_tax_closing,
                    COALESCE(f.group_tax_id, f.tax_line_id) AS applied_tax_id
                FROM filtered_aml f
                JOIN account_tax_repartition_line tax_rep ON tax_rep.id = f.tax_repartition_line_id
            ),
            tax_data AS (
                SELECT
                    lt.id AS tax_line_id,
                    lt.balance AS tax_amount,
                    lt.amount_currency AS tax_amount_currency,
                    aml.id AS base_line_id,
                    aml.move_id,
                    lt.display_type,
                    lt.tax_line_id AS tax_id,
                    lt.group_tax_id,
                    lt.tax_repartition_line_id,
                    aml.account_id AS base_account_id,
                    t.sequence,
                    CASE WHEN t.amount_type <> 'fixed' THEN aml.balance ELSE aml.quantity END AS base_value,
                    aml.balance AS base_amount,
                    CASE WHEN t.amount_type <> 'fixed' THEN aml.amount_currency ELSE aml.quantity END AS base_value_currency,
                    aml.amount_currency AS base_amount_currency,
                    curr.decimal_places AS curr_prec,
                    comp_curr.decimal_places AS comp_curr_prec,
                    (
                        t.tax_exigibility != 'on_payment'
                        OR move.tax_cash_basis_rec_id IS NOT NULL
                        OR move.always_tax_exigible
                    ) AS tax_exigible
                FROM base_lines aml
                JOIN account_move move ON move.id = aml.move_id
                JOIN tax_lines lt
                    ON lt.move_id = aml.move_id
                    AND lt.currency_id = aml.currency_id
                    AND lt.partner_id IS NOT DISTINCT FROM aml.partner_id
                    AND (
                        lt.applied_tax_id = aml.applied_tax_id
                        OR (
                            aml.tax_repartition_line_id IS NOT NULL
                            AND lt.tax_line_id = aml.applied_tax_id
                        )
                    )
                JOIN account_tax t ON lt.tax_line_id = t.id
                JOIN res_currency curr ON curr.id = lt.currency_id
                JOIN res_currency comp_curr ON comp_curr.id = lt.company_currency_id
                WHERE (
                    aml.move_type != 'entry'
                    OR (t.tax_exigibility = 'on_payment' AND t.cash_basis_transition_account_id IS NOT NULL)
                    OR sign(aml.balance) = sign(lt.balance * t.amount * lt.factor_percent)
                ) AND (
                    COALESCE(lt.rep_account_id, aml.account_id) = lt.account_id
                    OR (t.tax_exigibility = 'on_payment' AND t.cash_basis_transition_account_id IS NOT NULL)
                ) AND (
                    (t.analytic IS NOT TRUE AND lt.use_in_tax_closing IS TRUE)
                    OR (aml.analytic_distribution IS NULL AND lt.analytic_distribution IS NULL)
                    OR aml.analytic_distribution = lt.analytic_distribution
                )
            ),
            aggregated AS (
                SELECT
                    *,
                    SUM(base_value) OVER (
                        PARTITION BY tax_line_id, tax_id
                        ORDER BY sequence, base_line_id
                    ) AS base_cumul,
                    SUM(base_value) OVER (PARTITION BY tax_line_id, tax_id) AS base,
                    SUM(base_value_currency) OVER (
                        PARTITION BY tax_line_id, tax_id
                        ORDER BY sequence, base_line_id
                    ) AS base_cumul_currency,
                    SUM(base_value_currency) OVER (PARTITION BY tax_line_id, tax_id) AS base_currency
                FROM tax_data
            )
            SELECT
                tax_line_id || '-' || base_line_id || '-' || base_line_id AS id,
                base_line_id,
                tax_line_id,
                display_type,
                base_line_id AS src_line_id,
                tax_id,
                group_tax_id,
                tax_exigible,
                base_account_id,
                tax_repartition_line_id,
                base_amount,
                COALESCE(
                    ROUND(tax_amount * base_cumul / NULLIF(base, 0), comp_curr_prec)
                    - LAG(ROUND(tax_amount * base_cumul / NULLIF(base, 0), comp_curr_prec), 1, 0.0)
                        OVER (PARTITION BY tax_line_id, tax_id ORDER BY tax_line_id, base_line_id),
                    0.0
                ) AS tax_amount,
                base_amount_currency,
                COALESCE(
                    ROUND(tax_amount_currency * base_cumul_currency / NULLIF(base_currency, 0), curr_prec)
                    - LAG(ROUND(tax_amount_currency * base_cumul_currency / NULLIF(base_currency, 0), curr_prec), 1, 0.0)
                        OVER (PARTITION BY tax_line_id, tax_id ORDER BY tax_line_id, base_line_id),
                    0.0
                ) AS tax_amount_currency
            FROM aggregated
            ORDER BY tax_line_id, base_line_id
            ''',
            table_references=table_references,
            search_condition=search_condition,
        )

    @api.model
    def _get_query_tax_details(self, table_references, search_condition) -> SQL:
        """Create the tax details sub-query based on an existing SQL query.

        Kept as a compatibility wrapper for callers already building their own
        account.move.line query.
        """
        return self._get_query_tax_details_simplified(table_references, search_condition)

    @api.model
    def _get_query_tax_details_from_domain(self, domain, fallback=False) -> SQL:
        """Create the tax details sub-query based on the orm domain passed as parameter.

        The simplified query is always used; ``fallback`` is kept for compatibility.
        """
        query = self.env['account.move.line']._search(domain)
        return self._get_query_tax_details_simplified(query.from_clause, query.where_clause)
