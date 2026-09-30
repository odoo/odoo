from odoo import fields, models, tools

class EstateProjectReport(models.Model):
    _name = "estate.project.report"
    _description = "Báo cáo dự án"
    _auto = False

    project_id = fields.Many2one('estate.project', string="Dự án", readonly=True)

    month = fields.Date(string="Tháng")
    purchased_count = fields.Integer(string="Khách đã mua", readonly=True)
    interested_count = fields.Integer(string="Khách quan tâm", readonly=True)
    conversion_rate = fields.Float(string="Tỉ lệ chuyển đổi (%)", readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)

        self.env.cr.execute("""
            CREATE OR REPLACE VIEW estate_project_report AS (
                SELECT
                    p.id AS id,
                    p.id AS project_id,

                    date_trunc('month', p.create_date) AS month,

                    COUNT(DISTINCT pc.customer_id) AS purchased_count,
                    COUNT(DISTINCT ic.customer_id) AS interested_count,

                    CASE 
                        WHEN COUNT(DISTINCT ic.customer_id) = 0 THEN 0
                        ELSE COUNT(DISTINCT pc.customer_id) * 100.0
                            / COUNT(DISTINCT ic.customer_id)
                    END AS conversion_rate

                FROM estate_project p

                LEFT JOIN estate_project_purchased_rel pc
                    ON pc.project_id = p.id

                LEFT JOIN estate_project_interested_rel ic
                    ON ic.project_id = p.id

                GROUP BY
                    p.id,
                    date_trunc('month', p.create_date)
            )
        """)