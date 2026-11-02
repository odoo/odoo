from odoo import _, api, fields, models, tools


# Analytic profitability classification, copied from Odoo 19 core
# (addons/account/models/account_analytic_line.py, _field_to_sql). It must stay
# aligned with _compute_analytic_profitability so the SQL view and the Python
# helper _od19_get_pnl_values report the same numbers.
PROFITABILITY_SQL = """
                            CASE
                                WHEN (
                                    SPLIT_PART(aa.account_type, '_', 1) = 'expense'
                                    OR aa.account_type IN ('asset_current', 'asset_non_current', 'asset_fixed')
                                    OR (aa.account_type IS NULL AND al.category NOT IN ('invoice', 'other'))
                                    OR (aa.account_type IS NULL AND al.category = 'other' AND al.amount < 0)
                                ) THEN 'loss'
                                WHEN (
                                    SPLIT_PART(aa.account_type, '_', 1) = 'income'
                                    OR (aa.account_type IS NULL AND al.category = 'other' AND al.amount > 0)
                                ) THEN 'revenue'
                                ELSE 'uncategorized'
                            END"""


class Od19ProjectRiskReport(models.Model):
    _name = "od19.project.risk.report"
    _description = "OD19 Project Risk Report"
    _auto = False
    # NOTE: risk_score is a non-stored computed field, so it cannot be used in
    # _order (it does not exist as a column in the SQL view). Keep the default
    # ordering by "id"; sort by risk in the UI if needed.
    _order = "id"

    # Risk scoring contract (spec 6.7), single source of truth:
    # revenue > 0 and margin < 15 -> 40, overdue AR > 0 -> 30, past due date -> 30
    # level: high >= 70, medium >= 40, low < 40
    RISK_LEVEL_HIGH = 70
    RISK_LEVEL_MEDIUM = 40
    RISK_MARGIN_THRESHOLD = 15

    project_id = fields.Many2one("project.project", string="Project", readonly=True)
    project_name = fields.Char(string="Project Name", readonly=True)
    company_id = fields.Many2one("res.company", string="Company", readonly=True)
    analytic_account_id = fields.Many2one(
        "account.analytic.account", string="Analytic Account", readonly=True
    )
    contract_amount = fields.Float(string="Contract Amount", readonly=True)
    invoiced_amount = fields.Float(string="Invoiced Amount", readonly=True)
    revenue = fields.Float(string="Revenue", readonly=True)
    actual_cost = fields.Float(string="Actual Cost", readonly=True)
    committed_cost = fields.Float(string="Committed Cost", readonly=True)
    uncategorized_amount = fields.Float(string="Uncategorized", readonly=True)
    overdue_ar = fields.Float(string="Overdue AR", readonly=True)
    gross_margin = fields.Float(
        string="Gross Margin",
        compute="_compute_gross_margin",
        store=False,
    )
    has_analytic = fields.Boolean(
        string="Has Analytic Account",
        compute="_compute_has_analytic",
        store=False,
    )
    margin_percent = fields.Float(
        string="Margin %",
        compute="_compute_margin_percent",
        store=False,
    )
    risk_score = fields.Integer(
        string="Risk Score",
        compute="_compute_risk_score",
        store=False,
    )
    risk_level = fields.Selection(
        [
            ("low", "Low"),
            ("medium", "Medium"),
            ("high", "High"),
        ],
        string="Risk Level",
        compute="_compute_risk_level",
        store=False,
    )
    pnl_warning = fields.Char(
        string="P&L Warning",
        compute="_compute_pnl_warning",
        store=False,
    )

    @api.depends("revenue", "actual_cost")
    def _compute_gross_margin(self):
        for rec in self:
            rec.gross_margin = rec.revenue - rec.actual_cost

    @api.depends("analytic_account_id")
    def _compute_has_analytic(self):
        for rec in self:
            rec.has_analytic = bool(rec.analytic_account_id)

    @api.depends("revenue", "actual_cost")
    def _compute_margin_percent(self):
        # Project P&L margin (spec 6.6): (Revenue - Cost) / Revenue * 100
        for rec in self:
            if rec.revenue:
                rec.margin_percent = (rec.revenue - rec.actual_cost) / rec.revenue * 100
            else:
                rec.margin_percent = 0.0

    @api.depends("revenue", "margin_percent", "overdue_ar", "project_id.date")
    def _compute_risk_score(self):
        today = fields.Date.today()
        for rec in self:
            score = 0
            # No recognized revenue yet -> the margin rule is not applicable,
            # otherwise every work-in-progress project would score as risky.
            if rec.revenue and rec.margin_percent < self.RISK_MARGIN_THRESHOLD:
                score += 40
            if rec.overdue_ar > 0:
                score += 30
            project_date = rec.project_id.date if rec.project_id else False
            if project_date and project_date < today:
                score += 30
            rec.risk_score = score

    @api.depends("risk_score")
    def _compute_risk_level(self):
        for rec in self:
            if rec.risk_score >= self.RISK_LEVEL_HIGH:
                rec.risk_level = "high"
            elif rec.risk_score >= self.RISK_LEVEL_MEDIUM:
                rec.risk_level = "medium"
            else:
                rec.risk_level = "low"

    @api.depends("analytic_account_id", "revenue", "uncategorized_amount")
    def _compute_pnl_warning(self):
        for rec in self:
            if not rec.analytic_account_id:
                rec.pnl_warning = _("No analytic account - P&L shows 0.")
            elif not rec.revenue:
                rec.pnl_warning = _("No recognized revenue in the analytic lines yet.")
            elif rec.uncategorized_amount:
                rec.pnl_warning = _("Uncategorized analytic amounts must be reviewed.")
            else:
                rec.pnl_warning = False

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        # project_project.name is a jsonb translated column in Odoo 19; it must
        # be flattened to plain text here, otherwise the dict leaks into the
        # Char field and crashes the web client (VToggler.mount). Same pattern
        # as odoo core report views: current language, then en_US fallback.
        lang = (self.env.lang or "en_US").replace("'", "")
        self.env.cr.execute(
            f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                SELECT
                    p.id AS id,
                    p.id AS project_id,
                    COALESCE(p.name->>'{lang}', p.name->>'en_US') AS project_name,
                    p.company_id AS company_id,
                    p.account_id AS analytic_account_id,
                    COALESCE(so_agg.contract_amount, 0.0) AS contract_amount,
                    COALESCE(ar_agg.invoiced_amount, 0.0) AS invoiced_amount,
                    COALESCE(pnl_agg.revenue, 0.0) AS revenue,
                    COALESCE(pnl_agg.cost, 0.0) AS actual_cost,
                    COALESCE(pnl_agg.uncategorized_amount, 0.0) AS uncategorized_amount,
                    COALESCE(po_agg.committed_cost, 0.0) AS committed_cost,
                    COALESCE(overdue_agg.overdue_ar, 0.0) AS overdue_ar
                FROM project_project p
                LEFT JOIN (
                    SELECT
                        sub.project_id,
                        SUM(sub.amount_untaxed) AS contract_amount
                    FROM (
                        SELECT DISTINCT
                            p2.id AS project_id,
                            so.id,
                            so.amount_untaxed
                        FROM project_project p2
                        JOIN sale_order_line sol
                            ON sol.analytic_distribution ? p2.account_id::text
                        JOIN sale_order so
                            ON so.id = sol.order_id
                            AND so.state IN ('sale', 'done')
                        WHERE p2.account_id IS NOT NULL
                    ) sub
                    GROUP BY sub.project_id
                ) so_agg ON so_agg.project_id = p.id
                LEFT JOIN (
                    SELECT
                        sub.project_id,
                        SUM(sub.amount_untaxed) AS invoiced_amount
                    FROM (
                        SELECT DISTINCT
                            p2.id AS project_id,
                            am.id,
                            am.amount_untaxed
                        FROM project_project p2
                        JOIN account_move_line aml
                            ON aml.analytic_distribution ? p2.account_id::text
                        JOIN account_move am
                            ON am.id = aml.move_id
                            AND am.move_type = 'out_invoice'
                            AND am.state = 'posted'
                        WHERE p2.account_id IS NOT NULL
                    ) sub
                    GROUP BY sub.project_id
                ) ar_agg ON ar_agg.project_id = p.id
                LEFT JOIN (
                    SELECT
                        al.account_id AS analytic_account_id,
                        SUM(CASE WHEN {PROFITABILITY_SQL} = 'revenue' THEN al.amount ELSE 0.0 END) AS revenue,
                        SUM(CASE WHEN {PROFITABILITY_SQL} = 'loss' THEN -al.amount ELSE 0.0 END) AS cost,
                        SUM(CASE WHEN {PROFITABILITY_SQL} = 'uncategorized' THEN al.amount ELSE 0.0 END) AS uncategorized_amount
                    FROM account_analytic_line al
                    JOIN account_move_line aml
                        ON aml.id = al.move_line_id
                    JOIN account_move am
                        ON am.id = aml.move_id
                        AND am.state = 'posted'
                    LEFT JOIN account_account aa
                        ON aa.id = al.general_account_id
                    WHERE al.account_id IS NOT NULL
                    GROUP BY al.account_id
                ) pnl_agg ON pnl_agg.analytic_account_id = p.account_id
                LEFT JOIN (
                    SELECT
                        sub.project_id,
                        SUM(sub.amount_untaxed) AS committed_cost
                    FROM (
                        SELECT DISTINCT
                            p2.id AS project_id,
                            po.id,
                            po.amount_untaxed
                        FROM project_project p2
                        JOIN purchase_order_line pol
                            ON pol.analytic_distribution ? p2.account_id::text
                        JOIN purchase_order po
                            ON po.id = pol.order_id
                            AND po.state IN ('purchase', 'done')
                        WHERE p2.account_id IS NOT NULL
                    ) sub
                    GROUP BY sub.project_id
                ) po_agg ON po_agg.project_id = p.id
                LEFT JOIN (
                    SELECT
                        sub.project_id,
                        SUM(sub.amount_residual) AS overdue_ar
                    FROM (
                        SELECT DISTINCT
                            p2.id AS project_id,
                            am.id,
                            am.amount_residual
                        FROM project_project p2
                        JOIN account_move_line aml
                            ON aml.analytic_distribution ? p2.account_id::text
                        JOIN account_move am
                            ON am.id = aml.move_id
                            AND am.move_type = 'out_invoice'
                            AND am.state = 'posted'
                            AND am.invoice_date_due < CURRENT_DATE
                            AND am.amount_residual > 0
                        WHERE p2.account_id IS NOT NULL
                    ) sub
                    GROUP BY sub.project_id
                ) overdue_agg ON overdue_agg.project_id = p.id
                ORDER BY p.id
            )
            """
        )
