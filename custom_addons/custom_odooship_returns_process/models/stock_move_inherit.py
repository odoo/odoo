# Part of Odoo. See LICENSE file for full copyright and licensing details.
# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError

class StockMoveLine(models.Model):
    _inherit = "stock.move"


    product_grade = fields.Char(string="Product Grade")
    summary = fields.Char(string='Summary')

    def _merge_moves(self, merge_into=None, **kwargs):
        if self and self[0].picking_id and self[0].picking_id.picking_type_id.picking_process_type == 'returns':
            # No merging for returns: just return moves unchanged
            return self
        return super()._merge_moves(merge_into=merge_into, **kwargs)

