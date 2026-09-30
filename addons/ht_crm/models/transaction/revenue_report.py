from odoo import fields, models, tools

class RevenueReport(models.Model):
    _name = 'revenue.report'
    _description = 'Revenue By Quarter'
    _auto = False

    quarter= fields.Char(string='Quý')
    month = fields.Integer(string='Tháng')
    
    transaction_count = fields.Integer(
        string='Số giao dịch'
    )

    total_revenue = fields.Monetary(
        string='Doanh thu',
        currency_field='currency_id'
    )

    avg_revenue = fields.Monetary(
        string='Doanh thu trung bình',
        currency_field='currency_id'
    )

    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id
    )

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)

        self.env.cr.execute("""
            CREATE OR REPLACE VIEW revenue_report AS (

                SELECT

                    row_number() OVER () AS id,             

                    CONCAT(
                        EXTRACT(YEAR FROM t.date)::INTEGER,
                        ' / Quý ',
                        TO_CHAR(EXTRACT(QUARTER FROM t.date)::INTEGER, 'RN')
                    ) AS quarter,
                            
                    EXTRACT(MONTH FROM t.date)::INTEGER as month,

                    t.currency_id AS currency_id,

                    CAST(COUNT(t.id) AS INTEGER) AS transaction_count,

                    COALESCE(SUM(t.price_total), 0) AS total_revenue,

                    COALESCE(AVG(t.price_total), 0) AS avg_revenue

                FROM sale_transaction t WHERE t.state = 'deposit'

                GROUP BY
                    quarter,
                    month,
                    t.currency_id
            )
        """)