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
    task_id = fields.Many2one('project.task', string='Task', readonly=True)
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

    amount_untaxed_to_invoice = fields.Float("Amount to Invoice", digits=(16, 2), readonly=True, group_operator="sum")
    amount_untaxed_invoiced = fields.Float("Amount Invoiced", digits=(16, 2), readonly=True, group_operator="sum")
    expense_amount_untaxed_to_invoice = fields.Float("Amount to Re-invoice", digits=(16, 2), readonly=True, group_operator="sum")
    expense_amount_untaxed_invoiced = fields.Float("Amount Re-invoiced", digits=(16, 2), readonly=True, group_operator="sum")
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
                     -- Get empty project
                     SELECT
                           -1 AS id,
                           P.id AS project_id,
                           P.user_id AS user_id,
                           NULL AS sale_line_id,
                           NULL AS task_id,
                           P.analytic_account_id AS analytic_account_id,
                           P.partner_id AS partner_id,
                           C.id AS company_id,
                           C.currency_id AS currency_id,
                           NULL AS sale_order_id,
                           NULL AS order_confirmation_date,
                           NULL AS product_id,
                           NULL AS sale_qty_delivered_method,
                           0.0 AS timesheet_unit_amount,
                           0.0 AS timesheet_cost,
                           0.0 AS other_revenues,
                           0.0 AS expense_cost,
                           0.0 AS downpayment_invoiced,
                           0.0 AS expense_amount_untaxed_to_invoice,
                           0.0 AS expense_amount_untaxed_invoiced,
                           0.0 AS amount_untaxed_to_invoice,
                           0.0 AS amount_untaxed_invoiced,
                           NULL AS line_date,
                           0.0 AS margin
                      FROM project_project P
                      JOIN res_company C
                        ON C.id = P.company_id
                UNION ALL
                     -- Get the timesheet costs and amount
                     SELECT
                           (ROW_NUMBER() OVER (ORDER BY P.id, SOL.id)) * 10 AS id,
                           P.id AS project_id,
                           P.user_id AS user_id,
                           SOL.id AS sale_line_id,
                           SOL.task_id AS task_id,
                           P.analytic_account_id AS analytic_account_id,
                           P.partner_id AS partner_id,
                           C.id AS company_id,
                           C.currency_id AS currency_id,
                           SO.id AS sale_order_id,
                           SO.date_order AS order_confirmation_date,
                           SOL.product_id AS product_id,
                           SOL.qty_delivered_method AS sale_qty_delivered_method,
                           TS.unit_amount AS timesheet_unit_amount,
                           TS.amount AS timesheet_cost,
                           0.0 AS other_revenues,
                           0.0 AS expense_cost,
                           0.0 AS downpayment_invoiced,
                           0.0 AS expense_amount_untaxed_to_invoice,
                           0.0 AS expense_amount_untaxed_invoiced,
                           0.0 AS amount_untaxed_to_invoice,
                           0.0 AS amount_untaxed_invoiced,
                           TS.date AS line_date,
                           -TS.amount AS margin
                      FROM project_project P
                      JOIN res_company C
                        ON C.id = P.company_id
                INNER JOIN account_analytic_line TS
                        ON P.id = TS.project_id
                 LEFT JOIN sale_order_line SOL
                        ON TS.so_line = SOL.id
                 LEFT JOIN sale_order SO
                        ON SOL.order_id = SO.id
                     WHERE P.active = 't' AND P.allow_timesheets = 't'
                UNION ALL
                    -- Get the timesheet costs and amount, for every timesheet's SOL :
                    --      take the untaxed_amount_to_invoice of SOL expenses as to re-invoice amount,
                    --      take the price_reduce of SOL expenses as re-invoiced amount
                    --      sum the untaxed_amount_to_invoice of SOL (timesheet ou manual) as amount
                    --      sum the untaxed_amount_invoiced of SOL (timesheet ou manual)
                    SELECT
                           (ROW_NUMBER() OVER (ORDER BY P.id, SOL.id)) * 10 + 1 AS id,
                           P.id AS project_id,
                           P.user_id AS user_id,
                           SOL.id AS sale_line_id,
                           SOL.task_id AS task_id,
                           P.analytic_account_id AS analytic_account_id,
                           P.partner_id AS partner_id,
                           C.id AS company_id,
                           C.currency_id AS currency_id,
                           SO.id AS sale_order_id,
                           SO.date_order AS order_confirmation_date,
                           SOL.product_id AS product_id,
                           SOL.qty_delivered_method AS sale_qty_delivered_method,
                           0.0 AS timesheet_unit_amount, -- TODO
                           0.0 AS timesheet_cost, -- TODO
                           0.0 AS other_revenues,
                           0.0 AS expense_cost,
                           0.0 AS downpayment_invoiced,
                           CASE
                               WHEN SOL.qty_delivered_method = 'analytic'
                               THEN (SOL.untaxed_amount_to_invoice / COALESCE(NULLIF(SO.currency_rate, 0.0), 1.0))
                               ELSE 0.0
                           END AS expense_amount_untaxed_to_invoice,
                           CASE
                               WHEN SOL.qty_delivered_method = 'analytic' AND SOL.invoice_status != 'no'
                               THEN
                                   CASE
                                       WHEN TPL.expense_policy = 'sales_price'
                                       THEN (SOL.price_reduce / COALESCE(NULLIF(SO.currency_rate, 0.0), 1.0)) * SOL.qty_invoiced
                                       ELSE 0.0
                                   END
                               ELSE 0.0
                           END AS expense_amount_untaxed_invoiced,
                           CASE
                               WHEN SOL.qty_delivered_method IN ('timesheet', 'manual') THEN (SOL.untaxed_amount_to_invoice / COALESCE(NULLIF(SO.currency_rate, 0.0), 1.0))
                               ELSE 0.0
                           END AS amount_untaxed_to_invoice,
                           CASE
                               WHEN SOL.qty_delivered_method IN ('timesheet', 'manual') THEN (SOL.untaxed_amount_invoiced / COALESCE(NULLIF(SO.currency_rate, 0.0), 1.0))
                               ELSE 0.0
                           END AS amount_untaxed_invoiced,
                           SO.date_order AS line_date,
                           0.0 AS margin
                      FROM project_project P
                INNER JOIN res_company C
                        ON C.id = P.company_id
                INNER JOIN account_analytic_line TS
                        ON P.id = TS.project_id
                INNER JOIN sale_order_line SOL
                        ON TS.so_line = SOL.id
                INNER JOIN sale_order SO
                        ON SOL.order_id = SO.id
                      JOIN product_product PRO
                        ON PRO.id = SOL.product_id
                      JOIN product_template TPL
                        ON TPL.id = PRO.product_tmpl_id
                     WHERE P.active = 't' AND P.allow_timesheets = 't'
                  GROUP BY P.id, P.user_id, SOL.id, SOL.task_id, P.analytic_account_id, P.partner_id, C.id, C.currency_id, SO.id, SO.date_order, SOL.product_id, SOL.qty_delivered_method,
                           SOL.untaxed_amount_invoiced, SOL.untaxed_amount_to_invoice, SO.currency_rate, TPL.expense_policy, SOL.qty_invoiced
                UNION ALL
                    -- Get the timesheet costs and amount, for every SOL linked to a project :
                    --      take the untaxed_amount_to_invoice of SOL expenses as to re-invoice amount,
                    --      take the price_reduce of SOL expenses as re-invoiced amount
                    --      sum the untaxed_amount_to_invoice of SOL (timesheet ou manual) as amount
                    --      sum the untaxed_amount_invoiced of SOL (timesheet ou manual)
                    SELECT
                           (ROW_NUMBER() OVER (ORDER BY P.id, SOL.id)) * 10 + 2 AS id,
                           P.id AS project_id,
                           P.user_id AS user_id,
                           SOL.id AS sale_line_id,
                           SOL.task_id AS task_id,
                           P.analytic_account_id AS analytic_account_id,
                           P.partner_id AS partner_id,
                           C.id AS company_id,
                           C.currency_id AS currency_id,
                           SO.id AS sale_order_id,
                           SO.date_order AS order_confirmation_date,
                           SOL.product_id AS product_id,
                           SOL.qty_delivered_method AS sale_qty_delivered_method,
                           0.0 AS timesheet_unit_amount,
                           0.0 AS timesheet_cost,
                           0.0 AS other_revenues,
                           0.0 AS expense_cost,
                           0.0 AS downpayment_invoiced,
                           CASE
                               WHEN SOL.qty_delivered_method = 'analytic'
                               THEN (SOL.untaxed_amount_to_invoice / COALESCE(NULLIF(SO.currency_rate, 0.0), 1.0))
                               ELSE 0.0
                           END AS expense_amount_untaxed_to_invoice,
                           CASE
                               WHEN SOL.qty_delivered_method = 'analytic' AND SOL.invoice_status != 'no'
                               THEN
                                   CASE
                                       WHEN TPL.expense_policy = 'sales_price'
                                       THEN (SOL.price_reduce / COALESCE(NULLIF(SO.currency_rate, 0.0), 1.0)) * SOL.qty_invoiced
                                       ELSE 0.0
                                   END
                               ELSE 0.0
                           END AS expense_amount_untaxed_invoiced,
                           CASE
                               WHEN SOL.qty_delivered_method IN ('timesheet', 'manual') THEN (SOL.untaxed_amount_to_invoice / COALESCE(NULLIF(SO.currency_rate, 0.0), 1.0))
                               ELSE 0.0
                           END AS amount_untaxed_to_invoice,
                           CASE
                               WHEN SOL.qty_delivered_method IN ('timesheet', 'manual') THEN (SOL.untaxed_amount_invoiced / COALESCE(NULLIF(SO.currency_rate, 0.0), 1.0))
                               ELSE 0.0
                           END AS amount_untaxed_invoiced,
                           SO.date_order AS line_date,
                           0.0 AS margin
                      FROM project_project P
                      JOIN res_company C
                        ON C.id = P.company_id
                      JOIN sale_order_line SOL
                        ON SOL.project_id = P.id
                      JOIN sale_order SO
                        ON SOL.order_id = SO.id
                      JOIN product_product PRO
                        ON PRO.id = SOL.product_id
                      JOIN product_template TPL
                        ON TPL.id = PRO.product_tmpl_id
                     WHERE P.active = 't' AND P.allow_timesheets = 't'
                        AND SOL.task_id IS NULL
                        AND NOT EXISTS (
                            SELECT 1
                            FROM account_analytic_line TS
                            WHERE TS.so_line = SOL.id and TS.project_id = P.id
                        )
                  GROUP BY P.id, P.user_id, SOL.id, SOL.task_id, P.analytic_account_id, P.partner_id, C.id, C.currency_id, SO.id, SO.date_order, SOL.product_id, SOL.qty_delivered_method,
                           SOL.untaxed_amount_invoiced, SOL.untaxed_amount_to_invoice, SO.currency_rate, TPL.expense_policy, SOL.qty_invoiced
                UNION ALL
                    -- Get the timesheet costs and amount, for every SOL linked to the task :
                    --      take the untaxed_amount_to_invoice of SOL expenses as to re-invoice amount,
                    --      take the price_reduce of SOL expenses as re-invoiced amount
                    --      sum the untaxed_amount_to_invoice of SOL (timesheet ou manual) as amount
                    --      sum the untaxed_amount_invoiced of SOL (timesheet ou manual)
                    SELECT
                           (ROW_NUMBER() OVER (ORDER BY P.id, SOL.id)) * 10 + 3 AS id,
                           P.id AS project_id,
                           P.user_id AS user_id,
                           SOL.id AS sale_line_id,
                           SOL.task_id AS task_id,
                           P.analytic_account_id AS analytic_account_id,
                           P.partner_id AS partner_id,
                           C.id AS company_id,
                           C.currency_id AS currency_id,
                           SO.id AS sale_order_id,
                           SO.date_order AS order_confirmation_date,
                           SOL.product_id AS product_id,
                           SOL.qty_delivered_method AS sale_qty_delivered_method,
                           0.0 AS timesheet_unit_amount,
                           0.0 AS timesheet_cost,
                           0.0 AS other_revenues,
                           0.0 AS expense_cost,
                           0.0 AS downpayment_invoiced,
                           CASE
                               WHEN SOL.qty_delivered_method = 'analytic'
                               THEN (SOL.untaxed_amount_to_invoice / COALESCE(NULLIF(SO.currency_rate, 0.0), 1.0))
                               ELSE 0.0
                           END AS expense_amount_untaxed_to_invoice,
                           CASE
                               WHEN SOL.qty_delivered_method = 'analytic' AND SOL.invoice_status != 'no'
                               THEN
                                   CASE
                                       WHEN TPL.expense_policy = 'sales_price'
                                       THEN (SOL.price_reduce / COALESCE(NULLIF(SO.currency_rate, 0.0), 1.0)) * SOL.qty_invoiced
                                       ELSE 0.0
                                   END
                               ELSE 0.0
                           END AS expense_amount_untaxed_invoiced,
                           CASE
                               WHEN SOL.qty_delivered_method IN ('timesheet', 'manual') THEN (SOL.untaxed_amount_to_invoice / COALESCE(NULLIF(SO.currency_rate, 0.0), 1.0))
                               ELSE 0.0
                           END AS amount_untaxed_to_invoice,
                           CASE
                               WHEN SOL.qty_delivered_method IN ('timesheet', 'manual') THEN (SOL.untaxed_amount_invoiced / COALESCE(NULLIF(SO.currency_rate, 0.0), 1.0))
                               ELSE 0.0
                           END AS amount_untaxed_invoiced,
                           SO.date_order AS line_date,
                           0.0 AS margin
                      FROM project_project P
                INNER JOIN project_task TA
                        ON P.id = TA.project_id
                      JOIN res_company C
                        ON C.id = P.company_id
                 LEFT JOIN sale_order_line SOL
                        ON SOL.task_id = TA.id
                      JOIN sale_order SO
                        ON SOL.order_id = SO.id
                      JOIN product_product PRO
                        ON PRO.id = SOL.product_id
                      JOIN product_template TPL
                        ON TPL.id = PRO.product_tmpl_id
                     WHERE P.active = 't' AND P.allow_timesheets = 't'
                       AND NOT EXISTS (
                           SELECT 1
                           FROM account_analytic_line TS
                           WHERE TS.so_line = SOL.id and TS.project_id = P.id
                       )
                  GROUP BY P.id, P.user_id, SOL.id, SOL.task_id, P.analytic_account_id, P.partner_id, C.id, C.currency_id, SO.id, SO.date_order, SOL.product_id, SOL.qty_delivered_method,
                           SOL.untaxed_amount_invoiced, SOL.untaxed_amount_to_invoice, SO.currency_rate, TPL.expense_policy, SOL.qty_invoiced
                UNION ALL
                    -- Get the other revenues
                     SELECT
                           (ROW_NUMBER() OVER (ORDER BY P.id, SOL.id)) * 10 + 4 AS id,
                           P.id AS project_id,
                           P.user_id AS user_id,
                           SOL.id AS sale_line_id,
                           SOL.task_id AS task_id,
                           P.analytic_account_id AS analytic_account_id,
                           P.partner_id AS partner_id,
                           C.id AS company_id,
                           C.currency_id AS currency_id,
                           SO.id AS sale_order_id,
                           SO.date_order AS order_confirmation_date,
                           SOL.product_id AS product_id,
                           SOL.qty_delivered_method AS sale_qty_delivered_method,
                           0.0 AS timesheet_unit_amount,
                           0.0 AS timesheet_cost,
                           CASE
                               WHEN AAL.amount > 0.0
                               THEN AAL.amount
                               ELSE 0.0
                           END AS other_revenues,
                           CASE
                               WHEN AAL.amount < 0.0
                               THEN AAL.amount
                               ELSE 0.0
                           END AS expense_cost,
                           0.0 AS downpayment_invoiced,
                           0.0 AS expense_amount_untaxed_to_invoice,
                           0.0 AS expense_amount_untaxed_invoiced,
                           0.0 AS amount_untaxed_to_invoice,
                           0.0 AS amount_untaxed_invoiced,
                           AAL.date AS line_date,
                           AAL.amount AS margin
                      FROM project_project P
                      JOIN res_company C
                        ON C.id = P.company_id
                INNER JOIN account_analytic_account AA
                        ON P.analytic_account_id = AA.id
                      JOIN account_analytic_line AAL
                        ON AAL.account_id = AA.id
                 LEFT JOIN sale_order_line SOL
                        ON AAL.so_line = SOL.id
                 LEFT JOIN sale_order SO
                        ON SOL.order_id = SO.id
                 LEFT JOIN sale_order_line_invoice_rel SOINV -- opw-2444237
                        ON SOINV.order_line_id = SOL.id AND SOINV.invoice_line_id = AAL.move_id
                     WHERE AAL.project_id IS NULL
                       AND P.active = 't' AND P.allow_timesheets = 't'
                       AND ( -- opw-2444237
                           SOINV.invoice_line_id IS NULL
                           OR NOT (SOL.qty_delivered_method IN ('timesheet', 'manual')
                                OR (SOL.qty_delivered_method = 'analytic' AND SOL.invoice_status != 'no')) -- TODO : OK ?
                       )
                UNION ALL
                    -- Get the other revenues, for every SOL linked to Project AA :
                    --      take the untaxed_amount_to_invoice of SOL expenses as to re-invoice amount,
                    --      take the price_reduce of SOL expenses as re-invoiced amount
                    --      take the untaxed_amount_to_invoice of SOL (timesheet ou manual) as amount
                    --      take the untaxed_amount_invoiced of SOL (timesheet ou manual)
                     SELECT
                           (ROW_NUMBER() OVER (ORDER BY P.id, SOL.id)) * 10 + 5 AS id,
                           P.id AS project_id,
                           P.user_id AS user_id,
                           SOL.id AS sale_line_id,
                           SOL.task_id AS task_id,
                           P.analytic_account_id AS analytic_account_id,
                           P.partner_id AS partner_id,
                           C.id AS company_id,
                           C.currency_id AS currency_id,
                           SO.id AS sale_order_id,
                           SO.date_order AS order_confirmation_date,
                           SOL.product_id AS product_id,
                           SOL.qty_delivered_method AS sale_qty_delivered_method,
                           0.0 AS timesheet_unit_amount,
                           0.0 AS timesheet_cost,
                           0.0 AS other_revenues,
                           0.0 AS expense_cost,
                           0.0 AS downpayment_invoiced,
                           CASE
                               WHEN SOL.qty_delivered_method = 'analytic'
                               THEN (SOL.untaxed_amount_to_invoice / COALESCE(NULLIF(SO.currency_rate, 0.0), 1.0))
                               ELSE 0.0
                           END AS expense_amount_untaxed_to_invoice,
                           CASE
                               WHEN SOL.qty_delivered_method = 'analytic' AND SOL.invoice_status != 'no'
                               THEN
                                   CASE
                                       WHEN TPL.expense_policy = 'sales_price'
                                       THEN (SOL.price_reduce / COALESCE(NULLIF(SO.currency_rate, 0.0), 1.0)) * SOL.qty_invoiced
                                       ELSE SUM(CASE WHEN AAL.amount < 0.0 THEN AAL.amount ELSE 0.0 END) -- TODO SUM negative AAL amount : OK ?
                                   END
                               ELSE 0.0
                           END AS expense_amount_untaxed_invoiced,
                           CASE
                               WHEN SOL.qty_delivered_method IN ('timesheet', 'manual') THEN (SOL.untaxed_amount_to_invoice / COALESCE(NULLIF(SO.currency_rate, 0.0), 1.0))
                               ELSE 0.0
                           END AS amount_untaxed_to_invoice,
                           CASE
                               WHEN SOL.qty_delivered_method IN ('timesheet', 'manual') THEN (SOL.untaxed_amount_invoiced / COALESCE(NULLIF(SO.currency_rate, 0.0), 1.0))
                               ELSE 0.0
                           END AS amount_untaxed_invoiced,
                           SO.date_order AS line_date,
                           0.0 AS margin
                      FROM project_project P
                      JOIN res_company C
                        ON C.id = P.company_id
                INNER JOIN account_analytic_account AA
                        ON P.analytic_account_id = AA.id
                      JOIN account_analytic_line AAL
                        ON AAL.account_id = AA.id
                 LEFT JOIN sale_order_line SOL
                        ON AAL.so_line = SOL.id
                      JOIN sale_order SO
                        ON SOL.order_id = SO.id
                      JOIN product_product PRO
                        ON PRO.id = SOL.product_id
                      JOIN product_template TPL
                        ON TPL.id = PRO.product_tmpl_id
                     WHERE AAL.project_id IS NULL
                       AND P.active = 't' AND P.allow_timesheets = 't'
                  GROUP BY P.id, P.user_id, SOL.id, SOL.task_id, P.analytic_account_id, P.partner_id, C.id, C.currency_id, SO.id, SO.date_order, SOL.product_id, SOL.qty_delivered_method,
                           SOL.untaxed_amount_invoiced, SOL.untaxed_amount_to_invoice, SO.currency_rate, TPL.expense_policy, SOL.qty_invoiced
                UNION ALL
                    -- Get the invoiced downpayments, for every downpayments :
                    --      take the untaxed_amount_to_invoice of SOL expenses as to re-invoice amount,
                    --      take the price_reduce of SOL expenses as re-invoiced amount
                    --      take the untaxed_amount_to_invoice of SOL (timesheet ou manual) as amount
                    --      take the untaxed_amount_invoiced of SOL (timesheet ou manual)
                     SELECT
                           (ROW_NUMBER() OVER (ORDER BY P.id, SOLS.id)) * 10 + 8 AS id,
                           P.id AS project_id,
                           P.user_id AS user_id,
                           SOLS.id AS sale_line_id,
                           SOLS.task_id AS task_id,
                           P.analytic_account_id AS analytic_account_id,
                           P.partner_id AS partner_id,
                           C.id AS company_id,
                           C.currency_id AS currency_id,
                           SO.id AS sale_order_id,
                           SO.date_order AS order_confirmation_date,
                           SOLS.product_id AS product_id,
                           SOLS.qty_delivered_method AS sale_qty_delivered_method,
                           0.0 AS timesheet_unit_amount,
                           0.0 AS timesheet_cost,
                           0.0 AS other_revenues,
                           0.0 AS expense_cost,
                           CASE WHEN SOLS.invoice_status = 'invoiced' THEN SOLS.price_reduce ELSE 0.0 END AS downpayment_invoiced,
                           CASE
                               WHEN SOLS.qty_delivered_method = 'analytic'
                               THEN (SOLS.untaxed_amount_to_invoice / COALESCE(NULLIF(SO.currency_rate, 0.0), 1.0))
                               ELSE 0.0
                           END AS expense_amount_untaxed_to_invoice,
                           CASE
                               WHEN SOLS.qty_delivered_method = 'analytic' AND SOLS.invoice_status != 'no'
                               THEN
                                   CASE
                                       WHEN TPL.expense_policy = 'sales_price'
                                       THEN (SOLS.price_reduce / COALESCE(NULLIF(SO.currency_rate, 0.0), 1.0)) * SOLS.qty_invoiced
                                       ELSE 0.0
                                   END
                               ELSE 0.0
                           END AS expense_amount_untaxed_invoiced,
                           CASE
                               WHEN SOLS.qty_delivered_method IN ('timesheet', 'manual') THEN (SOLS.untaxed_amount_to_invoice / COALESCE(NULLIF(SO.currency_rate, 0.0), 1.0))
                               ELSE 0.0
                           END AS amount_untaxed_to_invoice,
                           CASE
                               WHEN SOLS.qty_delivered_method IN ('timesheet', 'manual')
                               THEN (
                                   COALESCE(
                                               SOLS.untaxed_amount_invoiced,
                                               CASE WHEN SOLS.invoice_status = 'invoiced' THEN SOLS.price_reduce ELSE 0.0 END
                                       )
                                   /
                                   COALESCE(NULLIF(SO.currency_rate, 0.0), 1.0))
                               ELSE 0.0
                           END AS amount_untaxed_invoiced,
                           SO.date_order AS line_date,
                           0.0 AS margin
                      FROM project_project P
                      JOIN res_company C
                        ON C.id = P.company_id
                INNER JOIN sale_order_line SOL
                        ON P.sale_line_id = SOL.id
                      JOIN sale_order SO
                        ON SOL.order_id = SO.id
                      JOIN sale_order_line SOLS
                        ON SOLS.order_id = SO.id
                      JOIN product_product PRO
                        ON PRO.id = SOLS.product_id
                      JOIN product_template TPL
                        ON TPL.id = PRO.product_tmpl_id
                     WHERE SOLS.is_downpayment = 't'
                  GROUP BY P.id, P.user_id, SOLS.id, SOLS.task_id, P.analytic_account_id, P.partner_id, C.id, C.currency_id, SO.id, SO.date_order, SOLS.product_id, SOLS.qty_delivered_method,
                           SOLS.untaxed_amount_invoiced, SOLS.untaxed_amount_to_invoice, SO.currency_rate, TPL.expense_policy, SOLS.qty_invoiced
                UNION ALL
                    -- Get the expense costs from sale order line :
                    --      price reduce of SOL as expense cost
                    --      take the untaxed_amount_to_invoice of SOL expenses as to re-invoice amount,
                    --      take the price_reduce of SOL expenses as re-invoiced amount
                    --      take the untaxed_amount_to_invoice of SOL (timesheet ou manual) as amount
                    --      take the untaxed_amount_invoiced of SOL (timesheet ou manual)
                    SELECT
                           (ROW_NUMBER() OVER (ORDER BY P.id, SOLS.id)) * 10 + 9 AS id,
                           P.id AS project_id,
                           P.user_id AS user_id,
                           SOLS.id AS sale_line_id,
                           SOLS.task_id AS task_id,
                           P.analytic_account_id AS analytic_account_id,
                           P.partner_id AS partner_id,
                           C.id AS company_id,
                           C.currency_id AS currency_id,
                           SO.id AS sale_order_id,
                           SO.date_order AS order_confirmation_date,
                           SOLS.product_id AS product_id,
                           SOLS.qty_delivered_method AS sale_qty_delivered_method,
                           0.0 AS timesheet_unit_amount,
                           0.0 AS timesheet_cost,
                           0.0 AS other_revenues,
                           SOLS.price_reduce AS expense_cost,
                           0.0 AS downpayment_invoiced,
                           CASE
                               WHEN SOLS.qty_delivered_method = 'analytic'
                               THEN (SOLS.untaxed_amount_to_invoice / COALESCE(NULLIF(SO.currency_rate, 0.0), 1.0))
                               ELSE 0.0
                           END AS expense_amount_untaxed_to_invoice,
                           CASE
                               WHEN SOLS.qty_delivered_method = 'analytic' AND SOLS.invoice_status != 'no'
                               THEN
                                   CASE
                                       WHEN TPL.expense_policy = 'sales_price'
                                       THEN (SOLS.price_reduce / COALESCE(NULLIF(SO.currency_rate, 0.0), 1.0)) * SOLS.qty_invoiced
                                       ELSE -SOLS.price_reduce
                                   END
                               ELSE 0.0
                           END AS expense_amount_untaxed_invoiced,
                           CASE
                               WHEN SOLS.qty_delivered_method IN ('timesheet', 'manual') THEN (SOLS.untaxed_amount_to_invoice / COALESCE(NULLIF(SO.currency_rate, 0.0), 1.0))
                               ELSE 0.0
                           END AS amount_untaxed_to_invoice,
                           CASE
                               WHEN SOLS.qty_delivered_method IN ('timesheet', 'manual') THEN (SOLS.untaxed_amount_invoiced / COALESCE(NULLIF(SO.currency_rate, 0.0), 1.0))
                               ELSE 0.0
                           END AS amount_untaxed_invoiced,
                           SO.date_order AS line_date,
                           0.0 AS margin
                      FROM project_project P
                      JOIN res_company C
                        ON C.id = P.company_id
                INNER JOIN account_analytic_account AA
                        ON P.analytic_account_id = AA.id
                      JOIN account_analytic_line AAL
                        ON AA.id = AAL.account_id
                INNER JOIN sale_order_line SOL
                        ON P.sale_line_id = SOL.id
                      JOIN sale_order SO
                        ON SOL.order_id = SO.id
                      JOIN sale_order_line SOLS
                        ON SO.id = SOLS.order_id
                      JOIN product_product PRO
                        ON PRO.id = SOLS.product_id
                      JOIN product_template TPL
                        ON TPL.id = PRO.product_tmpl_id
                     WHERE SOLS.product_id = AAL.product_id
                       AND SOLS.is_downpayment = 't'
                       AND AAL.amount < 0.0 AND AAL.project_id IS NULL
                       AND P.active = 't' AND P.allow_timesheets = 't'
                  GROUP BY P.id, P.user_id, SOLS.id, SOLS.task_id, P.analytic_account_id, P.partner_id, C.id, C.currency_id, SO.id, SO.date_order, SOLS.product_id, SOLS.qty_delivered_method,
                           SOLS.untaxed_amount_invoiced, SOLS.untaxed_amount_to_invoice, SO.currency_rate, TPL.expense_policy, SOLS.qty_invoiced
            )
        """ % self._table
        self._cr.execute(query)
