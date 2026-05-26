from odoo import models, fields, tools


class EmployeeSalesReport(models.Model):
    _name = 'employee.sales.report'
    _description = 'Báo Cáo Sales'
    _auto = False
    _rec_name = 'sales_id'

    sales_id = fields.Many2one(
        'employee.profile.sales',
        string="Sales",
        readonly=True
    )

    date = fields.Date(readonly=True)

    total_received = fields.Integer(readonly=True)

    total_handled = fields.Integer(readonly=True)

    performance = fields.Float(readonly=True)

    def init(self):
        tools.drop_view_if_exists(
            self.env.cr,
            self._table
        )

        self.env.cr.execute(f"""
            CREATE OR REPLACE VIEW employee_sales_report AS (

                SELECT
                    row_number() OVER() as id,

                    rel.sales_id as sales_id,

                    DATE(p.create_date) as date,

                    COUNT(p.id) as total_received,

                    COUNT(
                        CASE
                            WHEN p.status IN (
                                'contacted',
                                'callback'
                            )
                            THEN 1
                        END
                    ) as total_handled,

                    CASE
                        WHEN COUNT(p.id) = 0
                        THEN 0
                        ELSE (
                            COUNT(
                                CASE
                                    WHEN p.status IN (
                                        'contacted',
                                        'callback'
                                    )
                                    THEN 1
                                END
                            )::float
                            /
                            COUNT(p.id)
                        ) * 100
                    END as performance

                FROM sale_phonebook p

                JOIN employee_project_rel rel
                    ON rel.batch_id = p.batch_id

                WHERE p.salesperson_id = rel.sales_id

                GROUP BY
                    rel.sales_id,
                    DATE(p.create_date)

            )
        """)