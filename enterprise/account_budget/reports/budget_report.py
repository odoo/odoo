# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models
from odoo.tools import SQL


class BudgetReport(models.Model):
    _name = 'budget.report'
    _inherit = 'analytic.plan.fields.mixin'
    _description = "Budget Report"
    _auto = False
    _order = False

    date = fields.Date('Date')
    res_model = fields.Char('Model', readonly=True)
    res_id = fields.Many2oneReference('Document', model_field='res_model', readonly=True)
    description = fields.Char('Description', readonly=True)
    company_id = fields.Many2one('res.company', 'Company', readonly=True)
    user_id = fields.Many2one('res.users', 'User', readonly=True)
    line_type = fields.Selection([('budget', 'Budget'), ('committed', 'Committed'), ('achieved', 'Achieved')], 'Type', readonly=True)
    budget = fields.Float('Budget', readonly=True)
    committed = fields.Float('Committed', readonly=True)
    achieved = fields.Float('Achieved', readonly=True)
    budget_analytic_id = fields.Many2one('budget.analytic', 'Budget Analytic', readonly=True)
    budget_line_id = fields.Many2one('budget.line', 'Budget Line', readonly=True)

    def _get_bl_query(self, plan_fnames):
        budget_line_ids = self.env.context.get('budget_report_budget_line_ids')
        return SQL(
            """
            SELECT CONCAT('bl', bl.id::TEXT) AS id,
                   bl.budget_analytic_id AS budget_analytic_id,
                   bl.id AS budget_line_id,
                   'budget.analytic' AS res_model,
                   bl.budget_analytic_id AS res_id,
                   bl.date_from AS date,
                   ba.name AS description,
                   bl.company_id AS company_id,
                   NULL AS user_id,
                   'budget' AS line_type,
                   bl.budget_amount AS budget,
                   0 AS committed,
                   0 AS achieved,
                   %(plan_fields)s
              FROM budget_line bl
              JOIN budget_analytic ba ON ba.id = bl.budget_analytic_id
              %(budget_line_ids_condition)s
            """,
            plan_fields=SQL(', ').join(self.env['budget.line']._field_to_sql('bl', fname) for fname in plan_fnames),
            budget_line_ids_condition=SQL('WHERE bl.id = ANY(%(budget_line_ids)s)', budget_line_ids=budget_line_ids) if budget_line_ids else SQL(''),
        )

    def _get_aal_query(self, plan_fnames):
        budget_line_ids = self.env.context.get('budget_report_budget_line_ids')

        company_conditions = [
            SQL('aal.company_id = bl.company_id'),
            SQL('bl.company_id IS NULL'),
        ]

        queries = []
        for company_condition in company_conditions:
            queries.append(SQL(
                """
            SELECT CONCAT('aal', aal.id::TEXT) AS id,
                   bl.budget_analytic_id AS budget_analytic_id,
                   bl.id AS budget_line_id,
                   'account.analytic.line' AS res_model,
                   aal.id AS res_id,
                   aal.date AS date,
                   aal.name AS description,
                   aal.company_id AS company_id,
                   aal.user_id AS user_id,
                   'achieved' AS line_type,
                   0 AS budget,
                   aal.amount * CASE WHEN ba.budget_type = 'expense' THEN -1 ELSE 1 END AS committed,
                   aal.amount * CASE WHEN ba.budget_type = 'expense' THEN -1 ELSE 1 END AS achieved,
                   %(analytic_fields)s
              FROM account_analytic_line aal
         LEFT JOIN budget_line bl ON %(company_condition)s
                                 AND aal.date >= bl.date_from
                                 AND aal.date <= bl.date_to
                                 AND %(condition)s
         LEFT JOIN account_account aa ON aa.id = aal.general_account_id
         LEFT JOIN budget_analytic ba ON ba.id = bl.budget_analytic_id
             WHERE CASE
                       WHEN ba.budget_type = 'expense' THEN (
                           SPLIT_PART(aa.account_type, '_', 1) = 'expense'
                           OR aa.account_type IN ('asset_current', 'asset_non_current', 'asset_fixed')
                           OR (aa.account_type IS NULL AND aal.category NOT IN ('invoice', 'other'))
                           OR (aa.account_type IS NULL AND aal.category = 'other' AND aal.amount < 0)
                       )
                       WHEN ba.budget_type = 'revenue' THEN (
                           SPLIT_PART(aa.account_type, '_', 1) = 'income'
                           OR (aa.account_type IS NULL AND aal.category = 'other' AND aal.amount > 0)
                       )
                       ELSE TRUE
                   END
                   AND (
                       SPLIT_PART(aa.account_type, '_', 1) IN ('income', 'expense')
                       OR aa.account_type IN ('asset_current', 'asset_non_current', 'asset_fixed')
                       OR aa.account_type IS NULL
                   )
                   %(budget_line_ids_condition)s
                """,
                company_condition=company_condition,
                analytic_fields=SQL(', ').join(self.env['account.analytic.line']._field_to_sql('aal', fname) for fname in plan_fnames),
                condition=SQL(' AND ').join(SQL(
                    "(%(bl)s IS NULL OR %(aal)s = %(bl)s)",
                    bl=self.env['budget.line']._field_to_sql('bl', fname),
                    aal=self.env['budget.line']._field_to_sql('aal', fname),
                ) for fname in plan_fnames),
                budget_line_ids_condition=SQL('AND bl.id = ANY(%(budget_line_ids)s)', budget_line_ids=budget_line_ids) if budget_line_ids else SQL(''),
            ))

        return SQL(' UNION ALL ').join(queries)

    def _get_pol_query(self, plan_fnames):
        budget_line_ids = self.env.context.get('budget_report_budget_line_ids')
        qty_invoiced_table = SQL(
            """
               SELECT SUM(
                          CASE WHEN COALESCE(uom_aml.id != uom_pol.id, FALSE)
                               THEN ROUND((aml.quantity / uom_aml.factor) * uom_pol.factor, -LOG(uom_pol.rounding)::integer)
                               ELSE COALESCE(aml.quantity, 0)
                          END
                          * CASE WHEN am.move_type = 'in_invoice' THEN 1
                                 WHEN am.move_type = 'in_refund' THEN -1
                                 ELSE 0 END
                      ) AS qty_invoiced,
                      pol.id AS pol_id
                 FROM purchase_order po
            LEFT JOIN purchase_order_line pol ON pol.order_id = po.id
            LEFT JOIN account_move_line aml ON aml.purchase_line_id = pol.id
            LEFT JOIN account_move am ON aml.move_id = am.id
            LEFT JOIN uom_uom uom_aml ON uom_aml.id = aml.product_uom_id
            LEFT JOIN uom_uom uom_pol ON uom_pol.id = pol.product_uom
            LEFT JOIN uom_category uom_category_aml ON uom_category_aml.id = uom_pol.category_id
            LEFT JOIN uom_category uom_category_pol ON uom_category_pol.id = uom_pol.category_id
                WHERE aml.parent_state = 'posted'
             GROUP BY pol.id
        """)

        company_conditions = [
            SQL('po.company_id = bl.company_id'),
            SQL('bl.company_id IS NULL'),
        ]

        queries = []
        for company_condition in company_conditions:
            queries.append(SQL(
                """
            SELECT (pol.id::TEXT || '-' || ROW_NUMBER() OVER (PARTITION BY pol.id ORDER BY pol.id)) AS id,
                   bl.budget_analytic_id AS budget_analytic_id,
                   bl.id AS budget_line_id,
                   'purchase.order' AS res_model,
                   po.id AS res_id,
                   po.date_order AS date,
                   pol.name AS description,
                   pol.company_id AS company_id,
                   po.user_id AS user_id,
                   'committed' AS line_type,
                   0 AS budget,
                   COALESCE(pol.price_subtotal::FLOAT, pol.price_unit::FLOAT * pol.product_qty)
                        / COALESCE(NULLIF(pol.product_qty, 0), 1)
                        * (pol.product_qty - COALESCE(qty_invoiced_table.qty_invoiced, 0))
                        / po.currency_rate
                        * (a.rate)
                        * CASE WHEN ba.budget_type = 'both' THEN -1 ELSE 1 END AS committed,
                   0 AS achieved,
                   %(analytic_fields)s
              FROM purchase_order_line pol
         LEFT JOIN (%(qty_invoiced_table)s) qty_invoiced_table ON qty_invoiced_table.pol_id = pol.id
              JOIN purchase_order po ON pol.order_id = po.id AND po.state in ('purchase', 'done')
        CROSS JOIN JSONB_TO_RECORDSET(pol.analytic_json) AS a(rate FLOAT, %(field_cast)s)
         LEFT JOIN budget_line bl ON %(company_condition)s
                                 AND po.date_order >= bl.date_from
                                 AND date_trunc('day', po.date_order) <= bl.date_to
                                 AND %(condition)s
                                 %(budget_line_ids_condition)s
         LEFT JOIN budget_analytic ba ON ba.id = bl.budget_analytic_id
             WHERE pol.product_qty > COALESCE(qty_invoiced_table.qty_invoiced, 0)
               AND ba.budget_type != 'revenue'
                """,
                company_condition=company_condition,
                analytic_fields=SQL(', ').join(self.env['account.analytic.line']._field_to_sql('a', fname) for fname in plan_fnames),
                qty_invoiced_table=qty_invoiced_table,
                field_cast=SQL(', ').join(SQL('%s FLOAT', SQL.identifier(fname)) for fname in plan_fnames),
                condition=SQL(' AND ').join(SQL(
                    "(%(bl)s IS NULL OR %(a)s = %(bl)s)",
                    bl=self.env['budget.line']._field_to_sql('bl', fname),
                    a=self.env['budget.line']._field_to_sql('a', fname),
                ) for fname in plan_fnames),
                budget_line_ids_condition=SQL('AND bl.id = ANY(%(budget_line_ids)s)', budget_line_ids=budget_line_ids) if budget_line_ids else SQL(''),
            ))

        return SQL(' UNION ALL ').join(queries)

    @property
    def _table_query(self):
        self.env['account.move.line'].flush_model()
        self.env['budget.line'].flush_model()
        self.env['account.analytic.line'].flush_model()
        self.env['purchase.order'].flush_model()
        self.env['purchase.order.line'].flush_model()
        project_plan, other_plans = self.env['account.analytic.plan']._get_all_plans()
        plan_fnames = [
            fname
            for plan in project_plan | other_plans
            if (fname := plan._column_name()) in self
        ]
        return SQL(
            "%s UNION ALL %s UNION ALL %s",
            self._get_bl_query(plan_fnames),
            self._get_aal_query(plan_fnames),
            self._get_pol_query(plan_fnames),
        )

    def action_open_reference(self):
        self.ensure_one()
        if self.res_model == 'account.analytic.line':
            analytical_line = self.env['account.analytic.line'].browse(self.res_id)
            if analytical_line.move_line_id:
                return analytical_line.move_line_id.action_open_business_doc()
        return {
            'type': 'ir.actions.act_window',
            'res_model': self.res_model,
            'view_mode': 'form',
            'res_id': self.res_id,
        }
