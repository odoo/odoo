# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    quality_check_ids = fields.One2many('quality.check', 'move_line_id', string='Check')

    def _without_quality_checks(self):
        self.ensure_one()
        return not self.quality_check_ids

    def write(self, vals):
        res = super().write(vals)
        if 'lot_id' in vals and self.sudo().quality_check_ids:
            self.sudo().quality_check_ids._update_lots()
        return res
