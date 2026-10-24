# -*- coding: utf-8 -*-

from odoo import api, models
from odoo.tools import SQL


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _get_query_tax_details_simplified(self, table_references, search_condition):
        query = SQL('''
            WITH tax_data AS (
                SELECT
                    lt.id AS tax_line_id,
                    lt.tax_line_id AS tax_id,
                    lt.group_tax_id,
                    lt.balance AS tax_amount,
                    lt.amount_currency AS tax_amount_currency,
                    account_move_line.id AS base_line_id,
                    account_move_line.balance AS base_amount,
                    account_move_line.amount_currency AS base_amount_currency,
                    lt.move_id,
                    t.sequence,
                    CASE
                        WHEN t.amount_type <> 'fixed' THEN account_move_line.balance
                        ELSE account_move_line.quantity
                    END AS base_value,
                    CASE
                        WHEN t.amount_type <> 'fixed' THEN account_move_line.amount_currency
                        ELSE account_move_line.quantity
                    END AS base_value_currency,
                    lt.partner_id,
                    lt.currency_id,
                    lt.analytic_distribution,
                    account_move_line.account_id AS base_account_id,
                    lt.account_id AS tax_account_id,
                    t.amount,
                    tax_rep.factor_percent,
                    move.move_type,
                    curr.decimal_places AS curr_prec,
                    comp_curr.decimal_places AS comp_curr_prec
                FROM %(table_references)s
                JOIN account_move move ON move.id = account_move_line.move_id
                JOIN account_move_line_account_tax_rel r ON r.account_move_line_id = account_move_line.id
                JOIN account_tax t ON t.id = r.account_tax_id
                JOIN LATERAL (
                    WITH candidates AS (
                        SELECT
                            candidate_lt.*,
                            COALESCE(lt_tax_ids.ids, ARRAY[]::integer[]) AS lt_tax_ids,
                            COALESCE(lt_context_tax_ids.ids, ARRAY[]::integer[]) AS lt_context_tax_ids,
                            COALESCE(base_context_tax_ids.ids, ARRAY[]::integer[]) AS base_other_context_tax_ids
                        FROM account_move_line candidate_lt
                        JOIN account_tax_repartition_line candidate_tax_rep ON candidate_tax_rep.id = candidate_lt.tax_repartition_line_id
                        LEFT JOIN LATERAL (
                            SELECT ARRAY_AGG(DISTINCT lt_tax_rel.account_tax_id) AS ids
                            FROM account_move_line_account_tax_rel lt_tax_rel
                            WHERE lt_tax_rel.account_move_line_id = candidate_lt.id
                        ) lt_tax_ids ON TRUE
                        LEFT JOIN LATERAL (
                            SELECT ARRAY_AGG(DISTINCT tax_id) AS ids
                            FROM (
                                SELECT UNNEST(COALESCE(lt_tax_ids.ids, ARRAY[]::integer[])) AS tax_id

                                UNION

                                SELECT tax_filiation.parent_tax
                                FROM account_tax_filiation_rel tax_filiation
                                WHERE tax_filiation.child_tax = ANY(COALESCE(lt_tax_ids.ids, ARRAY[]::integer[]))
                            ) tax_ids
                        ) lt_context_tax_ids ON TRUE
                        LEFT JOIN LATERAL (
                            SELECT ARRAY_AGG(DISTINCT base_tax_rel.account_tax_id) AS ids
                            FROM account_move_line_account_tax_rel base_tax_rel
                            WHERE base_tax_rel.account_move_line_id = account_move_line.id
                        ) base_tax_ids ON TRUE
                        LEFT JOIN LATERAL (
                            SELECT ARRAY_AGG(DISTINCT tax_id) AS ids
                            FROM (
                                SELECT base_tax_rel.account_tax_id AS tax_id
                                FROM account_move_line_account_tax_rel base_tax_rel
                                WHERE base_tax_rel.account_move_line_id = account_move_line.id
                                AND base_tax_rel.account_tax_id != t.id
                                AND base_tax_rel.account_tax_id NOT IN (
                                    SELECT current_tax_filiation.parent_tax
                                    FROM account_tax_filiation_rel current_tax_filiation
                                    WHERE current_tax_filiation.child_tax = t.id
                                )

                                UNION

                                SELECT tax_filiation.parent_tax
                                FROM account_tax_filiation_rel tax_filiation
                                JOIN account_move_line_account_tax_rel base_tax_rel
                                    ON base_tax_rel.account_tax_id = tax_filiation.child_tax
                                WHERE base_tax_rel.account_move_line_id = account_move_line.id
                                AND tax_filiation.parent_tax != t.id
                            ) tax_ids
                        ) base_context_tax_ids ON TRUE
                        WHERE (
                            (
                                account_move_line.tax_repartition_line_id IS NULL
                                AND t.id = COALESCE(candidate_lt.group_tax_id, candidate_lt.tax_line_id)
                            )
                            OR (
                                account_move_line.tax_repartition_line_id IS NOT NULL
                                AND t.id = candidate_lt.tax_line_id
                            )
                        )
                        AND candidate_lt.move_id = account_move_line.move_id
                        AND COALESCE(candidate_lt.partner_id, 0) = COALESCE(account_move_line.partner_id, 0)
                        AND candidate_lt.currency_id = account_move_line.currency_id
                        AND (
                            (
                                account_move_line.tax_repartition_line_id IS NULL
                                AND (
                                    candidate_lt.group_tax_id IS NULL
                                    OR candidate_lt.group_tax_id = ANY(COALESCE(base_tax_ids.ids, ARRAY[]::integer[]))
                                )
                            )
                            OR (
                                account_move_line.tax_repartition_line_id IS NOT NULL
                                AND candidate_lt.group_tax_id IS NOT DISTINCT FROM account_move_line.group_tax_id
                            )
                        )
                        AND (
                            t.analytic IS NOT TRUE
                            OR (candidate_lt.analytic_distribution IS NULL AND account_move_line.analytic_distribution IS NULL)
                            OR candidate_lt.analytic_distribution = account_move_line.analytic_distribution
                        )
                        AND (
                            move.move_type != 'entry'
                            OR (t.tax_exigibility = 'on_payment' AND t.cash_basis_transition_account_id IS NOT NULL)
                            OR sign(account_move_line.balance) = sign(candidate_lt.balance * t.amount * candidate_tax_rep.factor_percent)
                        )
                        AND (
                            account_move_line.tax_repartition_line_id IS NOT NULL
                            OR COALESCE(candidate_tax_rep.account_id, account_move_line.account_id) = candidate_lt.account_id
                            OR (t.tax_exigibility = 'on_payment' AND t.cash_basis_transition_account_id IS NOT NULL)
                        )
                    )
                    SELECT candidates.*
                    FROM candidates
                    WHERE candidates.group_tax_id IS NOT NULL
                    OR NOT COALESCE((
                        SELECT BOOL_OR(CARDINALITY(candidate.lt_tax_ids) > 0)
                        FROM candidates candidate
                        WHERE candidate.group_tax_id IS NULL
                    ), FALSE)
                    OR candidates.id = COALESCE(
                        (
                            SELECT candidate.id
                            FROM candidates candidate
                            WHERE candidate.group_tax_id IS NULL
                            AND CARDINALITY(candidate.lt_tax_ids) > 0
                            AND candidate.lt_context_tax_ids <@ candidate.base_other_context_tax_ids
                            ORDER BY CARDINALITY(candidate.lt_context_tax_ids) DESC, candidate.id
                            LIMIT 1
                        ),
                        (
                            SELECT candidate.id
                            FROM candidates candidate
                            WHERE candidate.group_tax_id IS NULL
                            ORDER BY CARDINALITY(candidate.lt_tax_ids), candidate.id
                            LIMIT 1
                        )
                    )
                ) lt ON TRUE
                JOIN account_tax_repartition_line tax_rep ON tax_rep.id = lt.tax_repartition_line_id
                JOIN res_currency curr ON curr.id = lt.currency_id
                JOIN res_currency comp_curr ON comp_curr.id = lt.company_currency_id
                WHERE
                    %(search_condition)s
                AND (
                    move.move_type != 'entry'
                    OR (t.tax_exigibility = 'on_payment' AND t.cash_basis_transition_account_id IS NOT NULL)
                    OR sign(account_move_line.balance) = sign(lt.balance * t.amount * tax_rep.factor_percent)
                )
                AND (
                    account_move_line.tax_repartition_line_id IS NOT NULL
                    OR COALESCE(tax_rep.account_id, account_move_line.account_id) = lt.account_id
                    OR (t.tax_exigibility = 'on_payment' AND t.cash_basis_transition_account_id IS NOT NULL)
                )
            ),
            aggregated AS (
                SELECT
                    *,
                    SUM(base_value) OVER (PARTITION BY tax_line_id, tax_id ORDER BY sequence, base_line_id) AS base_cumul,
                    SUM(base_value) OVER (PARTITION BY tax_line_id, tax_id) AS base,
                    SUM(base_value_currency) OVER (PARTITION BY tax_line_id, tax_id ORDER BY sequence, base_line_id) AS base_cumul_currency,
                    SUM(base_value_currency) OVER (PARTITION BY tax_line_id, tax_id) AS base_currency
                FROM tax_data
            ),
            raw_tax_details AS (
                SELECT
                    move_id,
                    tax_line_id,
                    base_line_id,
                    tax_id,
                    group_tax_id,
                    curr_prec,
                    comp_curr_prec,
                    base_amount,
                    ROUND(tax_amount * base_cumul / NULLIF(base, 0), comp_curr_prec)
                      - LAG(ROUND(tax_amount * base_cumul / NULLIF(base, 0), comp_curr_prec), 1, 0.0)
                        OVER (PARTITION BY tax_line_id, tax_id ORDER BY tax_line_id, base_line_id) AS tax_amount,
                    base_amount_currency,
                    ROUND(tax_amount_currency * base_cumul_currency / NULLIF(base_currency, 0), curr_prec)
                      - LAG(ROUND(tax_amount_currency * base_cumul_currency / NULLIF(base_currency, 0), curr_prec), 1, 0.0)
                        OVER (PARTITION BY tax_line_id, tax_id ORDER BY tax_line_id, base_line_id) AS tax_amount_currency
                FROM aggregated
            ),
            direct_tax_details AS (
                SELECT raw_tax_details.*
                FROM raw_tax_details
                JOIN account_move_line base_line ON base_line.id = raw_tax_details.base_line_id
                WHERE base_line.tax_repartition_line_id IS NULL
            ),
            tax_line_base_details AS (
                SELECT
                    raw_tax_details.*,
                    base_line.balance AS base_line_balance,
                    base_line.amount_currency AS base_line_balance_currency,
                    base_line.currency_id,
                    base_line.company_currency_id
                FROM raw_tax_details
                JOIN account_move_line base_line ON base_line.id = raw_tax_details.base_line_id
                WHERE base_line.tax_repartition_line_id IS NOT NULL
            ),
            first_dispatched_tax_line_base_details AS (
                SELECT
                    move_id,
                    tax_line_id,
                    src_line_id,
                    base_line_id,
                    tax_id,
                    group_tax_id,
                    base_amount,
                    ROUND(
                        COALESCE(tax_amount * base_cumul / NULLIF(base_line_balance, 0), 0),
                        comp_curr_prec
                    )
                    - LAG(
                        ROUND(
                            COALESCE(tax_amount * base_cumul / NULLIF(base_line_balance, 0), 0),
                            comp_curr_prec
                        ), 1, 0.0
                    ) OVER (PARTITION BY tax_line_id, src_line_id ORDER BY base_line_id) AS tax_amount,
                    base_amount_currency,
                    ROUND(
                        COALESCE(tax_amount_currency * base_cumul_currency / NULLIF(base_line_balance_currency, 0), 0),
                        curr_prec
                    )
                    - LAG(
                        ROUND(
                            COALESCE(tax_amount_currency * base_cumul_currency / NULLIF(base_line_balance_currency, 0), 0),
                            curr_prec
                        ), 1, 0.0
                    ) OVER (PARTITION BY tax_line_id, src_line_id ORDER BY base_line_id) AS tax_amount_currency
                FROM (
                    SELECT
                        tax_line_base.move_id,
                        tax_line_base.tax_line_id,
                        direct_base.base_line_id,
                        tax_line_base.base_line_id AS src_line_id,
                        tax_line_base.tax_id,
                        tax_line_base.group_tax_id,
                        direct_base.tax_amount AS base_amount,
                        direct_base.tax_amount_currency AS base_amount_currency,
                        tax_line_base.tax_amount,
                        tax_line_base.tax_amount_currency,
                        tax_line_base.base_line_balance,
                        tax_line_base.base_line_balance_currency,
                        curr.decimal_places AS curr_prec,
                        tax_line_base.comp_curr_prec,
                        SUM(direct_base.tax_amount) OVER (
                            PARTITION BY tax_line_base.tax_line_id, tax_line_base.base_line_id
                            ORDER BY direct_base.base_line_id
                        ) AS base_cumul,
                        SUM(direct_base.tax_amount_currency) OVER (
                            PARTITION BY tax_line_base.tax_line_id, tax_line_base.base_line_id
                            ORDER BY direct_base.base_line_id
                        ) AS base_cumul_currency
                    FROM tax_line_base_details tax_line_base
                    JOIN res_currency curr ON curr.id = tax_line_base.currency_id
                    JOIN direct_tax_details direct_base ON direct_base.tax_line_id = tax_line_base.base_line_id
                ) source
            ),
            second_dispatched_tax_line_base_details AS (
                SELECT
                    move_id,
                    tax_line_id,
                    src_line_id,
                    base_line_id,
                    tax_id,
                    group_tax_id,
                    base_amount,
                    ROUND(
                        COALESCE(tax_amount * base_cumul / NULLIF(base_line_balance, 0), 0),
                        comp_curr_prec
                    )
                    - LAG(
                        ROUND(
                            COALESCE(tax_amount * base_cumul / NULLIF(base_line_balance, 0), 0),
                            comp_curr_prec
                        ), 1, 0.0
                    ) OVER (PARTITION BY tax_line_id, src_line_id ORDER BY base_line_id) AS tax_amount,
                    base_amount_currency,
                    ROUND(
                        COALESCE(tax_amount_currency * base_cumul_currency / NULLIF(base_line_balance_currency, 0), 0),
                        curr_prec
                    )
                    - LAG(
                        ROUND(
                            COALESCE(tax_amount_currency * base_cumul_currency / NULLIF(base_line_balance_currency, 0), 0),
                            curr_prec
                        ), 1, 0.0
                    ) OVER (PARTITION BY tax_line_id, src_line_id ORDER BY base_line_id) AS tax_amount_currency
                FROM (
                    SELECT
                        tax_line_base.move_id,
                        tax_line_base.tax_line_id,
                        first_dispatched.base_line_id,
                        tax_line_base.base_line_id AS src_line_id,
                        tax_line_base.tax_id,
                        tax_line_base.group_tax_id,
                        first_dispatched.tax_amount AS base_amount,
                        first_dispatched.tax_amount_currency AS base_amount_currency,
                        tax_line_base.tax_amount,
                        tax_line_base.tax_amount_currency,
                        tax_line_base.base_line_balance,
                        tax_line_base.base_line_balance_currency,
                        curr.decimal_places AS curr_prec,
                        tax_line_base.comp_curr_prec,
                        SUM(first_dispatched.tax_amount) OVER (
                            PARTITION BY tax_line_base.tax_line_id, tax_line_base.base_line_id
                            ORDER BY first_dispatched.base_line_id
                        ) AS base_cumul,
                        SUM(first_dispatched.tax_amount_currency) OVER (
                            PARTITION BY tax_line_base.tax_line_id, tax_line_base.base_line_id
                            ORDER BY first_dispatched.base_line_id
                        ) AS base_cumul_currency
                    FROM tax_line_base_details tax_line_base
                    JOIN res_currency curr ON curr.id = tax_line_base.currency_id
                    JOIN first_dispatched_tax_line_base_details first_dispatched ON first_dispatched.tax_line_id = tax_line_base.base_line_id
                ) source
            ),
            dispatched_tax_line_base_details AS (
                SELECT
                    move_id,
                    tax_line_id,
                    base_line_id,
                    tax_id,
                    group_tax_id,
                    SUM(base_amount) AS base_amount,
                    SUM(tax_amount) AS tax_amount,
                    SUM(base_amount_currency) AS base_amount_currency,
                    SUM(tax_amount_currency) AS tax_amount_currency
                FROM (
                    SELECT * FROM first_dispatched_tax_line_base_details

                    UNION ALL

                    SELECT * FROM second_dispatched_tax_line_base_details
                ) dispatched_tax_line_base_details
                GROUP BY move_id, tax_line_id, src_line_id, base_line_id, tax_id, group_tax_id
            )
            SELECT
                move_id,
                tax_line_id,
                base_line_id,
                tax_id,
                group_tax_id,
                base_amount,
                tax_amount,
                base_amount_currency,
                tax_amount_currency
            FROM direct_tax_details

            UNION ALL

            SELECT
                move_id,
                tax_line_id,
                base_line_id,
                tax_id,
                group_tax_id,
                base_amount,
                tax_amount,
                base_amount_currency,
                tax_amount_currency
            FROM dispatched_tax_line_base_details
            ORDER BY tax_line_id, base_line_id
            ''',
            table_references=table_references,
            search_condition=search_condition,
        )
        return query

    @api.model
    def _get_query_tax_details_from_domain(self, domain, fallback=False, use_simplified_query=True) -> SQL:
        """ Create the tax details sub-query based on the orm domain passed as parameter.

        :param domain:      An orm domain on account.move.line.
        :param fallback:    Fallback on an approximated mapping if the mapping failed.
        :return:            query as SQL object
        """
        query = self.env['account.move.line']._search(domain)
        if use_simplified_query and not fallback:
            return self._get_query_tax_details_simplified(query.from_clause, query.where_clause)

        return self._get_query_tax_details(query.from_clause, query.where_clause, fallback=fallback)

    @api.model
    def _get_extra_query_base_tax_line_mapping(self) -> SQL:
        #TO OVERRIDE
        return SQL()

    @api.model
    def _get_query_tax_details(self, table_references, search_condition, fallback=True) -> SQL:
        """ Create the tax details sub-query based on the orm domain passed as parameter.

        :param table_references:    The query to inject after the FROM, as an SQL object.
        :param search_condition:    The query to inject in the WHERE clause, as an SQL object.
        :param fallback:            Fallback on an approximated mapping if the mapping failed.
        :return:                    query as an SQL object
        """
        group_taxes = self.env['account.tax'].search([('amount_type', '=', 'group')])

        group_taxes_query_list = []
        for group_tax in group_taxes:
            children_taxes = group_tax.children_tax_ids
            if not children_taxes:
                continue

            children_taxes_in_query = SQL(','.join('%s' for dummy in children_taxes),
                                          *children_taxes.ids)
            group_taxes_query_list.append(SQL('WHEN tax.id = %s THEN ARRAY[%s]', group_tax.id, children_taxes_in_query))

        if group_taxes_query_list:
            group_taxes_query = SQL('''UNNEST(CASE %s ELSE ARRAY[tax.id] END)''', SQL(' ').join(group_taxes_query_list))
        else:
            group_taxes_query = SQL('tax.id')

        if fallback:
            fallback_query = SQL(
                '''
                UNION ALL

                SELECT
                    account_move_line.id AS tax_line_id,
                    base_line.id AS base_line_id,
                    base_line.id AS src_line_id,
                    base_line.balance AS base_amount,
                    base_line.amount_currency AS base_amount_currency
                FROM %(table_references)s
                LEFT JOIN base_tax_line_mapping ON
                    base_tax_line_mapping.tax_line_id = account_move_line.id
                JOIN account_move_line_account_tax_rel tax_rel ON
                    tax_rel.account_tax_id = COALESCE(account_move_line.group_tax_id, account_move_line.tax_line_id)
                JOIN account_move_line base_line ON
                    base_line.id = tax_rel.account_move_line_id
                    AND base_line.tax_repartition_line_id IS NULL
                    AND base_line.move_id = account_move_line.move_id
                    AND base_line.currency_id = account_move_line.currency_id
                WHERE base_tax_line_mapping.tax_line_id IS NULL
                AND %(search_condition)s
                ''',
                table_references=table_references,
                search_condition=search_condition,
            )
        else:
            fallback_query = SQL()

        extra_query_base_tax_line_mapping = self._get_extra_query_base_tax_line_mapping()

        return SQL(
            '''
            /*
            As example to explain the different parts of the query, we'll consider a move with the following lines:
            Name            Tax_line_id         Tax_ids                 Debit       Credit      Base lines
            ---------------------------------------------------------------------------------------------------
            base_line_1                         10_affect_base, 20      1000
            base_line_2                         10_affect_base, 5       2000
            base_line_3                         10_affect_base, 5       3000
            tax_line_1      10_affect_base      20                                  100         base_line_1
            tax_line_2      20                                                      220         base_line_1
            tax_line_3      10_affect_base      5                                   500         base_line_2/3
            tax_line_4      5                                                       275         base_line_2/3
            */

            WITH base_tax_line_mapping AS (

                /*
                Create the mapping of each tax lines with their corresponding base lines.

                In the example, it will give the following values:
                    base_line_id     tax_line_id    base_amount
                    -------------------------------------------
                    base_line_1      tax_line_1         1000
                    base_line_1      tax_line_2         1000
                    base_line_2      tax_line_3         2000
                    base_line_2      tax_line_4         2000
                    base_line_3      tax_line_3         3000
                    base_line_3      tax_line_4         3000
                */

                SELECT
                    account_move_line.id AS tax_line_id,
                    base_line.id AS base_line_id,
                    base_line.balance AS base_amount,
                    base_line.amount_currency AS base_amount_currency

                FROM %(table_references)s
                JOIN account_tax_repartition_line tax_rep ON
                    tax_rep.id = account_move_line.tax_repartition_line_id
                JOIN account_tax tax ON
                    tax.id = account_move_line.tax_line_id
                JOIN account_move_line_account_tax_rel tax_rel ON
                    tax_rel.account_tax_id = COALESCE(account_move_line.group_tax_id, account_move_line.tax_line_id)
                JOIN account_move move ON
                    move.id = account_move_line.move_id
                JOIN account_move_line base_line ON
                    base_line.id = tax_rel.account_move_line_id
                    AND base_line.tax_repartition_line_id IS NULL
                    AND base_line.move_id = account_move_line.move_id
                    AND (
                        move.move_type != 'entry'
                        OR (tax.tax_exigibility = 'on_payment' AND tax.cash_basis_transition_account_id IS NOT NULL)
                        OR sign(account_move_line.balance) = sign(base_line.balance * tax.amount * tax_rep.factor_percent)
                    )
                    AND COALESCE(base_line.partner_id, 0) = COALESCE(account_move_line.partner_id, 0)
                    AND base_line.currency_id = account_move_line.currency_id
                    AND (
                        COALESCE(tax_rep.account_id, base_line.account_id) = account_move_line.account_id
                        OR (tax.tax_exigibility = 'on_payment' AND tax.cash_basis_transition_account_id IS NOT NULL)
                    )
                    AND (
                        (tax.analytic IS NOT TRUE AND tax_rep.use_in_tax_closing IS TRUE)
                        OR (base_line.analytic_distribution IS NULL AND account_move_line.analytic_distribution IS NULL)
                        OR base_line.analytic_distribution = account_move_line.analytic_distribution
                    )
                    %(extra_query_base_tax_line_mapping)s
                JOIN res_currency curr ON
                    curr.id = account_move_line.currency_id
                JOIN res_currency comp_curr ON
                    comp_curr.id = account_move_line.company_currency_id
                LEFT JOIN LATERAL (
                    /*
                        This table builds a reference table based on the tax_ids field, with the following changes:
                          - flatten the group of taxes
                          - exclude the taxes having 'is_base_affected' set to False.
                        Those allow to match only base_line_1 when finding the base lines of tax_line_1, as we need to find
                        base lines having a 'affecting_base_tax_ids' ending with [10_affect_base, 20], not only containing
                        '10_affect_base'. Otherwise, base_line_2/3 would also be matched.
                        In our example, as all the taxes are set to be affected by previous ones affecting the base, the
                        result is similar to the table 'account_move_line_account_tax_rel':
                        Id                 Tax_ids
                        -------------------------------------------
                        base_line_1        [10_affect_base, 20]
                        base_line_2        [10_affect_base, 5]
                        base_line_3        [10_affect_base, 5]
                    */
                    SELECT ARRAY_AGG(sub.tax_id ORDER BY sub.sequence, sub.tax_id) AS tax_ids
                    FROM (
                        SELECT
                            %(group_taxes_query)s AS tax_id,
                            tax.sequence
                        FROM account_move_line_account_tax_rel tax_rel
                        JOIN account_tax tax ON tax.id = tax_rel.account_tax_id
                        WHERE tax.is_base_affected
                        AND tax_rel.account_move_line_id = account_move_line.id
                    ) AS sub
                ) tax_line_tax_ids ON TRUE
                LEFT JOIN LATERAL (
                    SELECT ARRAY_AGG(sub.tax_id ORDER BY sub.sequence, sub.tax_id) AS tax_ids
                    FROM (
                        SELECT
                            %(group_taxes_query)s AS tax_id,
                            tax.sequence
                        FROM account_move_line_account_tax_rel tax_rel
                        JOIN account_tax tax ON tax.id = tax_rel.account_tax_id
                        WHERE tax.is_base_affected
                        AND tax_rel.account_move_line_id = base_line.id
                    ) AS sub
                ) base_line_tax_ids ON TRUE
                WHERE account_move_line.tax_repartition_line_id IS NOT NULL
                    AND %(search_condition)s
                    AND (
                        -- keeping only the rows from affecting_base_tax_lines that end with the same taxes applied (see comment in tax_line_tax_ids)
                        NOT tax.include_base_amount
                        OR base_line_tax_ids.tax_ids[ARRAY_LENGTH(base_line_tax_ids.tax_ids, 1) - COALESCE(ARRAY_LENGTH(tax_line_tax_ids.tax_ids, 1), 0):ARRAY_LENGTH(base_line_tax_ids.tax_ids, 1)]
                            = ARRAY[account_move_line.tax_line_id] || COALESCE(tax_line_tax_ids.tax_ids, ARRAY[]::INTEGER[])
                    )
            ),


            tax_amount_affecting_base_to_dispatch AS (

                /*
                Computes the total amount to dispatch in case of tax lines affecting the base of subsequent taxes.
                Such tax lines are an additional base amount for others lines, that will be truly dispatch in next
                CTE.

                In the example:
                    - tax_line_1 is an additional base of 100.0 from base_line_1 for tax_line_2.
                    - tax_line_3 is an additional base of 2/5 * 500.0 = 200.0 from base_line_2 for tax_line_4.
                    - tax_line_3 is an additional base of 3/5 * 500.0 = 300.0 from base_line_3 for tax_line_4.

                    src_line_id    base_line_id     tax_line_id    total_base_amount
                    -------------------------------------------------------------
                    tax_line_1     base_line_1      tax_line_2         1000
                    tax_line_3     base_line_2      tax_line_4         5000
                    tax_line_3     base_line_3      tax_line_4         5000
                */

                SELECT
                    tax_line.id AS tax_line_id,
                    base_line.id AS base_line_id,
                    account_move_line.id AS src_line_id,

                    tax_line.company_id,
                    comp_curr.id AS company_currency_id,
                    comp_curr.decimal_places AS comp_curr_prec,
                    curr.id AS currency_id,
                    curr.decimal_places AS curr_prec,

                    tax_line.tax_line_id AS tax_id,

                    base_line.balance AS base_amount,
                    SUM(
                        CASE WHEN tax.amount_type = 'fixed'
                        THEN CASE WHEN base_line.balance < 0 THEN -1 ELSE 1 END * ABS(COALESCE(base_line.quantity, 1.0))
                        ELSE base_line.balance
                        END
                    ) OVER (PARTITION BY tax_line.id, account_move_line.id ORDER BY tax_line.tax_line_id, base_line.id) AS cumulated_base_amount,
                    SUM(
                        CASE WHEN tax.amount_type = 'fixed'
                        THEN CASE WHEN base_line.balance < 0 THEN -1 ELSE 1 END * ABS(COALESCE(base_line.quantity, 1.0))
                        ELSE base_line.balance
                        END
                    ) OVER (PARTITION BY tax_line.id, account_move_line.id) AS total_base_amount,
                    account_move_line.balance AS total_tax_amount,

                    base_line.amount_currency AS base_amount_currency,
                    SUM(
                        CASE WHEN tax.amount_type = 'fixed'
                        THEN CASE WHEN base_line.amount_currency < 0 THEN -1 ELSE 1 END * ABS(COALESCE(base_line.quantity, 1.0))
                        ELSE base_line.amount_currency
                        END
                    ) OVER (PARTITION BY tax_line.id, account_move_line.id ORDER BY tax_line.tax_line_id, base_line.id) AS cumulated_base_amount_currency,
                    SUM(
                        CASE WHEN tax.amount_type = 'fixed'
                        THEN CASE WHEN base_line.amount_currency < 0 THEN -1 ELSE 1 END * ABS(COALESCE(base_line.quantity, 1.0))
                        ELSE base_line.amount_currency
                        END
                    ) OVER (PARTITION BY tax_line.id, account_move_line.id) AS total_base_amount_currency,
                    account_move_line.amount_currency AS total_tax_amount_currency

                FROM %(table_references)s
                JOIN account_tax tax_include_base_amount ON
                    tax_include_base_amount.include_base_amount
                    AND tax_include_base_amount.id = account_move_line.tax_line_id
                JOIN base_tax_line_mapping base_tax_line_mapping ON
                    base_tax_line_mapping.tax_line_id = account_move_line.id
                JOIN account_move_line_account_tax_rel tax_rel ON
                    tax_rel.account_move_line_id = base_tax_line_mapping.tax_line_id
                JOIN account_tax tax ON
                    tax.id = tax_rel.account_tax_id
                JOIN base_tax_line_mapping tax_line_matching ON
                    tax_line_matching.base_line_id = base_tax_line_mapping.base_line_id
                JOIN account_move_line tax_line ON
                    tax_line.id = tax_line_matching.tax_line_id
                    AND tax_line.tax_line_id = tax_rel.account_tax_id
                JOIN res_currency curr ON
                    curr.id = tax_line.currency_id
                JOIN res_currency comp_curr ON
                    comp_curr.id = tax_line.company_currency_id
                JOIN account_move_line base_line ON
                    base_line.id = base_tax_line_mapping.base_line_id
                WHERE %(search_condition)s
            ),


            base_tax_matching_base_amounts AS (

                /*
                Build here the full mapping tax lines <=> base lines containing the final base amounts.
                This is done in a 3-parts union.

                Note: src_line_id is used only to build a unique ID.
                */

                /*
                PART 1: raw mapping computed in base_tax_line_mapping.
                */

                SELECT
                    tax_line_id,
                    base_line_id,
                    base_line_id AS src_line_id,
                    base_amount,
                    base_amount_currency
                FROM base_tax_line_mapping

                UNION ALL

                /*
                PART 2: Dispatch the tax amount of tax lines affecting the base of subsequent ones, using
                tax_amount_affecting_base_to_dispatch.

                This will effectively add the following rows:
                base_line_id    tax_line_id     src_line_id     base_amount
                -------------------------------------------------------------
                base_line_1     tax_line_2      tax_line_1      100
                base_line_2     tax_line_4      tax_line_3      200
                base_line_3     tax_line_4      tax_line_3      300
                */

                SELECT
                    sub.tax_line_id,
                    sub.base_line_id,
                    sub.src_line_id,

                    ROUND(
                        COALESCE(SIGN(sub.cumulated_base_amount) * sub.total_tax_amount * ABS(sub.cumulated_base_amount) / NULLIF(sub.total_base_amount, 0.0), 0.0),
                        sub.comp_curr_prec
                    )
                    - LAG(ROUND(
                        COALESCE(SIGN(sub.cumulated_base_amount) * sub.total_tax_amount * ABS(sub.cumulated_base_amount) / NULLIF(sub.total_base_amount, 0.0), 0.0),
                        sub.comp_curr_prec
                    ), 1, 0.0)
                    OVER (
                        PARTITION BY sub.tax_line_id, sub.src_line_id ORDER BY sub.tax_id, sub.base_line_id
                    ) AS base_amount,

                    ROUND(
                        COALESCE(SIGN(sub.cumulated_base_amount_currency) * sub.total_tax_amount_currency * ABS(sub.cumulated_base_amount_currency) / NULLIF(sub.total_base_amount_currency, 0.0), 0.0),
                        sub.curr_prec
                    )
                    - LAG(ROUND(
                        COALESCE(SIGN(sub.cumulated_base_amount_currency) * sub.total_tax_amount_currency * ABS(sub.cumulated_base_amount_currency) / NULLIF(sub.total_base_amount_currency, 0.0), 0.0),
                        sub.curr_prec
                    ), 1, 0.0)
                    OVER (
                        PARTITION BY sub.tax_line_id, sub.src_line_id ORDER BY sub.tax_id, sub.base_line_id
                    ) AS base_amount_currency
                FROM tax_amount_affecting_base_to_dispatch sub
                JOIN account_move_line tax_line ON
                    tax_line.id = sub.tax_line_id

                /*
                PART 3: In case of the matching failed because the configuration changed or some journal entries
                have been imported, construct a simple mapping as a fallback. This mapping is super naive and only
                build based on the 'tax_ids' and 'tax_line_id' fields, nothing else. Hence, the mapping will not be
                exact but will give an acceptable approximation.

                Skipped if the 'fallback' method parameter is False.
                */
                %(fallback_query)s
            ),


            base_tax_matching_all_amounts AS (

                /*
                Complete base_tax_matching_base_amounts with the tax amounts (prorata):
                base_line_id    tax_line_id     src_line_id     base_amount     tax_amount
                --------------------------------------------------------------------------
                base_line_1     tax_line_1      base_line_1     1000            100
                base_line_1     tax_line_2      base_line_1     1000            (1000 / 1100) * 220 = 200
                base_line_1     tax_line_2      tax_line_1      100             (100 / 1100) * 220 = 20
                base_line_2     tax_line_3      base_line_2     2000            (2000 / 5000) * 500 = 200
                base_line_2     tax_line_4      base_line_2     2000            (2000 / 5500) * 275 = 100
                base_line_2     tax_line_4      tax_line_3      200             (200 / 5500) * 275 = 10
                base_line_3     tax_line_3      base_line_3     3000            (3000 / 5000) * 500 = 300
                base_line_3     tax_line_4      base_line_3     3000            (3000 / 5500) * 275 = 150
                base_line_3     tax_line_4      tax_line_3      300             (300 / 5500) * 275 = 15
                */

                SELECT
                    sub.tax_line_id,
                    sub.base_line_id,
                    sub.src_line_id,

                    tax_line.tax_line_id AS tax_id,
                    tax_line.group_tax_id,
                    tax_line.tax_repartition_line_id,

                    tax_line.company_id,
                    tax_line.display_type AS display_type,
                    comp_curr.id AS company_currency_id,
                    comp_curr.decimal_places AS comp_curr_prec,
                    curr.id AS currency_id,
                    curr.decimal_places AS curr_prec,
                    (
                        tax.tax_exigibility != 'on_payment'
                        OR tax_move.tax_cash_basis_rec_id IS NOT NULL
                        OR tax_move.always_tax_exigible
                    ) AS tax_exigible,
                    base_line.account_id AS base_account_id,

                    sub.base_amount,
                    SUM(
                        CASE WHEN tax.amount_type = 'fixed'
                        THEN CASE WHEN base_line.balance < 0 THEN -1 ELSE 1 END * ABS(COALESCE(base_line.quantity, 1.0))
                        ELSE sub.base_amount
                        END
                    ) OVER (PARTITION BY tax_line.id ORDER BY tax_line.tax_line_id, sub.base_line_id, sub.src_line_id) AS cumulated_base_amount,
                    SUM(
                        CASE WHEN tax.amount_type = 'fixed'
                        THEN CASE WHEN base_line.balance < 0 THEN -1 ELSE 1 END * ABS(COALESCE(base_line.quantity, 1.0))
                        ELSE sub.base_amount
                        END
                    ) OVER (PARTITION BY tax_line.id) AS total_base_amount,
                    tax_line.balance AS total_tax_amount,

                    sub.base_amount_currency,
                    SUM(
                        CASE WHEN tax.amount_type = 'fixed'
                        THEN CASE WHEN base_line.amount_currency < 0 THEN -1 ELSE 1 END * ABS(COALESCE(base_line.quantity, 1.0))
                        ELSE sub.base_amount_currency
                        END
                    ) OVER (PARTITION BY tax_line.id ORDER BY tax_line.tax_line_id, sub.base_line_id, sub.src_line_id) AS cumulated_base_amount_currency,
                    SUM(
                        CASE WHEN tax.amount_type = 'fixed'
                        THEN CASE WHEN base_line.amount_currency < 0 THEN -1 ELSE 1 END * ABS(COALESCE(base_line.quantity, 1.0))
                        ELSE sub.base_amount_currency
                        END
                    ) OVER (PARTITION BY tax_line.id) AS total_base_amount_currency,
                    tax_line.amount_currency AS total_tax_amount_currency

                FROM base_tax_matching_base_amounts sub
                JOIN account_move_line tax_line ON
                    tax_line.id = sub.tax_line_id
                JOIN account_move tax_move ON
                    tax_move.id = tax_line.move_id
                JOIN account_move_line base_line ON
                    base_line.id = sub.base_line_id
                JOIN account_tax tax ON
                    tax.id = tax_line.tax_line_id
                JOIN res_currency curr ON
                    curr.id = tax_line.currency_id
                JOIN res_currency comp_curr ON
                    comp_curr.id = tax_line.company_currency_id

            )


           /* Final select that makes sure to deal with rounding errors, using LAG to dispatch the last cents. */

            SELECT
                sub.tax_line_id || '-' || sub.base_line_id || '-' || sub.src_line_id AS id,

                sub.base_line_id,
                sub.tax_line_id,
                sub.display_type,
                sub.src_line_id,

                sub.tax_id,
                sub.group_tax_id,
                sub.tax_exigible,
                sub.base_account_id,
                sub.tax_repartition_line_id,

                sub.base_amount,
                COALESCE(
                    ROUND(
                        COALESCE(SIGN(sub.cumulated_base_amount) * sub.total_tax_amount * ABS(sub.cumulated_base_amount) / NULLIF(sub.total_base_amount, 0.0), 0.0),
                        sub.comp_curr_prec
                    )
                    - LAG(ROUND(
                        COALESCE(SIGN(sub.cumulated_base_amount) * sub.total_tax_amount * ABS(sub.cumulated_base_amount) / NULLIF(sub.total_base_amount, 0.0), 0.0),
                        sub.comp_curr_prec
                    ), 1, 0.0)
                    OVER (
                        PARTITION BY sub.tax_line_id ORDER BY sub.tax_id, sub.base_line_id
                    ),
                    0.0
                ) AS tax_amount,

                sub.base_amount_currency,
                COALESCE(
                    ROUND(
                        COALESCE(SIGN(sub.cumulated_base_amount_currency) * sub.total_tax_amount_currency * ABS(sub.cumulated_base_amount_currency) / NULLIF(sub.total_base_amount_currency, 0.0), 0.0),
                        sub.curr_prec
                    )
                    - LAG(ROUND(
                        COALESCE(SIGN(sub.cumulated_base_amount_currency) * sub.total_tax_amount_currency * ABS(sub.cumulated_base_amount_currency) / NULLIF(sub.total_base_amount_currency, 0.0), 0.0),
                        sub.curr_prec
                    ), 1, 0.0)
                    OVER (
                        PARTITION BY sub.tax_line_id ORDER BY sub.tax_id, sub.base_line_id
                    ),
                    0.0
                ) AS tax_amount_currency
            FROM base_tax_matching_all_amounts sub
            ''',
            extra_query_base_tax_line_mapping=extra_query_base_tax_line_mapping,
            group_taxes_query=group_taxes_query,
            search_condition=search_condition,
            table_references=table_references,
            fallback_query=fallback_query,
        )
