# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.tools import SQL


class SaleReport(models.Model):
    _inherit = 'sale.report'

    project_id = fields.Many2one(comodel_name='project.project', readonly=True)

    def _get_project_sql(self, table):
        return SQL(
            "COALESCE(%s, %s, %s)",
            table.project_id,
            table.task_id.project_id,
            table.order_id.project_id,
        )

    def _select_dict(self, table):
        return super()._select_dict(table) | {'project_id': self._get_project_sql(table)}

    def _groupby_list(self, table):
        return super()._groupby_list(table) + [self._get_project_sql(table)]
