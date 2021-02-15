# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, tools


class ProfitabilityAnalysis(models.Model):

    _name = "project.profitability.report"
    _description = "Project Profitability Report"
    _order = 'project_id, sale_line_id'
    _auto = False

    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account', readonly=True)
    project_id = fields.Many2one('project.project', string='Project', readonly=True)
    currency_id = fields.Many2one('res.currency', string='Project Currency', readonly=True)
    company_id = fields.Many2one('res.company', string='Project Company', readonly=True)
    user_id = fields.Many2one('res.users', string='Project Manager', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Customer', readonly=True)
    line_date = fields.Date("Date", readonly=True)
    # cost
    timesheet_unit_amount = fields.Float("Timesheet Duration", digits=(16, 2), readonly=True, group_operator="sum")
    timesheet_cost = fields.Float("Timesheet Cost", digits=(16, 2), readonly=True, group_operator="sum")
    expense_cost = fields.Float("Other Costs", digits=(16, 2), readonly=True, group_operator="sum")
    # sale revenue
    order_confirmation_date = fields.Datetime('Sales Order Confirmation Date', readonly=True)
    sale_line_id = fields.Many2one('sale.order.line', string='Sale Order Line', readonly=True)
    sale_order_id = fields.Many2one('sale.order', string='Sale Order', readonly=True)
    product_id = fields.Many2one('product.product', string='Product', readonly=True)

    amount_untaxed_to_invoice = fields.Float("Untaxed Amount to Invoice", digits=(16, 2), readonly=True, group_operator="sum")
    amount_untaxed_invoiced = fields.Float("Untaxed Amount Invoiced", digits=(16, 2), readonly=True, group_operator="sum")
    expense_amount_untaxed_to_invoice = fields.Float("Untaxed Amount to Re-invoice", digits=(16, 2), readonly=True, group_operator="sum")
    expense_amount_untaxed_invoiced = fields.Float("Untaxed Amount Re-invoiced", digits=(16, 2), readonly=True, group_operator="sum")
    other_revenues = fields.Float("Other Revenues", digits=(16, 2), readonly=True, group_operator="sum",
                                  help="All revenues that are not from timesheets and that are linked to the analytic account of the project.")
    margin = fields.Float("Margin", digits=(16, 2), readonly=True, group_operator="sum")

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
            'date_order',
            'user_id',
            'partner_id',
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
                SELECT
                    sub.id as id,
                    sub.project_id as project_id,
                    sub.user_id as user_id,
                    sub.sale_line_id as sale_line_id,
                    sub.analytic_account_id as analytic_account_id,
                    sub.partner_id as partner_id,
                    sub.company_id as company_id,
                    sub.currency_id as currency_id,
                    sub.sale_order_id as sale_order_id,
                    sub.order_confirmation_date as order_confirmation_date,
                    sub.product_id as product_id,
                    sub.sale_qty_delivered_method as sale_qty_delivered_method,
                    sub.expense_amount_untaxed_to_invoice as expense_amount_untaxed_to_invoice,
                    sub.expense_amount_untaxed_invoiced as expense_amount_untaxed_invoiced,
                    sub.amount_untaxed_to_invoice as amount_untaxed_to_invoice,
                    sub.amount_untaxed_invoiced as amount_untaxed_invoiced,
                    sub.timesheet_unit_amount as timesheet_unit_amount,
                    sub.timesheet_cost as timesheet_cost,
                    sub.expense_cost as expense_cost,
                    sub.other_revenues as other_revenues,
                    sub.line_date as line_date,
                    (sub.expense_amount_untaxed_to_invoice + sub.expense_amount_untaxed_invoiced + sub.amount_untaxed_to_invoice +
                        sub.amount_untaxed_invoiced + sub.other_revenues + sub.timesheet_cost + sub.expense_cost)
                        as margin
                FROM (
                    SELECT
                        ROW_NUMBER() OVER (ORDER BY P.id, SOL.id) AS id,
                        P.id AS project_id,
                        P.user_id AS user_id,
                        SOL.id AS sale_line_id,
                        P.analytic_account_id AS analytic_account_id,
                        P.partner_id AS partner_id,
                        C.id AS company_id,
                        C.currency_id AS currency_id,
                        S.id AS sale_order_id,
                        S.date_order AS order_confirmation_date,
                        SOL.product_id AS product_id,
                        SOL.qty_delivered_method AS sale_qty_delivered_method,
                        COST_SUMMARY.expense_amount_untaxed_to_invoice AS expense_amount_untaxed_to_invoice,
                        COST_SUMMARY.expense_amount_untaxed_invoiced AS expense_amount_untaxed_invoiced,
                        COST_SUMMARY.amount_untaxed_to_invoice AS amount_untaxed_to_invoice,
                        COST_SUMMARY.amount_untaxed_invoiced AS amount_untaxed_invoiced,
                        COST_SUMMARY.timesheet_unit_amount AS timesheet_unit_amount,
                        COST_SUMMARY.timesheet_cost AS timesheet_cost,
                        COST_SUMMARY.expense_cost AS expense_cost,
                        COST_SUMMARY.other_revenues AS other_revenues,
                        COST_SUMMARY.line_date::date AS line_date
                    FROM project_project P
                        JOIN res_company C ON C.id = P.company_id
                        LEFT JOIN (
                            -- Each costs and revenues will be retrieved individually by sub-requests
                            -- This is required to able to get the date
                            SELECT
                                project_id,
                                analytic_account_id,
                                sale_line_id,
                                SUM(timesheet_unit_amount) AS timesheet_unit_amount,
                                SUM(timesheet_cost) AS timesheet_cost,
                                SUM(expense_cost) AS expense_cost,
                                SUM(other_revenues) AS other_revenues,
                                SUM(downpayment_invoiced) AS downpayment_invoiced,
                                SUM(expense_amount_untaxed_to_invoice) AS expense_amount_untaxed_to_invoice,
                                SUM(expense_amount_untaxed_invoiced) AS expense_amount_untaxed_invoiced,
                                SUM(amount_untaxed_to_invoice) AS amount_untaxed_to_invoice,
                                SUM(amount_untaxed_invoiced) AS amount_untaxed_invoiced,
                                line_date AS line_date
                            FROM (
                                -- Get the timesheet costs
                                SELECT
                                    P.id AS project_id,
                                    P.analytic_account_id AS analytic_account_id,
                                    TS.so_line AS sale_line_id,
                                    TS.unit_amount AS timesheet_unit_amount,
                                    TS.amount AS timesheet_cost,
                                    0.0 AS other_revenues,
                                    0.0 AS expense_cost,
                                    0.0 AS downpayment_invoiced,
                                    0.0 AS expense_amount_untaxed_to_invoice,
                                    0.0 AS expense_amount_untaxed_invoiced,
                                    0.0 AS amount_untaxed_to_invoice,
                                    0.0 AS amount_untaxed_invoiced,
                                    TS.date AS line_date
                                FROM account_analytic_line TS, project_project P
                                WHERE TS.project_id IS NOT NULL AND P.id = TS.project_id AND P.active = 't' AND P.allow_timesheets = 't'

                                UNION ALL

                                -- Get the other revenues
                                SELECT
                                    P.id AS project_id,
                                    P.analytic_account_id AS analytic_account_id,
                                    AAL.so_line AS sale_line_id,
                                    0.0 AS timesheet_unit_amount,
                                    0.0 AS timesheet_cost,
                                    AAL.amount AS other_revenues,
                                    0.0 AS expense_cost,
                                    0.0 AS downpayment_invoiced,
                                    0.0 AS expense_amount_untaxed_to_invoice,
                                    0.0 AS expense_amount_untaxed_invoiced,
                                    0.0 AS amount_untaxed_to_invoice,
                                    0.0 AS amount_untaxed_invoiced,
                                    AAL.date AS line_date
                                FROM project_project P
                                    LEFT JOIN account_analytic_account AA ON P.analytic_account_id = AA.id
                                    LEFT JOIN account_analytic_line AAL ON AAL.account_id = AA.id
                                WHERE AAL.amount > 0.0 AND AAL.project_id IS NULL AND P.active = 't' AND P.allow_timesheets = 't'
                                    AND NOT EXISTS (
                                        SELECT SOL.id
                                        FROM sale_order_line SOL
                                        JOIN sale_order_line_invoice_rel SOINV ON SOINV.order_line_id = SOL.id
                                        JOIN account_move_line AML ON SOINV.invoice_line_id = AAL.move_id
                                        WHERE SOL.qty_delivered_method IN ('timesheet', 'manual')
                                            OR (SOL.qty_delivered_method = 'analytic' AND SOL.invoice_status != 'no')
                                    )

                                UNION ALL

                                -- Get the expense costs from account analytic line
                                SELECT
                                    P.id AS project_id,
                                    P.analytic_account_id AS analytic_account_id,
                                    AAL.so_line AS sale_line_id,
                                    0.0 AS timesheet_unit_amount,
                                    0.0 AS timesheet_cost,
                                    0.0 AS other_revenues,
                                    AAL.amount AS expense_cost,
                                    0.0 AS downpayment_invoiced,
                                    0.0 AS expense_amount_untaxed_to_invoice,
                                    0.0 AS expense_amount_untaxed_invoiced,
                                    0.0 AS amount_untaxed_to_invoice,
                                    0.0 AS amount_untaxed_invoiced,
                                    AAL.date AS line_date
                                FROM project_project P
                                    LEFT JOIN account_analytic_account AA ON P.analytic_account_id = AA.id
                                    LEFT JOIN account_analytic_line AAL ON AAL.account_id = AA.id
                                WHERE AAL.amount < 0.0 AND AAL.project_id IS NULL AND P.active = 't' AND P.allow_timesheets = 't'

                                UNION ALL

                                -- Get the invoiced downpayments
                                SELECT
                                    P.id AS project_id,
                                    P.analytic_account_id AS analytic_account_id,
                                    MY_SOLS.id AS sale_line_id,
                                    0.0 AS timesheet_unit_amount,
                                    0.0 AS timesheet_cost,
                                    0.0 AS other_revenues,
                                    0.0 AS expense_cost,
                                    CASE WHEN MY_SOLS.invoice_status = 'invoiced' THEN MY_SOLS.price_reduce ELSE 0.0 END AS downpayment_invoiced,
                                    0.0 AS expense_amount_untaxed_to_invoice,
                                    0.0 AS expense_amount_untaxed_invoiced,
                                    0.0 AS amount_untaxed_to_invoice,
                                    0.0 AS amount_untaxed_invoiced,
                                    MY_S.date_order AS line_date
                                FROM project_project P
                                    LEFT JOIN sale_order_line MY_SOL ON P.sale_line_id = MY_SOL.id
                                    LEFT JOIN sale_order MY_S ON MY_SOL.order_id = MY_S.id
                                    LEFT JOIN sale_order_line MY_SOLS ON MY_SOLS.order_id = MY_S.id
                                WHERE MY_SOLS.is_downpayment = 't'

                                UNION ALL

                                -- Get the expense costs from sale order line
                                SELECT
                                    P.id AS project_id,
                                    P.analytic_account_id AS analytic_account_id,
                                    OLIS.id AS sale_line_id,
                                    0.0 AS timesheet_unit_amount,
                                    0.0 AS timesheet_cost,
                                    0.0 AS other_revenues,
                                    OLIS.price_reduce AS expense_cost,
                                    0.0 AS downpayment_invoiced,
                                    0.0 AS expense_amount_untaxed_to_invoice,
                                    0.0 AS expense_amount_untaxed_invoiced,
                                    0.0 AS amount_untaxed_to_invoice,
                                    0.0 AS amount_untaxed_invoiced,
                                    ANLI.date AS line_date
                                FROM project_project P
                                    LEFT JOIN account_analytic_account ANAC ON P.analytic_account_id = ANAC.id
                                    LEFT JOIN account_analytic_line ANLI ON ANAC.id = ANLI.account_id
                                    LEFT JOIN sale_order_line OLI ON P.sale_line_id = OLI.id
                                    LEFT JOIN sale_order ORD ON OLI.order_id = ORD.id
                                    LEFT JOIN sale_order_line OLIS ON ORD.id = OLIS.order_id
                                WHERE OLIS.product_id = ANLI.product_id AND OLIS.is_downpayment = 't' AND ANLI.amount < 0.0 AND ANLI.project_id IS NULL AND P.active = 't' AND P.allow_timesheets = 't'

                                UNION ALL

                                -- Get the following values: expense amount untaxed to invoice/invoiced, amount untaxed to invoice/invoiced
                                -- These values have to be computed from all the records retrieved just above but grouped by project and sale order line
                                SELECT
                                    AMOUNT_UNTAXED.project_id AS project_id,
                                    AMOUNT_UNTAXED.analytic_account_id AS analytic_account_id,
                                    AMOUNT_UNTAXED.sale_line_id AS sale_line_id,
                                    0.0 AS timesheet_unit_amount,
                                    0.0 AS timesheet_cost,
                                    0.0 AS other_revenues,
                                    0.0 AS expense_cost,
                                    0.0 AS downpayment_invoiced,
                                    CASE
                                        WHEN SOL.qty_delivered_method = 'analytic' THEN (SOL.untaxed_amount_to_invoice / CASE COALESCE(S.currency_rate, 0) WHEN 0 THEN 1.0 ELSE S.currency_rate END)
                                        ELSE 0.0
                                    END AS expense_amount_untaxed_to_invoice,
                                    CASE
                                        WHEN SOL.qty_delivered_method = 'analytic' AND SOL.invoice_status != 'no'
                                        THEN
                                            CASE
                                                WHEN T.expense_policy = 'sales_price'
                                                THEN (SOL.price_reduce / CASE COALESCE(S.currency_rate, 0) WHEN 0 THEN 1.0 ELSE S.currency_rate END) * SOL.qty_invoiced
                                                ELSE -AMOUNT_UNTAXED.expense_cost
                                            END
                                        ELSE 0.0
                                    END AS expense_amount_untaxed_invoiced,
                                    CASE
                                        WHEN SOL.qty_delivered_method IN ('timesheet', 'manual') THEN (SOL.untaxed_amount_to_invoice / CASE COALESCE(S.currency_rate, 0) WHEN 0 THEN 1.0 ELSE S.currency_rate END)
                                        ELSE 0.0
                                    END AS amount_untaxed_to_invoice,
                                    CASE
                                        WHEN SOL.qty_delivered_method IN ('timesheet', 'manual') THEN (COALESCE(SOL.untaxed_amount_invoiced, AMOUNT_UNTAXED.downpayment_invoiced) / CASE COALESCE(S.currency_rate, 0) WHEN 0 THEN 1.0 ELSE S.currency_rate END)
                                        ELSE 0.0
                                    END AS amount_untaxed_invoiced,
                                    S.date_order AS line_date
                                FROM project_project P
                                    JOIN res_company C ON C.id = P.company_id
                                    LEFT JOIN (
                                        SELECT
                                            P.id AS project_id,
                                            P.analytic_account_id AS analytic_account_id,
                                            AAL.so_line AS sale_line_id,
                                            0.0 AS expense_cost,
                                            0.0 AS downpayment_invoiced
                                        FROM account_analytic_line AAL, project_project P
                                        WHERE AAL.project_id IS NOT NULL AND P.id = AAL.project_id AND P.active = 't'
                                        GROUP BY P.id, AAL.so_line

                                        UNION

                                        SELECT
                                            P.id AS project_id,
                                            P.analytic_account_id AS analytic_account_id,
                                            AAL.so_line AS sale_line_id,
                                            0.0 AS expense_cost,
                                            0.0 AS downpayment_invoiced
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
                                            SUM(AAL.amount) AS expense_cost,
                                            0.0 AS downpayment_invoiced
                                        FROM project_project P
                                            LEFT JOIN account_analytic_account AA ON P.analytic_account_id = AA.id
                                            LEFT JOIN account_analytic_line AAL ON AAL.account_id = AA.id
                                        WHERE AAL.amount < 0.0 AND AAL.project_id IS NULL AND P.active = 't' AND P.allow_timesheets = 't'
                                        GROUP BY P.id, AA.id, AAL.so_line
                                        UNION
                                        SELECT
                                            P.id AS project_id,
                                            P.analytic_account_id AS analytic_account_id,
                                            MY_SOLS.id AS sale_line_id,
                                            0.0 AS expense_cost,
                                            CASE WHEN MY_SOLS.invoice_status = 'invoiced' THEN MY_SOLS.price_reduce ELSE 0.0 END AS downpayment_invoiced
                                        FROM project_project P
                                            LEFT JOIN sale_order_line MY_SOL ON P.sale_line_id = MY_SOL.id
                                            LEFT JOIN sale_order MY_S ON MY_SOL.order_id = MY_S.id
                                            LEFT JOIN sale_order_line MY_SOLS ON MY_SOLS.order_id = MY_S.id
                                        WHERE MY_SOLS.is_downpayment = 't'
                                        GROUP BY P.id, MY_SOLS.id
                                        UNION
                                        SELECT
                                            P.id AS project_id,
                                            P.analytic_account_id AS analytic_account_id,
                                            OLIS.id AS sale_line_id,
                                            OLIS.price_reduce AS expense_cost,
                                            0.0 AS downpayment_invoiced
                                        FROM project_project P
                                            LEFT JOIN account_analytic_account ANAC ON P.analytic_account_id = ANAC.id
                                            LEFT JOIN account_analytic_line ANLI ON ANAC.id = ANLI.account_id
                                            LEFT JOIN sale_order_line OLI ON P.sale_line_id = OLI.id
                                            LEFT JOIN sale_order ORD ON OLI.order_id = ORD.id
                                            LEFT JOIN sale_order_line OLIS ON ORD.id = OLIS.order_id
                                        WHERE OLIS.product_id = ANLI.product_id AND OLIS.is_downpayment = 't' AND ANLI.amount < 0.0 AND ANLI.project_id IS NULL AND P.active = 't' AND P.allow_timesheets = 't'
                                        GROUP BY P.id, OLIS.id
                                        UNION
                                        SELECT
                                            P.id AS project_id,
                                            P.analytic_account_id AS analytic_account_id,
                                            SOL.id AS sale_line_id,
                                            0.0 AS expense_cost,
                                            0.0 AS downpayment_invoiced
                                        FROM sale_order_line SOL
                                            INNER JOIN project_project P ON SOL.project_id = P.id
                                        WHERE P.active = 't' AND P.allow_timesheets = 't'
                                        UNION
                                        SELECT
                                            P.id AS project_id,
                                            P.analytic_account_id AS analytic_account_id,
                                            SOL.id AS sale_line_id,
                                            0.0 AS expense_cost,
                                            0.0 AS downpayment_invoiced
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
                            ) SUB_COST_SUMMARY
                            GROUP BY project_id, analytic_account_id, sale_line_id, line_date
                        ) COST_SUMMARY ON COST_SUMMARY.project_id = P.id
                        LEFT JOIN sale_order_line SOL ON COST_SUMMARY.sale_line_id = SOL.id
                        LEFT JOIN sale_order S ON SOL.order_id = S.id
                        WHERE P.active = 't' AND P.analytic_account_id IS NOT NULL
                    ) AS sub
            )
        """ % self._table
        self._cr.execute(query)
