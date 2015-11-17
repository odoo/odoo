# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class StockBackorderConfirmation(models.TransientModel):
    _inherit = 'stock.backorder.confirmation'

    @api.multi
    def process(self):
        self.ensure_one()
        res = super(StockBackorderConfirmation, self).process()
        if self.pick_id.carrier_tracking_ref != False:
            return self.pick_id.open_print_label_url()
        return res

    @api.multi
    def process_cancel_backorder(self):
        self.ensure_one()
        res = super(StockBackorderConfirmation, self).process_cancel_backorder()
        if self.pick_id.carrier_tracking_ref != False:
            return self.pick_id.open_print_label_url()
        return res
