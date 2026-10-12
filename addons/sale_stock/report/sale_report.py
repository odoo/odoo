# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class SaleReport(models.Model):
    _inherit = "sale.report"

    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse', readonly=True)

    def _select_dict(self, table):
        return super()._select_dict(table) | {'warehouse_id': table.order_id.warehouse_id}
