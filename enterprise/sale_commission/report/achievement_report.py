# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import models, api, fields

class SaleAchievementReport(models.Model):
    _name = "sale.commission.achievement.report"
    _description = "Sales Achievement Report"
    _order = 'id'
    _auto = False

    target_id = fields.Many2one('sale.commission.plan.target', "Period", readonly=True)
    plan_id = fields.Many2one('sale.commission.plan', "Commission Plan", readonly=True)
    user_id = fields.Many2one('res.users', "Sales Person", readonly=True)
    team_id = fields.Many2one('crm.team', "Sales Team", readonly=True)
    achieved = fields.Monetary("Achieved", readonly=True, currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', "Currency", readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    date = fields.Date(string="Date", readonly=True)

    related_res_model = fields.Char(readonly=True)
    related_res_id = fields.Many2oneReference("Related", model_field='related_res_model', readonly=True)

    def open_related(self):
        return {
            'view_mode': 'form',
            'res_model': self.related_res_model,
            'res_id': self.related_res_id,
            'type': 'ir.actions.act_window',
        }

    @property
    def _table_query(self):
        users = self.env.context.get('commission_user_ids', [])
        if users:
            users = self.env['res.users'].browse(users).exists()
        teams = self.env.context.get('commission_team_ids', [])
        if teams:
            teams = self.env['crm.team'].browse(teams).exists()
        return f"""
WITH {self._commission_lines_query(users=users, teams=teams)}
SELECT
    ROW_NUMBER() OVER (ORDER BY era.date_from DESC, era.id) AS id,
    era.id AS target_id,
    cl.user_id AS user_id,
    cl.team_id AS team_id,
    cl.achieved AS achieved,
    cl.currency_id AS currency_id,
    cl.company_id AS company_id,
    cl.plan_id,
    cl.related_res_model,
    cl.related_res_id,
    cl.date::date AS date
FROM commission_lines cl
JOIN sale_commission_plan_target era
    ON cl.plan_id = era.plan_id
    AND cl.date::date >= era.date_from
    AND cl.date::date <= era.date_to
"""

    @api.model
    def _rate_to_case(self, rates):
        case = "CASE WHEN scpa.type = '%s' THEN rate ELSE 0 END AS %s"
        return ",\n".join(case % (s, s + '_rate') for s in rates)

    @api.model
    def _get_sale_rates(self):
        return ['amount_sold', 'qty_sold']

    @api.model
    def _get_invoices_rates(self):
        return ['amount_invoiced', 'qty_invoiced']

    @api.model
    def _get_sale_rates_product(self):
        return """
            rules.amount_sold_rate * sol.price_subtotal / so.currency_rate +
            rules.qty_sold_rate * sol.product_uom_qty
        """

    @api.model
    def _get_invoice_rates_product(self):
        return """
            CASE
             WHEN am.move_type = 'out_invoice' THEN
                 rules.amount_invoiced_rate * aml.price_subtotal / am.invoice_currency_rate +
                 rules.qty_invoiced_rate * aml.quantity
             WHEN am.move_type = 'out_refund' THEN
                 (rules.amount_invoiced_rate * aml.price_subtotal / am.invoice_currency_rate +
                 rules.qty_invoiced_rate * aml.quantity) * -1
            END
        """
    @api.model
    def _get_company_condition(self, company_table):
        company_count = len(self.env.companies.ids)
        if company_count == 1:
            return f"AND \"{company_table}\".company_id = {self.env.companies.id}"
        else:
            return f"AND \"{company_table}\".company_id IN {tuple(self.env.companies.ids)}"

    @api.model
    def _select_invoices(self):
        return f"""
          rules.user_id,
          MAX(am.team_id),
          rules.plan_id,
          SUM({self._get_invoice_rates_product()}) AS achieved,
          MAX(rules.currency_id),
          MAX(am.date) AS date,
          MAX(rules.company_id),
          am.id AS related_res_id
        """

    @api.model
    def _join_invoices(self):
        return """
          JOIN account_move am
            ON am.company_id = rules.company_id
          JOIN account_move_line aml
            ON aml.move_id = am.id
          LEFT JOIN product_product pp
            ON aml.product_id = pp.id
          LEFT JOIN product_template pt
            ON pp.product_tmpl_id = pt.id
        """

    @api.model
    def _where_invoices(self):
        return f"""
          aml.display_type = 'product'
          AND am.move_type in ('out_invoice', 'out_refund')
          AND am.state != 'cancel'
          {self._get_company_condition('am')}
        """

    @api.model
    def _select_rules(self):
        return ""

    @api.model
    def _select_sales(self):
        return """
          so.id AS related_res_id
        """

    @api.model
    def _join_sales(self):
        return """
        JOIN sale_order so
          ON so.company_id = rules.company_id
        JOIN sale_order_line sol
          ON sol.order_id = so.id
        """

    @api.model
    def _where_sales(self):
        return f"""
          AND sol.display_type IS NULL
          AND (so.date_order BETWEEN rules.date_from AND rules.date_to)
          AND so.state = 'sale'
          AND (rules.product_id IS NULL OR rules.product_id = sol.product_id)
          AND (rules.product_categ_id IS NULL OR rules.product_categ_id = pt.categ_id)
          AND COALESCE(is_expense, false) = false
          AND COALESCE(is_downpayment, false) = false
          {self._get_company_condition('so')}
        """

    def _achievement_lines(self, users=None, teams=None):
        return f"""
achievement_commission_lines AS (
    SELECT
        sca.user_id,
        sca.team_id,
        scp.id AS plan_id,
        sca.currency_rate * sca.amount * scpa.rate AS achieved,
        scp.currency_id,
        sca.date,
        scp.company_id,
        sca.id AS related_res_id,
        'sale.commission.achievement' AS related_res_model
    FROM sale_commission_achievement sca
    JOIN sale_commission_plan scp ON scp.company_id = sca.company_id
    JOIN sale_commission_plan_achievement scpa ON scpa.plan_id = scp.id
    JOIN sale_commission_plan_user scpu ON scpu.plan_id = scp.id
    WHERE scp.active
      AND scp.state = 'approved'
      AND sca.type = scpa.type
      AND CASE
            WHEN scp.user_type = 'person' THEN sca.user_id = scpu.user_id
            ELSE sca.team_id = scp.team_id
      END
    {'AND sca.user_id in (%s)' % ','.join(str(i) for i in users.ids) if users else ''}
    {'AND sca.team_id in (%s)' % ','.join(str(i) for i in teams.ids) if teams else ''}
)""", 'achievement_commission_lines'

    def _invoices_lines(self, users=None, teams=None):
        return f"""
invoices_rules AS (
    SELECT
        COALESCE(scpu.date_from, scp.date_from) AS date_from,
        COALESCE(scpu.date_to, scp.date_to) AS date_to,
        scpu.user_id AS user_id,
        scp.team_id AS team_id,
        scp.id AS plan_id,
        scpa.product_id,
        scpa.product_categ_id,
        scp.company_id,
        scp.currency_id,
        scp.user_type = 'team' AS team_rule,
        {self._rate_to_case(self._get_invoices_rates())}
        {self._select_rules()}
    FROM sale_commission_plan_achievement scpa
    JOIN sale_commission_plan scp ON scp.id = scpa.plan_id
    JOIN sale_commission_plan_user scpu ON scpa.plan_id = scpu.plan_id
    WHERE scp.active
      AND scp.state = 'approved'
      AND scpa.type IN ({','.join("'%s'" % r for r in self._get_invoices_rates())})
    {'AND scpu.user_id in (%s)' % ','.join(str(i) for i in users.ids) if users else ''}
), invoice_commission_lines_team AS (
    SELECT
        {self._select_invoices()}
    FROM invoices_rules rules
         {self._join_invoices()}
    WHERE {self._where_invoices()}
      AND rules.team_rule
      AND am.team_id = rules.team_id
    {'AND am.team_id in (%s)' % ','.join(str(i) for i in teams.ids) if teams else ''}
      AND am.date BETWEEN rules.date_from AND rules.date_to
      AND (rules.product_id IS NULL OR rules.product_id = aml.product_id)
      AND (rules.product_categ_id IS NULL OR rules.product_categ_id = pt.categ_id)
    GROUP BY
        am.id,
        rules.plan_id,
        rules.user_id
), invoice_commission_lines_user AS (
    SELECT
          {self._select_invoices()}
    FROM invoices_rules rules
         {self._join_invoices()}
    WHERE {self._where_invoices()}
      AND NOT rules.team_rule
      AND am.invoice_user_id = rules.user_id
    {'AND am.invoice_user_id in (%s)' % ','.join(str(i) for i in users.ids) if users else ''}
      AND am.date BETWEEN rules.date_from AND rules.date_to
      AND (rules.product_id IS NULL OR rules.product_id = aml.product_id)
      AND (rules.product_categ_id IS NULL OR rules.product_categ_id = pt.categ_id)
    GROUP BY
        am.id,
        rules.plan_id,
        rules.user_id
), invoice_commission_lines AS (
    (SELECT *, 'account.move' AS related_res_model FROM invoice_commission_lines_team)
    UNION ALL
    (SELECT *, 'account.move' AS related_res_model FROM invoice_commission_lines_user)
)""", 'invoice_commission_lines'

    def _sale_lines(self, users=None, teams=None):
        return f"""
sale_rules AS (
    SELECT
        COALESCE(scpu.date_from, scp.date_from) AS date_from,
        COALESCE(scpu.date_to, scp.date_to) AS date_to,
        scpu.user_id AS user_id,
        scp.team_id AS team_id,
        scp.id AS plan_id,
        scpa.product_id,
        scpa.product_categ_id,
        scp.company_id,
        scp.currency_id,
        scp.user_type = 'team' AS team_rule,
        {self._rate_to_case(self._get_sale_rates())}
        {self._select_rules()}
    FROM sale_commission_plan_achievement scpa
    JOIN sale_commission_plan scp ON scp.id = scpa.plan_id
    JOIN sale_commission_plan_user scpu ON scpa.plan_id = scpu.plan_id
    WHERE scp.active
      AND scp.state = 'approved'
      {self._get_company_condition('scp')}
      AND scpa.type IN ({','.join("'%s'" % r for r in self._get_sale_rates())})
    {'AND scpu.user_id in (%s)' % ','.join(str(i) for i in users.ids) if users else ''}
), sale_commission_lines_team AS (
    SELECT
        rules.user_id,
        MAX(rules.team_id),
        rules.plan_id,
        SUM({self._get_sale_rates_product()}) AS achieved,
        MAX(rules.currency_id),
        MAX(so.date_order) AS date,
        MAX(rules.company_id),
        {self._select_sales()}
    FROM sale_rules rules
    {self._join_sales()}
    JOIN product_product pp
      ON sol.product_id = pp.id
    JOIN product_template pt
      ON pp.product_tmpl_id = pt.id
    WHERE rules.team_rule
      AND so.team_id = rules.team_id
    {'AND so.team_id in (%s)' % ','.join(str(i) for i in teams.ids) if teams else ''}
    {self._where_sales()}
    GROUP BY
        so.id,
        rules.plan_id,
        rules.user_id
), sale_commission_lines_user AS (
    SELECT
        rules.user_id,
        MAX(so.team_id),
        rules.plan_id,
        SUM({self._get_sale_rates_product()}) AS achieved,
        MAX(rules.currency_id),
        MAX(so.date_order) AS date,
        MAX(rules.company_id),
        {self._select_sales()}
    FROM sale_rules rules
    {self._join_sales()}
    JOIN product_product pp
      ON sol.product_id = pp.id
    JOIN product_template pt
      ON pp.product_tmpl_id = pt.id
    WHERE NOT rules.team_rule
      AND so.user_id = rules.user_id
    {'AND so.user_id in (%s)' % ','.join(str(i) for i in users.ids) if users else ''}
      {self._where_sales()}
    GROUP BY
        so.id,
        rules.plan_id,
        rules.user_id
), sale_commission_lines AS (
    (SELECT *, 'sale.order' AS related_res_model FROM sale_commission_lines_team)
    UNION ALL
    (SELECT *, 'sale.order' AS related_res_model FROM sale_commission_lines_user)
)""", 'sale_commission_lines'

    def _commission_lines_cte(self, users=None, teams=None):
        return [self._achievement_lines(users, teams), self._sale_lines(users, teams), self._invoices_lines(users, teams)]

    def _commission_lines_query(self, users=None, teams=None):
        ctes = self._commission_lines_cte(users, teams)
        queries = [x[0] for x in ctes]
        table_names = [x[1] for x in ctes]
        return f"""
{','.join(queries)},
commission_lines AS (
    {' UNION ALL '.join(f'(SELECT * FROM {name})' for name in table_names)}
)
"""
