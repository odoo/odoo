# -*- coding: utf-8 -*-

from odoo import api, models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.model
    def _get_query_tax_details_from_domain(self, domain, fallback=True):
        """ Create the tax details sub-query based on the orm domain passed as parameter.

        :param domain:      An orm domain on account.move.line.
        :param fallback:    Fallback on an approximated mapping if the mapping failed.
        :return:            A tuple <query, params>.
        """
        self.env['account.move.line'].check_access_rights('read')

        query = self.env['account.move.line']._where_calc(domain)

        # Wrap the query with 'company_id IN (...)' to avoid bypassing company access rights.
        self.env['account.move.line']._apply_ir_rules(query)

        tables, where_clause, where_params = query.get_sql()
        return self._get_query_tax_details(tables, where_clause, where_params, fallback=fallback)

    @api.model
    def _get_query_tax_details(self, tables, where_clause, where_params, fallback=True):
        """ Create the tax details sub-query based on the orm domain passed as parameter.

        :param tables:          The 'tables' query to inject after the FROM.
        :param where_clause:    The 'where_clause' query computed based on an orm domain.
        :param where_params:    The params to fill the 'where_clause' query.
        :param fallback:        Fallback on an approximated mapping if the mapping failed.
        :return:                A tuple <query, params>.
        """
        group_taxes = self.env['account.tax'].search([('amount_type', '=', 'group')])

        group_taxes_query_list = []
        group_taxes_params = []
        for group_tax in group_taxes:
            children_taxes = group_tax.children_tax_ids
            if not children_taxes:
                continue

            children_taxes_in_query = ','.join('%s' for dummy in children_taxes)
            group_taxes_query_list.append(f'WHEN tax.id = %s THEN ARRAY[{children_taxes_in_query}]')
            group_taxes_params.append(group_tax.id)
            group_taxes_params.extend(children_taxes.ids)

        if group_taxes_query_list:
            group_taxes_query = f'''UNNEST(CASE {' '.join(group_taxes_query_list)} ELSE ARRAY[tax.id] END)'''
        else:
            group_taxes_query = 'tax.id'

        if fallback:
            fallback_query = f'''
                UNION ALL

                SELECT
                    account_move_line.id AS tax_line_id,
                    base_line.id AS base_line_id,
                    base_line.id AS src_line_id,
                    base_line.balance AS base_amount,
                    base_line.amount_currency AS base_amount_currency
                FROM {tables}
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
                AND {where_clause}
            '''
            fallback_params = where_params
        else:
            fallback_query = ''
            fallback_params = []

        return f'''
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

            WITH affecting_base_tax_ids AS (

                /*
                This CTE builds a reference table based on the tax_ids field, with the following changes:
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

                SELECT
                    sub.line_id AS id,
                    ARRAY_AGG(sub.tax_id ORDER BY sub.sequence, sub.tax_id) AS tax_ids
                FROM (
                    SELECT
                        tax_rel.account_move_line_id AS line_id,
                        {group_taxes_query} AS tax_id,
                        tax.sequence
                    FROM {tables}
                    JOIN account_move_line_account_tax_rel tax_rel ON account_move_line.id = tax_rel.account_move_line_id
                    JOIN account_tax tax ON tax.id = tax_rel.account_tax_id
                    WHERE tax.is_base_affected
                    AND {where_clause}
                ) AS sub
                GROUP BY sub.line_id
            ),

            base_tax_line_mapping AS (

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

                FROM {tables}
                JOIN account_tax_repartition_line tax_rep ON
                    tax_rep.id = account_move_line.tax_repartition_line_id
                JOIN account_tax tax ON
                    tax.id = account_move_line.tax_line_id
                JOIN res_currency curr ON
                    curr.id = account_move_line.currency_id
                JOIN res_currency comp_curr ON
                    comp_curr.id = account_move_line.company_currency_id
                JOIN account_move_line_account_tax_rel tax_rel ON
                    tax_rel.account_tax_id = COALESCE(account_move_line.group_tax_id, account_move_line.tax_line_id)
                JOIN account_move_line base_line ON
                    base_line.id = tax_rel.account_move_line_id
                    AND base_line.tax_repartition_line_id IS NULL
                    AND base_line.move_id = account_move_line.move_id
                    AND COALESCE(base_line.partner_id, 0) = COALESCE(account_move_line.partner_id, 0)
                    AND base_line.currency_id = account_move_line.currency_id
                    AND (
                        COALESCE(tax_rep.account_id, base_line.account_id) = account_move_line.account_id
                        OR (tax.tax_exigibility = 'on_payment' AND tax.cash_basis_transition_account_id IS NOT NULL)
                    )
                    AND (
                        NOT tax.analytic
                        OR (base_line.analytic_account_id IS NULL AND account_move_line.analytic_account_id IS NULL)
                        OR base_line.analytic_account_id = account_move_line.analytic_account_id
                    )
                LEFT JOIN affecting_base_tax_ids tax_line_tax_ids ON tax_line_tax_ids.id = account_move_line.id
                JOIN affecting_base_tax_ids base_line_tax_ids ON base_line_tax_ids.id = base_line.id
                WHERE account_move_line.tax_repartition_line_id IS NOT NULL
                    AND {where_clause}
                    AND (
                        -- keeping only the rows from affecting_base_tax_lines that end with the same taxes applied (see comment in affecting_base_tax_ids)
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

                FROM {tables}
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
                WHERE {where_clause}
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
                        COALESCE(sub.total_tax_amount * ABS(sub.cumulated_base_amount) / ABS(NULLIF(sub.total_base_amount, 0.0)), 0.0),
                        sub.comp_curr_prec
                    )
                    - LAG(ROUND(
                        COALESCE(sub.total_tax_amount * ABS(sub.cumulated_base_amount) / ABS(NULLIF(sub.total_base_amount, 0.0)), 0.0),
                        sub.comp_curr_prec
                    ), 1, 0.0)
                    OVER (
                        PARTITION BY sub.tax_line_id, sub.src_line_id ORDER BY sub.tax_id, sub.base_line_id
                    ) AS base_amount,

                    ROUND(
                        COALESCE(sub.total_tax_amount_currency * ABS(sub.cumulated_base_amount_currency) / ABS(NULLIF(sub.total_base_amount_currency, 0.0)), 0.0),
                        sub.curr_prec
                    )
                    - LAG(ROUND(
                        COALESCE(sub.total_tax_amount_currency * ABS(sub.cumulated_base_amount_currency) / ABS(NULLIF(sub.total_base_amount_currency, 0.0)), 0.0),
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
                {fallback_query}
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
                sub.src_line_id,

                sub.tax_id,
                sub.group_tax_id,
                sub.tax_exigible,
                sub.base_account_id,
                sub.tax_repartition_line_id,

                sub.base_amount,
                ROUND(
                    COALESCE(sub.total_tax_amount * ABS(sub.cumulated_base_amount) / ABS(NULLIF(sub.total_base_amount, 0.0)), 0.0),
                    sub.comp_curr_prec
                )
                - LAG(ROUND(
                    COALESCE(sub.total_tax_amount * ABS(sub.cumulated_base_amount) / ABS(NULLIF(sub.total_base_amount, 0.0)), 0.0),
                    sub.comp_curr_prec
                ), 1, 0.0)
                OVER (
                    PARTITION BY sub.tax_line_id ORDER BY sub.tax_id, sub.base_line_id
                ) AS tax_amount,

                sub.base_amount_currency,
                ROUND(
                    COALESCE(sub.total_tax_amount_currency * ABS(sub.cumulated_base_amount_currency) / ABS(NULLIF(sub.total_base_amount_currency, 0.0)), 0.0),
                    sub.curr_prec
                )
                - LAG(ROUND(
                    COALESCE(sub.total_tax_amount_currency * ABS(sub.cumulated_base_amount_currency) / ABS(NULLIF(sub.total_base_amount_currency, 0.0)), 0.0),
                    sub.curr_prec
                ), 1, 0.0)
                OVER (
                    PARTITION BY sub.tax_line_id ORDER BY sub.tax_id, sub.base_line_id
                ) AS tax_amount_currency
            FROM base_tax_matching_all_amounts sub
        ''', group_taxes_params + where_params + where_params + where_params + fallback_params
