# -*- coding: utf-8 -*-

from odoo import api, models
from odoo.tools import SQL


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.model
    def _get_query_tax_details_from_domain(self, domain) -> SQL:
        """ Create the tax details sub-query based on the orm domain passed as parameter.

        :param domain:      An orm domain on account.move.line.
        :return:            query as SQL object
        """
        query = self.env['account.move.line']._search(domain)

        return self._get_query_tax_details(query.from_clause, query.where_clause)

    @api.model
    def _get_tax_query_extra_clauses(self) -> tuple[SQL, SQL]:
        #TO OVERRIDE
        return SQL(), SQL()

    @api.model
    def _get_query_tax_details(self, table_references, search_condition):
        """
        Create the tax details sub-query for the given account move lines.

        This query maps tax lines to their corresponding base lines and computes the
        portion of each tax amount attributable to every base line. If a tax line
        matches multiple base lines, the tax amount is distributed proportionally
        according to their base amounts.

        As an example, consider a move with the following accounting lines:

        +-------------+----------------+----------------------+--------+--------+----------------------+
        | Line        | Tax Line       | Tax IDs              | Debit  | Credit | Applies To           |
        +-------------+----------------+----------------------+--------+--------+----------------------+
        | base_line_1 |                | 10_affect_base, 20   | 1000   |        |                      |
        | base_line_2 |                | 10_affect_base, 5    | 2000   |        |                      |
        | base_line_3 |                | 10_affect_base, 5    | 3000   |        |                      |
        | tax_line_1  | 10_affect_base | 20                   |        | 100    | base_line_1          |
        | tax_line_2  | 20             |                      |        | 220    | base_line_1          |
        | tax_line_3  | 10_affect_base | 5                    |        | 500    | base_line_2,3        |
        | tax_line_4  | 5              |                      |        | 275    | base_line_2,3        |
        +-------------+----------------+----------------------+--------+--------+----------------------+
        """

        extra_aml_select_clause, extra_td_where_clause = self._get_tax_query_extra_clauses()
        return SQL("""
            -- filter required AMLs using the provided search condition and select only the required fields.
            WITH filtered_aml_tmp AS (
                SELECT
                    account_move_line.id,
                    account_move_line.move_id,
                    account_move_line.account_id,
                    account_move_line.partner_id,
                    account_move_line.currency_id,
                    account_move_line.company_currency_id,
                    account_move_line.balance,
                    account_move_line.amount_currency,
                    account_move_line.quantity,
                    account_move_line.tax_line_id,
                    account_move_line.group_tax_id,
                    account_move_line.tax_repartition_line_id,
                    account_move_line.analytic_distribution,
                    account_move_line.display_type
                    %(extra_aml_select_clause)s
                FROM %(table_references)s
                WHERE %(search_condition)s
            ),


            -- resolves group taxes into the ordered list of effective tax IDs that affect each line.
            /* Example
            +-------------+----------------------+
            | line_id     | tax_ids              |
            +-------------+----------------------+
            | base_line_1 | {10_affect_base,20}  |
            | base_line_2 | {10_affect_base,5}   |
            | base_line_3 | {10_affect_base,5}   |
            | tax_line_1  | {20}                 |
            | tax_line_3  | {5}                  |
            +-------------+----------------------+
            */
            line_base_affecting_tmp AS (
                SELECT
                    sub.line_id,
                    ARRAY_AGG(
                        sub.tax_id
                        ORDER BY sub.sequence, sub.tax_id
                    ) AS tax_ids
                FROM (
                    SELECT
                        tax_rel.account_move_line_id AS line_id,
                        COALESCE(child_tax.id, tax.id) AS tax_id,
                        tax.sequence AS sequence
                    FROM filtered_aml_tmp f
                    JOIN account_move_line_account_tax_rel tax_rel
                        ON tax_rel.account_move_line_id = f.id
                    JOIN account_tax tax
                        ON tax.id = tax_rel.account_tax_id
                    LEFT JOIN account_tax_filiation_rel fil
                        ON fil.parent_tax = tax.id
                    LEFT JOIN account_tax child_tax
                        ON child_tax.id = fil.child_tax
                        AND child_tax.is_base_affected
                    WHERE tax.is_base_affected
                ) AS sub
                GROUP BY sub.line_id
            ),


            -- prepares the base lines by attaching these tax IDs and building a common join key.
            /* Example
            +-------------+----------------------+----------------+----------------------------------+
            | base_line   | tax_ids              | applied_tax_id | join_key                         |
            +-------------+----------------------+----------------+----------------------------------+
            | base_line_1 | {10_affect_base,20}  | 10_affect_base | move:currency:10_affect_base     |
            | base_line_1 | {10_affect_base,20}  | 20             | move:currency:20                 |
            | base_line_2 | {10_affect_base,5}   | 10_affect_base | move:currency:10_affect_base     |
            | base_line_2 | {10_affect_base,5}   | 5              | move:currency:5                  |
            | base_line_3 | {10_affect_base,5}   | 10_affect_base | move:currency:10_affect_base     |
            | base_line_3 | {10_affect_base,5}   | 5              | move:currency:5                  |
            +-------------+----------------------+----------------+----------------------------------+
            */
            base_lines_tmp AS (
                SELECT
                    f.*, lba.tax_ids, rel.account_tax_id AS applied_tax_id,
                    (f.move_id::text || ':' || f.currency_id::text || ':' || rel.account_tax_id::text) AS join_key
                FROM filtered_aml_tmp f
                JOIN account_move_line_account_tax_rel rel ON f.id = rel.account_move_line_id
                LEFT JOIN line_base_affecting_tmp lba ON lba.line_id = f.id
                WHERE f.tax_repartition_line_id IS NULL
            ),


            -- prepares the tax lines by enriching them with the tax metadata required for matching and building the same join key.
            /* Example
            +------------+---------+------------------+------------------------------+
            | tax_line   | tax_ids | effective_tax_id | join_key                     |
            +------------+---------+------------------+------------------------------+
            | tax_line_1 | {20}    | 10_affect_base   | move:currency:10_affect_base |
            | tax_line_2 |         | 20               | move:currency:20             |
            | tax_line_3 | {5}     | 10_affect_base   | move:currency:10_affect_base |
            | tax_line_4 |         | 5                | move:currency:5              |
            +------------+---------+------------------+------------------------------+
            */
            tax_lines_tmp AS (
                SELECT f.*, tax_rep.tax_id, tax_rep.account_id AS rep_account_id, lba.tax_ids,
                    tax_rep.factor_percent, tax_rep.use_in_tax_closing,
                    COALESCE(f.group_tax_id, f.tax_line_id) AS effective_tax_id,
                    (f.move_id::text || ':' || f.currency_id::text || ':' || COALESCE(f.group_tax_id, f.tax_line_id)::text) AS join_key,
                    tax.amount AS tax_amount_rate,
                    tax.amount_type,
                    tax.tax_exigibility,
                    tax.cash_basis_transition_account_id,
                    tax.analytic,
                    tax.include_base_amount,
                    move.tax_cash_basis_rec_id,
                    move.always_tax_exigible,
                    move.move_type,
                    comp_curr.decimal_places AS comp_curr_prec,
                    curr.decimal_places AS curr_prec,
                    (
                        tax.tax_exigibility != 'on_payment'
                        OR move.tax_cash_basis_rec_id IS NOT NULL
                        OR move.always_tax_exigible
                    ) AS tax_exigible
                FROM filtered_aml_tmp f
                LEFT JOIN line_base_affecting_tmp lba ON lba.line_id = f.id
                JOIN account_tax_repartition_line tax_rep ON tax_rep.id = f.tax_repartition_line_id
                JOIN account_tax tax ON tax.id = f.tax_line_id
                JOIN account_move move ON move.id = f.move_id
                JOIN res_currency comp_curr ON comp_curr.id = f.company_currency_id
                JOIN res_currency curr ON curr.id = f.currency_id
            ),


            /* resolve base-to-tax line mapping after applying all matching conditions,
            allowing the mapping to be reused by the remaining query.
            Additionally, it determines whether each tax line has at least one valid base-line match.
            If not, the query falls back to using all candidate mappings for that tax line,
            providing an approximate mapping instead of returning no result. */
            /* Example
            +-------------+-------------+-------------+-------------+------------------+------------+--------------------+
            | base_line   | tax_line    | src_line    | base_amount | total_tax_amount | is_matched | tax_line_has_match |
            +-------------+-------------+-------------+-------------+------------------+------------+--------------------+
            | base_line_1 | tax_line_1  | base_line_1 | 1000.00     | 100.00           | t          | t                  |
            | base_line_2 | tax_line_1  | base_line_2 | 2000.00     | 100.00           | f          | t                  |
            | base_line_3 | tax_line_1  | base_line_3 | 3000.00     | 100.00           | f          | t                  |
            | base_line_1 | tax_line_2  | base_line_1 | 1000.00     | 220.00           | t          | t                  |
            | base_line_1 | tax_line_3  | base_line_1 | 1000.00     | 500.00           | f          | t                  |
            | base_line_2 | tax_line_3  | base_line_2 | 2000.00     | 500.00           | t          | t                  |
            | base_line_3 | tax_line_3  | base_line_3 | 3000.00     | 500.00           | t          | t                  |
            | base_line_2 | tax_line_4  | base_line_2 | 2000.00     | 275.00           | t          | t                  |
            | base_line_3 | tax_line_4  | base_line_3 | 3000.00     | 275.00           | t          | t                  |
            +-------------+-------------+-------------+-------------+------------------+------------+--------------------+
            */
            base_lines_mapping_tmp_with_fallback_tmp AS (
                SELECT
                    base_lines_mapping_tmp.*,
                    BOOL_OR(is_matched) OVER (PARTITION BY tax_line_id) AS tax_line_has_match
                FROM (
                    SELECT
                        base_line.id AS base_line_id,
                        tax_line.id AS tax_line_id,
                        base_line.id AS src_line_id,
                        base_line.quantity AS base_quantity,
                        base_line.balance AS base_amount,
                        base_line.amount_currency AS base_amount_currency,
                        tax_line.balance AS total_tax_amount,
                        tax_line.amount_currency AS total_tax_amount_currency,
                        tax_line.tax_line_id AS tax_id,
                        tax_line.effective_tax_id,
                        tax_line.tax_repartition_line_id,
                        base_line.account_id AS base_account_id,
                        tax_line.comp_curr_prec,
                        tax_line.curr_prec,
                        tax_line.amount_type,
                        tax_line.display_type,
                        tax_line.tax_exigible,
                        COALESCE(
                            COALESCE(base_line.partner_id, 0) = COALESCE(tax_line.partner_id, 0)
                            AND (
                                tax_line.move_type != 'entry'
                                OR (tax_line.tax_exigibility = 'on_payment' AND tax_line.cash_basis_transition_account_id IS NOT NULL)
                                OR sign(base_line.balance) = sign(tax_line.balance * tax_line.tax_amount_rate * tax_line.factor_percent)
                            ) AND (
                                COALESCE(tax_line.rep_account_id, base_line.account_id) = tax_line.account_id
                                OR (tax_line.tax_exigibility = 'on_payment' AND tax_line.cash_basis_transition_account_id IS NOT NULL)
                            ) AND (
                                (tax_line.analytic IS NOT TRUE AND tax_line.use_in_tax_closing IS TRUE)
                                OR (base_line.analytic_distribution IS NULL AND tax_line.analytic_distribution IS NULL)
                                OR base_line.analytic_distribution = tax_line.analytic_distribution
                            ) AND (
                                NOT tax_line.include_base_amount
                                OR base_line.tax_ids[
                                    ARRAY_LENGTH(base_line.tax_ids, 1) - COALESCE(ARRAY_LENGTH(tax_line.tax_ids, 1), 0)
                                    : ARRAY_LENGTH(base_line.tax_ids, 1)
                                ] = ARRAY[tax_line.tax_line_id] || COALESCE(tax_line.tax_ids, ARRAY[]::int[])
                            ) %(extra_td_where_clause)s,
                            FALSE
                        ) AS is_matched
                    FROM tax_lines_tmp tax_line
                    JOIN base_lines_tmp base_line
                        ON base_line.join_key = tax_line.join_key
                ) base_lines_mapping_tmp
            ),


            -- stores an unnested representation of ``tax_ids`` to provide an efficient row-based lookup for cascading tax resolution.
            /* Example
            +------------------+--------+
            | source_tax_line  | tax_id |
            +------------------+--------+
            | tax_line_1       | 20     |
            | tax_line_3       | 5      |
            +------------------+--------+
            */
            tax_lines_tax_ids_tmp AS (
                SELECT id AS source_tax_line_id, unnest(tax_ids) AS tax_id
                FROM tax_lines_tmp
                WHERE tax_ids IS NOT NULL
            ),


            -- dispatch tax lines that themselves affect the base of OTHER taxes (include_base_amount = true) onto the tax lines that stack on top of them.
            /* Example
            +-------------+-------------+-------------+-------------+------------------+
            | base_line   | tax_line    | src_line    | base_amount | total_tax_amount |
            +-------------+-------------+-------------+-------------+------------------+
            | base_line_1 | tax_line_2  | tax_line_1  | 100.00      | 220.00           |
            | base_line_2 | tax_line_4  | tax_line_3  | 200.00      | 275.00           |
            | base_line_3 | tax_line_4  | tax_line_3  | 300.00      | 275.00           |
            +-------------+-------------+-------------+-------------+------------------+
            */
            tax_lines_mapping AS (
                SELECT
                    base_line_id, tax_line_id, src_line_id, base_quantity,
                    ROUND(
                        COALESCE(SIGN(cumulative_base_amount) * source_total_tax_amount * ABS(cumulative_base_amount) / NULLIF(total_base_amount, 0), 0),
                        comp_curr_prec
                    ) - LAG(ROUND(
                        COALESCE(SIGN(cumulative_base_amount) * source_total_tax_amount * ABS(cumulative_base_amount) / NULLIF(total_base_amount, 0), 0),
                        comp_curr_prec
                    ), 1, 0) OVER (PARTITION BY tax_line_id, src_line_id ORDER BY tax_id, base_line_id) AS base_amount,

                    ROUND(
                        COALESCE(SIGN(cumulative_base_amount_currency) * source_total_tax_amount_currency * ABS(cumulative_base_amount_currency) / NULLIF(total_base_amount_currency, 0), 0),
                        curr_prec
                    ) - LAG(ROUND(
                        COALESCE(SIGN(cumulative_base_amount_currency) * source_total_tax_amount_currency * ABS(cumulative_base_amount_currency) / NULLIF(total_base_amount_currency, 0), 0),
                        curr_prec
                    ), 1, 0) OVER (PARTITION BY tax_line_id, src_line_id ORDER BY tax_id, base_line_id) AS base_amount_currency,

                    target_total_tax_amount AS total_tax_amount,
                    target_total_tax_amount_currency AS total_tax_amount_currency,
                    tax_id, effective_tax_id, tax_repartition_line_id,
                    base_account_id, comp_curr_prec, curr_prec, amount_type, display_type, tax_exigible
                FROM (
                    SELECT
                        base_line.base_line_id,
                        target_tax_line.tax_line_id,
                        source_tax_line.id AS src_line_id,
                        base_line.base_quantity,
                        source_tax_line.balance AS source_total_tax_amount,
                        source_tax_line.amount_currency AS source_total_tax_amount_currency,
                        target_tax_line.total_tax_amount AS target_total_tax_amount,
                        target_tax_line.total_tax_amount_currency AS target_total_tax_amount_currency,
                        target_tax_line.tax_id,
                        target_tax_line.effective_tax_id,
                        target_tax_line.tax_repartition_line_id,
                        target_tax_line.base_account_id,
                        target_tax_line.comp_curr_prec,
                        target_tax_line.curr_prec,
                        target_tax_line.amount_type,
                        target_tax_line.display_type,
                        target_tax_line.tax_exigible,

                        SUM(
                            CASE WHEN target_tax_line.amount_type = 'fixed'
                                THEN CASE WHEN base_line.base_amount < 0 THEN -1 ELSE 1 END * ABS(COALESCE(base_line.base_quantity, 1.0))
                                ELSE base_line.base_amount
                            END
                        ) OVER (PARTITION BY target_tax_line.tax_line_id, source_tax_line.id ORDER BY target_tax_line.tax_id, base_line.base_line_id) AS cumulative_base_amount,
                        SUM(
                            CASE WHEN target_tax_line.amount_type = 'fixed'
                                THEN CASE WHEN base_line.base_amount < 0 THEN -1 ELSE 1 END * ABS(COALESCE(base_line.base_quantity, 1.0))
                                ELSE base_line.base_amount
                            END
                        ) OVER (PARTITION BY target_tax_line.tax_line_id, source_tax_line.id) AS total_base_amount,

                        SUM(
                            CASE WHEN target_tax_line.amount_type = 'fixed'
                                THEN CASE WHEN base_line.base_amount_currency < 0 THEN -1 ELSE 1 END * ABS(COALESCE(base_line.base_quantity, 1.0))
                                ELSE base_line.base_amount_currency
                            END
                        ) OVER (PARTITION BY target_tax_line.tax_line_id, source_tax_line.id ORDER BY target_tax_line.tax_id, base_line.base_line_id) AS cumulative_base_amount_currency,
                        SUM(
                            CASE WHEN target_tax_line.amount_type = 'fixed'
                                THEN CASE WHEN base_line.base_amount_currency < 0 THEN -1 ELSE 1 END * ABS(COALESCE(base_line.base_quantity, 1.0))
                                ELSE base_line.base_amount_currency
                            END
                        ) OVER (PARTITION BY target_tax_line.tax_line_id, source_tax_line.id) AS total_base_amount_currency

                    FROM tax_lines_tmp source_tax_line
                    JOIN base_lines_mapping_tmp_with_fallback_tmp base_line
                        ON base_line.tax_line_id = source_tax_line.id
                        AND base_line.is_matched                                  -- to avoid fallback lines
                    JOIN base_lines_mapping_tmp_with_fallback_tmp target_tax_line
                        ON target_tax_line.base_line_id = base_line.base_line_id
                        AND target_tax_line.tax_line_id != source_tax_line.id
                        AND target_tax_line.is_matched                            -- to avoid fallback lines
                    JOIN tax_lines_tax_ids_tmp bti
                        ON bti.source_tax_line_id = source_tax_line.id
                        AND bti.tax_id = target_tax_line.tax_id
                    WHERE source_tax_line.include_base_amount
                ) source_target_tax_lines_mapping
            ),


            -- union the two sources of base<->tax pairs (direct + fallback match, cascade-dispatched match)
            -- and compute, the cumulative/total base amounts needed for the final proportional split below.
            /* Example
            +-------------+-------------+-------------+-------------+------------------+
            | base_line   | tax_line    | src_line    | base_amount | total_tax_amount |
            +-------------+-------------+-------------+-------------+------------------+
            | base_line_1 | tax_line_1  | base_line_1 | 1000.00     | 100.00           |
            | base_line_1 | tax_line_2  | base_line_1 | 1000.00     | 220.00           |
            | base_line_1 | tax_line_2  | tax_line_1  | 100.00      | 220.00           |
            | base_line_2 | tax_line_3  | base_line_2 | 2000.00     | 500.00           |
            | base_line_3 | tax_line_3  | base_line_3 | 3000.00     | 500.00           |
            | base_line_2 | tax_line_4  | base_line_2 | 2000.00     | 275.00           |
            | base_line_2 | tax_line_4  | tax_line_3  | 200.00      | 275.00           |
            | base_line_3 | tax_line_4  | base_line_3 | 3000.00     | 275.00           |
            | base_line_3 | tax_line_4  | tax_line_3  | 300.00      | 275.00           |
            +-------------+-------------+-------------+-------------+------------------+
            */
            tax_data AS (
                SELECT
                    base_line_id, tax_line_id, src_line_id,
                    base_amount, base_amount_currency,
                    total_tax_amount, total_tax_amount_currency,
                    tax_repartition_line_id, tax_id, effective_tax_id, display_type,
                    base_account_id, comp_curr_prec, curr_prec, tax_exigible,
                    SUM(
                        CASE WHEN amount_type = 'fixed'
                            THEN CASE WHEN base_amount < 0 THEN -1 ELSE 1 END * ABS(COALESCE(base_quantity, 1.0))
                            ELSE base_amount
                        END
                    ) OVER (PARTITION BY tax_line_id ORDER BY tax_id, base_line_id, src_line_id) AS cumulated_base_amount,
                    SUM(
                        CASE WHEN amount_type = 'fixed'
                            THEN CASE WHEN base_amount < 0 THEN -1 ELSE 1 END * ABS(COALESCE(base_quantity, 1.0))
                            ELSE base_amount
                        END
                    ) OVER (PARTITION BY tax_line_id) AS total_base_amount,

                    SUM(
                        CASE WHEN amount_type = 'fixed'
                            THEN CASE WHEN base_amount_currency < 0 THEN -1 ELSE 1 END * ABS(COALESCE(base_quantity, 1.0))
                            ELSE base_amount_currency
                        END
                    ) OVER (PARTITION BY tax_line_id ORDER BY tax_id, base_line_id, src_line_id) AS cumulated_base_amount_currency,
                    SUM(
                        CASE WHEN amount_type = 'fixed'
                            THEN CASE WHEN base_amount_currency < 0 THEN -1 ELSE 1 END * ABS(COALESCE(base_quantity, 1.0))
                            ELSE base_amount_currency
                        END
                    ) OVER (PARTITION BY tax_line_id) AS total_base_amount_currency
                FROM (
                    -- matched base_line <-> tax_line
                    SELECT base_line_id, tax_line_id, src_line_id,
                        base_amount, base_amount_currency,
                        total_tax_amount, total_tax_amount_currency,
                        base_quantity, tax_id, effective_tax_id, tax_repartition_line_id,
                        base_account_id, comp_curr_prec, curr_prec, amount_type, display_type, tax_exigible
                    FROM base_lines_mapping_tmp_with_fallback_tmp
                    WHERE is_matched

                    UNION ALL

                    -- fallback lines
                    SELECT base_line_id, tax_line_id, src_line_id,
                        base_amount, base_amount_currency,
                        total_tax_amount, total_tax_amount_currency,
                        base_quantity, tax_id, effective_tax_id, tax_repartition_line_id,
                        base_account_id, comp_curr_prec, curr_prec, amount_type, display_type, tax_exigible
                    FROM base_lines_mapping_tmp_with_fallback_tmp
                    WHERE NOT tax_line_has_match

                    UNION ALL

                    -- matched tax_line <-> tax_line
                    SELECT base_line_id, tax_line_id, src_line_id,
                        base_amount, base_amount_currency,
                        total_tax_amount, total_tax_amount_currency,
                        base_quantity, tax_id, effective_tax_id, tax_repartition_line_id,
                        base_account_id, comp_curr_prec, curr_prec, amount_type, display_type, tax_exigible
                    FROM tax_lines_mapping
                ) matched_tax_data
            )

            -- Final select that makes sure to deal with rounding errors, using LAG to dispatch the last cents.
            /* Final Result
            +-------------+-------------+-------------+-------------+------------+
            | base_line   | tax_line    | src_line    | base_amount | tax_amount |
            +-------------+-------------+-------------+-------------+------------+
            | base_line_1 | tax_line_1  | base_line_1 | 1000.00     | 100.00     |
            | base_line_1 | tax_line_2  | base_line_1 | 1000.00     | 200.00     |
            | base_line_1 | tax_line_2  | tax_line_1  | 100.00      |  20.00     |
            | base_line_2 | tax_line_3  | base_line_2 | 2000.00     | 200.00     |
            | base_line_3 | tax_line_3  | base_line_3 | 3000.00     | 300.00     |
            | base_line_2 | tax_line_4  | base_line_2 | 2000.00     | 100.00     |
            | base_line_2 | tax_line_4  | tax_line_3  | 200.00      |  10.00     |
            | base_line_3 | tax_line_4  | base_line_3 | 3000.00     | 150.00     |
            | base_line_3 | tax_line_4  | tax_line_3  | 300.00      |  15.00     |
            +-------------+-------------+-------------+-------------+------------+
            */
            SELECT
                base_line_id, tax_line_id, src_line_id, base_amount, base_amount_currency,

                ROUND(
                    COALESCE(SIGN(cumulated_base_amount) * total_tax_amount * ABS(cumulated_base_amount) / NULLIF(total_base_amount, 0), 0),
                    comp_curr_prec
                ) - LAG(
                    ROUND(
                        COALESCE(SIGN(cumulated_base_amount) * total_tax_amount * ABS(cumulated_base_amount) / NULLIF(total_base_amount, 0), 0),
                        comp_curr_prec
                    ), 1, 0
                ) OVER (PARTITION BY tax_line_id ORDER BY tax_id, base_line_id, src_line_id) AS tax_amount,

                ROUND(
                    COALESCE(SIGN(cumulated_base_amount_currency) * total_tax_amount_currency * ABS(cumulated_base_amount_currency) / NULLIF(total_base_amount_currency, 0), 0),
                    curr_prec
                ) - LAG(
                    ROUND(
                        COALESCE(SIGN(cumulated_base_amount_currency) * total_tax_amount_currency * ABS(cumulated_base_amount_currency) / NULLIF(total_base_amount_currency, 0), 0),
                        curr_prec
                    ), 1, 0
                ) OVER (PARTITION BY tax_line_id ORDER BY tax_id, base_line_id, src_line_id) AS tax_amount_currency,

                tax_id, display_type, effective_tax_id, tax_repartition_line_id, base_account_id, tax_exigible
            FROM tax_data
            ORDER BY tax_line_id, base_line_id, src_line_id
        """,
        extra_aml_select_clause=extra_aml_select_clause,
        table_references=table_references,
        search_condition=search_condition,
        extra_td_where_clause=extra_td_where_clause,
        )
