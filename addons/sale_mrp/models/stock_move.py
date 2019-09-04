# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.osv import expression

class StockMove(models.Model):
    _inherit = 'stock.move'

    def _search_picking_for_assignation_domain(self):
        res = []
        if self.sale_line_id and self.created_production_id:
            res.append(('|'))
            res.append(('sale_id', '=', self.sale_line_id.order_id.id))
        res.extend(super(StockMove, self)._search_picking_for_assignation_domain())
        return res
