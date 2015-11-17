# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models

class StockImmediateTransfer(models.TransientModel):
    _inherit = 'stock.immediate.transfer'

    @api.multi
    def process(self):
        self.ensure_one()
        res = super(StockImmediateTransfer, self).process()
        if self.pick_id.carrier_tracking_ref != False:
            return self.pick_id.open_print_label_url()
        return res
