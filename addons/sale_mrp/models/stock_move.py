# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _create_extra_so_line(self):
        return super(StockMove, self.filtered(lambda m: not m.bom_line_id))._create_extra_so_line()
