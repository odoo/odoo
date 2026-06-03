# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools


class ReportPosPayment(models.Model):
    _name = 'report.pos.payment'
    _description = "Point of Sale Payments Report"
    _auto = False
    _order = 'payment_date asc, id asc'

    payment_date = fields.Datetime(string='Payment Date', readonly=True)
    session_id = fields.Many2one('pos.session', string='Session', readonly=True)
    config_id = fields.Many2one('pos.config', string='Point of Sale', readonly=True)
    payment_method_id = fields.Many2one('pos.payment.method', string='Payment Method', readonly=True)
    amount = fields.Float(string='Expected Amount', readonly=True)
    difference = fields.Float(string='Difference', readonly=True)
    counted = fields.Float(string='Counted Amount', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    user_id = fields.Many2one('res.users', string='Employee', readonly=True)
    opening_amount = fields.Float(string='Opening Amount', readonly=True)
    closing_amount = fields.Float(string='Closing Amount', readonly=True)
    cash_in = fields.Float(string='Cash In', readonly=True)
    cash_out = fields.Float(string='Cash Out', readonly=True)
    net_revenue = fields.Float(string='Net Revenue (HT)', readonly=True)

    @api.model
    def _read_group(self, domain, groupby=(), aggregates=(), having=(), offset=0, limit=None, order=None):
        results = super()._read_group(domain, groupby, aggregates, having, offset, limit, order)

        # Force chronological ascending sort when grouping by session (Odoo defaults to descending)
        if groupby and groupby[0] == 'session_id':
            return sorted(results, key=lambda row: row[0].id if row[0] else 0)

        return results

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                WITH base AS (
                    SELECT
                        p.session_id,
                        s.config_id,
                        p.payment_method_id,
                        p.company_id,
                        s.user_id,
                        MIN(p.payment_date) AS payment_date,
                        SUM(p.amount) AS amount,
                        SUM(p.amount * (o.amount_total - o.amount_tax) / COALESCE(NULLIF(o.amount_total, 0.0), 1.0)) AS net_revenue,
                        -- Compute difference once
                        COALESCE(
                            CASE
                                WHEN ppm.is_cash_count = TRUE AND s.state = 'closed' THEN
                                    COALESCE(s.cash_register_balance_end_real, 0.0)
                                    - COALESCE(s.cash_register_balance_start, 0.0)
                                    - COALESCE(s.cash_real_transaction, 0.0)
                                    - SUM(p.amount)
                                WHEN ppm.is_cash_count = TRUE THEN
                                    0.0
                                ELSE (
                                    SELECT COALESCE(SUM(aml.balance), 0.0)
                                    FROM account_move am
                                    JOIN account_move_line aml ON aml.move_id = am.id
                                    WHERE am.ref LIKE '%%%%' || s.name || '%%%%'
                                      AND am.id != s.move_id
                                      AND aml.account_id = ppm.receivable_account_id
                                )
                            END,
                            0.0
                        ) AS difference,
                        COALESCE(
                            CASE
                                WHEN ppm.is_cash_count = TRUE THEN s.cash_register_balance_start
                                ELSE 0.0
                            END,
                            0.0
                        ) AS opening_amount,
                        COALESCE(
                            CASE
                                WHEN ppm.is_cash_count = TRUE THEN s.cash_register_balance_end_real
                                ELSE 0.0
                            END,
                            0.0
                        ) AS closing_amount,
                        COALESCE(
                            CASE
                                WHEN ppm.is_cash_count = TRUE THEN (
                                    SELECT SUM(absl.amount)
                                    FROM account_bank_statement_line absl
                                    WHERE absl.pos_session_id = s.id
                                      AND absl.amount > 0
                                      AND absl.is_reconciled = FALSE
                                      AND absl.payment_ref LIKE s.name || '-%%%%'
                                )
                                ELSE 0.0
                            END,
                            0.0
                        ) AS cash_in,
                        COALESCE(
                            CASE
                                WHEN ppm.is_cash_count = TRUE THEN (
                                    SELECT -SUM(absl.amount)
                                    FROM account_bank_statement_line absl
                                    WHERE absl.pos_session_id = s.id
                                      AND absl.amount < 0
                                      AND absl.is_reconciled = FALSE
                                      AND absl.payment_ref LIKE s.name || '-%%%%'
                                )
                                ELSE 0.0
                            END,
                            0.0
                        ) AS cash_out
                    FROM pos_payment p
                    JOIN pos_session s ON s.id = p.session_id
                    JOIN pos_order o ON o.id = p.pos_order_id
                    JOIN pos_payment_method ppm ON ppm.id = p.payment_method_id
                    WHERE o.state IN ('paid', 'done', 'invoiced')
                    GROUP BY
                        p.session_id,
                        s.config_id,
                        p.payment_method_id,
                        p.company_id,
                        s.user_id,
                        ppm.is_cash_count,
                        s.cash_register_balance_end_real,
                        s.cash_register_balance_start,
                        s.cash_real_transaction,
                        s.state,
                        s.move_id,
                        s.name,
                        ppm.receivable_account_id,
                        s.id
                )
                SELECT
                    ROW_NUMBER() OVER () AS id,
                    b.payment_date,
                    b.session_id,
                    b.config_id,
                    b.payment_method_id,
                    b.amount,
                    b.company_id,
                    b.user_id,
                    b.difference,
                    b.amount + b.difference AS counted,
                    b.opening_amount,
                    b.closing_amount,
                    b.cash_in,
                    b.cash_out,
                    b.net_revenue
                FROM base b
            )
        """ % self._table)
