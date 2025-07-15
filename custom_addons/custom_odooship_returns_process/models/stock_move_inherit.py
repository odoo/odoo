# Part of Odoo. See LICENSE file for full copyright and licensing details.
# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError

class StockMoveLine(models.Model):
    _inherit = "stock.move"


    product_grade = fields.Char(string="Product Grade")
    summary = fields.Char(string='Summary')
    line_number = fields.Integer(
        string='Line Number',
        index=True,
        readonly=True,
        copy=False
    )

    @api.model
    def create(self, vals_list):
        # Odoo allows both dict (single) and list-of-dicts (multi) in create
        if isinstance(vals_list, dict):
            vals_list = [vals_list]

        all_pickings = set(v.get('picking_id') for v in vals_list if v.get('picking_id'))
        picking_numbers = {}

        for picking_id in all_pickings:
            if picking_id:
                # Find max current line number for this picking
                max_number = self.search(
                    [('picking_id', '=', picking_id)],
                    order="line_number desc",
                    limit=1
                ).line_number or 0
                picking_numbers[picking_id] = max_number

        for vals in vals_list:
            picking_id = vals.get('picking_id')
            if picking_id:
                picking_numbers[picking_id] += 1
                vals['line_number'] = picking_numbers[picking_id]
            else:
                # If no picking_id on create, don't assign
                vals['line_number'] = 0

        records = super(StockMoveLine, self).create(vals_list)
        # If the API called with a single dict, return record not recordset
        return records if len(records) > 1 else records[0]

    def _merge_moves(self, merge_into=None, **kwargs):
        if self and self[0].picking_id and self[0].picking_id.picking_type_id.picking_process_type == 'returns':
            # No merging for returns: just return moves unchanged
            return self
        return super()._merge_moves(merge_into=merge_into, **kwargs)

