# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.addons import sale_stock, mrp


class StockMove(mrp.StockMove, sale_stock.StockMove):

    def _prepare_procurement_values(self):
        res = super()._prepare_procurement_values()
        project = self.sale_line_id.order_id.project_id
        if project:
            res['project_id'] = project.id
        return res
