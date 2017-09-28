# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class StockBackorderConfirmation(models.TransientModel):
    _name = 'stock.backorder.confirmation'
    _description = 'Backorder Confirmation'

    pick_ids = fields.Many2many('stock.picking', 'stock_picking_backorder_rel')

    @api.one
    def _process(self, cancel_backorder=False):
        self.pick_ids.action_done()
        if cancel_backorder:
            for pick_id in self.pick_ids:
                backorder_pick = self.env['stock.picking'].search([('backorder_id', '=', pick_id.id)])
                backorder_pick.action_cancel()
                pick_id.message_post(body=_("Back order <em>%s</em> <b>cancelled</b>.") % (backorder_pick.name))

    def process(self):
        self._process()

    def process_cancel_backorder(self):
        self._process(cancel_backorder=True)
