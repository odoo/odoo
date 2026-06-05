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

        Example:

            Move lines:
                Name            Balance     Tax
                ---------------------------------
                base_line_1      100        VAT 10%
                base_line_2      200        VAT 10%
                tax_line         30

            Result:
                base_line_id    tax_line_id    base_amount    tax_amount
                --------------------------------------------------------
                base_line_1     tax_line       100            10
                base_line_2     tax_line       200            20
        """

        def _prepare_filtered_aml_tmp_table(extra_aml_select_clause, table_references, search_condition):
            """
            Prepare the temporary table containing the account move lines relevant to the
            tax mapping query.

            The table materializes the filtered dataset once so that all subsequent
            preparation and matching steps operate on the same input without repeatedly
            filtering ``account_move_line``.
            """
            return SQL("""
                CREATE TEMPORARY TABLE filtered_aml_tmp ON COMMIT DROP AS
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
                WHERE %(search_condition)s;
                ANALYZE filtered_aml_tmp;
                """,
                extra_aml_select_clause=extra_aml_select_clause,
                table_references=table_references,
                search_condition=search_condition
            )

        def _prepare_tax_matching_data_tables():
            """
            Prepare the temporary tables used to match base lines with tax lines.

            ``line_base_affecting_tmp`` resolves group taxes into the ordered list of
            effective tax IDs that affect each base line.

            ``base_lines_tmp`` prepares the base lines by attaching these tax IDs and
            building a common join key.

            ``tax_lines_tmp`` prepares the tax lines by enriching them with the tax
            metadata required for matching and building the same join key.
            """
            return SQL("""
                CREATE TEMPORARY TABLE line_base_affecting_tmp ON COMMIT DROP AS
                SELECT
                    tax_rel.account_move_line_id AS line_id,
                    ARRAY_AGG(
                        COALESCE(fil.child_tax, tax.id)
                        ORDER BY tax.sequence, COALESCE(fil.child_tax, tax.id)
                    ) AS tax_ids
                FROM filtered_aml_tmp f
                JOIN account_move_line_account_tax_rel tax_rel
                    ON tax_rel.account_move_line_id = f.id
                JOIN account_tax tax
                    ON tax.id = tax_rel.account_tax_id
                LEFT JOIN account_tax_filiation_rel fil
                    ON fil.parent_tax = tax.id
                WHERE tax.is_base_affected
                GROUP BY tax_rel.account_move_line_id;
                ANALYZE line_base_affecting_tmp;

                -- filter out base_lines, create a single join key
                CREATE TEMPORARY TABLE base_lines_tmp ON COMMIT DROP AS
                SELECT
                    f.*, lba.tax_ids, rel.account_tax_id AS applied_tax_id,
                    (f.move_id::text || ':' || f.currency_id::text || ':' || rel.account_tax_id::text) AS join_key
                FROM filtered_aml_tmp f
                JOIN account_move_line_account_tax_rel rel ON f.id = rel.account_move_line_id
                LEFT JOIN line_base_affecting_tmp lba ON lba.line_id = f.id
                WHERE f.tax_repartition_line_id IS NULL;
                ANALYZE base_lines_tmp;

                -- filter out tax_lines, create a single join key, fetch tax/currency data
                CREATE TEMPORARY TABLE tax_lines_tmp ON COMMIT DROP AS
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
                JOIN res_currency curr ON curr.id = f.currency_id;
                ANALYZE tax_lines_tmp;
            """)

        def _prepare_matching_tables(extra_td_where_clause):
            """
            Prepare the temporary tables required for tax line matching.

            ``base_lines_mapping_tmp_with_fallback_tmp`` stores the resolved base-to-tax line mapping after
            applying all matching conditions, allowing the mapping to be reused by the
            remaining query. Additionally, it determines whether each tax line has at least one valid base-line match.
            If not, the query falls back to using all candidate mappings for that tax line,
            providing an approximate mapping instead of returning no result.

            ``tax_lines_tax_ids_tmp`` stores an unnested representation of ``tax_ids`` to
            provide an efficient row-based lookup for cascading tax resolution.
            """
            return SQL("""
                CREATE TEMPORARY TABLE base_lines_mapping_tmp_with_fallback_tmp ON COMMIT DROP AS
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
                ) base_lines_mapping_tmp;
                ANALYZE base_lines_mapping_tmp_with_fallback_tmp;

                CREATE TEMPORARY TABLE tax_lines_tax_ids_tmp ON COMMIT DROP AS
                SELECT id AS source_tax_line_id, unnest(tax_ids) AS tax_id
                FROM tax_lines_tmp
                WHERE tax_ids IS NOT NULL;
                ANALYZE tax_lines_tax_ids_tmp;
                """,
                extra_td_where_clause=extra_td_where_clause,
            )

        extra_aml_select_clause, extra_td_where_clause = self._get_tax_query_extra_clauses()
        # Prepare temporary tables
        self.env.cr.execute(SQL("""
            DROP TABLE IF EXISTS
                filtered_aml_tmp,
                line_base_affecting_tmp,
                base_lines_tmp,
                tax_lines_tmp,
                base_lines_mapping_tmp_with_fallback_tmp,
                tax_lines_tax_ids_tmp;

            %(filtered_aml_tmp_table)s
            %(tax_matching_data_tables)s
            %(matching_tables)s
            """,
            filtered_aml_tmp_table=_prepare_filtered_aml_tmp_table(extra_aml_select_clause, table_references, search_condition),
            tax_matching_data_tables=_prepare_tax_matching_data_tables(),
            matching_tables=_prepare_matching_tables(extra_td_where_clause),
        ))

        return SQL("""
            -- dispatch tax lines that themselves affect the base of OTHER taxes (include_base_amount = true) onto the tax lines that stack on top of them.
            WITH tax_lines_mapping AS (
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
        """)
