from odoo import fields, models, tools

class EstateProjectUnitReport(models.Model):
    _name = "estate.project.unit.report"
    _description = "Báo cáo sản phẩm dự án"
    _auto = False

    project_id = fields.Many2one("estate.project", string="Dự án")
    state = fields.Selection([
        ('available', 'Còn trống'),
        ('reserved', 'Giữ chỗ'),
        ('sold', 'Đã bán'),
        ('resale', 'Bán lại'),
        ('blocked', 'Khoá')
    ], string="Trạng thái")

    unit_count = fields.Integer(string="Số căn")
    avg_price = fields.Float(string="Giá TB")

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)

        self.env.cr.execute("""
            CREATE OR REPLACE VIEW estate_project_unit_report AS (
                SELECT
                    MIN(u.id) AS id,
                    u.project_id AS project_id,
                    u.state AS state,
                    COUNT(*) AS unit_count,
                    AVG(u.price) AS avg_price
                FROM estate_property_unit u
                GROUP BY u.project_id, u.state
            )
        """)