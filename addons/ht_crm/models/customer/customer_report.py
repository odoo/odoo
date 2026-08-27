from odoo import fields, models, tools


class CustomerReport(models.Model):
    _name = 'sale.customer.report'
    _description = 'Customer Report'
    _auto = False

    type = fields.Selection([
        ('individual', 'Cá nhân'),
        ('broker', 'Môi giới'),
        ('investor', 'Nhà đầu tư'),
        ('company', 'Doanh nghiệp'),
    ], string="Phân loại khách")

    status = fields.Selection([
        ('new', 'Khách mới'),
        ('active', 'Đang tương tác'),
        ('inactive', 'Không còn tương tác'),
        ('blacklist', 'Blacklist'),
    ], default='new', string="Trạng thái")

    tier = fields.Selection([
        ('normal', 'Thông thường'),
        ('vip', 'Thân thiết'),
    ], default='normal', string="Phân hạng")

    customer_count = fields.Integer(string="Số khách hàng")

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)

        self.env.cr.execute("""
            CREATE OR REPLACE VIEW sale_customer_report AS (

                SELECT
                    row_number() OVER () AS id,

                    c.status AS status,
                    c.tier AS tier,
                    c.type AS type,

                    COUNT(c.id) AS customer_count

                FROM sale_customer c

                GROUP BY
                    c.status,
                    c.tier,
                    c.type
            )
        """)