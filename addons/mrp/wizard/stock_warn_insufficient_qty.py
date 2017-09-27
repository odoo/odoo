# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class StockWarnInsufficientQtyUnbuild(models.TransientModel):
    _name = 'stock.warn.insufficient.qty.unbuild'
    _inherit = 'stock.warn.insufficient.qty'

    unbuild_id = fields.Many2one('mrp.unbuild', 'Unbuild')

    def action_done(self):
        self.ensure_one()
        return self.unbuild_id.action_unbuild()