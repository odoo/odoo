# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class PurchaseReport(models.Model):
    _inherit = "purchase.report"

    project_id = fields.Many2one('project.project', 'Project', readonly=True)

    def _select_list(self, table):
        return super()._select_list(table) + [
            table.order_id.project_id,
        ]

    def _groupby_list(self, table):
        return super()._groupby_list(table) + [
            table.order_id.project_id.id,
        ]
