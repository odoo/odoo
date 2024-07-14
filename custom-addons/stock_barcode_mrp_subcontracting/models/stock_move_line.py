#  -*- coding: utf-8 -*-
#  Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    is_subcontract_stock_barcode = fields.Boolean(compute="_compute_is_subcontract_stock_barcode")

    @api.depends('move_id.is_subcontract')
    def _compute_is_subcontract_stock_barcode(self):
        self.is_subcontract_stock_barcode = False
        for move_line in self:
            # Hide if not encoding state or it is not a subcontracting picking
            if move_line.state in ('draft', 'cancel', 'done') or not move_line.move_id.is_subcontract:
                continue
            if (move_line.move_id._subcontrating_should_be_record() or move_line.move_id._subcontrating_can_be_record()):
                move_line.is_subcontract_stock_barcode = True  # == mandatory or facultative

    def _get_fields_stock_barcode(self):
        """ Inject info if the line is subcontract and have tracked component """
        return super()._get_fields_stock_barcode() + ['is_subcontract_stock_barcode']
