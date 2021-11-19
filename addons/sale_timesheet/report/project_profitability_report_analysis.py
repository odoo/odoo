# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, tools


class ProfitabilityAnalysis(models.Model):

    _name = "project.profitability.report"
    _description = "Project Profitability Report"
    _order = 'project_id'
    _auto = False

    project_id = fields.Many2one('project.project', string='Project', readonly=True)
    # cost
    timesheet_unit_amount = fields.Float("Timesheet Duration", digits=(16, 2), readonly=True, group_operator="sum")
    timesheet_cost = fields.Float("Timesheet Cost", digits=(16, 2), readonly=True, group_operator="sum")
    expense_cost = fields.Float("Other Costs", digits=(16, 2), readonly=True, group_operator="sum")

    amount_untaxed_to_invoice = fields.Float("Amount to Invoice", digits=(16, 2), readonly=True, group_operator="sum")
    amount_untaxed_invoiced = fields.Float("Amount Invoiced", digits=(16, 2), readonly=True, group_operator="sum")
    expense_amount_untaxed_to_invoice = fields.Float("Amount to Re-invoice", digits=(16, 2), readonly=True, group_operator="sum")
    expense_amount_untaxed_invoiced = fields.Float("Amount Re-invoiced", digits=(16, 2), readonly=True, group_operator="sum")
    other_revenues = fields.Float("Other Revenues", digits=(16, 2), readonly=True, group_operator="sum",
                                  help="All revenues that are not from timesheets and that are linked to the analytic account of the project.")

    _depends = {
        'sale.order.line': [
            'order_id',
            'invoice_status',
            'price_reduce',
            'product_id',
            'qty_invoiced',
            'untaxed_amount_invoiced',
            'untaxed_amount_to_invoice',
            'currency_id',
            'company_id',
            'is_downpayment',
            'project_id',
            'task_id',
            'qty_delivered_method',
        ],
        'sale.order': [
            'currency_id',
            'analytic_account_id',
            'order_line',
            'invoice_status',
            'amount_untaxed',
            'currency_rate',
            'company_id',
            'project_id',
        ],
    }

    def init(self):
        tools.drop_view_if_exists(self._cr, self._table)
        query = """
            CREATE VIEW %s AS (
                -- Get the timesheet costs
                SELECT
                    ROW_NUMBER() OVER () * 10 + 1 AS id,
                    P.id AS project_id,
                    SUM(TS.unit_amount) AS timesheet_unit_amount,
                    SUM(TS.amount) AS timesheet_cost,
                    0.0 AS other_revenues,
                    0.0 AS expense_cost,
                    0.0 AS expense_amount_untaxed_to_invoice,
                    0.0 AS expense_amount_untaxed_invoiced,
                    0.0 AS amount_untaxed_to_invoice,
                    0.0 AS amount_untaxed_invoiced
                FROM project_project P
                    JOIN account_analytic_line TS ON TS.project_id = P.id
                WHERE P.active = 't' AND P.allow_timesheets = 't'
                GROUP BY P.id

                UNION ALL

                -- Get the other revenues (products that are not services)
                SELECT
                    ROW_NUMBER() OVER () * 10 + 2 AS id,
                    P.id AS project_id,
                    0.0 AS timesheet_unit_amount,
                    0.0 AS timesheet_cost,
                    SUM(AAL.amount) AS other_revenues,
                    0.0 AS expense_cost,
                    0.0 AS expense_amount_untaxed_to_invoice,
                    0.0 AS expense_amount_untaxed_invoiced,
                    0.0 AS amount_untaxed_to_invoice,
                    0.0 AS amount_untaxed_invoiced
                FROM project_project P
                    JOIN account_analytic_account AA ON P.analytic_account_id = AA.id
                    JOIN account_analytic_line AAL ON AAL.account_id = AA.id
                    LEFT JOIN sale_order_line_invoice_rel SOINV ON SOINV.invoice_line_id = AAL.move_id
                    LEFT JOIN sale_order_line SOL ON SOINV.order_line_id = SOL.id
                    LEFT JOIN account_move_line AML ON AAL.move_id = AML.id
                                                   AND AML.parent_state = 'posted'
                                                   AND AML.exclude_from_invoice_tab = 'f'
                    -- Check if it's not a Credit Note for a Vendor Bill
                    LEFT JOIN account_move RBILL ON RBILL.id = AML.move_id
                    LEFT JOIN account_move_line BILLL ON BILLL.move_id = RBILL.reversed_entry_id
                                                     AND BILLL.parent_state = 'posted'
                                                     AND BILLL.exclude_from_invoice_tab = 'f'
                                                     AND BILLL.product_id = AML.product_id
                    -- Check if it's not an Invoice reversed by a Credit Note
                    LEFT JOIN account_move RINV ON RINV.reversed_entry_id = AML.move_id
                    LEFT JOIN account_move_line RINVL ON RINVL.move_id = RINV.id
                                                     AND RINVL.parent_state = 'posted'
                                                     AND RINVL.exclude_from_invoice_tab = 'f'
                                                     AND RINVL.product_id = AML.product_id
                WHERE AAL.amount > 0.0 AND AAL.project_id IS NULL AND P.active = 't'
                    AND P.allow_timesheets = 't'
                    AND BILLL.id IS NULL
                    AND RINVL.id IS NULL
                    AND (SOL.id IS NULL
                        OR (SOL.is_expense IS NOT TRUE AND SOL.is_downpayment IS NOT TRUE AND SOL.is_service IS NOT TRUE))
                GROUP BY P.id

                UNION ALL

                -- Get the expense costs from account analytic line
                SELECT
                    ROW_NUMBER() OVER () * 10 + 3 AS id,
                    P.id AS project_id,
                    0.0 AS timesheet_unit_amount,
                    0.0 AS timesheet_cost,
                    0.0 AS other_revenues,
                    SUM(AAL.amount) AS expense_cost,
                    0.0 AS expense_amount_untaxed_to_invoice,
                    0.0 AS expense_amount_untaxed_invoiced,
                    0.0 AS amount_untaxed_to_invoice,
                    0.0 AS amount_untaxed_invoiced
                FROM project_project P
                    JOIN account_analytic_account AA ON P.analytic_account_id = AA.id
                    JOIN account_analytic_line AAL ON AAL.account_id = AA.id
                    LEFT JOIN account_move_line AML ON AAL.move_id = AML.id
                                                   AND AML.parent_state = 'posted'
                                                   AND AML.exclude_from_invoice_tab = 'f'
                    -- Check if it's not a Credit Note for an Invoice
                    LEFT JOIN account_move RINV ON RINV.id = AML.move_id
                    LEFT JOIN account_move_line INVL ON INVL.move_id = RINV.reversed_entry_id
                                                    AND INVL.parent_state = 'posted'
                                                    AND INVL.exclude_from_invoice_tab = 'f'
                                                    AND INVL.product_id = AML.product_id
                    -- Check if it's not a Bill reversed by a Credit Note
                    LEFT JOIN account_move RBILL ON RBILL.reversed_entry_id = AML.move_id
                    LEFT JOIN account_move_line RBILLL ON RBILLL.move_id = RBILL.id
                                                      AND RBILLL.parent_state = 'posted'
                                                      AND RBILLL.exclude_from_invoice_tab = 'f'
                                                      AND RBILLL.product_id = AML.product_id
                    -- Check if the AAL is not related to a consumed downpayment (when the SOL is fully invoiced - with downpayment discounted.)
                    LEFT JOIN sale_order_line_invoice_rel SOINVDOWN ON SOINVDOWN.invoice_line_id = AML.id
                    LEFT JOIN sale_order_line SOLDOWN on SOINVDOWN.order_line_id = SOLDOWN.id AND SOLDOWN.is_downpayment = 't'
                WHERE AAL.amount < 0.0 AND AAL.project_id IS NULL
                  AND INVL.id IS NULL
                  AND RBILLL.id IS NULL
                  AND SOLDOWN.id IS NULL
                  AND P.active = 't' AND P.allow_timesheets = 't'
                GROUP BY P.id

                UNION ALL

                SELECT
                    ROW_NUMBER() OVER () * 10 + 4 AS id,
                    project_id,
                    0.0 AS timesheet_unit_amount,
                    0.0 AS timesheet_cost,
                    0.0 AS expense_cost,
                    0.0 AS other_revenues,
                    SUM(expense_amount_untaxed_to_invoice) AS expense_amount_untaxed_to_invoice,
                    SUM(expense_amount_untaxed_invoiced) AS expense_amount_untaxed_invoiced,
                    SUM(amount_untaxed_to_invoice) AS amount_untaxed_to_invoice,
                    SUM(amount_untaxed_invoiced) AS amount_untaxed_invoiced
                FROM (
                    -- Get the following values: expense amount untaxed to invoice/invoiced, amount untaxed to invoice/invoiced
                    -- These values have to be computed from all the records retrieved just above but grouped by project and sale order line
                    SELECT
                        AMOUNT_UNTAXED.project_id AS project_id,
                        0.0 AS timesheet_unit_amount,
                        0.0 AS timesheet_cost,
                        0.0 AS other_revenues,
                        0.0 AS expense_cost,
                        CASE
                            WHEN SOL.qty_delivered_method = 'analytic' THEN (SOL.untaxed_amount_to_invoice / CASE COALESCE(S.currency_rate, 0) WHEN 0 THEN 1.0 ELSE S.currency_rate END)
                            ELSE 0.0
                        END AS expense_amount_untaxed_to_invoice,
                        CASE
                            WHEN SOL.qty_delivered_method = 'analytic' AND SOL.invoice_status = 'invoiced'
                            THEN
                                CASE
                                    WHEN T.expense_policy = 'sales_price'
                                    THEN (SOL.untaxed_amount_invoiced / CASE COALESCE(S.currency_rate, 0) WHEN 0 THEN 1.0 ELSE S.currency_rate END)
                                    ELSE -AMOUNT_UNTAXED.expense_cost
                                END
                            ELSE 0.0
                        END AS expense_amount_untaxed_invoiced,
                        CASE
                            WHEN SOL.qty_delivered_method IN ('timesheet', 'manual') THEN (SOL.untaxed_amount_to_invoice / CASE COALESCE(S.currency_rate, 0) WHEN 0 THEN 1.0 ELSE S.currency_rate END)
                            ELSE 0.0
                        END AS amount_untaxed_to_invoice,
                        CASE
                            WHEN SOL.qty_delivered_method IN ('timesheet', 'manual') THEN (SOL.untaxed_amount_invoiced / CASE COALESCE(S.currency_rate, 0) WHEN 0 THEN 1.0 ELSE S.currency_rate END)
                            ELSE 0.0
                        END AS amount_untaxed_invoiced
                    FROM project_project P
                        JOIN res_company C ON C.id = P.company_id
                        LEFT JOIN (
                            -- Gets SOL linked to timesheets
                            SELECT
                                P.id AS project_id,
                                P.analytic_account_id AS analytic_account_id,
                                AAL.so_line AS sale_line_id,
                                0.0 AS expense_cost
                            FROM project_project P
                                JOIN account_analytic_line AAL ON AAL.project_id = P.id
                            WHERE P.active = 't' AND P.allow_timesheets = 't'
                            GROUP BY P.id, AAL.so_line
                            UNION
                            -- Service SOL linked to a project task AND not yet timesheeted
                            SELECT
                                P.id AS project_id,
                                P.analytic_account_id AS analytic_account_id,
                                SOL.id AS sale_line_id,
                                0.0 AS expense_cost
                            FROM sale_order_line SOL
                                JOIN project_task T ON T.sale_line_id = SOL.id
                                JOIN project_project P ON T.project_id = P.id
                                LEFT JOIN account_analytic_line AAL ON AAL.task_id = T.id
                            WHERE SOL.is_service = 't'
                              AND AAL.id IS NULL -- not timesheeted
                              AND P.active = 't' AND P.allow_timesheets = 't'
                            GROUP BY P.id, SOL.id
                            UNION
                            -- Service SOL linked to project AND not yet timesheeted
                            SELECT
                                P.id AS project_id,
                                P.analytic_account_id AS analytic_account_id,
                                SOL.id AS sale_line_id,
                                0.0 AS expense_cost
                            FROM sale_order_line SOL
                                JOIN project_project P ON P.sale_line_id = SOL.id
                                LEFT JOIN account_analytic_line AAL ON AAL.project_id = P.id
                                LEFT JOIN project_task T ON T.sale_line_id = SOL.id
                            WHERE SOL.is_service = 't'
                              AND AAL.id IS NULL -- not timesheeted
                              AND (T.id IS NULL OR T.project_id != P.id) -- not linked to a task in this project
                              AND P.active = 't' AND P.allow_timesheets = 't'
                            GROUP BY P.id, SOL.id
                            UNION
                            -- Service SOL linked to analytic account AND not yet timesheeted
                            SELECT
                                P.id AS project_id,
                                P.analytic_account_id AS analytic_account_id,
                                SOL.id AS sale_line_id,
                                0.0 AS expense_cost
                            FROM sale_order_line SOL
                                JOIN sale_order SO ON SO.id = SOL.order_id
                                JOIN account_analytic_account AA ON AA.id = SO.analytic_account_id
                                JOIN project_project P ON P.analytic_account_id = AA.id
                                LEFT JOIN project_project PSOL ON PSOL.sale_line_id = SOL.id
                                LEFT JOIN project_task TSOL ON TSOL.sale_line_id = SOL.id
                                LEFT JOIN account_analytic_line AAL ON AAL.so_line = SOL.id
                            WHERE SOL.is_service = 't'
                              AND AAL.id IS NULL -- not timesheeted
                              AND TSOL.id IS NULL -- not linked to a task
                              AND PSOL.id IS NULL -- not linked to a project
                              AND P.active = 't' AND P.allow_timesheets = 't'
                            GROUP BY P.id, SOL.id
                            UNION

                            SELECT
                                P.id AS project_id,
                                P.analytic_account_id AS analytic_account_id,
                                AAL.so_line AS sale_line_id,
                                0.0 AS expense_cost
                            FROM project_project P
                                LEFT JOIN account_analytic_account AA ON P.analytic_account_id = AA.id
                                LEFT JOIN account_analytic_line AAL ON AAL.account_id = AA.id
                            WHERE AAL.amount > 0.0 AND AAL.project_id IS NULL AND P.active = 't' AND P.allow_timesheets = 't'
                            GROUP BY P.id, AA.id, AAL.so_line
                            UNION
                            SELECT
                                P.id AS project_id,
                                P.analytic_account_id AS analytic_account_id,
                                AAL.so_line AS sale_line_id,
                                SUM(AAL.amount) AS expense_cost
                            FROM project_project P
                                LEFT JOIN account_analytic_account AA ON P.analytic_account_id = AA.id
                                LEFT JOIN account_analytic_line AAL ON AAL.account_id = AA.id
                            WHERE AAL.amount < 0.0 AND AAL.project_id IS NULL AND P.active = 't' AND P.allow_timesheets = 't'
                            GROUP BY P.id, AA.id, AAL.so_line
                            UNION
                            SELECT
                                P.id AS project_id,
                                P.analytic_account_id AS analytic_account_id,
                                SOLDOWN.id AS sale_line_id,
                                0.0 AS expense_cost
                            FROM project_project P
                                JOIN sale_order_line SOL ON P.sale_line_id = SOL.id
                                JOIN sale_order SO ON SO.id = SOL.order_id OR SO.analytic_account_id = P.analytic_account_id
                                JOIN sale_order_line SOLDOWN ON SOLDOWN.order_id = SO.id AND SOLDOWN.is_downpayment = 't'
                                LEFT JOIN sale_order_line_invoice_rel SOINV ON SOINV.order_line_id = SOLDOWN.id
                                LEFT JOIN account_move_line INVL ON SOINV.invoice_line_id = INVL.id
                                                                AND INVL.parent_state = 'posted'
                                                                AND INVL.exclude_from_invoice_tab = 'f'
                                LEFT JOIN account_move RINV ON INVL.move_id = RINV.reversed_entry_id
                                LEFT JOIN account_move_line RINVL ON RINV.id = RINVL.move_id
                                                                AND RINVL.parent_state = 'posted'
                                                                AND RINVL.exclude_from_invoice_tab = 'f'
                                                                AND RINVL.product_id = SOLDOWN.product_id
                                LEFT JOIN account_analytic_line ANLI ON ANLI.move_id = RINVL.id AND ANLI.amount < 0.0
                            WHERE ANLI.id IS NULL -- there are no credit note for this downpayment
                              AND P.active = 't' AND P.allow_timesheets = 't'
                            GROUP BY P.id, SOLDOWN.id
                            UNION
                            SELECT
                                P.id AS project_id,
                                P.analytic_account_id AS analytic_account_id,
                                SOL.id AS sale_line_id,
                                0.0 AS expense_cost
                            FROM sale_order_line SOL
                                INNER JOIN project_project P ON SOL.project_id = P.id
                            WHERE P.active = 't' AND P.allow_timesheets = 't'
                            UNION
                            SELECT
                                P.id AS project_id,
                                P.analytic_account_id AS analytic_account_id,
                                SOL.id AS sale_line_id,
                                0.0 AS expense_cost
                            FROM sale_order_line SOL
                                INNER JOIN project_task T ON SOL.task_id = T.id
                                INNER JOIN project_project P ON P.id = T.project_id
                            WHERE P.active = 't' AND P.allow_timesheets = 't'
                        ) AMOUNT_UNTAXED ON AMOUNT_UNTAXED.project_id = P.id
                        LEFT JOIN sale_order_line SOL ON AMOUNT_UNTAXED.sale_line_id = SOL.id
                        LEFT JOIN sale_order S ON SOL.order_id = S.id
                        LEFT JOIN product_product PP on (SOL.product_id = PP.id)
                        LEFT JOIN product_template T on (PP.product_tmpl_id = T.id)
                    WHERE P.active = 't' AND P.analytic_account_id IS NOT NULL
                ) SOL_COSTS
                GROUP BY SOL_COSTS.project_id
            )
        """ % self._table
        self._cr.execute(query)
