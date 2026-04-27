# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    def _without_quality_checks(self):
        self.ensure_one()
        return super()._without_quality_checks() or not self.quality_check_ids.filtered(lambda qc: qc.measure_on != 'move_line')
