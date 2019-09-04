# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.osv import expression

class StockMove(models.Model):
    _inherit = 'stock.move'

    def _search_picking_for_assignation_domain(self):
        new_dom = []
        flag = False
        if self.sale_line_id and self.created_production_id:
            new_dom = [
                    '|',
                    ('sale_id', '=', self.sale_line_id.order_id.id),
                    ('move_lines.created_production_id', '=',self.created_production_id.id),
            ]
            flag = True

        res = super(StockMove, self.with_context(split_sfp_picking_nofix=flag))._search_picking_for_assignation_domain()
        return expression.AND([new_dom, res])
