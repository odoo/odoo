from odoo import models, fields
from odoo.tools import SQL


class ReportPosOrder(models.Model):
    _inherit = "report.pos.order"
    employee_id = fields.Many2one('hr.employee', string='Employee', readonly=True)

    def _select(self):
        return SQL('%s,s.employee_id AS employee_id', super()._select())

    def _group_by(self):
        return SQL('%s,s.employee_id', super()._group_by())
